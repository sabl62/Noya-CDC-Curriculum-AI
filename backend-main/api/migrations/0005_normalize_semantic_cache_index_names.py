# Generated for stable semantic cache index names

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_semantic_cache'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='cachelookupevent',
            new_name='api_cachelo_created_5d0e1e_idx',
            old_name='api_cachelo_created_b0e631_idx',
        ),
        migrations.RenameIndex(
            model_name='cachelookupevent',
            new_name='api_cachelo_plan_ti_4ea0b0_idx',
            old_name='api_cachelo_plan_ti_f5f587_idx',
        ),
        migrations.RenameIndex(
            model_name='knowledgebaseentry',
            new_name='api_knowled_grade_3b098b_idx',
            old_name='api_knowled_grade_5c5b24_idx',
        ),
        migrations.RenameIndex(
            model_name='knowledgebaseentry',
            new_name='api_knowled_subject_44151e_idx',
            old_name='api_knowled_subject_98eec9_idx',
        ),
        migrations.RenameIndex(
            model_name='knowledgebaseentry',
            new_name='api_knowled_query_f_164792_idx',
            old_name='api_knowled_query_f_b13e2a_idx',
        ),
        migrations.RenameIndex(
            model_name='semanticanswercache',
            new_name='api_semanti_grade_551a87_idx',
            old_name='api_semanti_grade_5bbef1_idx',
        ),
        migrations.RenameIndex(
            model_name='semanticanswercache',
            new_name='api_semanti_subject_687f32_idx',
            old_name='api_semanti_subject_e23fb6_idx',
        ),
        migrations.RenameIndex(
            model_name='semanticanswercache',
            new_name='api_semanti_query_f_590f24_idx',
            old_name='api_semanti_query_f_37b327_idx',
        ),
    ]
