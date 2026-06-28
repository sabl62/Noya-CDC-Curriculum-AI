# Generated for Noya semantic educational cache

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_remove_examattempt_exam_remove_examattempt_user_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='plan_tier',
            field=models.CharField(choices=[('free', 'Free'), ('paid', 'Paid')], default='free', max_length=20),
        ),
        migrations.CreateModel(
            name='KnowledgeBaseEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject', models.CharField(db_index=True, max_length=50)),
                ('grade', models.CharField(db_index=True, default='10', max_length=10)),
                ('unit', models.CharField(blank=True, db_index=True, default='', max_length=50)),
                ('chapter', models.CharField(blank=True, db_index=True, default='', max_length=50)),
                ('chapter_title', models.CharField(blank=True, default='', max_length=255)),
                ('topic', models.CharField(blank=True, db_index=True, default='', max_length=255)),
                ('learning_objective', models.CharField(blank=True, default='', max_length=255)),
                ('question_type', models.CharField(choices=[('explain', 'Explain'), ('definition', 'Definition'), ('exam_notes', 'Exam Notes'), ('important_questions', 'Important Questions'), ('summary', 'Summary'), ('quiz', 'Quiz'), ('solved_exercise', 'Solved Exercise'), ('derivation', 'Derivation'), ('formula', 'Formula'), ('page_explanation', 'Page Explanation'), ('faq', 'FAQ'), ('general', 'General')], db_index=True, default='general', max_length=40)),
                ('difficulty', models.CharField(blank=True, db_index=True, default='easy', max_length=30)),
                ('intent', models.CharField(blank=True, db_index=True, default='', max_length=80)),
                ('normalized_query', models.TextField(blank=True, default='')),
                ('query_fingerprint', models.CharField(blank=True, db_index=True, default='', max_length=64)),
                ('embedding', models.JSONField(blank=True, default=list)),
                ('answer', models.TextField()),
                ('source_type', models.CharField(choices=[('precomputed', 'Precomputed'), ('semantic_cache', 'Semantic Cache'), ('rag', 'RAG'), ('ai_generated', 'AI Generated'), ('manual', 'Manual')], db_index=True, default='semantic_cache', max_length=40)),
                ('source_reference', models.CharField(blank=True, default='', max_length=255)),
                ('quality_score', models.FloatField(db_index=True, default=0.0)),
                ('student_feedback_score', models.FloatField(default=0.0)),
                ('textbook_alignment_score', models.FloatField(default=0.0)),
                ('hallucination_risk_score', models.FloatField(default=0.0)),
                ('usage_count', models.PositiveIntegerField(db_index=True, default=0)),
                ('hit_count', models.PositiveIntegerField(default=0)),
                ('last_verified_at', models.DateTimeField(blank=True, null=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name_plural': 'Knowledge base entries',
                'indexes': [
                    models.Index(fields=['grade', 'subject', 'unit', 'chapter', 'question_type'], name='api_knowled_grade_5c5b24_idx'),
                    models.Index(fields=['subject', 'intent', 'quality_score'], name='api_knowled_subject_98eec9_idx'),
                    models.Index(fields=['query_fingerprint', 'is_active'], name='api_knowled_query_f_b13e2a_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='SemanticAnswerCache',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject', models.CharField(db_index=True, max_length=50)),
                ('grade', models.CharField(db_index=True, default='10', max_length=10)),
                ('unit', models.CharField(blank=True, db_index=True, default='', max_length=50)),
                ('chapter', models.CharField(blank=True, db_index=True, default='', max_length=50)),
                ('chapter_title', models.CharField(blank=True, default='', max_length=255)),
                ('topic', models.CharField(blank=True, db_index=True, default='', max_length=255)),
                ('learning_objective', models.CharField(blank=True, default='', max_length=255)),
                ('question_type', models.CharField(choices=[('explain', 'Explain'), ('definition', 'Definition'), ('exam_notes', 'Exam Notes'), ('important_questions', 'Important Questions'), ('summary', 'Summary'), ('quiz', 'Quiz'), ('solved_exercise', 'Solved Exercise'), ('derivation', 'Derivation'), ('formula', 'Formula'), ('page_explanation', 'Page Explanation'), ('faq', 'FAQ'), ('general', 'General')], db_index=True, default='general', max_length=40)),
                ('difficulty', models.CharField(blank=True, db_index=True, default='easy', max_length=30)),
                ('intent', models.CharField(blank=True, db_index=True, default='', max_length=80)),
                ('normalized_query', models.TextField(blank=True, default='')),
                ('query_fingerprint', models.CharField(blank=True, db_index=True, default='', max_length=64)),
                ('embedding', models.JSONField(blank=True, default=list)),
                ('answer', models.TextField()),
                ('source_type', models.CharField(choices=[('precomputed', 'Precomputed'), ('semantic_cache', 'Semantic Cache'), ('rag', 'RAG'), ('ai_generated', 'AI Generated'), ('manual', 'Manual')], db_index=True, default='semantic_cache', max_length=40)),
                ('source_reference', models.CharField(blank=True, default='', max_length=255)),
                ('quality_score', models.FloatField(db_index=True, default=0.0)),
                ('student_feedback_score', models.FloatField(default=0.0)),
                ('textbook_alignment_score', models.FloatField(default=0.0)),
                ('hallucination_risk_score', models.FloatField(default=0.0)),
                ('usage_count', models.PositiveIntegerField(db_index=True, default=0)),
                ('hit_count', models.PositiveIntegerField(default=0)),
                ('last_verified_at', models.DateTimeField(blank=True, null=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_from_model', models.CharField(blank=True, default='', max_length=100)),
            ],
            options={
                'verbose_name_plural': 'Semantic answer cache',
                'indexes': [
                    models.Index(fields=['grade', 'subject', 'unit', 'chapter', 'question_type'], name='api_semanti_grade_5bbef1_idx'),
                    models.Index(fields=['subject', 'intent', 'quality_score'], name='api_semanti_subject_e23fb6_idx'),
                    models.Index(fields=['query_fingerprint', 'is_active'], name='api_semanti_query_f_37b327_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='CacheLookupEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField()),
                ('normalized_query', models.TextField(blank=True, default='')),
                ('subject', models.CharField(blank=True, db_index=True, default='', max_length=50)),
                ('grade', models.CharField(blank=True, db_index=True, default='10', max_length=10)),
                ('unit', models.CharField(blank=True, default='', max_length=50)),
                ('chapter', models.CharField(blank=True, default='', max_length=50)),
                ('plan_tier', models.CharField(blank=True, db_index=True, default='free', max_length=20)),
                ('decision', models.CharField(choices=[('CACHE_HIT', 'Cache Hit'), ('KNOWLEDGE_BASE_HIT', 'Knowledge Base Hit'), ('RETRIEVAL_HIT', 'Retrieval Hit'), ('AI_REQUIRED', 'AI Required'), ('AI_FALLBACK', 'AI Fallback')], db_index=True, max_length=40)),
                ('confidence', models.FloatField(default=0.0)),
                ('latency_ms', models.PositiveIntegerField(default=0)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('matched_cache', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.semanticanswercache')),
                ('matched_kb', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.knowledgebaseentry')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['created_at', 'decision'], name='api_cachelo_created_b0e631_idx'),
                    models.Index(fields=['plan_tier', 'subject', 'decision'], name='api_cachelo_plan_ti_f5f587_idx'),
                ],
            },
        ),
    ]
