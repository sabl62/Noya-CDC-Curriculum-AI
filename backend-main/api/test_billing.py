import base64
import hashlib
import hmac
import json
import os
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Payment, User
from .payment_gateways import EsewaGateway, PaymentGatewayError


def esewa_expected_signature(message: str, secret: str) -> str:
    return base64.b64encode(
        hmac.new(secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).digest()
    ).decode('utf-8')


class EsewaSignatureTests(TestCase):
    def test_sign_matches_independent_hmac_sha256(self):
        secret = '8gBm/:&EnhH.1/q'
        message = 'total_amount=799,transaction_uuid=NOYA-1-ABCDEF,product_code=EPAYTEST'
        self.assertEqual(
            EsewaGateway.sign(
                total_amount=799,
                transaction_uuid='NOYA-1-ABCDEF',
                product_code='EPAYTEST',
                secret_key=secret,
            ),
            esewa_expected_signature(message, secret),
        )

    def test_amount_is_formatted_consistently(self):
        secret = '8gBm/:&EnhH.1/q'
        message = 'total_amount=799.5,transaction_uuid=X,product_code=EPAYTEST'
        self.assertEqual(
            EsewaGateway.sign(
                total_amount=799.50,
                transaction_uuid='X',
                product_code='EPAYTEST',
                secret_key=secret,
            ),
            esewa_expected_signature(message, secret),
        )

    def test_build_form_returns_all_required_fields(self):
        form = EsewaGateway.build_payment_form(
            amount=799,
            transaction_uuid='NOYA-1-ABCDEF',
            success_url='http://localhost:5173/billing',
            failure_url='http://localhost:5173/billing',
        )
        fields = form['fields']
        for key in (
            'amount', 'tax_amount', 'total_amount', 'transaction_uuid', 'product_code',
            'product_service_charge', 'product_delivery_charge', 'success_url',
            'failure_url', 'signed_field_names', 'signature',
        ):
            self.assertIn(key, fields)
        self.assertEqual(fields['signed_field_names'], 'total_amount,transaction_uuid,product_code')
        self.assertEqual(
            fields['signature'],
            esewa_expected_signature(
                f"total_amount={fields['total_amount']},"
                f"transaction_uuid={fields['transaction_uuid']},"
                f"product_code={fields['product_code']}",
                EsewaGateway.secret_key(),
            ),
        )

    def test_callback_payload_is_decoded_from_base64(self):
        payload = {'status': 'COMPLETE', 'transaction_uuid': 'NOYA-1-ABCDEF', 'total_amount': '799.0'}
        encoded = base64.b64encode(json.dumps(payload).encode()).decode()
        self.assertEqual(EsewaGateway.decode_callback(encoded), payload)

    def test_invalid_callback_raises(self):
        with self.assertRaises(PaymentGatewayError):
            EsewaGateway.decode_callback('not-valid-base64-json!!!')


class BillingCheckoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='payer', password='pw')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_plans_expose_all_providers(self):
        res = self.client.get('/api/billing/plans/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual([p['id'] for p in data['providers']], ['esewa', 'khalti', 'stripe'])
        self.assertTrue(data['providers'][0]['enabled'])  # eSewa sandbox works out of the box
        self.assertEqual(data['currency'], 'NPR')

    def test_esewa_checkout_creates_payment_with_signed_form(self):
        res = self.client.post('/api/billing/checkout/', {'plan': 'pro', 'provider': 'esewa'}, format='json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['provider'], 'esewa')
        self.assertEqual(data['method'], 'post')
        self.assertTrue(data['checkout_url'].startswith('https://'))

        payment = Payment.objects.get(reference=data['reference'])
        self.assertEqual(payment.user, self.user)
        self.assertEqual(payment.provider, 'esewa')
        self.assertEqual(payment.status, 'initiated')
        self.assertEqual(float(payment.amount), 799.0)

        fields = data['form_fields']
        self.assertEqual(fields['transaction_uuid'], payment.reference)
        expected = esewa_expected_signature(
            f"total_amount={fields['total_amount']},"
            f"transaction_uuid={fields['transaction_uuid']},"
            f"product_code={fields['product_code']}",
            EsewaGateway.secret_key(),
        )
        self.assertEqual(fields['signature'], expected)

    def test_khalti_checkout_stores_pidx(self):
        env = {'KHALTI_PUBLIC_KEY': 'test_public_key', 'KHALTI_SECRET_KEY': 'test_secret_key'}
        with patch.dict(os.environ, env), patch('api.views.KhaltiGateway.initiate') as initiate:
            initiate.return_value = {
                'pidx': 'PXID123ABC',
                'payment_url': 'https://test-pay.khalti.com/?pidx=PXID123ABC',
                'raw': {'pidx': 'PXID123ABC'},
            }
            res = self.client.post('/api/billing/checkout/', {'plan': 'pro', 'provider': 'khalti'}, format='json')

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['provider'], 'khalti')
        self.assertEqual(data['checkout_url'], 'https://test-pay.khalti.com/?pidx=PXID123ABC')
        self.assertEqual(data['reference'], 'PXID123ABC')
        self.assertEqual(initiate.call_args.kwargs['amount_paisa'], 79900)

        payment = Payment.objects.get(user=self.user, provider='khalti')
        self.assertEqual(payment.provider_reference, 'PXID123ABC')
        self.assertEqual(payment.status, 'pending')

    def test_unconfigured_provider_is_rejected(self):
        with patch.dict(os.environ, {'KHALTI_PUBLIC_KEY': '', 'KHALTI_SECRET_KEY': ''}):
            res = self.client.post('/api/billing/checkout/', {'plan': 'pro', 'provider': 'khalti'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('not configured', res.json()['error'])

    def test_unknown_plan_is_rejected(self):
        res = self.client.post('/api/billing/checkout/', {'plan': 'enterprise', 'provider': 'esewa'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_checkout_requires_auth(self):
        anon = APIClient()
        res = anon.post('/api/billing/checkout/', {'plan': 'pro', 'provider': 'esewa'}, format='json')
        self.assertIn(res.status_code, (401, 403))


class BillingVerifyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='verifier', password='pw')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.payment = Payment.objects.create(
            user=self.user,
            plan='pro',
            provider='esewa',
            amount=Decimal('799.00'),
            currency='NPR',
            reference='NOYA-9-ABCDEF0123456789',
            provider_reference='NOYA-9-ABCDEF0123456789',
            status='initiated',
        )

    @patch('api.views.EsewaGateway.check_status')
    def test_completed_payment_activates_pro_for_a_year(self, check_status):
        check_status.return_value = {
            'status': 'COMPLETE',
            'ref_id': '0001TS9',
            'raw': {'total_amount': 799.0, 'status': 'COMPLETE'},
        }
        res = self.client.post(
            '/api/billing/verify/',
            {'provider': 'esewa', 'reference': self.payment.reference},
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'completed')
        self.assertEqual(data['plan_tier'], 'paid')

        self.user.refresh_from_db()
        self.assertEqual(self.user.plan_tier, 'paid')
        self.assertEqual(self.user.billing_provider, 'esewa')
        self.assertEqual(self.user.billing_status, 'active')
        self.assertIsNotNone(self.user.billing_expires_at)
        self.assertAlmostEqual(
            (self.user.billing_expires_at - timezone.now()).days, 365, delta=1,
        )

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'completed')
        self.assertEqual(self.payment.provider_transaction_id, '0001TS9')

    @patch('api.views.EsewaGateway.check_status')
    def test_pending_payment_does_not_activate_pro(self, check_status):
        check_status.return_value = {'status': 'PENDING', 'ref_id': None, 'raw': {'status': 'PENDING'}}
        res = self.client.post(
            '/api/billing/verify/',
            {'provider': 'esewa', 'reference': self.payment.reference},
            format='json',
        )
        self.assertEqual(res.json()['status'], 'pending')
        self.user.refresh_from_db()
        self.assertEqual(self.user.plan_tier, 'free')

    @patch('api.views.EsewaGateway.check_status')
    def test_amount_mismatch_is_treated_as_failed(self, check_status):
        check_status.return_value = {
            'status': 'COMPLETE',
            'ref_id': '0001TS9',
            'raw': {'total_amount': 10.0, 'status': 'COMPLETE'},
        }
        res = self.client.post(
            '/api/billing/verify/',
            {'provider': 'esewa', 'reference': self.payment.reference},
            format='json',
        )
        self.assertEqual(res.json()['status'], 'failed')
        self.user.refresh_from_db()
        self.assertEqual(self.user.plan_tier, 'free')

    @patch('api.views.EsewaGateway.check_status')
    def test_esewa_callback_data_is_decoded(self, check_status):
        check_status.return_value = {
            'status': 'COMPLETE',
            'ref_id': '0001TS9',
            'raw': {'total_amount': 799.0},
        }
        encoded = base64.b64encode(json.dumps({
            'status': 'COMPLETE',
            'transaction_uuid': self.payment.reference,
            'total_amount': '799.0',
        }).encode()).decode()
        res = self.client.post('/api/billing/verify/', {'data': encoded}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['status'], 'completed')

    @patch('api.views.KhaltiGateway.lookup')
    def test_khalti_completed_lookup_activates_pro(self, lookup):
        lookup.return_value = {
            'status': 'completed',
            'gateway_status': 'Completed',
            'total_amount': 79900,
            'transaction_id': 'GFKHALTI123',
            'refunded': False,
            'raw': {'status': 'Completed', 'total_amount': 79900},
        }
        self.payment.provider = 'khalti'
        self.payment.provider_reference = 'PXID123ABC'
        self.payment.save(update_fields=['provider', 'provider_reference'])

        res = self.client.post(
            '/api/billing/verify/',
            {'provider': 'khalti', 'reference': 'PXID123ABC'},
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['status'], 'completed')
        self.user.refresh_from_db()
        self.assertEqual(self.user.plan_tier, 'paid')
        lookup.assert_called_once_with('PXID123ABC')

    def test_verification_is_idempotent(self):
        self.payment.status = 'completed'
        self.payment.save(update_fields=['status'])
        with patch('api.views.EsewaGateway.check_status') as check_status:
            res = self.client.post(
                '/api/billing/verify/',
                {'provider': 'esewa', 'reference': self.payment.reference},
                format='json',
            )
        check_status.assert_not_called()
        self.assertEqual(res.json()['status'], 'completed')

    def test_foreign_payment_cannot_be_verified(self):
        other = User.objects.create_user(username='stranger', password='pw')
        Payment.objects.create(
            user=other,
            plan='pro',
            provider='esewa',
            amount=Decimal('799.00'),
            reference='NOYA-6-FEE1234567890ABC',
            provider_reference='NOYA-6-FEE1234567890ABC',
        )
        res = self.client.post(
            '/api/billing/verify/',
            {'provider': 'esewa', 'reference': 'NOYA-6-FEE1234567890ABC'},
            format='json',
        )
        self.assertEqual(res.status_code, 404)

    def test_provider_mismatch_is_rejected(self):
        res = self.client.post(
            '/api/billing/verify/',
            {'provider': 'khalti', 'reference': self.payment.reference},
            format='json',
        )
        self.assertEqual(res.status_code, 400)

    def test_missing_reference_is_rejected(self):
        res = self.client.post('/api/billing/verify/', {}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_status_endpoint_lists_payments(self):
        res = self.client.get('/api/billing/status/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['plan_tier'], 'free')
        self.assertEqual(len(data['payments']), 1)
        self.assertEqual(data['payments'][0]['reference'], self.payment.reference)
