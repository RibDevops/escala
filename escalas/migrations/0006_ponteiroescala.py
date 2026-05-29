import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('escalas', '0005_configuracaoescala'),
    ]

    operations = [
        migrations.CreateModel(
            name='PonteiroEscala',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('organizacao_militar', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='ponteiros_escala',
                    to='escalas.organizacaomilitar',
                )),
                ('tipo_servico', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='ponteiros_escala',
                    to='escalas.tiposervico',
                )),
                ('ultimo_militar', models.ForeignKey(
                    blank=True,
                    help_text='Último militar escalado neste tipo de serviço.',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to='escalas.militar',
                )),
            ],
            options={
                'verbose_name': 'Ponteiro de Escala',
                'verbose_name_plural': 'Ponteiros de Escala',
                'db_table': 'ponteiro_escala',
                'unique_together': {('organizacao_militar', 'tipo_servico')},
            },
        ),
    ]
