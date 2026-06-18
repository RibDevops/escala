"""
MotorEscalaVertical v2 — Navegação por Quadrinho com Snapshot Operacional

CONCEITO CENTRAL
================
O motor reproduz o procedimento manual da planilha. Não é uma otimização
matemática — é uma simulação fiel do escalante humano navegando o quadrinho.

QUADRINHO (histórico oficial, por tipo de serviço)
===================================================
Cada tipo de serviço (Preta, Vermelha, Roxa) tem seu próprio quadrinho.
As colunas representam o Nº do serviço (S1=1º, S2=2º...).
A posição de cada militar = ajuste_inicial + quantidade + lançamentos_manuais.

SNAPSHOT OPERACIONAL (temporário, por serviço)
===============================================
Antes de cada serviço, é criado um Snapshot: visão temporária do quadrinho
com os bloqueios do dia (folga, indisponibilidade) aplicados.
O Snapshot não altera o quadrinho — é descartado após cada serviço.

ALGORITMO DE NAVEGAÇÃO
======================
1. Menor coluna (menor count do tipo) → mais prioritária
2. Dentro da coluna: BASE → TOPO (mais moderno primeiro)
3. Primeiro DISPONIVEL vence
4. Se coluna inteira bloqueada: próxima coluna à direita, reinicia do BASE
5. Cada serviço gera nova execução completa

FOLGA GLOBAL
============
Um serviço Preta bloqueia Vermelha e vice-versa.
Folga existe apenas em memória — não altera o quadrinho.
Carry-over: serviços do mês anterior propagam folga para o início do mês.

ORDEM DE GERAÇÃO
================
Preta completa → Vermelha completa → demais tipos (TipoServico.ordem ASC).
A folga_global é compartilhada entre todos os tipos.

FALLBACK
========
1. Militar com indisponibilidade real: NUNCA escalado automaticamente.
2. Militar em folga: escalado apenas se config.permitir_quebrar_folga=True,
   com alerta ⚠ e forcar_escala=True.
3. Todos indisponíveis: dia vazio + alerta crítico 🚨.
"""

import logging
import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from django.db import transaction
from django.db.models import F
from django.core.exceptions import ValidationError

from .models import (
    CalendarioDia,
    ConfiguracaoEscala,
    Escala,
    EscalaCalendarioOverride,
    EscalaItem,
    Indisponibilidade,
    LancamentoManualQuadrinho,
    Militar,
    Quadrinho,
    TipoServico,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# SNAPSHOT OPERACIONAL — estruturas de dados
# ==============================================================================

class EstadoCelula(Enum):
    DISPONIVEL   = "DISPONIVEL"
    FOLGA        = "FOLGA"
    INDISPONIVEL = "INDISPONIVEL"


@dataclass
class LinhaSnapshot:
    """Representa a situação de um militar no Snapshot de um serviço."""
    militar: Militar
    indice: int           # posição na lista de antiguidade (0=TOPO, n-1=BASE)
    coluna: int           # count atual do tipo (ajuste + quantidade + manuais)
    estado: EstadoCelula
    motivo: Optional[str] = None


@dataclass
class SnapshotOperacional:
    """Visão temporária do quadrinho para um dia e tipo de serviço."""
    data: date
    tipo_servico: TipoServico
    linhas: List[LinhaSnapshot] = field(default_factory=list)


# ==============================================================================
# MOTOR PRINCIPAL
# ==============================================================================

class MotorEscalaVertical:
    """
    Simula o processo humano de escalamento em planilha.

    Estados durante a execução:
    - counts_historicos_por_tipo  : carregado do banco por tipo, imutável
    - counts_operacional_por_tipo : histórico + gerados nesta sessão, por tipo
    - folga_global                : bloqueios temporários (descartados ao fim)
    - indisponibilidades          : férias/licença (NUNCA quebradas)
    """

    def __init__(self, escala: Escala):
        self.escala = escala
        self.om = escala.organizacao_militar
        self.tipo_escala = escala.tipo_escala
        self.ano = escala.ano
        self.mes = escala.mes
        self.config = ConfiguracaoEscala.obter_para_om(self.om)

        # Militares: índice 0=TOPO/mais antigo, índice n-1=BASE/mais moderno
        self.lista_militares: List[Militar] = []
        self.indice_por_id: Dict[int, int] = {}

        # Counts por tipo de serviço:
        #   {tipo_servico_id: {militar_id: count}}
        #   count = ajuste_inicial + quantidade + soma(lancamentos_manuais)
        self.counts_historicos_por_tipo: Dict[int, Dict[int, int]] = {}
        self.counts_operacional_por_tipo: Dict[int, Dict[int, int]] = {}

        # Folga global (temporária): {militar_id: set(datas bloqueadas)}
        self.folga_global: Dict[int, Set[date]] = {}

        # Indisponibilidades reais: {militar_id: set(datas)}
        self.indisponibilidades: Dict[int, Set[date]] = {}

        # Resultados
        self.alocacoes_criadas: int = 0
        self.dias_sem_militar: List[date] = []
        self.alertas: List[str] = []
        self.log: List[str] = []

    # ==========================================================================
    # MÉTODO PRINCIPAL
    # ==========================================================================

    def gerar(self) -> Dict:
        """
        Executa a geração completa da escala.

        Retorna dict com: sucesso, alocacoes_criadas, dias_sem_militar, alertas, log
        """
        self._log("=" * 60)
        self._log("MOTOR ESCALA VERTICAL v2 — Snapshot por Quadrinho")
        self._log(f"{self.tipo_escala.nome} — {self.mes:02d}/{self.ano} — {self.om.sigla}")
        self._log("=" * 60)

        with transaction.atomic():
            self._limpar_itens_existentes()
            self._carregar_militares()
            self._carregar_quadrinhos()
            self._carregar_indisponibilidades()
            self._inicializar_carryover()
            self._processar_todos_os_tipos()

        self._log("\n" + "=" * 60)
        self._log(f"CONCLUÍDO: {self.alocacoes_criadas} serviço(s) gerado(s)")
        if self.dias_sem_militar:
            self._log(f"ATENÇÃO: {len(self.dias_sem_militar)} dia(s) sem cobertura")
        if self.alertas:
            self._log(f"ALERTAS ({len(self.alertas)}):")
            for a in self.alertas:
                self._log(f"  {a}")
        self._log("=" * 60)

        return {
            'sucesso': True,
            'alocacoes_criadas': self.alocacoes_criadas,
            'dias_sem_militar': len(self.dias_sem_militar),
            'alertas': self.alertas,
            'log': self.log,
        }

    # ==========================================================================
    # PASSO 1 — LIMPEZA (com reversão de Quadrinhos)
    # ==========================================================================

    def _limpar_itens_existentes(self):
        """
        Remove todos os itens da escala e reverte os Quadrinhos correspondentes.

        Cada item gerado pelo sistema incrementou Quadrinho.quantidade em 1.
        Ao apagar, decrementamos para manter consistência.
        """
        itens = list(
            self.escala.itens.select_related('militar', 'calendario_dia__tipo_servico')
        )
        if not itens:
            self._log("Sem itens existentes para remover.")
            return

        self._log(f"Removendo {len(itens)} item(ns) existentes e revertendo Quadrinhos...")

        for item in itens:
            Quadrinho.objects.filter(
                militar=item.militar,
                tipo_escala=self.tipo_escala,
                tipo_servico=item.calendario_dia.tipo_servico,
                ano=self.ano,
                quantidade__gt=0,
            ).update(quantidade=F('quantidade') - 1)

        self.escala.itens.all().delete()
        self._log(f"  → {len(itens)} item(ns) removidos, Quadrinhos revertidos.")

    # ==========================================================================
    # PASSO 2 — CARREGAR MILITARES
    # ==========================================================================

    def _carregar_militares(self):
        """
        Carrega militares ativos ordenados por antiguidade.

        Ordem (TOPO → BASE):
          1º posto__ordem_hierarquica ASC  — menor = mais antigo
          2º data_ultima_promocao     ASC  — mais velha = mais antigo no posto
          3º nota                     DESC — maior nota = mais antigo
          4º nome_guerra              ASC  — desempate estável

        índice 0  = TOPO (mais antigo)
        índice n-1 = BASE (mais moderno) — primeiro a ser escalado em empate
        """
        self.lista_militares = list(
            Militar.objects.filter(organizacao_militar=self.om, ativo=True)
            .select_related('posto')
            .order_by('posto__ordem_hierarquica', 'data_ultima_promocao', '-nota', 'nome_guerra')
        )

        if not self.lista_militares:
            raise ValidationError("Nenhum militar ativo nesta OM.")

        n = len(self.lista_militares)
        self.indice_por_id = {m.id: i for i, m in enumerate(self.lista_militares)}

        for m in self.lista_militares:
            self.folga_global[m.id] = set()

        self._log(f"\nMilitares ({n}) — índice 0=TOPO(mais antigo), {n-1}=BASE(mais moderno):")
        for i, m in enumerate(self.lista_militares):
            label = "TOPO" if i == 0 else ("BASE" if i == n - 1 else f"idx {i}")
            self._log(f"  {i}: {m.posto.sigla} {m.nome_guerra} [{label}]")

    # ==========================================================================
    # PASSO 3 — CARREGAR QUADRINHOS POR TIPO
    # ==========================================================================

    def _carregar_quadrinhos(self):
        """
        Carrega counts históricos para referência/log.

        REGRA: Ciclo independente por mês — a geração sempre começa do zero
        (counts_operacional = 0 para todos). O histórico (ajuste_inicial +
        quantidade + lançamentos) é carregado apenas para exibição no log;
        NÃO afeta a ordem de escalamento.

        Dentro de um mês, a ordem é determinada exclusivamente pela posição na
        lista de antiguidade: BASE (mais moderno) → TOPO (mais antigo).
        """
        mil_ids = [m.id for m in self.lista_militares]

        # 1. Quadrinhos do banco: ajuste_inicial + quantidade (somente para log)
        quadrinhos = Quadrinho.objects.filter(
            militar_id__in=mil_ids,
            tipo_escala=self.tipo_escala,
            ano=self.ano,
        ).select_related('tipo_servico')

        for q in quadrinhos:
            ts_id = q.tipo_servico_id
            if ts_id not in self.counts_historicos_por_tipo:
                self.counts_historicos_por_tipo[ts_id] = {m.id: 0 for m in self.lista_militares}
            self.counts_historicos_por_tipo[ts_id][q.militar_id] = q.total

        # 2. Lançamentos manuais: também no histórico (somente para log)
        lancamentos = LancamentoManualQuadrinho.objects.filter(
            militar_id__in=mil_ids,
            tipo_escala=self.tipo_escala,
            ano=self.ano,
        ).select_related('tipo_servico')

        for lm in lancamentos:
            ts_id = lm.tipo_servico_id
            if ts_id not in self.counts_historicos_por_tipo:
                self.counts_historicos_por_tipo[ts_id] = {m.id: 0 for m in self.lista_militares}
            self.counts_historicos_por_tipo[ts_id][lm.militar_id] += lm.quantidade

        # 3. Operacional SEMPRE começa do zero — ciclo independente por mês.
        #    Não copiar histórico: a posição de antiguidade (BASE→TOPO) é que
        #    define quem serve primeiro, não o saldo acumulado.
        self.counts_operacional_por_tipo = {}

        # Log (mostra histórico para referência, mas não é usado na geração)
        self._log("\nQUADRINHOS HISTÓRICOS (somente referência — geração começa do zero):")
        for ts_id, counts in self.counts_historicos_por_tipo.items():
            try:
                ts = TipoServico.objects.get(id=ts_id)
                ts_nome = ts.nome
            except TipoServico.DoesNotExist:
                ts_nome = str(ts_id)
            self._log(f"  [{ts_nome}]")
            for m in sorted(self.lista_militares, key=lambda x: self.indice_por_id[x.id]):
                self._log(
                    f"    histórico {counts.get(m.id, 0):>3} "
                    f"— {m.posto.sigla} {m.nome_guerra}"
                )

    # ==========================================================================
    # PASSO 4 — INDISPONIBILIDADES REAIS (nunca quebradas)
    # ==========================================================================

    def _carregar_indisponibilidades(self):
        """
        Carrega indisponibilidades reais: férias, licença, missão, etc.

        ESTAS NUNCA SÃO QUEBRADAS.
        Inclui bloqueios pré/pós-férias se configurado.
        """
        primeiro_dia, ultimo_dia = self._intervalo_mes()
        folga_td = timedelta(days=self._folga_dias())

        registros = Indisponibilidade.objects.filter(
            militar_id__in=[m.id for m in self.lista_militares],
            tipo__exclui_do_sorteio=True,
            data_inicio__lte=ultimo_dia,
            data_fim__gte=primeiro_dia - folga_td,
        ).values_list('militar_id', 'data_inicio', 'data_fim')

        for mil_id, ini, fim in registros:
            self.indisponibilidades.setdefault(mil_id, set())

            cursor = ini
            while cursor <= fim:
                if primeiro_dia <= cursor <= ultimo_dia:
                    self.indisponibilidades[mil_id].add(cursor)
                cursor += timedelta(days=1)

            if self.config.bloquear_pre_ferias:
                cursor = max(primeiro_dia, ini - folga_td)
                while cursor < ini and cursor <= ultimo_dia:
                    self.indisponibilidades[mil_id].add(cursor)
                    cursor += timedelta(days=1)

            if self.config.bloquear_pos_ferias:
                cursor = fim + timedelta(days=1)
                while cursor <= min(ultimo_dia, fim + folga_td):
                    self.indisponibilidades[mil_id].add(cursor)
                    cursor += timedelta(days=1)

        if self.indisponibilidades:
            self._log("\nIndisponibilidades do período:")
            for mil_id, datas in self.indisponibilidades.items():
                m = next(x for x in self.lista_militares if x.id == mil_id)
                datas_str = ", ".join(d.strftime('%d/%m') for d in sorted(datas))
                self._log(f"  {m.nome_guerra}: {datas_str}")

    # ==========================================================================
    # PASSO 5 — CARRY-OVER (folga inter-mês)
    # ==========================================================================

    def _inicializar_carryover(self):
        """
        Inicializa folga_global com carry-over do mês anterior.

        Se o militar teve serviço nos últimos N dias antes deste mês,
        os primeiros dias do mês ficam bloqueados por folga.
        A folga é GLOBAL — qualquer tipo (Preta/Vermelha) do mês anterior
        bloqueia os primeiros dias deste mês.
        """
        primeiro_dia, _ = self._intervalo_mes()
        janela_td = timedelta(days=self._janela_bloqueio())
        lookback = primeiro_dia - janela_td

        servicos_anteriores = EscalaItem.objects.filter(
            escala__organizacao_militar=self.om,
            escala__tipo_escala=self.tipo_escala,
            militar_id__in=[m.id for m in self.lista_militares],
            calendario_dia__data__gte=lookback,
            calendario_dia__data__lt=primeiro_dia,
            forcar_escala=False,
        ).values_list('militar_id', 'calendario_dia__data')

        carryover_count = 0
        for mil_id, data_servico in servicos_anteriores:
            fim_folga = data_servico + janela_td
            cursor = max(primeiro_dia, data_servico + timedelta(days=1))
            while cursor <= fim_folga:
                self.folga_global[mil_id].add(cursor)
                cursor += timedelta(days=1)
            carryover_count += 1

        if carryover_count:
            self._log(
                f"\nCarry-over: {carryover_count} serviço(s) do mês anterior "
                f"geraram bloqueio de folga nos primeiros dias do mês."
            )

    # ==========================================================================
    # PASSO 6 — PROCESSAR TIPO POR TIPO
    # ==========================================================================

    def _processar_todos_os_tipos(self):
        """
        Carrega dias do mês, aplica overrides e processa tipo por tipo.

        Ordem: TipoServico.ordem ASC (Preta → Vermelha → Roxa...).
        A folga_global é compartilhada entre todos os tipos.
        Cada tipo usa seu próprio quadrinho (counts_operacional_por_tipo[ts.id]).
        """
        primeiro_dia, ultimo_dia = self._intervalo_mes()

        todos_os_dias = list(
            CalendarioDia.objects.filter(
                organizacao_militar=self.om,
                data__range=(primeiro_dia, ultimo_dia),
            )
            .select_related('tipo_servico')
            .order_by('data')
        )

        if not todos_os_dias:
            raise ValidationError(
                f"Nenhum dia cadastrado no calendário para {self.mes}/{self.ano}. "
                "Gere o calendário automático primeiro."
            )

        # Aplicar overrides desta escala
        overrides = {
            ov.data: ov.tipo_servico
            for ov in EscalaCalendarioOverride.objects.filter(
                escala=self.escala,
            ).select_related('tipo_servico')
        }
        if overrides:
            self._log(f"\nOverrides de calendário nesta escala: {len(overrides)} dia(s)")
            for cd in todos_os_dias:
                if cd.data in overrides:
                    self._log(f"  {cd.data:%d/%m}: {cd.tipo_servico.nome} → {overrides[cd.data].nome}")

        # Agrupar por tipo mantendo ordem por TipoServico.ordem
        tipos_em_ordem: List[TipoServico] = []
        dias_por_tipo: Dict[str, List[CalendarioDia]] = {}
        for dia in sorted(todos_os_dias, key=lambda d: (d.tipo_servico.ordem, d.data)):
            nome = dia.tipo_servico.nome
            if nome not in dias_por_tipo:
                tipos_em_ordem.append(dia.tipo_servico)
                dias_por_tipo[nome] = []
            dias_por_tipo[nome].append(dia)

        self._log(
            f"\nOrdem de geração: "
            + " → ".join(f"{t.nome} ({len(dias_por_tipo[t.nome])} dias)" for t in tipos_em_ordem)
        )

        for tipo_servico in tipos_em_ordem:
            # Garantir entrada no dicionário operacional para tipos sem histórico
            if tipo_servico.id not in self.counts_operacional_por_tipo:
                self.counts_operacional_por_tipo[tipo_servico.id] = {
                    m.id: 0 for m in self.lista_militares
                }

            dias = sorted(dias_por_tipo[tipo_servico.nome], key=lambda d: d.data)
            self._log(f"\n{'─' * 50}")
            self._log(f"TIPO: {tipo_servico.nome} ({len(dias)} dias)")
            self._log(f"{'─' * 50}")

            for dia in dias:
                self._processar_dia(dia)

    # ==========================================================================
    # PASSO 7 — PROCESSAR UM DIA (Snapshot + Navegação)
    # ==========================================================================

    def _processar_dia(self, dia: CalendarioDia):
        """
        Para cada serviço:
          1. Cria Snapshot Operacional (quadrinho + bloqueios do dia)
          2. Navega: menor coluna → BASE → TOPO
          3. Registra o primeiro DISPONIVEL
          4. Fallback se ninguém disponível
        """
        data = dia.data
        ts = dia.tipo_servico
        counts_tipo = self.counts_operacional_por_tipo[ts.id]

        self._log(f"\n  {data.strftime('%d/%m/%Y')} ({ts.nome})")

        # Montar Snapshot
        snapshot = self._criar_snapshot(data, ts, counts_tipo)
        self._log(self._fmt_snapshot(snapshot))

        # Navegar: menor coluna → BASE → TOPO
        escolhida = self._navegar_snapshot(snapshot)

        if escolhida is not None:
            self._registrar_servico(dia, escolhida.militar, forcado=False)
            return

        # Nenhum DISPONIVEL encontrado — fallback
        self._tratar_fallback(dia, snapshot)

    def _criar_snapshot(
        self,
        data: date,
        tipo_servico: TipoServico,
        counts_tipo: Dict[int, int],
    ) -> SnapshotOperacional:
        """
        Cria o Snapshot Operacional para um dia e tipo de serviço.

        Para cada militar:
          coluna = count atual do tipo (posição no quadrinho)
          estado = DISPONIVEL | FOLGA | INDISPONIVEL

        O Snapshot não altera o quadrinho real.
        """
        linhas = []
        for i, militar in enumerate(self.lista_militares):
            coluna = counts_tipo[militar.id]

            if data in self.indisponibilidades.get(militar.id, set()):
                estado = EstadoCelula.INDISPONIVEL
                motivo = "férias/licença"
            elif data in self.folga_global.get(militar.id, set()):
                estado = EstadoCelula.FOLGA
                motivo = "folga global"
            else:
                estado = EstadoCelula.DISPONIVEL
                motivo = None

            linhas.append(LinhaSnapshot(
                militar=militar,
                indice=i,
                coluna=coluna,
                estado=estado,
                motivo=motivo,
            ))

        return SnapshotOperacional(data=data, tipo_servico=tipo_servico, linhas=linhas)

    def _navegar_snapshot(self, snapshot: SnapshotOperacional) -> Optional[LinhaSnapshot]:
        """
        Navega o Snapshot: menor coluna → BASE → TOPO.

        Algoritmo fiel à planilha:
          1. Encontra a menor coluna (menor count entre todos os militares)
          2. Percorre a coluna de baixo para cima (BASE=mais moderno → TOPO=mais antigo)
          3. Retorna o primeiro DISPONIVEL encontrado
          4. Se a coluna inteira for bloqueada, passa para a próxima coluna à direita
          5. Ao mudar de coluna, reinicia a busca pelo BASE
        """
        # Colunas em ordem crescente (menor = mais prioritária)
        colunas = sorted(set(l.coluna for l in snapshot.linhas))

        for coluna in colunas:
            candidatos = [l for l in snapshot.linhas if l.coluna == coluna]
            # BASE → TOPO: índice decrescente (maior índice = BASE = mais moderno)
            candidatos.sort(key=lambda l: -l.indice)

            coluna_tem_disponivel = False
            for linha in candidatos:
                if linha.estado == EstadoCelula.DISPONIVEL:
                    coluna_tem_disponivel = True
                    return linha

            if not coluna_tem_disponivel:
                self._log(
                    f"    Coluna {coluna}: todos bloqueados "
                    f"({', '.join(l.militar.nome_guerra + '=' + l.estado.value for l in candidatos)})"
                    f" → próxima coluna"
                )

        return None

    def _tratar_fallback(self, dia: CalendarioDia, snapshot: SnapshotOperacional):
        """
        Fallback quando nenhum militar está DISPONIVEL.

        Regra:
          - Militares com FOLGA (sem indisponibilidade real):
              se config.permitir_quebrar_folga=True → escala o de menor coluna
              (BASE no empate) com alerta ⚠ e forcar_escala=True
              se False → dia sem cobertura + alerta 🚨
          - Todos com INDISPONIVEL: dia sem cobertura + alerta crítico 🚨
        """
        data = dia.data

        bloqueados_por_folga = [
            l for l in snapshot.linhas
            if l.estado == EstadoCelula.FOLGA
        ]

        if bloqueados_por_folga and self.config.permitir_quebrar_folga:
            # Menor coluna, BASE primeiro no empate
            bloqueados_por_folga.sort(key=lambda l: (l.coluna, -l.indice))
            escolhida = bloqueados_por_folga[0]
            alerta = (
                f"⚠ {data.strftime('%d/%m/%Y')} [{dia.tipo_servico.nome}]: "
                f"todos em folga — folga relaxada → {escolhida.militar.nome_guerra}"
            )
            self.alertas.append(alerta)
            self._log(f"    {alerta}")
            self._registrar_servico(dia, escolhida.militar, forcado=True)

        else:
            if bloqueados_por_folga:
                motivo = "configuração não permite quebrar folga"
            else:
                motivo = "todos com férias/licença"
            alerta = (
                f"🚨 {data.strftime('%d/%m/%Y')} [{dia.tipo_servico.nome}]: "
                f"nenhum militar disponível ({motivo}) — dia sem cobertura."
            )
            self.alertas.append(alerta)
            self._log(f"    {alerta}")
            self.dias_sem_militar.append(data)

    # ==========================================================================
    # REGISTRAR SERVIÇO
    # ==========================================================================

    def _registrar_servico(self, dia: CalendarioDia, militar: Militar, forcado: bool):
        """
        Registra o serviço no banco e atualiza o estado operacional.

        Persistido no banco:
          - EscalaItem (serviço real)
          - Quadrinho.incrementar (count do tipo específico)

        Em memória (descartado ao fim):
          - counts_operacional_por_tipo[ts.id][mil.id] += 1
          - folga_global[mil.id] += próximos N dias (global para todos os tipos)
        """
        ts = dia.tipo_servico
        obs = 'Motor v2' + (' [folga relaxada — fallback]' if forcado else '')

        EscalaItem.objects.create(
            escala=self.escala,
            militar=militar,
            calendario_dia=dia,
            observacao=obs,
            forcar_escala=forcado,
        )

        # Persistir no quadrinho do tipo específico
        Quadrinho.incrementar(
            militar=militar,
            tipo_escala=self.tipo_escala,
            tipo_servico=ts,
            ano=self.ano,
        )

        # Atualizar count operacional SOMENTE do tipo gerado
        count_anterior = self.counts_operacional_por_tipo[ts.id][militar.id]
        self.counts_operacional_por_tipo[ts.id][militar.id] += 1

        # Folga GLOBAL: bloqueia este militar para TODOS os tipos
        janela = self._janela_bloqueio()
        for k in range(1, janela + 1):
            self.folga_global[militar.id].add(dia.data + timedelta(days=k))

        self.alocacoes_criadas += 1
        self._log(
            f"    ✓ {militar.posto.sigla} {militar.nome_guerra}"
            f" [{ts.nome}] col {count_anterior} → {count_anterior + 1}"
            f" | folga até {(dia.data + timedelta(days=janela)).strftime('%d/%m')}"
            + (" [FALLBACK]" if forcado else "")
        )

    # ==========================================================================
    # HELPERS
    # ==========================================================================

    def _folga_dias(self) -> int:
        """Folga mínima em dias inteiros (arredondado para cima)."""
        horas = self.tipo_escala.folga_minima_horas
        if horas is None:
            horas = self.config.folga_minima_horas
        return max(1, (horas + 23) // 24)

    def _janela_bloqueio(self) -> int:
        """Dias totais bloqueados após serviço = duração + folga mínima."""
        return self.config.duracao_servico_dias + self._folga_dias()

    def _intervalo_mes(self) -> Tuple[date, date]:
        primeiro_dia = date(self.ano, self.mes, 1)
        ultimo_num = calendar.monthrange(self.ano, self.mes)[1]
        return primeiro_dia, date(self.ano, self.mes, ultimo_num)

    def _fmt_snapshot(self, snapshot: SnapshotOperacional) -> str:
        """Formata o Snapshot para o log."""
        linhas = sorted(snapshot.linhas, key=lambda l: (l.coluna, -l.indice))
        header = f"    Snapshot {snapshot.data:%d/%m/%Y} [{snapshot.tipo_servico.nome}] (col=count acumulado do tipo):"
        corpo = "\n".join(
            f"      col {l.coluna:>3} — {l.militar.posto.sigla} {l.militar.nome_guerra:<20} "
            f"[{'BASE' if l.indice == len(snapshot.linhas) - 1 else ('TOPO' if l.indice == 0 else f'idx {l.indice}')}]"
            f" → {l.estado.value}"
            + (f" ({l.motivo})" if l.motivo else "")
            for l in linhas
        )
        return header + "\n" + corpo

    def _log(self, msg: str):
        self.log.append(msg)
        logger.debug(msg)


# ==============================================================================
# FUNÇÃO DE ALTO NÍVEL
# ==============================================================================

def gerar_escala_vertical(escala: Escala) -> Dict:
    """
    Instancia e executa o MotorEscalaVertical.

    Args:
        escala: Instância de Escala em status 'rascunho' ou 'previsao'.

    Returns:
        Dict com: sucesso, alocacoes_criadas, dias_sem_militar, alertas, log

    Raises:
        ValidationError: Se a escala não estiver no status correto,
                        ou se não houver militares/dias cadastrados.
    """
    if escala.status not in ('rascunho', 'previsao'):
        raise ValidationError(
            "Apenas escalas em Rascunho ou Previsão podem ser geradas."
        )

    motor = MotorEscalaVertical(escala)
    return motor.gerar()
