"""
Views do Sistema de Escala Militar.
Foco atual: dashboard, autenticação e cadastros (OM, Divisões, Postos,
Especialidades, Militares). As views de geração de escala estão em
`views_escala_legado.py` e serão integradas em uma próxima etapa.

Suporta múltiplas OMs: a OM ativa é mantida na sessão do usuário
(`request.session['om_id_ativa']`) e selecionada via dropdown na navbar.
"""
from datetime import date as _date, date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .context_processors import SESSION_KEY_OM, obter_om_da_sessao
from .forms_cadastro import (
    DivisaoForm,
    EscalaCriarForm,
    EspecialidadeForm,
    IndisponibilidadeRegistrarForm,
    MilitarForm,
    OrganizacaoMilitarForm,
    PostoForm,
    QuadrinhoForm,
    TipoEscalaForm,
    TipoIndisponibilidadeForm,
)
from .models import (
    CalendarioDia,
    ConfiguracaoEscala,
    Divisao,
    Escala,
    EscalaItem,
    Especialidade,
    Indisponibilidade,
    Militar,
    OrganizacaoMilitar,
    Posto,
    PonteiroEscala,
    Quadrinho,
    TipoEscala,
    TipoIndisponibilidade,
    TipoServico,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def obter_om_ativa(request):
    """Retorna a OM ativa do usuário (sessão) ou None se nenhuma cadastrada."""
    return obter_om_da_sessao(request)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    om = obter_om_ativa(request)

    contexto = {
        'om': om,
        'total_militares': 0,
        'total_divisoes': 0,
        'total_postos': Posto.objects.filter(ativo=True).count(),
        'total_especialidades': Especialidade.objects.filter(ativo=True).count(),
        'total_oms': OrganizacaoMilitar.objects.filter(ativo=True).count(),
        'militares_recentes': [],
        'divisoes_resumo': [],
    }

    if om:
        contexto.update({
            'total_militares': Militar.objects.filter(
                organizacao_militar=om, ativo=True
            ).count(),
            'total_divisoes': Divisao.objects.filter(
                organizacao_militar=om, ativo=True
            ).count(),
            'militares_recentes': Militar.objects.filter(
                organizacao_militar=om, ativo=True
            ).select_related('posto', 'divisao', 'especialidade').order_by(
                '-data_criacao'
            )[:6],
            'divisoes_resumo': Divisao.objects.filter(
                organizacao_militar=om, ativo=True
            ).annotate(
                total_militares=Count('militares', filter=Q(militares__ativo=True))
            ).order_by('nome'),
        })

    return render(request, 'dashboard.html', contexto)


# ---------------------------------------------------------------------------
# Organizações Militares (multi-OM)
# ---------------------------------------------------------------------------

@login_required
def organizacao_listar(request):
    oms = OrganizacaoMilitar.objects.annotate(
        total_militares=Count('militares', filter=Q(militares__ativo=True)),
        total_divisoes=Count('divisoes', filter=Q(divisoes__ativo=True), distinct=True),
    ).order_by('-ativo', 'sigla')
    return render(request, 'cadastro/organizacao_list.html', {'oms': oms})


@login_required
def organizacao_detalhe(request, om_id=None):
    """Detalhe de uma OM. Se om_id não informado, usa a OM ativa."""
    if om_id is None:
        om = obter_om_ativa(request)
        if om is None:
            return redirect('organizacao_novo')
    else:
        om = get_object_or_404(OrganizacaoMilitar, pk=om_id)
    return render(request, 'cadastro/organizacao_detail.html', {'om': om})


@login_required
def organizacao_form(request, om_id=None):
    instancia = get_object_or_404(OrganizacaoMilitar, pk=om_id) if om_id else None
    if request.method == 'POST':
        form = OrganizacaoMilitarForm(request.POST, request.FILES, instance=instancia)
        if form.is_valid():
            om = form.save()
            # se for a primeira, ativa na sessão
            if not request.session.get(SESSION_KEY_OM):
                request.session[SESSION_KEY_OM] = om.id
            messages.success(
                request,
                f'OM {om.sigla} {"atualizada" if instancia else "cadastrada"} com sucesso.',
            )
            return redirect('organizacao_detalhe', om_id=om.id)
    else:
        form = OrganizacaoMilitarForm(instance=instancia)
    return render(
        request,
        'cadastro/organizacao_form.html',
        {'form': form, 'om': instancia},
    )


@login_required
def organizacao_excluir(request, om_id):
    om = get_object_or_404(OrganizacaoMilitar, pk=om_id)
    qtd_militares = om.militares.count()
    qtd_escalas = om.escalas.count()
    qtd_divisoes = om.divisoes.count()
    tem_vinculos = bool(qtd_militares or qtd_escalas or qtd_divisoes)
    if request.method == 'POST':
        om_ativa_id = request.session.get(SESSION_KEY_OM)
        if tem_vinculos:
            om.ativo = False
            om.save()
            if om_ativa_id == om.id:
                request.session.pop(SESSION_KEY_OM, None)
            messages.success(
                request,
                f'OM {om.sigla} desativada (existem militares, escalas ou divisões '
                'vinculados; histórico preservado).',
            )
        else:
            if om_ativa_id == om.id:
                request.session.pop(SESSION_KEY_OM, None)
            om.delete()
            messages.success(request, f'OM excluída.')
        return redirect('organizacao_listar')
    return render(
        request,
        'cadastro/organizacao_confirm_delete.html',
        {
            'om': om,
            'qtd_militares': qtd_militares,
            'qtd_escalas': qtd_escalas,
            'qtd_divisoes': qtd_divisoes,
            'tem_vinculos': tem_vinculos,
        },
    )


@login_required
@require_POST
def organizacao_trocar(request):
    """Define a OM ativa na sessão e volta para a página anterior."""
    om_id_raw = request.POST.get('om_id')
    proximo = request.POST.get('next') or 'dashboard'
    try:
        om_id = int(om_id_raw) if om_id_raw not in (None, '', 'None') else None
    except (TypeError, ValueError):
        om_id = None
    if om_id:
        om = OrganizacaoMilitar.objects.filter(pk=om_id, ativo=True).first()
        if om:
            request.session[SESSION_KEY_OM] = om.id
            messages.success(request, f'OM ativa alterada para {om.sigla}.')
        else:
            messages.error(request, 'OM inválida ou inativa.')
    return redirect(proximo)


# ---------------------------------------------------------------------------
# Postos (lista global, hierarquia militar)
# ---------------------------------------------------------------------------

@login_required
def posto_listar(request):
    postos = Posto.objects.all().order_by('ordem_hierarquica')
    return render(request, 'cadastro/posto_list.html', {'postos': postos})


@login_required
def posto_form(request, posto_id=None):
    instancia = get_object_or_404(Posto, pk=posto_id) if posto_id else None
    if request.method == 'POST':
        form = PostoForm(request.POST, instance=instancia)
        if form.is_valid():
            form.save()
            messages.success(request, 'Posto salvo com sucesso.')
            return redirect('posto_listar')
    else:
        form = PostoForm(instance=instancia)
    return render(
        request,
        'cadastro/posto_form.html',
        {'form': form, 'posto': instancia},
    )


@login_required
def posto_excluir(request, posto_id):
    posto = get_object_or_404(Posto, pk=posto_id)
    if request.method == 'POST':
        if posto.militares.filter(ativo=True).exists():
            messages.error(
                request,
                'Existem militares ativos com este posto. '
                'Desative o posto ao invés de excluir.',
            )
        else:
            posto.ativo = False
            posto.save()
            messages.success(request, 'Posto desativado.')
        return redirect('posto_listar')
    return render(
        request,
        'cadastro/posto_confirm_delete.html',
        {'posto': posto},
    )


# ---------------------------------------------------------------------------
# Especialidades
# ---------------------------------------------------------------------------

@login_required
def especialidade_listar(request):
    especialidades = Especialidade.objects.all().order_by('nome')
    return render(
        request,
        'cadastro/especialidade_list.html',
        {'especialidades': especialidades},
    )


@login_required
def especialidade_form(request, especialidade_id=None):
    instancia = (
        get_object_or_404(Especialidade, pk=especialidade_id)
        if especialidade_id else None
    )
    if request.method == 'POST':
        form = EspecialidadeForm(request.POST, instance=instancia)
        if form.is_valid():
            form.save()
            messages.success(request, 'Especialidade salva com sucesso.')
            return redirect('especialidade_listar')
    else:
        form = EspecialidadeForm(instance=instancia)
    return render(
        request,
        'cadastro/especialidade_form.html',
        {'form': form, 'especialidade': instancia},
    )


@login_required
def especialidade_excluir(request, especialidade_id):
    esp = get_object_or_404(Especialidade, pk=especialidade_id)
    if request.method == 'POST':
        esp.ativo = False
        esp.save()
        messages.success(request, 'Especialidade desativada.')
        return redirect('especialidade_listar')
    return render(
        request,
        'cadastro/especialidade_confirm_delete.html',
        {'especialidade': esp},
    )


# ---------------------------------------------------------------------------
# Tipos de Indisponibilidade (lista global)
# ---------------------------------------------------------------------------

@login_required
def tipo_indisponibilidade_listar(request):
    tipos = TipoIndisponibilidade.objects.all().order_by('nome')
    return render(
        request,
        'cadastro/tipo_indisponibilidade_list.html',
        {'tipos': tipos},
    )


@login_required
def tipo_indisponibilidade_form(request, tipo_id=None):
    instancia = (
        get_object_or_404(TipoIndisponibilidade, pk=tipo_id) if tipo_id else None
    )
    if request.method == 'POST':
        form = TipoIndisponibilidadeForm(request.POST, instance=instancia)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tipo de indisponibilidade salvo com sucesso.')
            return redirect('tipo_indisponibilidade_listar')
    else:
        form = TipoIndisponibilidadeForm(instance=instancia)
    return render(
        request,
        'cadastro/tipo_indisponibilidade_form.html',
        {'form': form, 'tipo': instancia},
    )


@login_required
def tipo_indisponibilidade_excluir(request, tipo_id):
    tipo = get_object_or_404(TipoIndisponibilidade, pk=tipo_id)
    if request.method == 'POST':
        if tipo.indisponibilidades.exists():
            tipo.ativo = False
            tipo.save()
            messages.success(
                request,
                'Tipo de indisponibilidade desativado (existem registros vinculados, '
                'histórico preservado).',
            )
        else:
            tipo.delete()
            messages.success(request, 'Tipo de indisponibilidade excluído.')
        return redirect('tipo_indisponibilidade_listar')
    return render(
        request,
        'cadastro/tipo_indisponibilidade_confirm_delete.html',
        {'tipo': tipo},
    )


# ---------------------------------------------------------------------------
# Tipos de Escala (cadastro global, não escopado por OM)
# ---------------------------------------------------------------------------

@login_required
def tipo_escala_listar(request):
    tipos = (
        TipoEscala.objects.all()
        .annotate(
            qtd_escalas=Count('escalas', distinct=True),
            qtd_quadrinhos=Count('quadrinhos', distinct=True),
        )
        .order_by('-ativo', 'nome')
    )
    return render(
        request,
        'cadastro/tipo_escala_list.html',
        {'tipos': tipos},
    )


@login_required
def tipo_escala_form(request, tipo_id=None):
    instancia = get_object_or_404(TipoEscala, pk=tipo_id) if tipo_id else None
    if request.method == 'POST':
        form = TipoEscalaForm(request.POST, instance=instancia)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tipo de escala salvo com sucesso.')
            return redirect('tipo_escala_listar')
    else:
        form = TipoEscalaForm(instance=instancia)
    return render(
        request,
        'cadastro/tipo_escala_form.html',
        {'form': form, 'tipo': instancia},
    )


@login_required
def tipo_escala_excluir(request, tipo_id):
    tipo = get_object_or_404(TipoEscala, pk=tipo_id)
    tem_vinculos = tipo.escalas.exists() or tipo.quadrinhos.exists()
    if request.method == 'POST':
        if tem_vinculos:
            tipo.ativo = False
            tipo.save()
            messages.success(
                request,
                'Tipo de escala desativado (existem escalas ou quadrinhos '
                'vinculados, histórico preservado).',
            )
        else:
            tipo.delete()
            messages.success(request, 'Tipo de escala excluído.')
        return redirect('tipo_escala_listar')
    return render(
        request,
        'cadastro/tipo_escala_confirm_delete.html',
        {
            'tipo': tipo,
            'qtd_escalas': tipo.escalas.count(),
            'qtd_quadrinhos': tipo.quadrinhos.count(),
            'tem_vinculos': tem_vinculos,
        },
    )


# ---------------------------------------------------------------------------
# Divisões (escopo: OM ativa)
# ---------------------------------------------------------------------------

@login_required
def divisao_listar(request):
    om = obter_om_ativa(request)
    divisoes = (
        Divisao.objects.filter(organizacao_militar=om).annotate(
            total_militares=Count('militares', filter=Q(militares__ativo=True))
        ).order_by('nome')
        if om else Divisao.objects.none()
    )
    return render(
        request,
        'cadastro/divisao_list.html',
        {'divisoes': divisoes, 'om': om},
    )


@login_required
def divisao_form(request, divisao_id=None):
    om = obter_om_ativa(request)
    if om is None:
        messages.error(request, 'Cadastre uma Organização Militar antes.')
        return redirect('organizacao_novo')

    instancia = get_object_or_404(Divisao, pk=divisao_id) if divisao_id else None

    if request.method == 'POST':
        form = DivisaoForm(request.POST, instance=instancia)
        if form.is_valid():
            divisao = form.save(commit=False)
            divisao.organizacao_militar = om
            divisao.save()
            messages.success(request, 'Divisão salva com sucesso.')
            return redirect('divisao_listar')
    else:
        form = DivisaoForm(instance=instancia)

    return render(
        request,
        'cadastro/divisao_form.html',
        {'form': form, 'divisao': instancia, 'om': om},
    )


@login_required
def divisao_excluir(request, divisao_id):
    divisao = get_object_or_404(Divisao, pk=divisao_id)
    if request.method == 'POST':
        divisao.ativo = False
        divisao.save()
        messages.success(request, 'Divisão desativada.')
        return redirect('divisao_listar')
    return render(
        request,
        'cadastro/divisao_confirm_delete.html',
        {'divisao': divisao},
    )


# ---------------------------------------------------------------------------
# Militares (escopo: OM ativa)
# ---------------------------------------------------------------------------

@login_required
def militar_listar(request):
    om = obter_om_ativa(request)
    q = request.GET.get('q', '').strip()
    divisao_filtro = request.GET.get('divisao', '')
    posto_filtro = request.GET.get('posto', '')

    ano_atual = _date.today().year
    try:
        ano = int(request.GET.get('ano') or ano_atual)
    except ValueError:
        ano = ano_atual

    tipo_escala_filtro = request.GET.get('tipo_escala', '')

    militares_qs = (
        Militar.objects.filter(organizacao_militar=om, ativo=True)
        if om else Militar.objects.none()
    )
    militares_qs = militares_qs.select_related('posto', 'divisao', 'especialidade')

    if q:
        militares_qs = militares_qs.filter(
            Q(nome_guerra__icontains=q)
            | Q(nome_completo__icontains=q)
            | Q(matricula__icontains=q)
            | Q(cpf__icontains=q)
        )

    if divisao_filtro:
        militares_qs = militares_qs.filter(divisao_id=divisao_filtro)

    if posto_filtro:
        militares_qs = militares_qs.filter(posto_id=posto_filtro)

    militares_qs = militares_qs.order_by('-posto__ordem_hierarquica', 'data_ultima_promocao', 'nome_guerra')
    militares = list(militares_qs)

    divisoes = (
        Divisao.objects.filter(organizacao_militar=om, ativo=True).order_by('nome')
        if om else Divisao.objects.none()
    )
    postos = Posto.objects.filter(ativo=True).order_by('-ordem_hierarquica')

    tipos_escala = list(TipoEscala.objects.filter(ativo=True).order_by('nome'))
    tipo_escala_atual = None
    if tipo_escala_filtro:
        tipo_escala_atual = next(
            (t for t in tipos_escala if str(t.id) == tipo_escala_filtro), None
        )
    if tipo_escala_atual is None and tipos_escala:
        tipo_escala_atual = tipos_escala[0]
        tipo_escala_filtro = str(tipo_escala_atual.id)

    tipos_servico = (
        list(om.tipos_servico.filter(ativo=True).order_by('ordem')) if om else []
    )

    quadrinhos_map = {}
    if om and tipo_escala_atual and militares:
        for qd in Quadrinho.objects.filter(
            militar__in=militares,
            tipo_escala=tipo_escala_atual,
            ano=ano,
        ):
            quadrinhos_map[(qd.militar_id, qd.tipo_servico_id)] = qd

    militares_lista = []
    for m in militares:
        celulas = []
        total = 0
        for ts in tipos_servico:
            qd = quadrinhos_map.get((m.id, ts.id))
            valor = qd.total if qd else 0
            celulas.append({'tipo_servico': ts, 'valor': valor})
            total += valor
        militares_lista.append({'militar': m, 'celulas': celulas, 'total': total})

    anos_opcoes = list(range(ano_atual + 1, ano_atual - 5, -1))

    return render(
        request,
        'cadastro/militar_list.html',
        {
            'militares_lista': militares_lista,
            'tipos_servico': tipos_servico,
            'tipos_escala': tipos_escala,
            'tipo_escala_atual': tipo_escala_atual,
            'tipo_escala_filtro': tipo_escala_filtro,
            'ano': ano,
            'anos_opcoes': anos_opcoes,
            'divisoes': divisoes,
            'postos': postos,
            'om': om,
            'q': q,
            'divisao_filtro': divisao_filtro,
            'posto_filtro': posto_filtro,
            'total_militares': len(militares),
        },
    )


@login_required
def militar_detalhe(request, militar_id):
    militar = get_object_or_404(
        Militar.objects.select_related(
            'posto', 'divisao', 'especialidade', 'organizacao_militar'
        ),
        pk=militar_id,
    )

    om = militar.organizacao_militar
    ano_atual = _date.today().year
    try:
        ano = int(request.GET.get('ano') or ano_atual)
    except ValueError:
        ano = ano_atual

    tipos_servico = list(om.tipos_servico.filter(ativo=True).order_by('ordem'))
    tipos_escala = list(TipoEscala.objects.filter(ativo=True).order_by('nome'))

    quadrinhos = Quadrinho.objects.filter(militar=militar, ano=ano).select_related(
        'tipo_escala', 'tipo_servico'
    )
    quadrinhos_map = {(q.tipo_escala_id, q.tipo_servico_id): q for q in quadrinhos}

    contadores = []
    for te in tipos_escala:
        celulas = []
        total = 0
        tem_dado = False
        for ts in tipos_servico:
            qd = quadrinhos_map.get((te.id, ts.id))
            valor = qd.total if qd else 0
            celulas.append({
                'tipo_servico': ts,
                'valor': valor,
                'quadrinho': qd,
            })
            total += valor
            if qd:
                tem_dado = True
        contadores.append({
            'tipo_escala': te,
            'celulas': celulas,
            'total': total,
            'tem_dado': tem_dado,
        })

    itens_qs = (
        EscalaItem.objects.filter(
            militar=militar,
            calendario_dia__data__year=ano,
        )
        .select_related(
            'escala__tipo_escala',
            'calendario_dia__tipo_servico',
        )
        .order_by('calendario_dia__data')
    )
    itens = list(itens_qs)

    dias_servico = {it.calendario_dia.data: it for it in itens}

    DIAS_SEMANA_ABREV = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']

    import calendar as _cal
    cal = _cal.Calendar(firstweekday=0)
    meses = []
    for mes_num in range(1, 13):
        nome_mes = _cal.month_name[mes_num].capitalize() if False else [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
        ][mes_num - 1]
        semanas = []
        tem_servico_no_mes = False
        for semana in cal.monthdatescalendar(ano, mes_num):
            dias_semana = []
            for d in semana:
                pertence_mes = d.month == mes_num
                item = dias_servico.get(d) if pertence_mes else None
                if item:
                    tem_servico_no_mes = True
                dias_semana.append({
                    'data': d,
                    'pertence_mes': pertence_mes,
                    'item': item,
                })
            semanas.append(dias_semana)
        meses.append({
            'numero': mes_num,
            'nome': nome_mes,
            'semanas': semanas,
            'tem_servico': tem_servico_no_mes,
        })

    anos_opcoes = list(range(ano_atual + 1, ano_atual - 5, -1))

    return render(
        request,
        'cadastro/militar_detail.html',
        {
            'militar': militar,
            'ano': ano,
            'anos_opcoes': anos_opcoes,
            'contadores': contadores,
            'tipos_servico': tipos_servico,
            'itens': itens,
            'meses': meses,
            'dias_semana_abrev': DIAS_SEMANA_ABREV,
            'total_servicos_ano': len(itens),
        },
    )


# ---------------------------------------------------------------------------
# Quadrinho (visão geral por OM × Tipo de Escala × Ano)
# ---------------------------------------------------------------------------

@login_required
def quadrinho_visao(request):
    om = obter_om_ativa(request)
    militar_proprio = getattr(request.user, 'militar', None)

    ano_atual = _date.today().year
    try:
        ano = int(request.GET.get('ano') or ano_atual)
    except ValueError:
        ano = ano_atual

    tipo_escala_param = request.GET.get('tipo_escala', '')

    tipos_escala = list(TipoEscala.objects.filter(ativo=True).order_by('nome'))
    tipo_escala_atual = None
    if tipo_escala_param:
        tipo_escala_atual = next(
            (t for t in tipos_escala if str(t.id) == tipo_escala_param), None
        )
    if tipo_escala_atual is None and tipos_escala:
        tipo_escala_atual = tipos_escala[0]

    tipos_servico = (
        list(om.tipos_servico.filter(ativo=True).order_by('ordem')) if om else []
    )

    # Se for militar próprio, filtra somente ele no quadrinho
    if militar_proprio:
        militares = [militar_proprio] if om else []
    else:
        militares = (
            list(
                Militar.objects.filter(organizacao_militar=om, ativo=True)
                .select_related('posto', 'divisao')
            )
            if om else []
        )

    quadrinhos_map = {}
    if om and tipo_escala_atual and militares and tipos_servico:
        for qd in Quadrinho.objects.filter(
            militar__in=militares,
            tipo_escala=tipo_escala_atual,
            tipo_servico__in=tipos_servico,
            ano=ano,
        ):
            quadrinhos_map[(qd.militar_id, qd.tipo_servico_id)] = qd

    linhas = []
    totais_coluna = {ts.id: 0 for ts in tipos_servico}
    total_geral = 0
    for m in militares:
        celulas = []
        total_militar = 0
        for ts in tipos_servico:
            qd = quadrinhos_map.get((m.id, ts.id))
            valor = qd.total if qd else 0
            celulas.append({
                'tipo_servico': ts,
                'quadrinho': qd,
                'valor': valor,
                'ajuste_inicial': qd.ajuste_inicial if qd else 0,
                'quantidade': qd.quantidade if qd else 0,
            })
            totais_coluna[ts.id] += valor
            total_militar += valor
        linhas.append({
            'militar': m,
            'celulas': celulas,
            'total': total_militar,
        })
        total_geral += total_militar

    ordem = request.GET.get('ordem', 'desc')
    if ordem == 'asc':
        linhas.sort(key=lambda x: (x['total'], x['militar'].nome_guerra))
    elif ordem == 'nome':
        linhas.sort(key=lambda x: x['militar'].nome_guerra.lower())
    else:
        linhas.sort(key=lambda x: (-x['total'], x['militar'].nome_guerra))

    totais_coluna_lista = [
        {'tipo_servico': ts, 'valor': totais_coluna[ts.id]} for ts in tipos_servico
    ]

    anos_opcoes = list(range(ano_atual + 1, ano_atual - 5, -1))

    # Escala atual do mês/ano para exibir links de Matriz e Detalhe no quadrinho
    from datetime import date as _d
    hoje = _d.today()
    escala_atual = None
    if om and tipo_escala_atual:
        escala_atual = (
            Escala.objects.filter(
                organizacao_militar=om,
                tipo_escala=tipo_escala_atual,
                ano=ano,
                mes=hoje.month,
            )
            .order_by('-data_criacao')
            .first()
        )
        if escala_atual is None:
            escala_atual = (
                Escala.objects.filter(
                    organizacao_militar=om,
                    tipo_escala=tipo_escala_atual,
                    ano=ano,
                )
                .order_by('-mes', '-data_criacao')
                .first()
            )

    return render(
        request,
        'cadastro/quadrinho_visao.html',
        {
            'om': om,
            'ano': ano,
            'anos_opcoes': anos_opcoes,
            'tipos_escala': tipos_escala,
            'tipo_escala_atual': tipo_escala_atual,
            'tipos_servico': tipos_servico,
            'linhas': linhas,
            'totais_coluna': totais_coluna_lista,
            'total_geral': total_geral,
            'ordem': ordem,
            'escala_atual': escala_atual,
            'militar_proprio': militar_proprio,
        },
    )


# ---------------------------------------------------------------------------
# Indisponibilidades — auto-serviço do militar e gestão pelo escalante
# ---------------------------------------------------------------------------

@login_required
def indisponibilidade_listar(request):
    om = obter_om_ativa(request)
    militar_proprio = getattr(request.user, 'militar', None)

    if militar_proprio:
        indisp = (
            Indisponibilidade.objects.filter(militar=militar_proprio)
            .select_related('tipo', 'militar__posto')
            .order_by('-data_inicio')
        )
        militares = None
        filtro_mil = None
    else:
        indisp = (
            Indisponibilidade.objects.filter(militar__organizacao_militar=om)
            .select_related('tipo', 'militar__posto')
            .order_by('-data_inicio')
        )
        militares = (
            Militar.objects.filter(organizacao_militar=om, ativo=True)
            .select_related('posto')
            .order_by('posto__ordem_hierarquica', 'data_ultima_promocao', 'nome_guerra')
        ) if om else []
        filtro_mil = request.GET.get('militar', '')
        if filtro_mil:
            indisp = indisp.filter(militar_id=filtro_mil)


    return render(request, 'indisponibilidade/listar.html', {
        'indisp': indisp,
        'om': om,
        'militar_proprio': militar_proprio,
        'militares': militares,
        'filtro_mil': filtro_mil,
    })


@login_required
def indisponibilidade_criar(request):
    om = obter_om_ativa(request)
    militar_proprio = getattr(request.user, 'militar', None)

    if request.method == 'POST':
        form = IndisponibilidadeRegistrarForm(
            request.POST, om=om, militar_fixo=militar_proprio
        )
        if form.is_valid():
            ind = form.save(commit=False)
            if militar_proprio and not ind.militar_id:
                ind.militar = militar_proprio
            ind.data_fim = form.cleaned_data['data_fim']
            ind.save()
            um_dia = form.cleaned_data['data_inicio'] == form.cleaned_data['data_fim']
            if getattr(form, '_data_fim_ajustada', False):
                msg = (
                    f'Indisponibilidade registrada como 1 dia: '
                    f'{ind.tipo.nome} em {ind.data_inicio.strftime("%d/%m/%Y")}.'
                )
            else:
                msg = (
                    f'Indisponibilidade registrada: {ind.tipo.nome} de '
                    f'{ind.data_inicio.strftime("%d/%m/%Y")} a {ind.data_fim.strftime("%d/%m/%Y")}.'
                )
            messages.success(request, msg)
            return redirect('indisponibilidade_listar')
    else:
        form = IndisponibilidadeRegistrarForm(om=om, militar_fixo=militar_proprio)

    return render(request, 'indisponibilidade/criar.html', {
        'form': form,
        'om': om,
        'militar_proprio': militar_proprio,
    })


@login_required
@require_POST
def indisponibilidade_excluir(request, ind_id):
    ind = get_object_or_404(Indisponibilidade, pk=ind_id)
    militar_proprio = getattr(request.user, 'militar', None)

    if militar_proprio and ind.militar_id != militar_proprio.id:
        messages.error(request, 'Sem permissão para excluir esta indisponibilidade.')
        return redirect('indisponibilidade_listar')

    desc = f'{ind.tipo.nome} — {ind.militar.nome_guerra}'
    ind.delete()
    messages.success(request, f'Indisponibilidade removida: {desc}.')
    return redirect('indisponibilidade_listar')


@login_required
def quadrinho_editar(request, militar_id, tipo_escala_id, tipo_servico_id, ano):
    om = obter_om_ativa(request)
    militar = get_object_or_404(
        Militar.objects.select_related('posto', 'organizacao_militar'),
        pk=militar_id,
    )
    if om and militar.organizacao_militar_id != om.id:
        messages.error(request, 'O militar não pertence à OM ativa.')
        return redirect('quadrinho_visao')

    tipo_escala = get_object_or_404(TipoEscala, pk=tipo_escala_id)
    tipo_servico = get_object_or_404(
        TipoServico, pk=tipo_servico_id, organizacao_militar=militar.organizacao_militar
    )

    quadrinho, _ = Quadrinho.objects.get_or_create(
        militar=militar,
        tipo_escala=tipo_escala,
        tipo_servico=tipo_servico,
        ano=ano,
        defaults={'quantidade': 0, 'ajuste_inicial': 0},
    )

    voltar_para = request.GET.get('voltar', 'quadrinho_visao')

    if request.method == 'POST':
        form = QuadrinhoForm(request.POST, instance=quadrinho)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'Quadrinho de {militar.nome_guerra} atualizado '
                f'({tipo_escala.nome} / {tipo_servico.nome}).'
            )
            if voltar_para == 'militar_detalhe':
                return redirect(
                    f"{reverse('militar_detalhe', args=[militar.id])}?ano={ano}"
                )
            return redirect(
                f"{reverse('quadrinho_visao')}?ano={ano}"
                f"&tipo_escala={tipo_escala.id}"
            )
    else:
        form = QuadrinhoForm(instance=quadrinho)

    return render(
        request,
        'cadastro/quadrinho_form.html',
        {
            'form': form,
            'quadrinho': quadrinho,
            'militar': militar,
            'tipo_escala': tipo_escala,
            'tipo_servico': tipo_servico,
            'ano': ano,
            'voltar_para': voltar_para,
        },
    )


@login_required
def militar_form(request, militar_id=None):
    om = obter_om_ativa(request)
    if om is None:
        messages.error(request, 'Cadastre uma Organização Militar antes.')
        return redirect('organizacao_novo')

    instancia = get_object_or_404(Militar, pk=militar_id) if militar_id else None

    if request.method == 'POST':
        form = MilitarForm(request.POST, instance=instancia, om=om)
        if form.is_valid():
            militar = form.save(commit=False)
            militar.organizacao_militar = om
            militar.save()
            messages.success(
                request,
                f'Militar {militar.nome_guerra} salvo com sucesso.',
            )
            return redirect('militar_detalhe', militar_id=militar.id)
    else:
        form = MilitarForm(instance=instancia, om=om)

    return render(
        request,
        'cadastro/militar_form.html',
        {'form': form, 'militar': instancia, 'om': om},
    )


@login_required
def militar_excluir(request, militar_id):
    militar = get_object_or_404(Militar, pk=militar_id)
    if request.method == 'POST':
        militar.ativo = False
        militar.save()
        messages.success(
            request,
            f'Militar {militar.nome_guerra} desativado (histórico preservado).',
        )
        return redirect('militar_listar')
    return render(
        request,
        'cadastro/militar_confirm_delete.html',
        {'militar': militar},
    )


# ===========================================================================
# ESCALAS — listagem, criação, detalhe, geração automática (matriz)
# ===========================================================================

NOMES_MESES = [
    '', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
]


@login_required
def escala_listar(request):
    """Lista todas as escalas da OM ativa."""
    om = obter_om_ativa(request)
    if not om:
        messages.warning(request, 'Nenhuma OM ativa. Cadastre ou selecione uma OM.')
        return redirect('organizacao_novo')

    escalas = (
        Escala.objects.filter(organizacao_militar=om)
        .select_related('tipo_escala')
        .order_by('-ano', '-mes')
    )

    # filtros simples
    filtro_tipo = request.GET.get('tipo')
    filtro_status = request.GET.get('status')
    filtro_ano = request.GET.get('ano')
    if filtro_tipo:
        escalas = escalas.filter(tipo_escala_id=filtro_tipo)
    if filtro_status:
        escalas = escalas.filter(status=filtro_status)
    if filtro_ano:
        escalas = escalas.filter(ano=filtro_ano)

    tipos = TipoEscala.objects.filter(ativo=True)
    anos = sorted(
        Escala.objects.filter(organizacao_militar=om)
        .values_list('ano', flat=True).distinct(),
        reverse=True,
    )

    return render(request, 'escala/listar.html', {
        'escalas': escalas,
        'tipos': tipos,
        'anos': anos,
        'filtro_tipo': filtro_tipo,
        'filtro_status': filtro_status,
        'filtro_ano': filtro_ano,
        'STATUS_CHOICES': Escala.STATUS_CHOICES,
        'nomes_meses': NOMES_MESES,
    })


@login_required
def escala_criar(request):
    """Cria um novo cabeçalho de escala para a OM ativa."""
    om = obter_om_ativa(request)
    if not om:
        messages.warning(request, 'Nenhuma OM ativa.')
        return redirect('organizacao_novo')

    if request.method == 'POST':
        form = EscalaCriarForm(request.POST)
        if form.is_valid():
            tipo = form.cleaned_data['tipo_escala']
            mes = int(form.cleaned_data['mes'])
            ano = form.cleaned_data['ano']
            obs = form.cleaned_data.get('observacao', '')

            # Verificar duplicidade
            if Escala.objects.filter(
                organizacao_militar=om, tipo_escala=tipo, mes=mes, ano=ano
            ).exists():
                messages.error(
                    request,
                    f'Já existe uma escala de {tipo.nome} para '
                    f'{NOMES_MESES[mes]}/{ano}.',
                )
            else:
                escala = Escala.objects.create(
                    organizacao_militar=om,
                    tipo_escala=tipo,
                    mes=mes,
                    ano=ano,
                    observacao=obs,
                    status='rascunho',
                )
                messages.success(
                    request,
                    f'Escala {NOMES_MESES[mes]}/{ano} criada com sucesso!',
                )
                return redirect('escala_detalhar', escala_id=escala.id)
    else:
        form = EscalaCriarForm()

    return render(request, 'escala/criar.html', {'form': form, 'om': om})


@login_required
def escala_detalhar(request, escala_id):
    """Exibe os itens da escala em formato de lista e tabela."""
    om = obter_om_ativa(request)
    escala = get_object_or_404(Escala, pk=escala_id)

    itens = (
        escala.itens
        .select_related('militar__posto', 'calendario_dia__tipo_servico')
        .order_by('calendario_dia__data')
    )

    # Contagem por militar
    contagem: dict = {}
    for item in itens:
        m = item.militar
        contagem.setdefault(m, 0)
        contagem[m] += 1

    contagem_lista = sorted(contagem.items(), key=lambda x: -x[1])

    return render(request, 'escala/detalhar.html', {
        'escala': escala,
        'itens': itens,
        'contagem_lista': contagem_lista,
        'nomes_meses': NOMES_MESES,
        'pode_editar': escala.status in ('rascunho', 'previsao'),
    })


@login_required
def escala_gerar(request, escala_id):
    """
    Gera a escala automaticamente usando o algoritmo de ponteiro BASE→TOPO.

    Executa separadamente para cada TipoServico (Preta, Vermelha, etc.)
    mantendo um ponteiro persistente entre meses por OM + TipoServico.

    POST = executa; GET = tela de confirmação.
    """
    from calendar import monthrange

    escala = get_object_or_404(Escala, pk=escala_id)
    om = escala.organizacao_militar

    if escala.status not in ('rascunho', 'previsao'):
        messages.error(request, 'Somente escalas em Rascunho ou Previsão podem ser geradas.')
        return redirect('escala_detalhar', escala_id=escala_id)

    if request.method == 'POST':
        from .engine_escala import gerar_escala_multi_tipo, obter_indisponibilidades

        # Limpar itens existentes antes de regerar
        escala.itens.all().delete()

        # ----- Intervalo do mês -----
        primeiro_dia = date(escala.ano, escala.mes, 1)
        ultimo_num   = monthrange(escala.ano, escala.mes)[1]
        ultimo_dia   = date(escala.ano, escala.mes, ultimo_num)

        # ----- Calendário -----
        dias_qs = CalendarioDia.objects.filter(
            organizacao_militar=om,
            data__range=(primeiro_dia, ultimo_dia),
        ).select_related('tipo_servico').order_by('data')

        if not dias_qs.exists():
            try:
                CalendarioDia.gerar_calendario_automatico(om, escala.ano)
                dias_qs = CalendarioDia.objects.filter(
                    organizacao_militar=om,
                    data__range=(primeiro_dia, ultimo_dia),
                ).select_related('tipo_servico').order_by('data')
            except Exception as e:
                messages.error(
                    request,
                    f'Sem calendário para {NOMES_MESES[escala.mes]}/{escala.ano}. '
                    f'Cadastre os Tipos de Serviço da OM primeiro. ({e})'
                )
                return redirect('escala_detalhar', escala_id=escala_id)

        lista_dias = list(dias_qs)

        # ----- Militares: índice 0 = mais antigo (TOPO), último = mais moderno (BASE) -----
        lista_militares = list(
            Militar.objects.filter(organizacao_militar=om, ativo=True)
            .select_related('posto')
            .order_by('posto__ordem_hierarquica', 'data_ultima_promocao', 'nome_guerra')
        )

        if not lista_militares:
            messages.error(request, 'Nenhum militar ativo nesta OM.')
            return redirect('escala_detalhar', escala_id=escala_id)

        # ----- Configuração -----
        config = ConfiguracaoEscala.obter_para_om(om)
        tipo_escala_obj = escala.tipo_escala

        # ----- Indisponibilidades + carryover inter-mês -----
        # Carryover considera TODOS os tipos de serviço do mesmo tipo_escala (folga global).
        indisp = obter_indisponibilidades(
            lista_militares, primeiro_dia, ultimo_dia,
            config=config, tipo_escala=tipo_escala_obj,
        )

        # ----- Quadrinhos acumulados por tipo de serviço antes deste mês -----
        # Detecta os tipos de serviço presentes nos dias do mês
        tipos_servico_no_mes = {}
        for dia in lista_dias:
            ts = dia.tipo_servico
            if ts.nome not in tipos_servico_no_mes:
                tipos_servico_no_mes[ts.nome] = ts

        quadrinhos_inicio = {}
        ultimos_militares = {}
        for nome_ts, ts in tipos_servico_no_mes.items():
            qi = {}
            for m in lista_militares:
                qs = Quadrinho.objects.filter(
                    militar=m,
                    tipo_escala=tipo_escala_obj,
                    tipo_servico=ts,
                    ano=escala.ano,
                )
                qi[m.id] = qs.first().total if qs.exists() else 0
            quadrinhos_inicio[nome_ts] = qi
            ultimos_militares[nome_ts] = PonteiroEscala.obter_ultimo_id(om, ts)

        # ----- ENGINE CRONOLÓGICO: todos os tipos em ordem de data -----
        resultado_por_tipo, novos_ultimos = gerar_escala_multi_tipo(
            lista_militares=lista_militares,
            lista_dias=lista_dias,          # TODOS os dias, misturados — engine ordena
            indisponibilidades=indisp,
            quadrinhos_inicio=quadrinhos_inicio,
            ultimos_militares=ultimos_militares,
            config=config,
            tipo_escala=tipo_escala_obj,
        )

        # ----- Salvar ponteiros e persistir itens -----
        criados     = 0
        sem_militar = 0

        for nome_ts, pares in resultado_por_tipo.items():
            ts = tipos_servico_no_mes[nome_ts]

            # Atualiza ponteiro para o próximo mês
            novo_id = novos_ultimos.get(nome_ts)
            if novo_id:
                PonteiroEscala.salvar(om, ts, novo_id)

            for dia, militar in pares:
                if militar is not None:
                    EscalaItem.objects.create(
                        escala=escala,
                        militar=militar,
                        calendario_dia=dia,
                        observacao='Gerado automaticamente (cronológico global)',
                    )
                    Quadrinho.incrementar(
                        militar=militar,
                        tipo_escala=tipo_escala_obj,
                        tipo_servico=ts,
                        ano=escala.ano,
                    )
                    criados += 1
                else:
                    sem_militar += 1

        if sem_militar:
            messages.warning(
                request,
                f'{sem_militar} dia(s) sem militar disponível (todos indisponíveis naquele dia).',
            )
        messages.success(
            request,
            f'Escala gerada com folga global! '
            f'{criados} dia(s) preenchidos.',
        )
        return redirect('escala_detalhar', escala_id=escala_id)

    # GET — tela de confirmação
    militares_count = Militar.objects.filter(organizacao_militar=om, ativo=True).count()
    tem_itens = escala.itens.exists()
    return render(request, 'escala/gerar.html', {
        'escala': escala,
        'militares_count': militares_count,
        'tem_itens': tem_itens,
        'nomes_meses': NOMES_MESES,
    })


@login_required
@require_POST
def escala_limpar(request, escala_id):
    """Remove todos os itens da escala (só rascunho/previsão)."""
    escala = get_object_or_404(Escala, pk=escala_id)
    if escala.status not in ('rascunho', 'previsao'):
        messages.error(request, 'Não é possível limpar uma escala publicada.')
    else:
        total = escala.itens.count()
        escala.itens.all().delete()
        messages.success(request, f'{total} item(ns) removido(s).')
    return redirect('escala_detalhar', escala_id=escala_id)


@login_required
@require_POST
def escala_item_forcar(request, item_id):
    """Toggle do flag forcar_escala em um EscalaItem."""
    item = get_object_or_404(EscalaItem, pk=item_id)
    escala = item.escala
    if escala.status in ('rascunho', 'previsao'):
        item.forcar_escala = not item.forcar_escala
        item.save(update_fields=['forcar_escala'])
        if item.forcar_escala:
            messages.warning(
                request,
                f'{item.militar.nome_guerra} em {item.calendario_dia.data:%d/%m/%Y} '
                'marcado como FORÇADO — folga mínima ignorada para este dia.',
            )
        else:
            messages.success(
                request,
                f'Exceção removida de {item.militar.nome_guerra} '
                f'em {item.calendario_dia.data:%d/%m/%Y}.',
            )
    else:
        messages.error(request, 'Não é possível alterar itens de uma escala publicada.')
    return redirect('escala_detalhar', escala_id=escala.id)


@login_required
@require_POST
def escala_marcar_previsao(request, escala_id):
    """Muda status para Previsão."""
    escala = get_object_or_404(Escala, pk=escala_id)
    try:
        escala.marcar_previsao()
        messages.success(request, 'Escala marcada como Previsão.')
    except Exception as e:
        messages.error(request, str(e))
    return redirect('escala_detalhar', escala_id=escala_id)


@login_required
@require_POST
def escala_publicar(request, escala_id):
    """Publica a escala (status → publicada)."""
    escala = get_object_or_404(Escala, pk=escala_id)
    if not escala.itens.exists():
        messages.error(request, 'Escala vazia — preencha antes de publicar.')
        return redirect('escala_detalhar', escala_id=escala_id)
    try:
        escala.publicar()
        messages.success(request, 'Escala publicada com sucesso!')
    except Exception as e:
        messages.error(request, str(e))
    return redirect('escala_detalhar', escala_id=escala_id)


@login_required
@require_POST
def escala_excluir(request, escala_id):
    """Exclui completamente uma escala (cabeçalho + todos os itens)."""
    escala = get_object_or_404(Escala, pk=escala_id)
    if escala.status == 'publicada':
        messages.error(request, 'Escalas publicadas não podem ser excluídas.')
        return redirect('escala_detalhar', escala_id=escala_id)
    nome = str(escala)
    escala.delete()
    messages.success(request, f'Escala "{nome}" excluída com sucesso.')
    return redirect('escala_listar')


@login_required
def configuracao_escala(request):
    """Tela de configuração das regras operacionais da escala para a OM ativa."""
    om = obter_om_ativa(request)
    if not om:
        messages.warning(request, 'Selecione ou cadastre uma OM antes de configurar.')
        return redirect('organizacao_novo')

    config = ConfiguracaoEscala.obter_para_om(om)

    if request.method == 'POST':
        try:
            folga = int(request.POST.get('folga_minima_horas', 48))
            duracao = int(request.POST.get('duracao_servico_horas', 24))
            if folga < 0 or duracao < 1:
                raise ValueError
        except (TypeError, ValueError):
            messages.error(request, 'Valores inválidos. Informe números inteiros positivos.')
            return redirect('configuracao_escala')

        config.folga_minima_horas = folga
        config.duracao_servico_horas = duracao
        config.bloquear_pre_ferias = 'bloquear_pre_ferias' in request.POST
        config.bloquear_pos_ferias = 'bloquear_pos_ferias' in request.POST
        config.save()
        messages.success(request, 'Configurações salvas com sucesso.')
        return redirect('configuracao_escala')

    return render(request, 'escala/configuracao.html', {'config': config, 'om': om})


@login_required
def escala_matriz(request, escala_id):
    """Visualização da matriz algoritmo: militares × dias + passo a passo."""
    escala = get_object_or_404(Escala, pk=escala_id)
    om = escala.organizacao_militar  # usa a OM da própria escala (igual ao escala_detalhar)

    # Militares ordenados ASC: índice 0 = mais antigo (topo), último = mais moderno (base)
    militares = list(
        Militar.objects.filter(organizacao_militar=om, ativo=True)
        .select_related('posto')
        .order_by('posto__ordem_hierarquica', 'data_ultima_promocao', 'nome_guerra')
    )

    # Dias do calendário do mês
    dias = list(
        CalendarioDia.objects.filter(
            organizacao_militar=om,
            data__year=escala.ano,
            data__month=escala.mes,
        ).select_related('tipo_servico').order_by('data')
    )

    # Mapa de itens salvos: data → militar
    itens = list(
        escala.itens.select_related('militar__posto', 'calendario_dia__tipo_servico')
        .order_by('calendario_dia__data')
    )
    itens_map = {item.calendario_dia.data: item.militar for item in itens}

    # Indisponibilidades do período
    import calendar as _cal
    ultimo_dia_num = _cal.monthrange(escala.ano, escala.mes)[1]
    inicio = date(escala.ano, escala.mes, 1)
    fim = date(escala.ano, escala.mes, ultimo_dia_num)

    indisp_map = {}  # (militar_id, data) → motivo (str)
    for ind in (
        Indisponibilidade.objects.filter(
            militar__organizacao_militar=om,
            data_inicio__lte=fim,
            data_fim__gte=inicio,
        )
        .select_related('militar', 'tipo')
    ):
        d = ind.data_inicio
        while d <= ind.data_fim:
            if inicio <= d <= fim:
                indisp_map[(ind.militar_id, d)] = ind.tipo.nome
            d += timedelta(days=1)

    # ── Construir linhas da matriz ──────────────────────────────────────
    # Tabela visual: topo = mais antigo (ordem menor), base = mais moderno (ordem maior)
    # Iteramos militares em ordem ASC (mais antigo primeiro = topo da tabela HTML)
    # e invertemos para exibir de baixo para cima no template via CSS flex-direction:column-reverse

    matrix_rows = []
    for mil in militares:
        cells = []
        total_servicos = 0
        for dia in dias:
            d = dia.data
            serves = itens_map.get(d) == mil
            unavailable = (mil.id, d) in indisp_map
            motivo_indisp = indisp_map.get((mil.id, d), '')
            if serves:
                total_servicos += 1
            cells.append({
                'dia': dia,
                'serves': serves,
                'unavailable': unavailable,
                'motivo': motivo_indisp,
            })
        # eventos: só dias em que serviu ou estava indisponível (para colunas da tabela)
        eventos = [c for c in cells if c['serves'] or c['unavailable']]
        matrix_rows.append({
            'militar': mil,
            'cells': cells,
            'eventos': eventos,
            'total': total_servicos,
        })

    # ── Passo a passo: reconstruir raciocínio por dia ───────────────────
    contagem = {mil.id: 0 for mil in militares}
    ultimo_serv = {mil.id: None for mil in militares}
    passos = []

    for dia in dias:
        d = dia.data
        escolhido = itens_map.get(d)

        candidatos = []
        indisponiveis = []
        for mil in militares:
            if (mil.id, d) in indisp_map:
                indisponiveis.append({'militar': mil, 'motivo': indisp_map[(mil.id, d)]})
            else:
                ult = ultimo_serv[mil.id]
                dias_desde = (d - ult).days if ult else None
                candidatos.append({
                    'militar': mil,
                    'count': contagem[mil.id],
                    'dias_desde': dias_desde,
                    'escolhido': mil == escolhido,
                })

        # Ordenar candidatos pela mesma lógica do engine (para exibição)
        candidatos.sort(key=lambda c: (
            c['count'],
            -(c['dias_desde'] if c['dias_desde'] is not None else 9999),
            -militares.index(c['militar']),  # base→topo
        ))

        # Atualizar acumuladores APÓS montar o passo
        if escolhido:
            contagem[escolhido.id] += 1
            ultimo_serv[escolhido.id] = d

        passos.append({
            'dia': dia,
            'escolhido': escolhido,
            'candidatos': candidatos,
            'indisponiveis': indisponiveis,
        })

    max_eventos = max((len(r['eventos']) for r in matrix_rows), default=0)
    # Padear cada linha com None até max_eventos para facilitar o template
    for r in matrix_rows:
        faltam = max_eventos - len(r['eventos'])
        r['eventos_padded'] = r['eventos'] + [None] * faltam

    return render(request, 'escala/matriz.html', {
        'escala': escala,
        'militares': militares,
        'dias': dias,
        'matrix_rows': matrix_rows,
        'max_eventos': max_eventos,
        'max_eventos_range': range(max_eventos),
        'passos': passos,
        'itens': itens,
        'nomes_meses': NOMES_MESES,
    })


# ---------------------------------------------------------------------------
# Tela pública — Escala de Sobreaviso
# ---------------------------------------------------------------------------

def sobreaviso_publico(request):
    """
    Tela pública (sem login) que exibe:
    - Cards dos próximos 15 dias da escala atual (publicada ou previsão) de cada tipo
    - Os 5 próximos militares da Preto e da Vermelho (menor total no quadrinho)
    - A próxima escala publicada/previsão, se existir
    """
    from datetime import date as _d, timedelta

    hoje = _d.today()

    # Pega a primeira OM ativa (ordem de id)
    om = OrganizacaoMilitar.objects.filter(ativo=True).order_by('id').first()

    tipos_servico = list(om.tipos_servico.filter(ativo=True).order_by('ordem')) if om else []
    tipos_escala = list(TipoEscala.objects.filter(ativo=True).order_by('nome')) if om else []

    # --- Escala atual e próxima por tipo de escala ---
    escalas_data = []
    for te in tipos_escala:
        # Escala atual: publicada ou previsão cujo mês/ano >= hoje e mais próxima
        escala_atual = (
            Escala.objects.filter(
                organizacao_militar=om,
                tipo_escala=te,
                status__in=('publicada', 'previsao'),
            )
            .order_by('-ano', '-mes')
            .first()
        )

        itens_15 = []
        proxima_escala = None
        proximos_15_itens = []

        if escala_atual:
            data_ini = max(hoje, _d(escala_atual.ano, escala_atual.mes, 1))
            data_fim = data_ini + timedelta(days=14)

            itens_qs = (
                EscalaItem.objects.filter(
                    escala=escala_atual,
                    calendario_dia__data__range=(data_ini, data_fim),
                )
                .select_related('militar__posto', 'calendario_dia__tipo_servico')
                .order_by('calendario_dia__data')
            )

            # Agrupa por data
            dias_map = {}
            for item in itens_qs:
                dt = item.calendario_dia.data
                if dt not in dias_map:
                    dias_map[dt] = {
                        'data': dt,
                        'dia_semana': ['Segunda', 'Terça', 'Quarta', 'Quinta',
                                       'Sexta', 'Sábado', 'Domingo'][dt.weekday()],
                        'tipo_servico': item.calendario_dia.tipo_servico,
                        'militar': item.militar,
                    }
            itens_15 = [dias_map[d] for d in sorted(dias_map)]

            # Próxima escala
            import calendar as _cal
            ultimo_dia_mes = _cal.monthrange(escala_atual.ano, escala_atual.mes)[1]
            prox_data = _d(escala_atual.ano, escala_atual.mes, ultimo_dia_mes) + timedelta(days=1)
            proxima_escala = (
                Escala.objects.filter(
                    organizacao_militar=om,
                    tipo_escala=te,
                    status__in=('publicada', 'previsao'),
                    ano__gte=prox_data.year,
                )
                .order_by('ano', 'mes')
                .first()
            )
            if proxima_escala and (proxima_escala.ano, proxima_escala.mes) <= (escala_atual.ano, escala_atual.mes):
                proxima_escala = None

        escalas_data.append({
            'tipo_escala': te,
            'escala_atual': escala_atual,
            'itens_15': itens_15,
            'proxima_escala': proxima_escala,
        })

    # --- 5 próximos da Preto e Vermelho (menor total no quadrinho do ano atual) ---
    ano_atual = hoje.year
    militares_om = (
        list(Militar.objects.filter(organizacao_militar=om, ativo=True)
             .select_related('posto'))
        if om else []
    )

    def _ranking_servico(nome_servico):
        ts = next((t for t in tipos_servico if nome_servico.lower() in t.nome.lower()), None)
        if not ts or not militares_om:
            return []
        # Para cada tipo de escala, pega o quadrinho e soma
        totais = {}
        for m in militares_om:
            totais[m.id] = {'militar': m, 'total': 0}
        for te in tipos_escala:
            for qd in Quadrinho.objects.filter(
                militar__in=militares_om,
                tipo_servico=ts,
                tipo_escala=te,
                ano=ano_atual,
            ).select_related('militar__posto'):
                totais[qd.militar_id]['total'] += qd.total
        return sorted(totais.values(), key=lambda x: (x['total'], x['militar'].nome_guerra))[:5]

    proximos_preto = _ranking_servico('preto')
    proximos_vermelho = _ranking_servico('vermelho')

    return render(request, 'escala/sobreaviso_publico.html', {
        'om': om,
        'hoje': hoje,
        'escalas_data': escalas_data,
        'proximos_preto': proximos_preto,
        'proximos_vermelho': proximos_vermelho,
        'tipos_servico': tipos_servico,
    })
