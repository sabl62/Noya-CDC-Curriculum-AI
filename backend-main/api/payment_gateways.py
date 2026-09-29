"""Payment gateway SDK clients for Noya billing.

Thin, self-contained clients around the two Nepali gateways this app supports:

* eSewa ePay v2  — https://developer.esewa.com.np/pages/Epay-V2
  Signed form redirect (HMAC-SHA256) + server-side transaction status lookup.
* Khalti KPG     — https://docs.khalti.com/khalti-epayment/
  JSON initiate (`pidx` + `payment_url`) + server-side lookup confirmation.

Both gateways are configured through environment variables (see .env.example),
so sandbox works out of the box and flipping one variable switches to live.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os

import httpx


class PaymentGatewayError(Exception):
    """Raised when a gateway rejects a request or replies with an error."""


def _env(name: str, default: str = '') -> str:
    return os.getenv(name, default).strip()


def _amount_str(value) -> str:
    """Format an amount exactly the way it is signed and sent."""
    text = f"{float(value):.2f}".rstrip('0').rstrip('.')
    return text or '0'


def _error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            return str(payload.get('detail') or payload.get('error') or payload)
    except Exception:
        pass
    return (response.text or '')[:300]


class EsewaGateway:
    """eSewa ePay v2 (form redirect checkout + transaction status API)."""

    SANDBOX_FORM_URL = 'https://rc-epay.esewa.com.np/api/epay/main/v2/form'
    PRODUCTION_FORM_URL = 'https://epay.esewa.com.np/api/epay/main/v2/form'
    SANDBOX_STATUS_URL = 'https://rc.esewa.com.np/api/epay/transaction/status/'
    PRODUCTION_STATUS_URL = 'https://esewa.com.np/api/epay/transaction/status/'

    # Public UAT credentials published by eSewa for the sandbox environment.
    SANDBOX_PRODUCT_CODE = 'EPAYTEST'
    SANDBOX_SECRET_KEY = '8gBm/:&EnhH.1/q'

    SIGNED_FIELD_NAMES = 'total_amount,transaction_uuid,product_code'

    @classmethod
    def is_production(cls) -> bool:
        return _env('ESEWA_MODE', 'sandbox').lower() in {'production', 'live', 'prod'}

    @classmethod
    def product_code(cls) -> str:
        return _env('ESEWA_PRODUCT_CODE') or ('' if cls.is_production() else cls.SANDBOX_PRODUCT_CODE)

    @classmethod
    def secret_key(cls) -> str:
        return _env('ESEWA_SECRET_KEY') or ('' if cls.is_production() else cls.SANDBOX_SECRET_KEY)

    @classmethod
    def is_configured(cls) -> bool:
        return bool(cls.product_code() and cls.secret_key())

    @classmethod
    def form_url(cls) -> str:
        return _env('ESEWA_FORM_URL') or (
            cls.PRODUCTION_FORM_URL if cls.is_production() else cls.SANDBOX_FORM_URL
        )

    @classmethod
    def status_url(cls) -> str:
        return _env('ESEWA_STATUS_URL') or (
            cls.PRODUCTION_STATUS_URL if cls.is_production() else cls.SANDBOX_STATUS_URL
        )

    @classmethod
    def sign(cls, *, total_amount, transaction_uuid, product_code, secret_key) -> str:
        """HMAC-SHA256 over the ordered signed fields, base64 encoded."""
        message = (
            f"total_amount={_amount_str(total_amount)},"
            f"transaction_uuid={transaction_uuid},"
            f"product_code={product_code}"
        )
        digest = hmac.new(
            secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(digest).decode('utf-8')

    @classmethod
    def build_payment_form(
        cls,
        *,
        amount,
        transaction_uuid: str,
        success_url: str,
        failure_url: str,
        tax_amount=0,
    ) -> dict:
        """Build the auto-submitting form payload that starts an eSewa payment."""
        if not cls.is_configured():
            raise PaymentGatewayError(
                'eSewa is not configured. Set ESEWA_PRODUCT_CODE and ESEWA_SECRET_KEY.'
            )

        product_code = cls.product_code()
        secret_key = cls.secret_key()
        total_amount = float(amount) + float(tax_amount)

        fields = {
            'amount': _amount_str(amount),
            'tax_amount': _amount_str(tax_amount),
            'total_amount': _amount_str(total_amount),
            'transaction_uuid': transaction_uuid,
            'product_code': product_code,
            'product_service_charge': '0',
            'product_delivery_charge': '0',
            'success_url': success_url,
            'failure_url': failure_url,
            'signed_field_names': cls.SIGNED_FIELD_NAMES,
            'signature': cls.sign(
                total_amount=total_amount,
                transaction_uuid=transaction_uuid,
                product_code=product_code,
                secret_key=secret_key,
            ),
        }
        return {
            'action': cls.form_url(),
            'fields': fields,
        }

    @classmethod
    def decode_callback(cls, data_b64: str) -> dict:
        """Decode the base64 JSON blob eSewa appends to the success/failure URL."""
        try:
            padded = data_b64 + '=' * (-len(data_b64) % 4)
            payload = json.loads(base64.b64decode(padded).decode('utf-8'))
        except Exception as exc:
            raise PaymentGatewayError('Invalid eSewa callback payload.') from exc
        if not isinstance(payload, dict):
            raise PaymentGatewayError('Invalid eSewa callback payload.')
        return payload

    @classmethod
    def check_status(cls, *, transaction_uuid: str, total_amount) -> dict:
        """Authoritative server-to-server status lookup (never trust the redirect)."""
        if not cls.is_configured():
            raise PaymentGatewayError(
                'eSewa is not configured. Set ESEWA_PRODUCT_CODE and ESEWA_SECRET_KEY.'
            )

        url = cls.status_url()
        try:
            response = httpx.get(
                url,
                params={
                    'product_code': cls.product_code(),
                    'total_amount': _amount_str(total_amount),
                    'transaction_uuid': transaction_uuid,
                },
                timeout=20,
            )
        except httpx.HTTPError as exc:
            raise PaymentGatewayError(f'eSewa status check failed: {exc}') from exc

        if response.status_code != 200:
            raise PaymentGatewayError(
                f'eSewa status check failed (HTTP {response.status_code}): {_error_detail(response)}'
            )

        try:
            data = response.json()
        except Exception as exc:
            raise PaymentGatewayError('eSewa status check returned an unreadable response.') from exc

        if not isinstance(data, dict) or 'status' not in data:
            raise PaymentGatewayError('eSewa could not find that transaction.')

        return {
            'status': str(data.get('status') or '').upper(),
            'ref_id': str(data.get('ref_id') or ''),
            'raw': data,
        }


class KhaltiGateway:
    """Khalti ePayment web checkout (KPG-2): initiate + lookup."""

    SANDBOX_BASE_URL = 'https://test-api.khalti.com/api/v2'
    PRODUCTION_BASE_URL = 'https://api.khalti.com/api/v2'

    @classmethod
    def is_production(cls) -> bool:
        return _env('KHALTI_MODE', 'sandbox').lower() in {'production', 'live', 'prod'}

    @classmethod
    def base_url(cls) -> str:
        return _env('KHALTI_BASE_URL') or (
            cls.PRODUCTION_BASE_URL if cls.is_production() else cls.SANDBOX_BASE_URL
        )

    @classmethod
    def public_key(cls) -> str:
        return _env('KHALTI_PUBLIC_KEY')

    @classmethod
    def secret_key(cls) -> str:
        return _env('KHALTI_SECRET_KEY')

    @classmethod
    def is_configured(cls) -> bool:
        return bool(cls.public_key() and cls.secret_key())

    @classmethod
    def _headers(cls, key: str) -> dict:
        return {'Authorization': f'Key {key}', 'Content-Type': 'application/json'}

    @classmethod
    def initiate(
        cls,
        *,
        amount_paisa: int,
        return_url: str,
        website_url: str,
        purchase_order_id: str,
        purchase_order_name: str,
        customer_info: str = '',
        product_details: list | None = None,
    ) -> dict:
        """Start a checkout; returns ``pidx`` and the hosted ``payment_url``."""
        if not cls.is_configured():
            raise PaymentGatewayError(
                'Khalti is not configured. Set KHALTI_PUBLIC_KEY and KHALTI_SECRET_KEY.'
            )

        payload = {
            'return_url': return_url,
            'website_url': website_url,
            'amount': int(amount_paisa),
            'purchase_order_id': purchase_order_id,
            'purchase_order_name': purchase_order_name,
        }
        if customer_info:
            payload['customer_info'] = customer_info
        if product_details:
            payload['product_details'] = product_details

        try:
            response = httpx.post(
                f"{cls.base_url()}/epayment/initiate/",
                json=payload,
                headers=cls._headers(cls.public_key()),
                timeout=20,
            )
        except httpx.HTTPError as exc:
            raise PaymentGatewayError(f'Khalti initiate failed: {exc}') from exc

        if response.status_code not in (200, 201):
            raise PaymentGatewayError(
                f'Khalti initiate failed (HTTP {response.status_code}): {_error_detail(response)}'
            )

        data = response.json()
        if not isinstance(data, dict) or not data.get('pidx') or not data.get('payment_url'):
            raise PaymentGatewayError('Khalti initiate returned an unexpected response.')

        return {
            'pidx': str(data.get('pidx')),
            'payment_url': str(data.get('payment_url')),
            'expires_at': data.get('expires_at'),
            'expires_in': data.get('expires_in'),
            'raw': data,
        }

    @classmethod
    def lookup(cls, pidx: str) -> dict:
        """Confirm a payment with Khalti's lookup API (the source of truth)."""
        if not cls.is_configured():
            raise PaymentGatewayError(
                'Khalti is not configured. Set KHALTI_PUBLIC_KEY and KHALTI_SECRET_KEY.'
            )

        try:
            response = httpx.post(
                f"{cls.base_url()}/epayment/lookup/",
                json={'pidx': pidx},
                headers=cls._headers(cls.secret_key()),
                timeout=20,
            )
        except httpx.HTTPError as exc:
            raise PaymentGatewayError(f'Khalti lookup failed: {exc}') from exc

        if response.status_code != 200:
            raise PaymentGatewayError(
                f'Khalti lookup failed (HTTP {response.status_code}): {_error_detail(response)}'
            )

        data = response.json()
        if not isinstance(data, dict) or 'status' not in data:
            raise PaymentGatewayError('Khalti could not find that payment.')

        raw_status = str(data.get('status') or '')
        status_map = {
            'Completed': 'completed',
            'Pending': 'pending',
            'Initiated': 'pending',
            'Expired': 'expired',
            'User canceled': 'failed',
            'Refunded': 'refunded',
            'Partially refunded': 'refunded',
        }

        return {
            'status': status_map.get(raw_status, 'pending'),
            'gateway_status': raw_status,
            'total_amount': data.get('total_amount'),
            'transaction_id': str(data.get('transaction_id') or ''),
            'refunded': bool(data.get('refunded')),
            'raw': data,
        }
