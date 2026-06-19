"""Cria dados de exemplo da FAB para o Sistema de Escala.

Uso:
    python manage.py seed_dados
    python manage.py seed_dados --reset   # apaga dados anteriores
"""
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from escalas.models import (
    CalendarioDia,
    Divisao,
    Especialidade,
    Militar,
    OrganizacaoMilitar,
    Posto,
    TipoEscala,
    TipoIndisponibilidade,
    TipoServico,
)


# Hierarquia de postos da Força Aérea Brasileira
POSTOS_FAB = [
    ('Tenente-Brigadeiro', 'TenBrig', 1),
    ('Major-Brigadeiro', 'MajBrig', 2),
    ('Brigadeiro', 'Brig', 3),
    ('Coronel', 'Cel', 4),
    ('Tenente-Coronel', 'TC', 5),
    ('Major', 'Maj', 6),
    ('Capitão', 'Cap', 7),
    ('1º Tenente', '1º Ten', 8),
    ('2º Tenente', '2º Ten', 9),
    ('Aspirante a Oficial', 'Asp', 10),
    ('Suboficial', 'SO', 11),
    ('1º Sargento', '1º Sgt', 12),
    ('2º Sargento', '2º Sgt', 13),
    ('3º Sargento', '3º Sgt', 14),
    ('Cabo', 'Cb', 15),
    ('Soldado de 1ª Classe', 'S1', 16),
    ('Soldado de 2ª Classe', 'S2', 17),
]

# Especialidades típicas da FAB
ESPECIALIDADES_FAB = [
    ('Aviador', 'AV', 'Pilotagem operacional de aeronaves'),
    ('Mecânico de Aeronave', 'MEC', 'Manutenção de aeronaves e equipamentos'),
    ('Controlador de Tráfego Aéreo', 'CTA', 'Controle de tráfego no espaço aéreo'),
    ('Comunicações', 'COM', 'Comunicações terra-ar e telecomunicações'),
    ('Inteligência', 'INT', 'Atividade de inteligência aeroespacial'),
    ('Meteorologia', 'MET', 'Análise meteorológica de apoio ao voo'),
    ('Saúde', 'SAU', 'Atendimento médico e de saúde operacional'),
    ('Logística', 'LOG', 'Suprimento, transporte e movimentação'),
    ('Infraestrutura', 'INF', 'Engenharia, obras e instalações'),
    ('Segurança e Defesa', 'SEG', 'Segurança de instalações e tropa'),
]

# Organizações Militares da FAB (Comando + 3 unidades)
OMS_FAB = [
    {
        'sigla': 'COMAER',
        'nome': 'Comando da Aeronáutica',
        'tipo': 'outro',
        'comandante': 'Ten Brig Ar Marcelo Damasceno',
        'endereco': 'Esplanada dos Ministérios, Bloco M — Brasília/DF',
        'telefone': '(61) 2023-1000',
        'email': 'comaer@fab.mil.br',
        'om_superior_sigla': None,
    },
    {
        'sigla': 'BABR',
        'nome': 'Base Aérea de Brasília',
        'tipo': 'batalhao',
        'comandante': 'Cel Av Roberto Andrade',
        'endereco': 'Aeroporto Militar — SHIS QI 09 — Brasília/DF',
        'telefone': '(61) 2025-3000',
        'email': 'comando@babr.fab.mil.br',
        'om_superior_sigla': 'COMAER',
    },
    {
        'sigla': 'BAAN',
        'nome': 'Base Aérea de Anápolis',
        'tipo': 'batalhao',
        'comandante': 'Cel Av Fernando Tavares',
        'endereco': 'Rod. BR-414 km 5 — Anápolis/GO',
        'telefone': '(62) 3315-2000',
        'email': 'comando@baan.fab.mil.br',
        'om_superior_sigla': 'COMAER',
    },
    {
        'sigla': 'BARF',
        'nome': 'Base Aérea do Recife',
        'tipo': 'batalhao',
        'comandante': 'Cel Av Antônio Vasconcelos',
        'endereco': 'Praça Salgado Filho s/nº — Recife/PE',
        'telefone': '(81) 3322-4000',
        'email': 'comando@barf.fab.mil.br',
        'om_superior_sigla': 'COMAER',
    },
]

# Modelo de divisões usado em cada base aérea
DIVISOES_BASE_AEREA = [
    ('Esquadrão de Aviação', 'ESC-AV', 'Operação aérea e missões de voo'),
    ('Esquadrão de Manutenção', 'ESC-MN', 'Manutenção de aeronaves e equipamentos'),
    ('Seção de Operações', 'SUOP', 'Planejamento e coordenação operacional'),
    ('Seção de Apoio', 'SAP', 'Logística, transporte e apoio ao efetivo'),
]

DIVISOES_COMAER = [
    ('Estado-Maior da Aeronáutica', 'EMAER', 'Planejamento estratégico'),
    ('Diretoria de Pessoal', 'DIRPES', 'Gestão de pessoal da Aeronáutica'),
    ('Centro de Comunicação Social', 'CECOM', 'Comunicação institucional'),
]

# Militares por OM (sigla_om → lista)
MILITARES = {
    # Tupla: (nome_completo, nome_guerra, cpf, matricula, posto, especialidade, divisao, nasc, data_ultima_promocao)
    'COMAER': [
        ('Mauro Souza Lima',       'M. LIMA', '11000000001', 'C0001', 'Brig',  'INT', 'EMAER',  date(1972,  3, 12), date(2010,  3, 1)),
        ('Patrícia Faria Mendes',  'MENDES',  '11000000002', 'C0002', 'Cel',   'COM', 'CECOM',  date(1978, 11,  5), date(2013, 11, 1)),
        ('Ricardo Vieira Alves',   'VIEIRA',  '11000000003', 'C0003', 'TC',    'AV',  'EMAER',  date(1980,  7, 21), date(2016,  7, 1)),
        ('Júlia Albuquerque Nunes','JÚLIA',   '11000000004', 'C0004', 'Maj',   'INT', 'DIRPES', date(1985,  5, 18), date(2019,  5, 1)),
    ],
    'BABR': [
        ('Diego Oliveira Ramos',   'RAMOS',   '21000000008', 'B0008', 'Maj',   'AV',  'ESC-AV', date(1980, 12,  3), date(2012,  6, 1)),
        ('Carlos Eduardo Silva',   'SILVA',   '21000000001', 'B0001', 'Cap',   'AV',  'ESC-AV', date(1985,  3, 12), date(2015,  3, 1)),
        ('Felipe Rodrigues Nunes', 'NUNES',   '21000000007', 'B0007', '1º Sgt','COM', 'SUOP',   date(1988,  4, 25), date(2016,  4, 1)),
        ('Marcos Antônio Pereira', 'PEREIRA', '21000000002', 'B0002', '1º Ten','AV',  'ESC-AV', date(1990,  7, 21), date(2018,  7, 1)),
        ('João Batista Souza',     'SOUZA',   '21000000003', 'B0003', '2º Sgt','MEC', 'ESC-MN', date(1992, 11,  5), date(2019, 11, 1)),
        ('Rafael Almeida Costa',   'COSTA',   '21000000004', 'B0004', '3º Sgt','LOG', 'SAP',    date(1994,  1, 30), date(2020,  1, 1)),
        ('Bruno Henrique Lima',    'B. LIMA', '21000000005', 'B0005', 'Cb',    'CTA', 'SUOP',   date(1998,  5, 18), date(2022,  5, 1)),
        ('André Luiz Martins',     'MARTINS', '21000000006', 'B0006', 'S1',    'SAU', 'SAP',    date(2001,  9,  9), date(2023,  9, 1)),
    ],
    'BAAN': [
        ('Lucas Ferreira Borges',  'BORGES',  '22000000001', 'A0001', 'Cap',   'AV',  'ESC-AV', date(1986,  6, 14), date(2016,  6, 1)),
        ('Roberta Caldas Rocha',   'CALDAS',  '22000000002', 'A0002', '1º Ten','MET', 'SUOP',   date(1991,  2,  8), date(2019,  2, 1)),
        ('Thiago Mendes Carvalho', 'CARVALHO','22000000003', 'A0003', '2º Sgt','MEC', 'ESC-MN', date(1993, 10, 22), date(2020, 10, 1)),
        ('Camila Torres Ferreira', 'TORRES',  '22000000005', 'A0005', '3º Sgt','CTA', 'SUOP',   date(1995, 11, 11), date(2021, 11, 1)),
        ('Vinícius Souza Prado',   'PRADO',   '22000000004', 'A0004', 'Cb',    'SEG', 'SAP',    date(1997,  7,  3), date(2022,  7, 1)),
        ('Henrique Santos Gomes',  'GOMES',   '22000000006', 'A0006', 'S1',    'INF', 'SAP',    date(2002,  4, 19), date(2024,  4, 1)),
    ],
    'BARF': [
        ('Eduardo Lima Castro',    'CASTRO',  '23000000001', 'R0001', 'TC',    'AV',  'SUOP',   date(1979,  9,  1), date(2013,  9, 1)),
        ('Mariana Bezerra Lopes',  'LOPES',   '23000000002', 'R0002', 'Cap',   'INT', 'SUOP',   date(1987,  3, 27), date(2017,  3, 1)),
        ('Pedro Henrique Tavares', 'TAVARES', '23000000003', 'R0003', '1º Sgt','COM', 'ESC-MN', date(1989, 12, 15), date(2017, 12, 1)),
        ('Letícia Araújo Cunha',   'CUNHA',   '23000000004', 'R0004', '2º Sgt','SAU', 'SAP',    date(1993,  8,  5), date(2021,  8, 1)),
        ('Gustavo Moreira Pires',  'PIRES',   '23000000005', 'R0005', 'Cb',    'MEC', 'ESC-MN', date(1996,  5, 20), date(2022,  5, 1)),
        ('Rodrigo Barros Mello',   'MELLO',   '23000000006', 'R0006', 'S1',    'LOG', 'SAP',    date(2000, 10, 30), date(2023, 10, 1)),
    ],
}

TIPOS_SERVICO = [
    ('Preto', '#1a1a1a', 'Segunda a sexta — dias úteis', 1),
    ('Vermelho', '#a83232', 'Sábado e domingo', 2),
    ('Roxo', '#5b3a5b', 'Feriados e datas especiais', 3),
]

TIPOS_ESCALA = [
    ('Permanência', 'Serviço de 24h na OM'),
    ('Sobreaviso', 'Disponibilidade para chamada'),
    ('Serviço Administrativo', 'Expediente em horário comercial'),
    ('Voo Operacional', 'Escala de voo de instrução ou missão'),
]

TIPOS_INDISPONIBILIDADE = [
    # (nome, descricao, exclui_do_sorteio, gera_bloqueio_pre, gera_bloqueio_pos)
    ('Férias',            'Período de férias regulamentares',    True, True,  True),
    ('Licença Médica',    'Afastamento por motivo de saúde',     True, False, False),
    ('Missão',            'Em missão fora da OM',                True, False, False),
    ('Dispensa',          'Dispensa do serviço',                 True, False, False),
    ('Curso',             'Em curso/capacitação',                True, False, False),
    ('Voo Internacional', 'Escala em missão internacional',      True, False, False),
]


class Command(BaseCommand):
    help = 'Popula o banco com dados de exemplo da FAB para o Sistema de Escala.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Apaga dados anteriores antes de inserir.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(self.style.WARNING('Removendo dados existentes...'))
            CalendarioDia.objects.all().delete()
            Militar.objects.all().delete()
            Divisao.objects.all().delete()
            TipoServico.objects.all().delete()
            OrganizacaoMilitar.objects.all().delete()
            Posto.objects.all().delete()
            Especialidade.objects.all().delete()
            TipoEscala.objects.all().delete()
            TipoIndisponibilidade.objects.all().delete()

        # ---- Postos
        self.stdout.write('Postos da FAB...')
        postos = {}
        for nome, sigla, ordem in POSTOS_FAB:
            obj, _ = Posto.objects.update_or_create(
                sigla=sigla,
                defaults={'nome': nome, 'ordem_hierarquica': ordem, 'ativo': True},
            )
            postos[sigla] = obj

        # ---- Especialidades
        self.stdout.write('Especialidades...')
        especialidades = {}
        for nome, sigla, descricao in ESPECIALIDADES_FAB:
            obj, _ = Especialidade.objects.update_or_create(
                sigla=sigla,
                defaults={'nome': nome, 'descricao': descricao, 'ativo': True},
            )
            especialidades[sigla] = obj

        # ---- OMs (passo 1: criar todas; passo 2: ligar OM superior)
        self.stdout.write('Organizações Militares...')
        oms = {}
        for dados in OMS_FAB:
            obj, _ = OrganizacaoMilitar.objects.update_or_create(
                sigla=dados['sigla'],
                defaults={
                    'nome': dados['nome'],
                    'tipo': dados['tipo'],
                    'comandante': dados['comandante'],
                    'endereco': dados['endereco'],
                    'telefone': dados['telefone'],
                    'email': dados['email'],
                    'ativo': True,
                },
            )
            oms[dados['sigla']] = obj
        for dados in OMS_FAB:
            if dados['om_superior_sigla']:
                om = oms[dados['sigla']]
                om.om_superior = oms[dados['om_superior_sigla']]
                om.save()

        # ---- Divisões, tipos de serviço, militares por OM
        for sigla_om, om in oms.items():
            self.stdout.write(f'  {sigla_om}: divisões / tipos de serviço / militares...')

            # Divisões
            modelo_div = DIVISOES_COMAER if sigla_om == 'COMAER' else DIVISOES_BASE_AEREA
            divisoes_om = {}
            for nome, sigla_d, descricao in modelo_div:
                obj, _ = Divisao.objects.update_or_create(
                    organizacao_militar=om,
                    sigla=sigla_d,
                    defaults={'nome': nome, 'descricao': descricao, 'ativo': True},
                )
                divisoes_om[sigla_d] = obj

            # Tipos de serviço (escopo por OM)
            for nome, cor, descricao, ordem in TIPOS_SERVICO:
                TipoServico.objects.update_or_create(
                    organizacao_militar=om,
                    nome=nome,
                    defaults={
                        'cor_hex': cor,
                        'descricao': descricao,
                        'ordem': ordem,
                        'ativo': True,
                    },
                )

            # Militares
            for (nome_c, ng, cpf, mat, posto_s, esp_s, div_s, nasc, ult_prom) in MILITARES.get(sigla_om, []):
                Militar.objects.update_or_create(
                    cpf=cpf,
                    defaults={
                        'organizacao_militar': om,
                        'divisao': divisoes_om.get(div_s),
                        'posto': postos[posto_s],
                        'especialidade': especialidades.get(esp_s),
                        'nome_guerra': ng,
                        'nome_completo': nome_c,
                        'matricula': mat,
                        'data_nascimento': nasc,
                        'data_ultima_promocao': ult_prom,
                        'ativo': True,
                    },
                )

            # Calendário 2026 da OM
            try:
                CalendarioDia.gerar_calendario_automatico(om, 2026)
            except Exception as exc:  # noqa: BLE001
                self.stdout.write(self.style.WARNING(f'  Calendário {sigla_om}: {exc}'))

        # ---- Tipos globais (escala/indisponibilidade)
        self.stdout.write('Tipos de escala e indisponibilidade...')
        for nome, descricao in TIPOS_ESCALA:
            TipoEscala.objects.update_or_create(
                nome=nome,
                defaults={'descricao': descricao, 'ativo': True},
            )
        for nome, descricao, exclui, blq_pre, blq_pos in TIPOS_INDISPONIBILIDADE:
            TipoIndisponibilidade.objects.update_or_create(
                nome=nome,
                defaults={
                    'descricao': descricao,
                    'exclui_do_sorteio': exclui,
                    'gera_bloqueio_pre': blq_pre,
                    'gera_bloqueio_pos': blq_pos,
                    'ativo': True,
                },
            )

        # ---- Resumo
        self.stdout.write(self.style.SUCCESS('Seed da FAB concluído.'))
        self.stdout.write(
            f'  - OMs: {OrganizacaoMilitar.objects.count()}\n'
            f'  - Postos FAB: {Posto.objects.count()}\n'
            f'  - Especialidades: {Especialidade.objects.count()}\n'
            f'  - Divisões: {Divisao.objects.count()}\n'
            f'  - Militares: {Militar.objects.count()}\n'
            f'  - Tipos de serviço: {TipoServico.objects.count()}\n'
            f'  - Tipos de escala: {TipoEscala.objects.count()}\n'
            f'  - Dias no calendário (todas as OMs): {CalendarioDia.objects.count()}'
        )
