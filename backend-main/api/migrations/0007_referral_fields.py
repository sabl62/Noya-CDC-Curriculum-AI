from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0006_user_billing_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='referral_code',
            field=models.CharField(blank=True, db_index=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='user',
            name='referred_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='referrals', to='api.user'),
        ),
    ]
