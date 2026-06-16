"""
Migração 0018 — Torna os campos de aprovação dos militares que entram
nullable (None = pendente, True = aceito, False = recusado).

Antes: default=False → todos apareciam como "Recusado" ao criar a troca.
Depois: default=None → campo fica "pendente" até o militar responder.

Também converte trocas existentes em status 'pendente' cujos campos
ainda estejam em False para None (limpeza dos dados antigos).
"""
from django.db import migrations, models


def corrigir_aprovacoes_pendentes(apps, schema_editor):
    """
    Para trocas ainda 'pendente', zera os campos de aprovação que
    estavam False por default mas ainda não foram respondidos pelo militar.
    Como não há como saber se foi resposta real ou apenas o default,
    reseta tudo para None (pendente) em trocas pendentes.
    """
    TrocaServico = apps.get_model('escalas', 'TrocaServico')
    TrocaServico.objects.filter(status='pendente').update(
        aprovada_militar_entra=None,
        aprovada_militar_sai_2=None,
        aprovada_militar_entra_2=None,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('escalas', '0017_remove_campos_legados_usuario'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trocaservico',
            name='aprovada_militar_entra',
            field=models.BooleanField(
                null=True, blank=True, default=None,
                help_text='None=pendente, True=aceito, False=recusado'
            ),
        ),
        migrations.AlterField(
            model_name='trocaservico',
            name='aprovada_militar_sai_2',
            field=models.BooleanField(
                null=True, blank=True, default=None,
                help_text='None=pendente, True=aceito, False=recusado'
            ),
        ),
        migrations.AlterField(
            model_name='trocaservico',
            name='aprovada_militar_entra_2',
            field=models.BooleanField(
                null=True, blank=True, default=None,
                help_text='None=pendente, True=aceito, False=recusado'
            ),
        ),
        migrations.RunPython(corrigir_aprovacoes_pendentes, migrations.RunPython.noop),
    ]
