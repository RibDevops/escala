"""
Motor de geração automática de escala — Algoritmo de Busca Reversa (Baixo para Cima).
Implementado conforme especificações: Método 1 (Primeiro válido) e Salto de Coluna (Opção A).
"""

from datetime import date as date_type, timedelta
from typing import Dict, List, Optional, Set, Tuple

def gerar_escala_multi_tipo(
    lista_militares: list,
    lista_dias: list,                     
    indisponibilidades: Dict[int, Set[date_type]],
    quadrinhos_inicio: Dict[str, Dict[int, int]],  
    ultimos_militares: Dict[str, Optional[int]],   
    config=None,
    tipo_escala=None,
) -> Tuple[Dict[str, List[Tuple]], Dict[str, Optional[int]]]:
    
    if not lista_militares or not lista_dias:
        return {}, {}

    n = len(lista_militares)
    idx_por_id = {m.id: i for i, m in enumerate(lista_militares)}

    # ── Janela de folga ──────────────────────────────────────────────────────
    duracao_dias = 1
    folga_dias   = 2 # Padrão 48h (2 dias)
    if config is not None:
        duracao_dias = config.duracao_servico_dias
        folga_dias   = config.folga_minima_dias
    if tipo_escala is not None and tipo_escala.folga_minima_horas is not None:
        folga_dias = max(1, tipo_escala.folga_minima_horas // 24)
    janela_bloqueio = duracao_dias + folga_dias

    # ── Estado por tipo de serviço ───────────────────────────────────────────
    counts: Dict[str, Dict[int, int]] = {}
    ponteiros: Dict[str, Tuple[int, int]] = {}
    novos_ultimos: Dict[str, Optional[int]] = {}

    tipos_servico = {}
    for dia in lista_dias:
        ts = dia.tipo_servico
        nome = ts.nome
        if nome not in tipos_servico:
            tipos_servico[nome] = ts
            qi = quadrinhos_inicio.get(nome, {})
            counts[nome] = {m.id: qi.get(m.id, 0) for m in lista_militares}

            # LÓGICA DE INÍCIO: Sempre começa do fundo (n-1) na menor coluna
            min_count = min(counts[nome].values())
            ponteiros[nome] = (n - 1, min_count) 
            novos_ultimos[nome] = None

    # ── Bloqueio global de folga ─────────────────────────────────────────────
    folga_global: Dict[int, Set[date_type]] = {m.id: set() for m in lista_militares}
    resultado: Dict[str, List[Tuple]] = {nome: [] for nome in tipos_servico}

    # ── Processamento cronológico ────────────────────────────────────────────
    for dia in sorted(lista_dias, key=lambda d: d.data):
        data = dia.data
        nome_tipo = dia.tipo_servico.nome
        cnt = counts[nome_tipo]
        
        # IMPORTANTE: Reinicia a busca do fundo para cada novo dia (conforme regra)
        min_count_atual = min(cnt.values())
        idx = n - 1
        coluna = min_count_atual

        atribuido = None
        tentativas_totais = 0
        
        # Busca em múltiplas colunas se necessário (Opção A)
        while tentativas_totais < n * 5: # n*5 para permitir percorrer várias colunas
            if idx < 0:
                idx = n - 1
                coluna += 1 # Salta para a próxima coluna à direita
            
            militar = lista_militares[idx]
            
            # Critério: O militar deve estar na "coluna" atual (ou ter menos serviços que ela)
            if cnt[militar.id] <= coluna:
                bloqueado = (
                    data in indisponibilidades.get(militar.id, set())
                    or data in folga_global.get(militar.id, set())
                )
                
                if not bloqueado:
                    atribuido = militar
                    break
            
            idx -= 1 # SOBE NA LISTA (Baixo para Cima)
            tentativas_totais += 1

        # ── Fallback: Se NINGUÉM estiver disponível em nenhuma coluna ──────────
        if atribuido is None:
            # Mantém como None para indicar erro na escala ou escolher o menos prejudicado
            pass

        # ── Registra ─────────────────────────────────────────────────────────
        if atribuido:
            cnt[atribuido.id] += 1
            novos_ultimos[nome_tipo] = atribuido.id
            
            # Propaga folga GLOBAL (bloqueia dias seguintes)
            if janela_bloqueio > 0:
                for k in range(1, janela_bloqueio + 1):
                    folga_global[atribuido.id].add(data + timedelta(days=k))

        resultado[nome_tipo].append((dia, atribuido))

    return resultado, novos_ultimos
