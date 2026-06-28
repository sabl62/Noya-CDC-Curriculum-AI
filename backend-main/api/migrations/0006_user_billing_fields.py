from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_normalize_semantic_cache_index_names'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='billing_customer_id',
            field=models.CharField(blank=True, db_index=True, default='', max_length=128),
        ),
        migrations.AddField(
            model_name='user',
            name='billing_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='billing_provider',
            field=models.CharField(blank=True, default='', max_length=40),
        ),
        migrations.AddField(
            model_name='user',
            name='billing_status',
            field=models.CharField(blank=True, db_index=True, default='inactive', max_length=32),
        ),
        migrations.AddField(
            model_name='user',
            name='billing_subscription_id',
            field=models.CharField(blank=True, db_index=True, default='', max_length=128),
        ),
    ]