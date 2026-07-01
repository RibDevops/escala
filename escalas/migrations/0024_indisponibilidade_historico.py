# Generated manually on 2026-07-01

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('escalas', '0023_fluxo_aprovacao_indisponibilidade'),
    ]

    operations = [
        migrations.CreateModel(
            name='IndisponibilidadeHistorico',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('acao', models.CharField(choices=[('criada', 'Criada'), ('editada', 'Editada'), ('aprovada', 'Aprovada'), ('reprovada', 'Reprovada'), ('excluida', 'Excluída')], max_length=20)),
                ('status_anterior', models.CharField(blank=True, max_length=20)),
                ('status_novo', models.CharField(blank=True, max_length=20)),
                ('resumo', models.TextField(blank=True)),
                ('motivo', models.TextField(blank=True)),
                ('data_criacao', models.DateTimeField(auto_now_add=True)),
                ('indisponibilidade', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='historicos', to='escalas.indisponibilidade')),
                ('militar', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='historicos_indisponibilidade', to='escalas.militar')),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='historicos_indisponibilidade', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Histórico de Indisponibilidade',
                'verbose_name_plural': 'Históricos de Indisponibilidade',
                'db_table': 'indisponibilidade_historico',
                'ordering': ['-data_criacao'],
                'indexes': [
                    models.Index(fields=['militar', 'data_criacao'], name='indisponib_militar_4d89e0_idx'),
                    models.Index(fields=['acao', 'data_criacao'], name='indisponib_acao_5c4d70_idx'),
                ],
            },
        ),
    ]
