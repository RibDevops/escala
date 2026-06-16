"""
Motor de geração automática de escala — Algoritmo de Ponteiro por Coluna.

╔══════════════════════════════════════════════════════════════════════════╗
║  LÓGICA DA MATRIZ                                                        ║
║                                                                          ║
║  Linhas  = militares, do mais moderno (índice 0, BASE) ao               ║
║            mais antigo (índice n-1, TOPO)                                ║
║                                                                          ║
║  Colunas = rodadas de serviço por tipo de serviço.                       ║
║                                                                          ║
║  Regra de folga GLOBAL (dentro do mesmo tipo de escala):                ║
║    • Qualquer serviço (Preto, Vermelho ou Roxo) bloqueia o militar      ║
║      para TODOS os outros tipos de serviço pelo período de folga.       ║
║    • Permanência e Sobreaviso têm filas INDEPENDENTES entre si.         ║
║    • Exceção: itens com forcar_escala=True não geram carryover.         ║
║                                                                          ║
║  Processamento CRONOLÓGICO:                                              ║
║    • Os dias (Preto, Vermelho, Roxo…) são processados em ordem de data. ║
║    • Um bloqueio de folga gerado por qualquer tipo de serviço é         ║
║      imediatamente visível para todos os tipos seguintes na mesma data   ║
║      ou em datas posteriores — eliminando violações retroativas.        ║
║    • Cada tipo de serviço mantém seu próprio ponteiro/contagem.         ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from datetime import date as date_type, timedelta
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Algoritmo principal: processamento cronológico unificado
# ---------------------------------------------------------------------------

def gerar_escala_multi_tipo(
    lista_militares: list,
    lista_dias: list,                     # TODOS os dias do mês, ordem cronológica
    indisponibilidades: Dict[int, Set[date_type]],
    quadrinhos_inicio: Dict[str, Dict[int, int]],  # {tipo_servico_nome: {mil_id: n}}
    ultimos_militares: Dict[str, Optional[int]],   # {tipo_servico_nome: ultimo_mil_id}
    config=None,
    tipo_escala=None,
) -> Tuple[Dict[str, List[Tuple]], Dict[str, Optional[int]]]:
    """
    Gera a escala para TODOS os tipos de serviço de um mês em ordem cronológica.

    Args:
        lista_militares      : militares ordenados [mais_moderno … mais_antigo].
        lista_dias           : CalendarioDia de todos os tipos do mês, ordem cronológica.
        indisponibilidades   : {militar_id: set(datas)} — férias + carryover inter-mês.
        quadrinhos_inicio    : {tipo_servico_nome: {militar_id: n}} contagem pré-mês.
        ultimos_militares    : {tipo_servico_nome: ultimo_mil_id} ponteiro mês anterior.
        config               : ConfiguracaoEscala.
        tipo_escala          : TipoEscala (pode ter folga_minima_horas específica).

    Returns:
        (resultado_por_tipo, novos_ultimos)
        resultado_por_tipo = {tipo_servico_nome: [(CalendarioDia, Militar|None), …]}
        novos_ultimos      = {tipo_servico_nome: ultimo_mil_id}
    """
    if not lista_militares or not lista_dias:
        return {}, {}

    n = len(lista_militares)
    idx_por_id = {m.id: i for i, m in enumerate(lista_militares)}

    # ── Janela de folga ──────────────────────────────────────────────────────
    duracao_dias = 1
    folga_dias   = 2
    if config is not None:
        duracao_dias = config.duracao_servico_dias
        folga_dias   = config.folga_minima_dias
    if tipo_escala is not None and tipo_escala.folga_minima_horas is not None:
        folga_dias = max(1, tipo_escala.folga_minima_horas // 24)
    janela_bloqueio = duracao_dias + folga_dias

    # ── Estado por tipo de serviço ───────────────────────────────────────────
    # counts[tipo][mil_id] = serviços atribuídos neste mês para este tipo
    counts: Dict[str, Dict[int, int]] = {}
    # ponteiro[tipo] = (idx, col) — posição atual do ponteiro
    ponteiros: Dict[str, Tuple[int, int]] = {}
    # último atribuído por tipo
    novos_ultimos: Dict[str, Optional[int]] = {}

    tipos_servico = {}  # nome -> objeto TipoServico
    for dia in lista_dias:
        ts = dia.tipo_servico
        nome = ts.nome
        if nome not in tipos_servico:
            tipos_servico[nome] = ts
            qi = quadrinhos_inicio.get(nome, {})
            counts[nome] = {m.id: qi.get(m.id, 0) for m in lista_militares}

            # Determinar ponto de partida do ponteiro
            ultimo_id = ultimos_militares.get(nome)
            min_count = min(counts[nome].values())
            if ultimo_id and ultimo_id in idx_por_id:
                start_idx = (idx_por_id[ultimo_id] + 1) % n
                start_col = min_count
            else:
                start_col = min_count
                start_idx = next(
                    (i for i, m in enumerate(lista_militares)
                     if counts[nome][m.id] == min_count), 0
                )
            ponteiros[nome] = (start_idx, start_col)
            novos_ultimos[nome] = ultimo_id

    # ── Bloqueio global de folga (compartilhado entre TODOS os tipos) ────────
    # {militar_id: set(datas bloqueadas por qualquer serviço já atribuído)}
    folga_global: Dict[int, Set[date_type]] = {m.id: set() for m in lista_militares}

    # ── Resultados ───────────────────────────────────────────────────────────
    resultado: Dict[str, List[Tuple]] = {nome: [] for nome in tipos_servico}

    # ── Processamento cronológico ────────────────────────────────────────────
    for dia in sorted(lista_dias, key=lambda d: d.data):
        data = dia.data
        nome_tipo = dia.tipo_servico.nome
        cnt   = counts[nome_tipo]
        idx, col = ponteiros[nome_tipo]

        atribuido = None

        # ── Ponteiro: procura militar disponível ─────────────────────────────
        tentativas = 0
        pos    = idx
        coluna = col

        while tentativas < n * 3:
            if pos >= n:
                pos    = 0
                coluna += 1

            militar   = lista_militares[pos]
            mil_count = cnt[militar.id]

            if mil_count == coluna:
                bloqueado = (
                    data in indisponibilidades.get(militar.id, set())
                    or data in folga_global.get(militar.id, set())
                )
                if not bloqueado:
                    atribuido = militar
                    break

            pos        += 1
            tentativas += 1

        # ── Fallback: todos em folga/indisponibilidade ───────────────────────
        if atribuido is None:
            candidatos = []
            for m in lista_militares:
                if data in indisponibilidades.get(m.id, set()):
                    continue  # afastamento real — nunca viola
                folgas_m = folga_global.get(m.id, set())
                if data in folgas_m:
                    bloqueado_ate = max(
                        (d for d in folgas_m if d >= data), default=data
                    )
                    dias_faltando = (bloqueado_ate - data).days
                else:
                    dias_faltando = 0
                candidatos.append((dias_faltando, idx_por_id[m.id], m))
            if candidatos:
                candidatos.sort()
                atribuido = candidatos[0][2]

        # ── Registra ─────────────────────────────────────────────────────────
        if atribuido:
            cnt[atribuido.id] += 1
            novos_ultimos[nome_tipo] = atribuido.id

            pos_atribuido = idx_por_id[atribuido.id]
            ponteiros[nome_tipo] = (pos_atribuido + 1, cnt[atribuido.id] - 1)

            # Propaga folga GLOBAL (bloqueia para todos os tipos desta sessão)
            if janela_bloqueio > 0:
                for k in range(1, janela_bloqueio + 1):
                    folga_global[atribuido.id].add(data + timedelta(days=k))

        resultado[nome_tipo].append((dia, atribuido))

    return resultado, novos_ultimos


# ---------------------------------------------------------------------------
# Função legada — mantida para compatibilidade (não é mais chamada pela view)
# ---------------------------------------------------------------------------

def gerar_escala_ponteiro(
    lista_militares: list,
    lista_dias: list,
    indisponibilidades: Dict[int, Set[date_type]],
    quadrinhos_inicio: Dict[int, int],
    ultimo_militar_id: Optional[int] = None,
    config=None,
    tipo_escala=None,
    folga_sessao: Optional[Dict[int, Set[date_type]]] = None,
) -> Tuple[List[Tuple], Optional[int]]:
    """Wrapper legado — encapsula gerar_escala_multi_tipo para um único tipo."""
    if not lista_militares or not lista_dias:
        return [], ultimo_militar_id

    nome_tipo = lista_dias[0].tipo_servico.nome

    resultado_map, novos = gerar_escala_multi_tipo(
        lista_militares=lista_militares,
        lista_dias=lista_dias,
        indisponibilidades=indisponibilidades,
        quadrinhos_inicio={nome_tipo: quadrinhos_inicio},
        ultimos_militares={nome_tipo: ultimo_militar_id},
        config=config,
        tipo_escala=tipo_escala,
    )
    return resultado_map.get(nome_tipo, []), novos.get(nome_tipo)


# ---------------------------------------------------------------------------
# Indisponibilidades + carryover inter-mês
# ---------------------------------------------------------------------------

def obter_indisponibilidades(
    militares: list,
    data_inicio,
    data_fim,
    config=None,
    tipo_escala=None,
) -> Dict[int, Set[date_type]]:
    """
    Retorna {militar_id: set(datas bloqueadas)} para [data_inicio, data_fim].

    Fontes:
      1. Indisponibilidades diretas (férias, licença…).
      2. Bloqueio pré/pós-indisponibilidade (configurável).
      3. Carryover inter-mês: QUALQUER serviço do mesmo tipo_escala no mês
         anterior bloqueia (Preto+Vermelho+Roxo = folga global).
         Itens com forcar_escala=True não geram carryover.
    """
    from .models import EscalaItem, Indisponibilidade

    if not militares:
        return {}

    if config is None:
        from .models import ConfiguracaoEscala
        om = militares[0].organizacao_militar
        config = ConfiguracaoEscala.obter_para_om(om)

    duracao_dias = config.duracao_servico_dias
    if tipo_escala is not None and tipo_escala.folga_minima_horas is not None:
        folga_min_dias = max(1, tipo_escala.folga_minima_horas // 24)
    else:
        folga_min_dias = config.folga_minima_dias

    janela_total = duracao_dias + folga_min_dias
    militar_ids  = [m.id for m in militares]
    resultado: Dict[int, Set[date_type]] = {}
    margem = timedelta(days=janela_total)

    # ── 1. Indisponibilidades diretas ────────────────────────────────────────
    registros = Indisponibilidade.objects.filter(
        militar_id__in=militar_ids,
        tipo__exclui_do_sorteio=True,
        data_inicio__lte=data_fim + margem,
        data_fim__gte=data_inicio - margem,
    ).values_list('militar_id', 'data_inicio', 'data_fim')

    for militar_id, ini, fim in registros:
        resultado.setdefault(militar_id, set())

        cursor = ini
        while cursor <= fim:
            if data_inicio <= cursor <= data_fim:
                resultado[militar_id].add(cursor)
            cursor += timedelta(days=1)

        if config.bloquear_pre_ferias:
            cursor = max(data_inicio, ini - timedelta(days=folga_min_dias))
            while cursor <= min(data_fim, ini - timedelta(days=1)):
                resultado[militar_id].add(cursor)
                cursor += timedelta(days=1)

        if config.bloquear_pos_ferias:
            cursor = max(data_inicio, fim + timedelta(days=1))
            while cursor <= min(data_fim, fim + timedelta(days=folga_min_dias)):
                resultado[militar_id].add(cursor)
                cursor += timedelta(days=1)

    # ── 2. Carryover inter-mês ───────────────────────────────────────────────
    # TODOS os tipos de serviço (Preto+Vermelho+Roxo) do mesmo tipo_escala
    # são considerados — a folga é global dentro do tipo_escala.
    lookback = data_inicio - timedelta(days=janela_total)
    qs = EscalaItem.objects.filter(
        militar_id__in=militar_ids,
        calendario_dia__data__gte=lookback,
        calendario_dia__data__lt=data_inicio,
        forcar_escala=False,
    )
    if tipo_escala is not None:
        qs = qs.filter(escala__tipo_escala=tipo_escala)

    for militar_id, data_servico in qs.values_list('militar_id', 'calendario_dia__data'):
        resultado.setdefault(militar_id, set())
        cursor = max(data_inicio, data_servico + timedelta(days=1))
        fim_blq = data_servico + timedelta(days=janela_total)
        while cursor <= min(data_fim, fim_blq):
            resultado[militar_id].add(cursor)
            cursor += timedelta(days=1)

    return resultado
