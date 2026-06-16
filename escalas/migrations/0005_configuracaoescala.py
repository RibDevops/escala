import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('escalas', '0004_add_user_to_militar'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfiguracaoEscala',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('folga_minima_horas', models.PositiveIntegerField(
                    default=48,
                    help_text='Horas mínimas de folga exigidas após um serviço ou retorno de férias/indisponibilidade antes de novo serviço. Exemplo: 48 = dois dias de folga.',
                )),
                ('duracao_servico_horas', models.PositiveIntegerField(
                    default=24,
                    help_text='Duração padrão de um serviço em horas. Usado para calcular quando o militar fica livre após o serviço.',
                )),
                ('bloquear_pre_ferias', models.BooleanField(
                    default=True,
                    help_text='Se ativado, bloqueia serviços que terminariam dentro do período de folga mínima antes do início de uma férias/indisponibilidade.',
                )),
                ('bloquear_pos_ferias', models.BooleanField(
                    default=True,
                    help_text='Se ativado, bloqueia serviços dentro do período de folga mínima após o retorno de férias/indisponibilidade.',
                )),
                ('data_atualizacao', models.DateTimeField(auto_now=True)),
                ('organizacao_militar', models.OneToOneField(
                    help_text='OM à qual esta configuração se aplica',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='configuracao_escala',
                    to='escalas.organizacaomilitar',
                )),
            ],
            options={
                'verbose_name': 'Configuração de Escala',
                'verbose_name_plural': 'Configurações de Escala',
                'db_table': 'configuracao_escala',
            },
        ),
    ]
