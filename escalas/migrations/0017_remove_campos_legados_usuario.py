from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('escalas', '0016_simplificar_status_escala'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='usuariocustomizado',
            name='eh_militar',
        ),
        migrations.RemoveField(
            model_name='usuariocustomizado',
            name='militar_associado',
        ),
    ]
