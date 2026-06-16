import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('escalas', '0014_lancamento_manual_quadrinho'),
    ]

    operations = [
        migrations.CreateModel(
            name='EscalaCalendarioOverride',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.DateField()),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('observacao', models.CharField(blank=True, max_length=120)),
                ('criado_por', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                )),
                ('escala', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='calendario_overrides',
                    to='escalas.escala',
                )),
                ('tipo_servico', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='calendario_overrides',
                    to='escalas.tiposervico',
                )),
            ],
            options={
                'db_table': 'escala_calendario_override',
                'ordering': ['data'],
                'unique_together': {('escala', 'data')},
            },
        ),
    ]
