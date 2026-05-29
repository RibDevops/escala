"""
MotorEscalaVertical — Simulação computacional do processo humano de escalamento.

CONCEITO CENTRAL
================
O algoritmo imita exatamente o comportamento de um escalante humano
preenchendo uma planilha Excel operacional.

MATRIZ HISTÓRICA (persistida no banco via Quadrinho):
    Cada militar tem uma linha.
    As colunas representam o Nº do serviço (1º, 2º, 3º...).
    A célula contém a DATA do serviço.
    Contém APENAS serviços reais — é a fonte da verdade.

MATRIZ OPERACIONAL (temporária, em memória):
    Gerada no início de cada execução.
    Contém: serviços reais + folgas temporárias + indisponibilidades.
    A folga ocupa posições temporariamente — NÃO cria serviço real.
    Descartada ao fim da geração — NÃO persiste no banco.

ALGORITMO POR DIA
=================
    1. Ordenar militares: MENOR quantidade total de serviços reais (Quadrinho.total
       acumulado de TODOS os tipos de serviço do tipo_escala + ano corrente)
    2. Desempate: BASE → TOPO (mais moderno/júnior vem PRIMEIRO quando counts iguais)
       "de baixo para cima" = começa pelo Cb/Sd (mais moderno, fundo da lista)
    3. Verificar: sem indisponibilidade E sem folga global
    4. Primeiro válido recebe o serviço
    5. Folga marcada na matriz operacional (temporária, não conta como serviço)

FOLGA
=====
    - GLOBAL: Preto bloqueia Vermelho e vice-versa
    - Configurável em HORAS (TipoEscala.folga_minima_horas ou ConfiguracaoEscala)
    - NÃO persiste, NÃO aumenta o count real do militar

ORDEM DE GERAÇÃO
================
    Preto completo (todos os dias 01→31) → Vermelho completo → outros tipos
    (ordenado por TipoServico.ordem ASC)

FALLBACK CONTROLADO
===================
    1. Tentar todos em ordem (menor count → BASE→TOPO)
    2. Se todos bloqueados APENAS por folga → fallback com alerta (folga relaxada)
    3. Se todos com indisponibilidade real → dia vazio + alerta crítico
       (indisponibilidade NUNCA é quebrada)
"""

import logging
import calendar
from datetime import date, timedelta
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
    Militar,
    Quadrinho,
    TipoServico,
)

logger = logging.getLogger(__name__)


class MotorEscalaVertical:
    """
    Simula o processo humano de escalamento em planilha Excel.

    Estados durante a execução:
    - counts_historicos  : carregado do banco (Quadrinho), imutável
    - counts_operacional : histórico + serviços desta sessão (em memória)
    - folga_global       : bloqueios temporários por folga (em memória, descartado)
    - indisponibilidades : férias/licença do período (em memória, NUNCA quebrado)
    """

    def __init__(self, escala: Escala):
        self.escala = escala
        self.om = escala.organizacao_militar
        self.tipo_escala = escala.tipo_escala
        self.ano = escala.ano
        self.mes = escala.mes
        self.config = ConfiguracaoEscala.obter_para_om(self.om)

        # Militares (índice 0 = TOPO/mais antigo, índice n-1 = BASE/mais moderno)
        # Desempate: BASE → TOPO (mais moderno ganha quando counts iguais)
        self.lista_militares: List[Militar] = []
        self.indice_por_id: Dict[int, int] = {}
        self.desempate_por_id: Dict[int, int] = {}  # 0=BASE(prioridade), n-1=TOPO

        # MATRIZ HISTÓRICA: Quadrinho.total somado por militar (todos os tipos de serviço)
        self.counts_historicos: Dict[int, int] = {}

        # MATRIZ OPERACIONAL (temporária): histórico + gerados nesta sessão
        self.counts_operacional: Dict[int, int] = {}

        # Folga global (temporária): {militar_id: set(datas bloqueadas)}
        self.folga_global: Dict[int, Set[date]] = {}

        # Indisponibilidades reais: NUNCA quebradas
        self.indisponibilidades: Dict[int, Set[date]] = {}

        # Resultados e log operacional
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
        self._log(f"MOTOR ESCALA VERTICAL")
        self._log(f"{self.tipo_escala.nome} — {self.mes:02d}/{self.ano} — {self.om.sigla}")
        self._log("=" * 60)

        with transaction.atomic():
            self._limpar_itens_existentes()
            self._carregar_militares()
            self._carregar_matriz_historica()
            self._carregar_indisponibilidades()
            self._inicializar_carryover()
            self._processar_todos_os_tipos()

        self._log("\n" + "=" * 60)
        self._log(f"CONCLUÍDO: {self.alocacoes_criadas} serviço(s) gerado(s)")
        if self.dias_sem_militar:
            self._log(f"ATENÇÃO: {len(self.dias_sem_militar)} dia(s) sem cobertura")
        if self.alertas:
            self._log(f"ALERTAS: {len(self.alertas)}")
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

        Ordem: posto__ordem_hierarquica ASC → data_ultima_promocao ASC → nome_guerra ASC
          Índice 0  = TOPO (mais antigo, Ten/Cel/etc.)
          Índice -1 = BASE (mais moderno, Cb/Sd/mais júnior)

        A varredura de desempate é BASE → TOPO (mais moderno primeiro).
        Na chave de ordenação usamos +indice_por_id para que o maior índice
        (BASE / mais moderno) fique com valor MENOR e ganhe a disputa:
          sorted key = (count, n - 1 - indice)  →  índice maior = valor menor
        """
        self.lista_militares = list(
            Militar.objects.filter(organizacao_militar=self.om, ativo=True)
            .select_related('posto')
            .order_by('posto__ordem_hierarquica', 'data_ultima_promocao', 'nome_guerra')
        )

        if not self.lista_militares:
            raise ValidationError("Nenhum militar ativo nesta OM.")

        n = len(self.lista_militares)
        self.indice_por_id = {m.id: i for i, m in enumerate(self.lista_militares)}
        # Chave de desempate: inverte o índice para que a BASE (mais moderno) venha primeiro.
        # Cb João (índice n-1) → desempate_key = 0  (menor = prioridade mais alta)
        # Ten Silva (índice 0) → desempate_key = n-1 (maior = prioridade mais baixa)
        self.desempate_por_id = {m.id: (n - 1 - i) for i, m in enumerate(self.lista_militares)}

        for m in self.lista_militares:
            self.counts_historicos[m.id] = 0
            self.counts_operacional[m.id] = 0
            self.folga_global[m.id] = set()

        self._log(f"\nMilitares ({len(self.lista_militares)}) — TOPO=mais antigo, BASE=mais moderno:")
        for i, m in enumerate(self.lista_militares):
            posicao = "TOPO" if i == 0 else ("BASE" if i == len(self.lista_militares) - 1 else f"idx {i}")
            self._log(f"  {i}: {m.posto.sigla} {m.nome_guerra} [{posicao}] (desempate={self.desempate_por_id[m.id]})")

    # ==========================================================================
    # PASSO 3 — MATRIZ HISTÓRICA (Quadrinho → counts_historicos)
    # ==========================================================================

    def _carregar_matriz_historica(self):
        """
        Carrega a MATRIZ HISTÓRICA do banco (Quadrinho).

        Conta o TOTAL de serviços de cada militar:
          - Soma todos os tipos de serviço (Preto + Vermelho + Roxo)
          - Para este tipo_escala e ano
          - Usa Quadrinho.total = ajuste_inicial + quantidade

        Este total é a "coluna Count" da planilha — define a PRIORIDADE.
        Quem tem MENOS count tem mais prioridade.
        """
        mil_ids = [m.id for m in self.lista_militares]

        quadrinhos = Quadrinho.objects.filter(
            militar_id__in=mil_ids,
            tipo_escala=self.tipo_escala,
            ano=self.ano,
        )

        for q in quadrinhos:
            if q.militar_id in self.counts_historicos:
                self.counts_historicos[q.militar_id] += q.total

        # Sincronizar matriz operacional com histórica
        for mil_id in self.counts_historicos:
            self.counts_operacional[mil_id] = self.counts_historicos[mil_id]

        self._log("\nMATRIZ HISTÓRICA (count do banco = prioridade inicial):")
        for m in sorted(self.lista_militares, key=lambda x: self.counts_historicos[x.id]):
            self._log(f"  {m.nome_guerra:20s} → {self.counts_historicos[m.id]} serviço(s)")

    # ==========================================================================
    # PASSO 4 — INDISPONIBILIDADES REAIS (nunca quebradas)
    # ==========================================================================

    def _carregar_indisponibilidades(self):
        """
        Carrega indisponibilidades reais: férias, licença, missão, etc.

        ESTAS NUNCA SÃO QUEBRADAS — nem no fallback de último recurso.
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

        A folga é GLOBAL — qualquer tipo de serviço (Preto/Vermelho)
        do mês anterior bloqueia os primeiros dias deste mês.
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
        Carrega dias do mês, aplica overrides por escala, e processa tipo por tipo.

        Ordem: TipoServico.ordem ASC
          → Preto (ordem=0) completo primeiro
          → Vermelho (ordem=1) completo depois
          → etc.

        Override: se o escalante trocou o tipo de um dia nesta escala específica
          (EscalaCalendarioOverride), o CalendarioDia desse dia é substituído
          pelo CalendarioDia com o novo tipo — sem alterar o calendário global da OM.

        A folga_global é COMPARTILHADA entre todos os tipos:
        um serviço Preto bloqueia dias Vermelhos seguintes.
        """
        primeiro_dia, ultimo_dia = self._intervalo_mes()

        # Carregar todos os dias da OM para o mês
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

        # Aplicar overrides desta escala (não afeta o calendário global da OM)
        overrides = {
            ov.data: ov.tipo_servico
            for ov in EscalaCalendarioOverride.objects.filter(
                escala=self.escala,
            ).select_related('tipo_servico')
        }

        if overrides:
            self._log(f"\nOverrides de calendário nesta escala: {len(overrides)} dia(s)")
            # Para cada dia com override, encontra o CalendarioDia que já aponta
            # para o tipo correto (o override pode ter já atualizado o cd.tipo_servico)
            # ou usa o cd existente (que foi atualizado pela view ajax).
            dias_com_override = []
            for cd in todos_os_dias:
                if cd.data in overrides:
                    tipo_override = overrides[cd.data]
                    self._log(
                        f"  {cd.data:%d/%m}: {cd.tipo_servico.nome} → {tipo_override.nome}"
                    )
                    # O CalendarioDia já foi atualizado pela view ajax — usar como está
                    dias_com_override.append(cd)
                else:
                    dias_com_override.append(cd)
            todos_os_dias = dias_com_override

        # Agrupar por tipo mantendo a ordem por `tipo_servico.ordem`
        tipos_em_ordem: List[TipoServico] = []
        dias_por_tipo: Dict[str, List[CalendarioDia]] = {}
        for dia in sorted(todos_os_dias, key=lambda d: (d.tipo_servico.ordem, d.data)):
            nome = dia.tipo_servico.nome
            if nome not in dias_por_tipo:
                tipos_em_ordem.append(dia.tipo_servico)
                dias_por_tipo[nome] = []
            dias_por_tipo[nome].append(dia)

        self._log(
            f"\nTipos a processar em ordem: "
            + " → ".join(f"{t.nome} ({len(dias_por_tipo[t.nome])} dias)" for t in tipos_em_ordem)
        )

        for tipo_servico in tipos_em_ordem:
            dias = sorted(dias_por_tipo[tipo_servico.nome], key=lambda d: d.data)
            self._log(f"\n{'─' * 50}")
            self._log(f"TIPO: {tipo_servico.nome} ({len(dias)} dias)")
            self._log(f"{'─' * 50}")

            for dia in dias:
                self._processar_dia(dia)

    # ==========================================================================
    # PASSO 7 — PROCESSAR UM DIA
    # ==========================================================================

    def _processar_dia(self, dia: CalendarioDia):
        """
        Para um dia: encontra o próximo militar válido e registra.

        Ordenação de busca:
          1. Menor counts_operacional (menor count = maior prioridade)
          2. Desempate: BASE → TOPO (maior índice na lista de antiguidade → menor)

        Verificação por militar:
          ✓ Sem indisponibilidade (férias/licença)
          ✓ Sem folga global (qualquer tipo de serviço recente)

        Fallback:
          - Todos em folga (sem indisponibilidade): relaxa folga + alerta
          - Todos com indisponibilidade: dia vazio + alerta crítico
        """
        data = dia.data
        self._log(f"\n  {data.strftime('%d/%m/%Y')} ({dia.tipo_servico.nome})")

        # Ordenar: menor count → BASE (mais moderno) primeiro em empate
        # desempate_por_id: 0 = BASE (mais júnior, maior prioridade),
        #                   n-1 = TOPO (mais antigo, menor prioridade)
        militares_ordenados = sorted(
            self.lista_militares,
            key=lambda m: (
                self.counts_operacional[m.id],
                self.desempate_por_id[m.id],
            )
        )

        ordem_resumo = " → ".join(
            f"{m.nome_guerra}[{self.counts_operacional[m.id]}]"
            for m in militares_ordenados
        )
        self._log(f"    Verificando (menor count primeiro, BASE→TOPO): {ordem_resumo}")

        # Tentativa principal: sem indisponibilidade E sem folga
        for militar in militares_ordenados:
            motivo = self._verificar_militar(militar, data)
            if motivo == 'OK':
                self._registrar_servico(dia, militar, forcado=False)
                return
            self._log(f"    ✗ {militar.nome_guerra} — {motivo}")

        # Fallback: classificar bloqueios
        bloqueados_so_por_folga = [
            m for m in militares_ordenados
            if data not in self.indisponibilidades.get(m.id, set())
            and data in self.folga_global.get(m.id, set())
        ]

        if bloqueados_so_por_folga:
            # Relaxar folga para o de menor count (já está ordenado)
            escolhido = bloqueados_so_por_folga[0]
            alerta = (
                f"⚠ {data.strftime('%d/%m/%Y')} [{dia.tipo_servico.nome}]: "
                f"todos em folga. Fallback: folga relaxada → {escolhido.nome_guerra}"
            )
            self.alertas.append(alerta)
            self._log(f"    {alerta}")
            self._registrar_servico(dia, escolhido, forcado=True)
        else:
            # Todos com indisponibilidade real → dia vazio
            alerta = (
                f"🚨 {data.strftime('%d/%m/%Y')} [{dia.tipo_servico.nome}]: "
                f"nenhum militar disponível — todos com férias/licença. Dia sem cobertura."
            )
            self.alertas.append(alerta)
            self._log(f"    {alerta}")
            self.dias_sem_militar.append(data)

    def _verificar_militar(self, militar: Militar, data: date) -> str:
        """
        Verifica se o militar pode ser escalado na data.

        Returns 'OK' ou descrição do bloqueio.
        """
        if data in self.indisponibilidades.get(militar.id, set()):
            return 'indisponibilidade (férias/licença)'
        if data in self.folga_global.get(militar.id, set()):
            return 'em período de folga'
        return 'OK'

    # ==========================================================================
    # REGISTRAR SERVIÇO
    # ==========================================================================

    def _registrar_servico(self, dia: CalendarioDia, militar: Militar, forcado: bool):
        """
        Registra o serviço no banco e atualiza a MATRIZ OPERACIONAL (em memória).

        Persistido no banco:
          - EscalaItem (serviço real)
          - Quadrinho.incrementar (histórico real)

        Em memória apenas (descartado ao fim):
          - counts_operacional[militar.id] += 1
          - folga_global[militar.id] += próximos N dias
        """
        obs = 'Motor Vertical' + (' [folga relaxada — fallback]' if forcado else '')

        EscalaItem.objects.create(
            escala=self.escala,
            militar=militar,
            calendario_dia=dia,
            observacao=obs,
            forcar_escala=forcado,
        )

        # Persistir no histórico (Quadrinho)
        Quadrinho.incrementar(
            militar=militar,
            tipo_escala=self.tipo_escala,
            tipo_servico=dia.tipo_servico,
            ano=self.ano,
        )

        # Atualizar MATRIZ OPERACIONAL (em memória)
        count_anterior = self.counts_operacional[militar.id]
        self.counts_operacional[militar.id] += 1

        # Marcar folga GLOBAL temporária (não persiste, não conta como serviço)
        janela = self._janela_bloqueio()
        for k in range(1, janela + 1):
            self.folga_global[militar.id].add(dia.data + timedelta(days=k))

        self.alocacoes_criadas += 1
        self._log(
            f"    ✓ {militar.nome_guerra} "
            f"(count: {count_anterior} → {self.counts_operacional[militar.id]})"
            f" | folga até: {(dia.data + timedelta(days=janela)).strftime('%d/%m')}"
            + (" [FALLBACK]" if forcado else "")
        )

    # ==========================================================================
    # HELPERS
    # ==========================================================================

    def _folga_dias(self) -> int:
        """Folga mínima em dias (usa override do TipoEscala ou config global)."""
        if self.tipo_escala.folga_minima_horas is not None:
            horas = self.tipo_escala.folga_minima_horas
        else:
            horas = self.config.folga_minima_dias * 24
        return max(1, (horas + 23) // 24)  # arredonda para cima

    def _janela_bloqueio(self) -> int:
        """Dias totais bloqueados após serviço = duração_serviço + folga_mínima."""
        return self.config.duracao_servico_dias + self._folga_dias()

    def _intervalo_mes(self) -> Tuple[date, date]:
        """Retorna (primeiro_dia, ultimo_dia) do mês."""
        primeiro_dia = date(self.ano, self.mes, 1)
        ultimo_num = calendar.monthrange(self.ano, self.mes)[1]
        return primeiro_dia, date(self.ano, self.mes, ultimo_num)

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
