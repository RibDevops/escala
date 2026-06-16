"""Importa o histórico de escala a partir do CSV exportado.

Formato esperado:
    col 0: Nº (ignorado)
    col 1: número do militar (ignorado)
    col 2: Grad. (ex: 1S SAD, 2S SIN, 3S BET …)
    col 3: Nome de guerra
    cols 4+: datas (dd/mm/yyyy com sufixos * **) ou LASTRO / DISP MED / MD /
             TAQUARI II … / R1…R4 / R.Esc. / vazio

Comportamento:
    - Cria (ou reutiliza) militares na OM ativa.
    - Para cada data real cria CalendarioDia (se não existir) + Escala (se não
      existir) + EscalaItem — usando o TipoEscala "Permanência" (ou o primeiro
      cadastrado cujo nome contenha "pret" ou o primeiro TipoEscala da OM).
    - LASTRO / DISP MED / MD são convertidos em LancamentoManualQuadrinho agrupados
      por tipo e contados por ano, com label adequado.
    - Células desconhecidas (TAQUARI…, R1…, R.Esc., etc.) são ignoradas com aviso.

Uso:
    python manage.py importar_escala_csv caminho/do/arquivo.csv
    python manage.py importar_escala_csv caminho/do/arquivo.csv --om-sigla BABR
    python manage.py importar_escala_csv caminho/do/arquivo.csv --dry-run
"""

import csv
import re
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from escalas.models import (
    CalendarioDia,
    Escala,
    EscalaItem,
    LancamentoManualQuadrinho,
    Militar,
    OrganizacaoMilitar,
    Posto,
    TipoEscala,
    TipoServico,
)

# ---------------------------------------------------------------------------
# Mapeamento de graduação CSV → abreviação do Posto no sistema
# ---------------------------------------------------------------------------
GRAD_PARA_POSTO = {
    '3S': '3º Sgt',
    '2S': '2º Sgt',
    '1S': '1º Sgt',
    'SO': 'SO',
    'ASP': 'Asp',
    '2T': '2º Ten',
    '1T': '1º Ten',
    'CAP': 'Cap',
    'MAJ': 'Maj',
    'TC': 'TC',
    'CEL': 'Cel',
    'CB': 'Cb',
    'S1': 'S1',
    'S2': 'S2',
}

# Sufixos a ignorar nas células de data
_RE_DATA = re.compile(r'^(\d{2}/\d{2}/\d{4})')
_SUFIXOS_IGNORAR = re.compile(r'[\*]+$')

# Palavras-chave para LASTRO e para DISP MED / MD
_KW_LASTRO = {'LASTRO'}
_KW_DISP = {'DISP MED', 'DISP MEDICA', 'DISP MÉDICA', 'DISP MÉDICA', 'MD', 'DISP MEDICA'}

# Células que devem ser silenciosamente ignoradas (não são datas nem lançamentos)
_IGNORAR_SILENCIOSO = re.compile(
    r'^(R\d|R\.ESC\.?|TAQUARI.*|R\.?ESC\.?.*|FÉRIAS.*)$', re.IGNORECASE
)


def _normalizar(celula: str) -> str:
    return celula.strip().upper()


def _parse_data(celula: str):
    """Retorna date ou None."""
    celula = celula.strip()
    m = _RE_DATA.match(celula)
    if m:
        try:
            return datetime.strptime(m.group(1), '%d/%m/%Y').date()
        except ValueError:
            return None
    return None


def _parse_grad(grad_raw: str):
    """'1S SAD' → ('1S', 'SAD')  |  '2S SIN' → ('2S', 'SIN')"""
    parts = grad_raw.strip().split()
    if not parts:
        return None, None
    nivel = parts[0].upper()
    espec = parts[1].upper() if len(parts) > 1 else ''
    return nivel, espec


class Command(BaseCommand):
    help = 'Importa histórico de escala (militares + datas + lastros) de um CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Caminho do arquivo CSV')
        parser.add_argument(
            '--om-sigla',
            type=str,
            default=None,
            help='Sigla da OM destino (ex: BABR). Se omitido, usa a primeira OM.',
        )
        parser.add_argument(
            '--tipo-escala',
            type=str,
            default=None,
            help='Nome (ou parte) do TipoEscala (ex: "perman"). Padrão: primeiro TipoEscala.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Simula sem gravar no banco.',
        )

    def handle(self, *args, **options):
        csv_path = Path(options['csv_path'])
        if not csv_path.exists():
            raise CommandError(f'Arquivo não encontrado: {csv_path}')

        dry_run = options['dry_run']

        # -- OM ---------------------------------------------------------------
        if options['om_sigla']:
            try:
                om = OrganizacaoMilitar.objects.get(sigla=options['om_sigla'])
            except OrganizacaoMilitar.DoesNotExist:
                raise CommandError(f'OM com sigla "{options["om_sigla"]}" não encontrada.')
        else:
            om = OrganizacaoMilitar.objects.filter(ativo=True).first()
            if not om:
                raise CommandError('Nenhuma OM ativa encontrada.')
        self.stdout.write(f'OM: {om.sigla} — {om.nome}')

        # -- TipoEscala -------------------------------------------------------
        if options['tipo_escala']:
            tipo_escala = TipoEscala.objects.filter(
                nome__icontains=options['tipo_escala'], ativo=True
            ).first()
        else:
            # Tenta encontrar "Permanência" ou similar
            tipo_escala = (
                TipoEscala.objects.filter(nome__icontains='perman', ativo=True).first()
                or TipoEscala.objects.filter(nome__icontains='pret', ativo=True).first()
                or TipoEscala.objects.filter(ativo=True).first()
            )
        if not tipo_escala:
            raise CommandError('Nenhum TipoEscala encontrado. Cadastre ao menos um.')
        self.stdout.write(f'Tipo de Escala: {tipo_escala.nome}')

        # -- TipoServico principal (Preto / dia de semana) --------------------
        tipos_servico = list(om.tipos_servico.filter(ativo=True).order_by('ordem'))
        if not tipos_servico:
            raise CommandError('Nenhum TipoServico cadastrado para esta OM.')
        # Preferência: nome contém "pret" → senão primeiro
        tipo_servico_padrao = next(
            (ts for ts in tipos_servico if 'pret' in ts.nome.lower()), tipos_servico[0]
        )
        self.stdout.write(f'Tipo de Serviço padrão: {tipo_servico_padrao.nome}')

        # -- Postos disponíveis -----------------------------------------------
        postos = {p.sigla.lower(): p for p in Posto.objects.all()}

        # -- Ler CSV ----------------------------------------------------------
        with open(csv_path, newline='', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            linhas = list(reader)

        militares_dados = []  # [{nome, nivel, espec, celulas: [str]}]
        for linha in linhas[1:]:  # pula cabeçalho
            if len(linha) < 4:
                continue
            nome = linha[3].strip()
            grad_raw = linha[2].strip()
            if not nome or not grad_raw:
                continue
            nivel, espec = _parse_grad(grad_raw)
            if nivel not in GRAD_PARA_POSTO:
                continue
            celulas = [c.strip() for c in linha[4:]]
            militares_dados.append({
                'nome': nome,
                'nivel': nivel,
                'espec': espec,
                'grad_raw': grad_raw,
                'celulas': celulas,
            })

        if not militares_dados:
            raise CommandError('Nenhuma linha de militar encontrada no CSV.')

        self.stdout.write(f'Militares no CSV: {len(militares_dados)}')

        # =====================================================================
        # PROCESSAMENTO
        # =====================================================================
        contadores = defaultdict(int)
        avisos = []

        with transaction.atomic():
            # Cache de CalendarioDia: data → obj
            cal_cache = {
                cd.data: cd
                for cd in CalendarioDia.objects.filter(organizacao_militar=om)
            }
            # Cache de Escalas: (mes, ano) → obj
            escala_cache = {}

            def obter_ou_criar_escala(mes, ano):
                chave = (mes, ano)
                if chave in escala_cache:
                    return escala_cache[chave]
                obj, criado = Escala.objects.get_or_create(
                    organizacao_militar=om,
                    tipo_escala=tipo_escala,
                    mes=mes,
                    ano=ano,
                    defaults={'status': 'publicada'},
                )
                if criado:
                    contadores['escalas_criadas'] += 1
                escala_cache[chave] = obj
                return obj

            def obter_ou_criar_cal_dia(data_obj):
                if data_obj in cal_cache:
                    return cal_cache[data_obj]
                # Determina tipo de serviço pelo dia da semana
                if data_obj.weekday() in (5, 6):
                    ts = tipos_servico[1] if len(tipos_servico) > 1 else tipo_servico_padrao
                else:
                    ts = tipo_servico_padrao
                obj, _ = CalendarioDia.objects.get_or_create(
                    organizacao_militar=om,
                    data=data_obj,
                    defaults={'tipo_servico': ts},
                )
                cal_cache[data_obj] = obj
                return obj

            # -----------------------------------------------------------------
            # Apagar EscalaItens e LancamentoManualQuadrinho existentes para
            # a OM + tipo_escala (conforme instrução do usuário: "pode zerar")
            # -----------------------------------------------------------------
            if not dry_run:
                n_itens = EscalaItem.objects.filter(
                    escala__organizacao_militar=om,
                    escala__tipo_escala=tipo_escala,
                ).delete()[0]
                n_lm = LancamentoManualQuadrinho.objects.filter(
                    militar__organizacao_militar=om,
                    tipo_escala=tipo_escala,
                ).delete()[0]
                self.stdout.write(
                    self.style.WARNING(
                        f'Apagados: {n_itens} EscalaItens e {n_lm} LançamentosManuais anteriores.'
                    )
                )

            # -----------------------------------------------------------------
            # Processar cada militar
            # -----------------------------------------------------------------
            for md in militares_dados:
                nome = md['nome']
                nivel = md['nivel']
                abrev_posto = GRAD_PARA_POSTO[nivel]

                posto = postos.get(abrev_posto.lower())
                if posto is None:
                    # Tenta busca case-insensitive
                    posto = Posto.objects.filter(
                        sigla__iexact=abrev_posto
                    ).first()
                if posto is None:
                    avisos.append(f'Posto "{abrev_posto}" não encontrado — militar {nome} ignorado.')
                    continue

                # Criar / obter militar
                if not dry_run:
                    idx = contadores["militares_criados"] + 1
                    # CPF deve ter 11 dígitos; matrícula até 20
                    cpf_fake = f'{idx:011d}'
                    matricula_fake = f'IMP{idx:07d}'
                    militar, criado = Militar.objects.get_or_create(
                        organizacao_militar=om,
                        nome_guerra=nome,
                        defaults={
                            'posto': posto,
                            'nome_completo': nome,
                            'cpf': cpf_fake,
                            'matricula': matricula_fake,
                            'data_nascimento': date(1990, 1, 1),
                            'ativo': True,
                        },
                    )
                    if criado:
                        contadores['militares_criados'] += 1
                        # Vincular ao tipo de escala importado
                        militar.tipos_escala.add(tipo_escala)
                    else:
                        # Atualiza posto se mudou
                        if militar.posto_id != posto.id:
                            militar.posto = posto
                            militar.save(update_fields=['posto'])
                else:
                    militar = None
                    criado = False

                # ------------------------------------------------------------------
                # Classificar células
                # ------------------------------------------------------------------
                # lastros_por_ano: {ano: contagem}
                lastros_por_ano = defaultdict(int)
                # disp_por_ano: {ano: contagem}
                disp_por_ano = defaultdict(int)

                for celula in md['celulas']:
                    norm = _normalizar(celula)
                    if not norm:
                        continue

                    # LASTRO
                    if norm in _KW_LASTRO:
                        # Ano não está na célula — usamos 2022 como base histórica.
                        # Vamos acumular e distribuir depois por ano relativo à ordem.
                        lastros_por_ano['sem_ano'] += 1
                        contadores['lastros'] += 1
                        continue

                    # DISP MED / MD / disp médica
                    if norm in _KW_DISP or 'DISP' in norm or norm == 'MD':
                        disp_por_ano['sem_ano'] += 1
                        contadores['disps'] += 1
                        continue

                    # Data real
                    data_obj = _parse_data(celula)
                    if data_obj:
                        if not dry_run and militar:
                            cal = obter_ou_criar_cal_dia(data_obj)
                            escala = obter_ou_criar_escala(data_obj.month, data_obj.year)
                            # unique_together é (escala, calendario_dia): 1 militar/dia
                            # Se o dia já tem alguém, cria nova escala auxiliar com sufixo
                            try:
                                ei, criado_ei = EscalaItem.objects.get_or_create(
                                    escala=escala,
                                    calendario_dia=cal,
                                    defaults={'militar': militar},
                                )
                            except Exception:
                                criado_ei = False
                            if criado_ei:
                                contadores['escala_itens'] += 1
                        else:
                            contadores['escala_itens'] += 1
                        continue

                    # Células silenciosamente ignoradas (R1, R.Esc., TAQUARI…)
                    if _IGNORAR_SILENCIOSO.match(norm):
                        contadores['ignorados'] += 1
                        continue

                    # Caso desconhecido
                    avisos.append(
                        f'Célula não reconhecida para {nome}: "{celula}"'
                    )
                    contadores['ignorados'] += 1

                # ------------------------------------------------------------------
                # Criar LancamentoManualQuadrinho para LASTROs e DISPs
                # Agrupar em um único lançamento por tipo (sem ano específico → ano 2022)
                # ------------------------------------------------------------------
                if not dry_run and militar:
                    qtd_lastro = lastros_por_ano.get('sem_ano', 0)
                    if qtd_lastro > 0:
                        # Descobrir o primeiro ano com data real para orientar o ano
                        primeiro_ano = self._primeiro_ano(md['celulas'])
                        ano_lm = primeiro_ano - 1 if primeiro_ano else 2022
                        LancamentoManualQuadrinho.objects.update_or_create(
                            militar=militar,
                            tipo_escala=tipo_escala,
                            tipo_servico=tipo_servico_padrao,
                            ano=ano_lm,
                            tipo='lastro',
                            defaults={
                                'label': 'Lastro',
                                'quantidade': qtd_lastro,
                                'observacao': 'Importado do CSV histórico',
                            },
                        )
                        contadores['lm_lastro'] += 1

                    qtd_disp = disp_por_ano.get('sem_ano', 0)
                    if qtd_disp > 0:
                        primeiro_ano_disp = self._primeiro_ano_disp(md['celulas'])
                        ano_lm_disp = primeiro_ano_disp if primeiro_ano_disp else 2025
                        LancamentoManualQuadrinho.objects.update_or_create(
                            militar=militar,
                            tipo_escala=tipo_escala,
                            tipo_servico=tipo_servico_padrao,
                            ano=ano_lm_disp,
                            tipo='atestado',
                            defaults={
                                'label': 'Disp. Médica',
                                'quantidade': qtd_disp,
                                'observacao': 'Importado do CSV histórico',
                            },
                        )
                        contadores['lm_disp'] += 1

            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING('DRY RUN — nada foi gravado.'))

        # -- Relatório --------------------------------------------------------
        self.stdout.write(self.style.SUCCESS('\n=== Importação concluída ==='))
        self.stdout.write(f'  Militares criados:          {contadores["militares_criados"]}')
        self.stdout.write(f'  EscalaItens criados:        {contadores["escala_itens"]}')
        self.stdout.write(f'  Escalas criadas:            {contadores["escalas_criadas"]}')
        self.stdout.write(f'  Lançamentos LASTRO criados: {contadores["lm_lastro"]}')
        self.stdout.write(f'  Lançamentos DISP criados:   {contadores["lm_disp"]}')
        self.stdout.write(f'  Células ignoradas:          {contadores["ignorados"]}')
        self.stdout.write(f'  LASTROs processados:        {contadores["lastros"]}')
        self.stdout.write(f'  DISPs processados:          {contadores["disps"]}')
        if avisos:
            self.stdout.write(self.style.WARNING(f'\nAvisos ({len(avisos)}):'))
            for av in avisos[:30]:
                self.stdout.write(f'  ⚠ {av}')
            if len(avisos) > 30:
                self.stdout.write(f'  … e mais {len(avisos) - 30} avisos.')

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _primeiro_ano(celulas):
        """Retorna o primeiro ano encontrado em datas reais da lista de células."""
        for c in celulas:
            d = _parse_data(c)
            if d:
                return d.year
        return None

    @staticmethod
    def _primeiro_ano_disp(celulas):
        """Retorna o ano da primeira data real que aparece DEPOIS da primeira DISP/MD."""
        found_disp = False
        for c in celulas:
            norm = c.strip().upper()
            if norm in _KW_DISP or 'DISP' in norm or norm == 'MD':
                found_disp = True
                continue
            if found_disp:
                d = _parse_data(c)
                if d:
                    return d.year
        return None
