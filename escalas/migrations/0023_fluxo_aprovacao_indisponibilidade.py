# Generated manually on 2026-07-01

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def marcar_existentes_como_aprovadas(apps, schema_editor):
    Indisponibilidade = apps.get_model('escalas', 'Indisponibilidade')
    Indisponibilidade.objects.filter(status='pendente').update(status='aprovada')


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('escalas', '0022_add_anexo_indisponibilidade'),
    ]

    operations = [
        migrations.AddField(
            model_name='indisponibilidade',
            name='status',
            field=models.CharField(
                choices=[
                    ('pendente', 'Pendente'),
                    ('aprovada', 'Aprovada'),
                    ('reprovada', 'Reprovada'),
                ],
                db_index=True,
                default='pendente',
                help_text='Somente indisponibilidades aprovadas bloqueiam a geração da escala.',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='indisponibilidade',
            name='aprovado_por',
            field=models.ForeignKey(
                blank=True,
                help_text='Usuário que aprovou ou reprovou a indisponibilidade.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='indisponibilidades_decididas',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='indisponibilidade',
            name='data_decisao',
            field=models.DateTimeField(
                blank=True,
                help_text='Data/hora da aprovação ou reprovação.',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='indisponibilidade',
            name='motivo_reprovacao',
            field=models.TextField(
                blank=True,
                help_text='Justificativa quando a indisponibilidade for reprovada.',
            ),
        ),
        migrations.RunPython(
            marcar_existentes_como_aprovadas,
            migrations.RunPython.noop,
        ),
    ]
