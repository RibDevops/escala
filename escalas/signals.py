"""
Sistema de Escala Militar - Django Signals
Registra eventos de auditoria. O Quadrinho é gerenciado diretamente pelo
MotorEscalaVertical (services.py) — NÃO incrementar/decrementar aqui para
evitar dupla contagem.
"""

import logging

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import EscalaItem, Quadrinho, Escala, UsuarioCustomizado

logger = logging.getLogger(__name__)


# ============================================================================
# SIGNALS DE AUDITORIA — EscalaItem
# Apenas logging. O Quadrinho é atualizado pelo motor (services.py).
# ============================================================================

@receiver(post_save, sender=EscalaItem)
def log_escala_item_criado(sender, instance, created, **kwargs):
    """Registra criação de um item de escala no log de debug."""
    if not created:
        return
    try:
        logger.debug(
            "EscalaItem criado: militar=%s tipo=%s data=%s escala=%s/%s",
            instance.militar.nome_guerra,
            instance.calendario_dia.tipo_servico.nome,
            instance.calendario_dia.data.strftime("%d/%m/%Y"),
            instance.escala.mes,
            instance.escala.ano,
        )
    except Exception:
        pass  # Nunca deve quebrar o fluxo principal


@receiver(post_delete, sender=EscalaItem)
def log_escala_item_removido(sender, instance, **kwargs):
    """Registra remoção de um item de escala no log de debug."""
    try:
        logger.debug(
            "EscalaItem removido: militar=%s tipo=%s data=%s escala=%s/%s",
            instance.militar.nome_guerra,
            instance.calendario_dia.tipo_servico.nome,
            instance.calendario_dia.data.strftime("%d/%m/%Y"),
            instance.escala.mes,
            instance.escala.ano,
        )
    except Exception:
        pass


# ============================================================================
# SIGNALS DE AUDITORIA — Escala e Usuário
# ============================================================================

@receiver(post_save, sender=Escala)
def log_escala_publicada(sender, instance, created, **kwargs):
    """Registra quando uma escala é publicada."""
    if not created and instance.status == 'publicada' and instance.data_publicacao:
        logger.info(
            "Escala publicada: %02d/%s (%s) em %s",
            instance.mes,
            instance.ano,
            instance.tipo_escala.nome,
            instance.data_publicacao.strftime("%d/%m/%Y %H:%M"),
        )


@receiver(post_save, sender=UsuarioCustomizado)
def log_usuario_criado(sender, instance, created, **kwargs):
    """Registra criação de novo usuário."""
    if created:
        logger.info(
            "Novo usuario criado: %s (%s)",
            instance.username,
            instance.get_perfil_display(),
        )


# ============================================================================
# FUNÇÃO AUXILIAR PARA RESETAR QUADRINHO (USE COM CUIDADO)
# ============================================================================

def resetar_quadrinho_do_ano(ano: int):
    """
    Reseta TODOS os Quadrinhos de um ano e os recalcula a partir dos EscalaItem.
    Use apenas em caso de erro crítico ou necessidade de recalcular do zero.

    Exemplo de uso no shell Django:
        from escalas.signals import resetar_quadrinho_do_ano
        resetar_quadrinho_do_ano(2026)
    """
    print(f"RESETANDO Quadrinhos de {ano}...")  # OK aqui — chamado só no shell

    deletados = Quadrinho.objects.filter(ano=ano).delete()[0]
    print(f"  Deletados {deletados} Quadrinhos")

    escalas = Escala.objects.filter(ano=ano, status='publicada')
    total_itens = 0

    for escala in escalas:
        for item in escala.itens.all():
            Quadrinho.incrementar(
                militar=item.militar,
                tipo_escala=escala.tipo_escala,
                tipo_servico=item.calendario_dia.tipo_servico,
                ano=ano,
            )
            total_itens += 1

    print(f"  Reprocessados {total_itens} itens de escala")
    print(f"Reset concluido!")
