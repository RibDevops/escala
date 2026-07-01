# Generated manually on 2026-07-01

import django.core.validators
from django.db import migrations, models

import escalas.models


class Migration(migrations.Migration):

    dependencies = [
        ('escalas', '0021_add_bloqueio_pre_pos_tipo_indisponibilidade'),
    ]

    operations = [
        migrations.AddField(
            model_name='indisponibilidade',
            name='anexo',
            field=models.FileField(
                blank=True,
                help_text='Documento comprobatório em PDF ou imagem (até 10 MB)',
                null=True,
                upload_to='indisponibilidades/anexos/%Y/%m/',
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'webp']
                    ),
                    escalas.models.validar_tamanho_anexo_indisponibilidade,
                ],
            ),
        ),
    ]
