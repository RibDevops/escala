from django.db import migrations, models
from django.utils.text import slugify


def populate_slugs(apps, schema_editor):
    TipoEscala = apps.get_model('escalas', 'TipoEscala')
    for te in TipoEscala.objects.all():
        base = slugify(te.nome) or f'tipo-{te.pk}'
        slug = base
        n = 1
        while TipoEscala.objects.filter(slug=slug).exclude(pk=te.pk).exists():
            slug = f'{base}-{n}'
            n += 1
        te.slug = slug
        te.save(update_fields=['slug'])


class Migration(migrations.Migration):

    dependencies = [
        ('escalas', '0009_substituto_escala_item'),
    ]

    operations = [
        migrations.AddField(
            model_name='tipoescala',
            name='slug',
            field=models.SlugField(blank=True, default='', max_length=80),
            preserve_default=False,
        ),
        migrations.RunPython(populate_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='tipoescala',
            name='slug',
            field=models.SlugField(
                blank=True,
                max_length=80,
                unique=True,
                help_text='URL amigável gerada automaticamente do nome. Não altere após criação.',
            ),
        ),
    ]
