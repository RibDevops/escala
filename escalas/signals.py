"""
Sistema de Escala Militar - Django Signals
Automatiza updates no Quadrinho quando escalas são criadas/deletadas
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import EscalaItem, Quadrinho, Escala, UsuarioCustomizado


# ============================================================================
# SIGNALS PARA ATUALIZAR QUADRINHO AUTOMATICAMENTE
# ============================================================================

@receiver(post_save, sender=EscalaItem)
def atualizar_quadrinho_ao_adicionar_item(sender, instance, created, **kwargs):
    """
    Quando um EscalaItem é criado, incrementa o Quadrinho correspondente.
    Chamado automaticamente ao inserir um item de escala.
    """
    if not created:
        # Se é uma atualização (não criação), ignora
        return
    
    try:
        # Obter informações necessárias
        militar = instance.militar
        tipo_escala = instance.escala.tipo_escala
        tipo_servico = instance.calendario_dia.tipo_servico
        ano = instance.escala.ano
        
        # Incrementar quadrinho
        Quadrinho.incrementar(
            militar=militar,
            tipo_escala=tipo_escala,
            tipo_servico=tipo_servico,
            ano=ano,
            quantidade=1
        )
        
        print(f"✓ Quadrinho atualizado: {militar.nome_guerra} (+1 {tipo_escala.nome})")
    
    except Exception as e:
        print(f"⚠ Erro ao atualizar Quadrinho: {e}")


@receiver(post_delete, sender=EscalaItem)
def atualizar_quadrinho_ao_remover_item(sender, instance, **kwargs):
    """
    Quando um EscalaItem é deletado, decrementa o Quadrinho correspondente.
    Mantém a contagem em 0 no mínimo (não nega).
    """
    try:
        militar = instance.militar
        tipo_escala = instance.escala.tipo_escala
        tipo_servico = instance.calendario_dia.tipo_servico
        ano = instance.escala.ano
        
        # Buscar quadrinho e decrementar
        try:
            quadrinho = Quadrinho.objects.get(
                militar=militar,
                tipo_escala=tipo_escala,
                tipo_servico=tipo_servico,
                ano=ano
            )
            
            if quadrinho.quantidade > 0:
                quadrinho.quantidade -= 1
                quadrinho.save()
                print(f"✓ Quadrinho atualizado: {militar.nome_guerra} (-1 {tipo_escala.nome})")
            else:
                print(f"ℹ Quadrinho já estava em zero: {militar.nome_guerra}")
        
        except Quadrinho.DoesNotExist:
            print(f"⚠ Quadrinho não encontrado para {militar.nome_guerra}")
    
    except Exception as e:
        print(f"⚠ Erro ao decrementar Quadrinho: {e}")


# ============================================================================
# SIGNALS PARA RASTREAMENTO DE AUDITORIA
# ============================================================================

@receiver(post_save, sender=Escala)
def registrar_publicacao_escala(sender, instance, created, **kwargs):
    """
    Registra quando uma escala é publicada (para auditoria).
    """
    if not created and instance.status == 'publicada' and instance.data_publicacao:
        # Se está publicada, registra no sistema
        msg = (
            f"Escala {instance.mes:02d}/{instance.ano} "
            f"({instance.tipo_escala.nome}) publicada em "
            f"{instance.data_publicacao.strftime('%d/%m/%Y às %H:%M')}"
        )
        print(f"📊 {msg}")


@receiver(post_save, sender=UsuarioCustomizado)
def registrar_criacao_usuario(sender, instance, created, **kwargs):
    """
    Registra criação de novo usuário.
    """
    if created:
        msg = (
            f"Novo usuário criado: {instance.username} "
            f"({instance.get_perfil_display()})"
        )
        print(f"👤 {msg}")


# ============================================================================
# FUNÇÃO AUXILIAR PARA RESETAR QUADRINHO (USE COM CUIDADO)
# ============================================================================

def resetar_quadrinho_do_ano(ano: int):
    """
    ATENÇÃO: Esta função reseta TODOS os Quadrinhos de um ano.
    Use apenas se houver erro crítico ou necessidade de recalcular.
    
    Exemplo de uso:
    >>> from .models import resetar_quadrinho_do_ano
    >>> resetar_quadrinho_do_ano(2025)
    
    Args:
        ano: Ano a resetar
    """
    from django.db import connection
    
    print(f"⚠️  RESETANDO Quadrinhos de {ano}...")
    
    # Deletar todos os Quadrinhos do ano
    deletados = Quadrinho.objects.filter(ano=ano).delete()[0]
    print(f"  → Deletados {deletados} Quadrinhos")
    
    # Recalcular a partir dos EscalaItem
    print(f"  → Recalculando...")
    
    escalas = Escala.objects.filter(ano=ano, status='publicada')
    total_itens = 0
    
    for escala in escalas:
        for item in escala.itens.all():
            Quadrinho.incrementar(
                militar=item.militar,
                tipo_escala=escala.tipo_escala,
                tipo_servico=item.calendario_dia.tipo_servico,
                ano=ano,
                quantidade=1
            )
            total_itens += 1
    
    print(f"  → Reprocessados {total_itens} itens de escala")
    print(f"✅ Reset concluído!")


# ============================================================================
# APPS CONFIG - REGISTRAR SIGNALS
# ============================================================================

def ready():
    """
    Chamada automaticamente quando a app é inicializada.
    Coloque isto em apps.py:
    
    from django.apps import AppConfig
    
    class SeuAppConfig(AppConfig):
        default_auto_field = 'django.db.models.BigAutoField'
        name = 'seu_app'
        
        def ready(self):
            import seu_app.signals  # Importa este arquivo
    """
    # Signals já estão registrados acima via decoradores @receiver
    pass
