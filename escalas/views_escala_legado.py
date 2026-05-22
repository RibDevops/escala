"""
Sistema de Escala Militar - Django Views
CRUD e lógica de negócio principal
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Count, Q, F, Prefetch
from django.utils import timezone
from datetime import datetime, timedelta
from calendar import monthrange

from .models import (
    Escala, EscalaItem, Militar, Quadrinho, TipoEscala, TipoServico,
    OrganizacaoMilitar, CalendarioDia, Indisponibilidade, UsuarioCustomizado
)
from .forms import (
    EscalaForm, EscalaItemForm, IndisponibilidadeForm,
    GeracaoAutomaticaEscalaForm, PublicarEscalaForm
)


# ============================================================================
# UTILITIES - FUNÇÕES AUXILIARES
# ============================================================================

def usuario_pode_acessar_om(usuario, om):
    """Verifica se usuário tem acesso à OM"""
    if usuario.pode_administrar():
        return usuario.om_principal_id == om.id
    militar = getattr(usuario, 'militar', None)
    if militar is not None:
        return militar.organizacao_militar_id == om.id
    return False


def usuario_pode_editar_escala(usuario, escala):
    """Verifica se usuário pode editar uma escala"""
    if not usuario_pode_acessar_om(usuario, escala.organizacao_militar):
        return False
    
    if escala.status == 'publicada':
        # Apenas admin_om pode editar publicadas
        return usuario.pode_administrar()
    
    return usuario.pode_escalar() or usuario.pode_administrar()


def obter_dias_disponiveis_mes(om, mes, ano):
    """Retorna todos os CalendarioDia do mês para uma OM"""
    primeiro_dia = datetime(ano, mes, 1).date()
    ultimo_dia = datetime(
        ano, mes, monthrange(ano, mes)[1]
    ).date()
    
    return CalendarioDia.objects.filter(
        organizacao_militar=om,
        data__gte=primeiro_dia,
        data__lte=ultimo_dia
    ).order_by('data')


def gerar_escala_automaticamente(escala):
    """
    Algoritmo de geração automática de escala.
    Usa Quadrinho para balancear distribuição de serviços.
    """
    from django.db import transaction
    
    om = escala.organizacao_militar
    
    # Obter todos os dias do mês
    dias = obter_dias_disponiveis_mes(om, escala.mes, escala.ano)
    
    if not dias.exists():
        raise ValueError(f"Nenhum dia cadastrado para {escala.mes}/{escala.ano}")
    
    # Obter militares ativos da OM
    militares_ativos = Militar.objects.filter(
        organizacao_militar=om,
        ativo=True
    ).select_related('posto', 'especialidade')
    
    if not militares_ativos.exists():
        raise ValueError(f"Nenhum militar ativo em {om.sigla}")
    
    alocacoes_criadas = 0
    
    with transaction.atomic():
        for dia in dias:
            # Buscar quadrinho para este tipo de escala/serviço
            ranking = Quadrinho.obter_ranking(
                tipo_escala=escala.tipo_escala,
                tipo_servico=dia.tipo_servico,
                ano=escala.ano,
                om=om
            )
            
            # Tentar alocar o próximo militar (com menor contagem)
            alocado = False
            
            for quadrinho in ranking:
                militar = quadrinho.militar
                
                # Verificar se está disponível
                tem_indisponibilidade = militar.indisponibilidades.filter(
                    data_inicio__lte=dia.data,
                    data_fim__gte=dia.data,
                    tipo__exclui_do_sorteio=True
                ).exists()
                
                if not tem_indisponibilidade:
                    # Criar alocação
                    EscalaItem.objects.create(
                        escala=escala,
                        militar=militar,
                        calendario_dia=dia,
                        observacao="Gerado automaticamente"
                    )
                    alocado = True
                    alocacoes_criadas += 1
                    break
            
            if not alocado:
                # Nenhum militar disponível neste dia
                print(f"⚠️  Nenhum militar disponível em {dia.data}")
    
    return alocacoes_criadas


# ============================================================================
# VIEWS DE ESCALA
# ============================================================================

@login_required
def listar_escalas(request):
    """Lista todas as escalas acessíveis ao usuário"""
    
    # Filtrar por OMs do usuário
    if request.user.pode_administrar():
        oms = OrganizacaoMilitar.objects.filter(
            id=request.user.om_principal_id,
            ativo=True
        )
    elif (m := getattr(request.user, 'militar', None)) is not None:
        oms = OrganizacaoMilitar.objects.filter(
            id=m.organizacao_militar_id,
            ativo=True
        )
    else:
        oms = OrganizacaoMilitar.objects.none()
    
    escalas = Escala.objects.filter(
        organizacao_militar__in=oms
    ).select_related(
        'organizacao_militar', 'tipo_escala', 'usuario_criacao'
    ).order_by('-ano', '-mes')
    
    # Filtros opcionais
    filtro_om = request.GET.get('om')
    filtro_tipo = request.GET.get('tipo')
    filtro_status = request.GET.get('status')
    filtro_ano = request.GET.get('ano')
    
    if filtro_om:
        escalas = escalas.filter(organizacao_militar_id=filtro_om)
    
    if filtro_tipo:
        escalas = escalas.filter(tipo_escala_id=filtro_tipo)
    
    if filtro_status:
        escalas = escalas.filter(status=filtro_status)
    
    if filtro_ano:
        escalas = escalas.filter(ano=filtro_ano)
    
    context = {
        'escalas': escalas,
        'oms': oms,
        'tipos_escala': TipoEscala.objects.filter(ativo=True),
        'anos': range(2020, timezone.now().year + 2),
    }
    
    return render(request, 'escala/listar.html', context)


@login_required
def detalhar_escala(request, escala_id):
    """Visualiza detalhes de uma escala"""
    
    escala = get_object_or_404(Escala, id=escala_id)
    
    # Verificar permissão
    if not usuario_pode_acessar_om(request.user, escala.organizacao_militar):
        messages.error(request, "Você não tem acesso a esta escala.")
        return redirect('listar_escalas')
    
    # Obter itens agrupados por dia
    itens = escala.itens.select_related(
        'militar', 'calendario_dia__tipo_servico'
    ).order_by('calendario_dia__data')
    
    # Agrupar por tipo de serviço (preto, vermelho, roxo)
    itens_por_tipo = {}
    for item in itens:
        tipo = item.calendario_dia.tipo_servico
        if tipo not in itens_por_tipo:
            itens_por_tipo[tipo] = []
        itens_por_tipo[tipo].append(item)
    
    # Estatísticas
    total_dias = escala.itens.count()
    total_militares = escala.itens.values('militar').distinct().count()
    
    context = {
        'escala': escala,
        'itens': itens,
        'itens_por_tipo': itens_por_tipo,
        'total_dias': total_dias,
        'total_militares': total_militares,
        'pode_editar': usuario_pode_editar_escala(request.user, escala),
    }
    
    return render(request, 'escala/detalhar.html', context)


@login_required
def criar_escala(request):
    """Cria nova escala"""
    
    # Verificar permissão
    if not request.user.pode_escalar() and not request.user.pode_administrar():
        messages.error(request, "Você não tem permissão para criar escalas.")
        return redirect('listar_escalas')
    
    if request.method == 'POST':
        form = EscalaForm(request.POST)
        if form.is_valid():
            escala = form.save(commit=False)
            escala.usuario_criacao = request.user
            escala.save()
            
            messages.success(
                request,
                f"Escala {escala.mes:02d}/{escala.ano} criada com sucesso!"
            )
            return redirect('detalhar_escala', escala_id=escala.id)
    else:
        # Se usuário é admin_om, usar sua OM como padrão
        initial = {}
        if request.user.pode_administrar():
            initial['organizacao_militar'] = request.user.om_principal
        
        form = EscalaForm(initial=initial)
        
        # Limitar OMs disponíveis
        if request.user.pode_administrar():
            form.fields['organizacao_militar'].queryset = \
                OrganizacaoMilitar.objects.filter(
                    id=request.user.om_principal_id
                )
    
    return render(request, 'escala/criar.html', {'form': form})


@login_required
def editar_escala(request, escala_id):
    """Edita uma escala em rascunho"""
    
    escala = get_object_or_404(Escala, id=escala_id)
    
    # Verificar permissão
    if not usuario_pode_editar_escala(request.user, escala):
        messages.error(request, "Você não tem permissão para editar esta escala.")
        return redirect('detalhar_escala', escala_id=escala.id)
    
    if escala.status == 'publicada':
        messages.warning(request, "Escalas publicadas não podem ser alteradas.")
        return redirect('detalhar_escala', escala_id=escala.id)
    
    if request.method == 'POST':
        form = EscalaForm(request.POST, instance=escala)
        if form.is_valid():
            form.save()
            messages.success(request, "Escala atualizada com sucesso!")
            return redirect('detalhar_escala', escala_id=escala.id)
    else:
        form = EscalaForm(instance=escala)
    
    return render(request, 'escala/editar.html', {
        'form': form,
        'escala': escala
    })


@login_required
def gerar_automaticamente(request, escala_id):
    """Gera escala automaticamente usando Quadrinho"""
    
    escala = get_object_or_404(Escala, id=escala_id)
    
    # Verificar permissão e status
    if not usuario_pode_editar_escala(request.user, escala):
        messages.error(request, "Você não tem permissão.")
        return redirect('detalhar_escala', escala_id=escala.id)
    
    if escala.status != 'rascunho':
        messages.error(request, "Apenas escalas em rascunho podem ser geradas.")
        return redirect('detalhar_escala', escala_id=escala.id)
    
    if escala.itens.exists():
        messages.warning(
            request,
            "Esta escala já possui itens. Limpe antes de gerar novamente."
        )
        return redirect('detalhar_escala', escala_id=escala.id)
    
    if request.method == 'POST':
        try:
            alocacoes = gerar_escala_automaticamente(escala)
            messages.success(
                request,
                f"Escala gerada com sucesso! {alocacoes} alocações criadas."
            )
            return redirect('detalhar_escala', escala_id=escala.id)
        except ValueError as e:
            messages.error(request, str(e))
    
    # GET: mostrar confirmação
    form = GeracaoAutomaticaEscalaForm()
    
    return render(request, 'escala/gerar_automaticamente.html', {
        'escala': escala,
        'form': form
    })


@login_required
def publicar_escala(request, escala_id):
    """Publica uma escala (muda de rascunho para publicada)"""
    
    escala = get_object_or_404(Escala, id=escala_id)
    
    # Verificar permissão
    if not request.user.pode_administrar():
        messages.error(request, "Apenas admins de OM podem publicar escalas.")
        return redirect('detalhar_escala', escala_id=escala.id)
    
    if escala.organizacao_militar_id != request.user.om_principal_id:
        messages.error(request, "Você não pode publicar escalas de outra OM.")
        return redirect('detalhar_escala', escala_id=escala.id)
    
    if escala.status != 'rascunho':
        messages.error(request, "Apenas escalas em rascunho podem ser publicadas.")
        return redirect('detalhar_escala', escala_id=escala.id)
    
    if not escala.itens.exists():
        messages.error(request, "Escala vazia. Preencha antes de publicar.")
        return redirect('detalhar_escala', escala_id=escala.id)
    
    if request.method == 'POST':
        form = PublicarEscalaForm(request.POST)
        if form.is_valid():
            try:
                escala.publicar()
                messages.success(
                    request,
                    f"Escala {escala.mes:02d}/{escala.ano} publicada com sucesso!"
                )
                return redirect('detalhar_escala', escala_id=escala.id)
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = PublicarEscalaForm()
    
    return render(request, 'escala/publicar.html', {
        'escala': escala,
        'form': form
    })


# ============================================================================
# VIEWS DE ITEMS DE ESCALA
# ============================================================================

@login_required
def adicionar_item_escala(request, escala_id):
    """Adiciona militar a um dia da escala"""
    
    escala = get_object_or_404(Escala, id=escala_id)
    
    if not usuario_pode_editar_escala(request.user, escala):
        messages.error(request, "Você não tem permissão.")
        return redirect('detalhar_escala', escala_id=escala.id)
    
    if escala.status != 'rascunho':
        messages.error(request, "Não pode adicionar itens em escala publicada.")
        return redirect('detalhar_escala', escala_id=escala.id)
    
    if request.method == 'POST':
        form = EscalaItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.escala = escala
            
            # Validações adicionais
            if item.militar.organizacao_militar_id != escala.organizacao_militar_id:
                messages.error(request, "Militar deve pertencer à mesma OM.")
            elif item.calendario_dia.organizacao_militar_id != escala.organizacao_militar_id:
                messages.error(request, "Dia deve pertencer à mesma OM.")
            else:
                item.save()
                messages.success(
                    request,
                    f"{item.militar.nome_guerra} escalado para {item.calendario_dia.data}."
                )
                return redirect('detalhar_escala', escala_id=escala.id)
    else:
        # Limitar opções aos militares e dias da OM
        form = EscalaItemForm()
        form.fields['militar'].queryset = Militar.objects.filter(
            organizacao_militar=escala.organizacao_militar,
            ativo=True
        )
        form.fields['calendario_dia'].queryset = obter_dias_disponiveis_mes(
            escala.organizacao_militar,
            escala.mes,
            escala.ano
        )
    
    return render(request, 'escala/adicionar_item.html', {
        'escala': escala,
        'form': form
    })


@login_required
def remover_item_escala(request, item_id):
    """Remove um item de escala"""
    
    item = get_object_or_404(EscalaItem, id=item_id)
    
    if not usuario_pode_editar_escala(request.user, item.escala):
        messages.error(request, "Você não tem permissão.")
        return redirect('detalhar_escala', escala_id=item.escala.id)
    
    if item.escala.status != 'rascunho':
        messages.error(request, "Não pode remover itens de escala publicada.")
        return redirect('detalhar_escala', escala_id=item.escala.id)
    
    if request.method == 'POST':
        militar_nome = item.militar.nome_guerra
        data = item.calendario_dia.data
        escala_id = item.escala.id
        
        item.delete()
        
        messages.success(
            request,
            f"{militar_nome} removido de {data}."
        )
        return redirect('detalhar_escala', escala_id=escala_id)
    
    return render(request, 'escala/confirmar_remocao.html', {'item': item})


# ============================================================================
# VIEWS DE DASHBOARD
# ============================================================================

@login_required
def dashboard(request):
    """Dashboard com estatísticas e próximas escalas"""
    
    if request.user.pode_administrar():
        oms = OrganizacaoMilitar.objects.filter(
            id=request.user.om_principal_id
        )
        escalas_mes = Escala.objects.filter(
            organizacao_militar__in=oms,
            status='publicada'
        ).order_by('-ano', '-mes')[:12]
    
    elif (militar := getattr(request.user, 'militar', None)) is not None:
        escalas_mes = EscalaItem.objects.filter(
            militar=militar
        ).select_related(
            'escala', 'calendario_dia__tipo_servico'
        ).order_by('-calendario_dia__data')[:30]
    
    else:
        escalas_mes = Escala.objects.none()
    
    context = {
        'escalas_mes': escalas_mes,
        'total_militares': Militar.objects.filter(ativo=True).count() if request.user.pode_administrar() else 0,
    }
    
    return render(request, 'dashboard.html', context)


@login_required
def relatorio_balanceamento(request, escala_id):
    """Relatório de balanceamento de escalas"""
    
    escala = get_object_or_404(Escala, id=escala_id)
    
    if not usuario_pode_acessar_om(request.user, escala.organizacao_militar):
        messages.error(request, "Você não tem acesso.")
        return redirect('listar_escalas')
    
    # Calcular contagem por militar
    contagem = escala.itens.values(
        'militar__nome_guerra',
        'calendario_dia__tipo_servico__nome'
    ).annotate(
        quantidade=Count('id')
    ).order_by('-quantidade')
    
    # Obter Quadrinho para comparação
    quadrinhos = Quadrinho.objects.filter(
        tipo_escala=escala.tipo_escala,
        ano=escala.ano
    ).select_related('militar', 'tipo_servico')
    
    context = {
        'escala': escala,
        'contagem': contagem,
        'quadrinhos': quadrinhos,
    }
    
    return render(request, 'escala/relatorio_balanceamento.html', context)
