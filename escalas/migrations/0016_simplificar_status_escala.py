from django.db import migrations


def migrar_status(apps, schema_editor):
    Escala = apps.get_model('escalas', 'Escala')
    Escala.objects.filter(status__in=('rascunho', 'arquivada')).update(status='previsao')


class Migration(migrations.Migration):

    dependencies = [
        ('escalas', '0015_escala_calendario_override'),
    ]

    operations = [
        migrations.RunPython(migrar_status, migrations.RunPython.noop),
    ]
