"""
EXEMPLOS DE USO - Sistema de Escala Militar Django
Snippets úteis para shell do Django (python manage.py shell)
"""

# ============================================================================
# EXEMPLOS 1: CRIAR DADOS DE TESTE
# ============================================================================

"""
Execute isto no shell Django para criar dados de teste:
$ python manage.py shell
"""

# Importar modelos
from seu_app.models import (
    OrganizacaoMilitar, Divisao, Posto, Especialidade, TipoServico,
    TipoEscala, TipoIndisponibilidade, Militar, CalendarioDia, Escala,
    EscalaItem, Quadrinho, Indisponibilidade, UsuarioCustomizado
)
from django.utils import timezone
from datetime import date, timedelta

# ────────────────────────────────────────────────────────────────
# 1. Criar OM
# ────────────────────────────────────────────────────────────────

om = OrganizacaoMilitar.objects.create(
    nome="1º Batalhão de Infantaria",
    sigla="BtlInf01",
    tipo="batalhao",
    comandante="Capitão Silva"
)
print(f"✓ OM criada: {om}")

# ────────────────────────────────────────────────────────────────
# 2. Criar Divisões
# ────────────────────────────────────────────────────────────────

div_pessoal = Divisao.objects.create(
    organizacao_militar=om,
    nome="Divisão de Pessoal",
    sigla="DPE",
    chefe="Tenente Costa"
)

div_operacoes = Divisao.objects.create(
    organizacao_militar=om,
    nome="Divisão de Operações",
    sigla="DOP",
    chefe="Capitão Oliveira"
)

print(f"✓ Divisões criadas: {div_pessoal}, {div_operacoes}")

# ────────────────────────────────────────────────────────────────
# 3. Criar Postos
# ────────────────────────────────────────────────────────────────

postos_dados = [
    {"nome": "Soldado", "sigla": "Sd", "ordem": 1},
    {"nome": "Cabo", "sigla": "Cb", "ordem": 2},
    {"nome": "Sargento", "sigla": "Sgt", "ordem": 3},
    {"nome": "Tenente", "sigla": "Tte", "ordem": 4},
]

postos = {}
for dados in postos_dados:
    posto = Posto.objects.create(**dados)
    postos[dados['sigla']] = posto
    print(f"✓ Posto criado: {posto}")

# ────────────────────────────────────────────────────────────────
# 4. Criar Especialidades
# ────────────────────────────────────────────────────────────────

espec_piloto = Especialidade.objects.create(
    nome="Piloto",
    sigla="PLT",
    descricao="Responsável por operações aéreas"
)

espec_mecanico = Especialidade.objects.create(
    nome="Mecânico",
    sigla="MEC",
    descricao="Manutenção de aeronaves"
)

print(f"✓ Especialidades criadas: {espec_piloto}, {espec_mecanico}")

# ────────────────────────────────────────────────────────────────
# 5. Criar Tipos de Serviço
# ────────────────────────────────────────────────────────────────

tipo_preto = TipoServico.objects.create(
    organizacao_militar=om,
    nome="Preto",
    cor_hex="#000000",
    descricao="Segunda a sexta - dias úteis",
    ordem=1
)

tipo_vermelho = TipoServico.objects.create(
    organizacao_militar=om,
    nome="Vermelho",
    cor_hex="#FF0000",
    descricao="Sábado e domingo",
    ordem=2
)

tipo_roxo = TipoServico.objects.create(
    organizacao_militar=om,
    nome="Roxo",
    cor_hex="#800080",
    descricao="Feriados especiais",
    ordem=3
)

print(f"✓ Tipos de Serviço criados: {tipo_preto}, {tipo_vermelho}, {tipo_roxo}")

# ────────────────────────────────────────────────────────────────
# 6. Criar Tipo de Escala
# ────────────────────────────────────────────────────────────────

tipo_escala_perm = TipoEscala.objects.create(
    nome="Permanência",
    descricao="Militar fica o dia todo"
)

tipo_escala_sobreaviso = TipoEscala.objects.create(
    nome="Sobreaviso",
    descricao="Militar fica disponível"
)

print(f"✓ Tipos de Escala criados: {tipo_escala_perm}, {tipo_escala_sobreaviso}")

# ────────────────────────────────────────────────────────────────
# 7. Gerar Calendário Automático
# ────────────────────────────────────────────────────────────────

CalendarioDia.gerar_calendario_automatico(om, 2025)
print(f"✓ Calendário 2025 gerado para {om.sigla}")

# ────────────────────────────────────────────────────────────────
# 8. Adicionar feriado móvel manualmente
# ────────────────────────────────────────────────────────────────

carnaval = CalendarioDia.objects.create(
    organizacao_militar=om,
    data=date(2025, 3, 4),  # Carnaval 2025
    tipo_servico=tipo_roxo,
    origem_tipo='MANUAL',
    observacao='Carnaval 2025'
)

print(f"✓ Feriado manual criado: {carnaval}")

# ────────────────────────────────────────────────────────────────
# 9. Criar Militares
# ────────────────────────────────────────────────────────────────

militares_dados = [
    {
        "nome_guerra": "SILVA",
        "nome_completo": "João da Silva Santos",
        "cpf": "12345678901",
        "matricula": "BtlInf01001",
        "data_nascimento": date(1995, 5, 15),
        "posto": postos['Sd'],
        "especialidade": espec_piloto,
    },
    {
        "nome_guerra": "COSTA",
        "nome_completo": "Maria Costa Oliveira",
        "cpf": "98765432101",
        "matricula": "BtlInf01002",
        "data_nascimento": date(1992, 8, 22),
        "posto": postos['Cb'],
        "especialidade": espec_mecanico,
    },
    {
        "nome_guerra": "SANTOS",
        "nome_completo": "Pedro dos Santos",
        "cpf": "11111111111",  # INVÁLIDO - testes de validação
        "matricula": "BtlInf01003",
        "data_nascimento": date(1998, 1, 10),
        "posto": postos['Sgt'],
    },
]

militares = []
for dados in militares_dados[:-1]:  # Ignorar o inválido por enquanto
    militar = Militar.objects.create(
        organizacao_militar=om,
        divisao=div_pessoal,
        **dados
    )
    militares.append(militar)
    print(f"✓ Militar criado: {militar}")

# ────────────────────────────────────────────────────────────────
# 10. Criar Tipo de Indisponibilidade
# ────────────────────────────────────────────────────────────────

tipo_ind_ferias = TipoIndisponibilidade.objects.create(
    nome="Férias",
    descricao="Férias regulamentares",
    exclui_do_sorteio=True
)

tipo_ind_licenca = TipoIndisponibilidade.objects.create(
    nome="Licença Médica",
    descricao="Afastamento por motivos de saúde",
    exclui_do_sorteio=True
)

print(f"✓ Tipos de Indisponibilidade criados")

# ────────────────────────────────────────────────────────────────
# 11. Registrar Indisponibilidades
# ────────────────────────────────────────────────────────────────

ind_silva = Indisponibilidade.objects.create(
    militar=militares[0],  # SILVA
    tipo=tipo_ind_ferias,
    data_inicio=date(2025, 1, 1),
    data_fim=date(2025, 1, 15),
    observacao="Férias de verão"
)

print(f"✓ Indisponibilidade registrada: {ind_silva}")


# ============================================================================
# EXEMPLOS 2: GERAR ESCALAS
# ============================================================================

# ────────────────────────────────────────────────────────────────
# 12. Criar Escala em Rascunho
# ────────────────────────────────────────────────────────────────

escala = Escala.objects.create(
    organizacao_militar=om,
    tipo_escala=tipo_escala_perm,
    mes=1,
    ano=2025,
    status='rascunho',
    observacao='Primeira escala teste'
)

print(f"✓ Escala criada: {escala}")

# ────────────────────────────────────────────────────────────────
# 13. Gerar Automaticamente (usando algoritmo de balanceamento)
# ────────────────────────────────────────────────────────────────

from seu_app.views import gerar_escala_automaticamente

try:
    alocacoes = gerar_escala_automaticamente(escala)
    print(f"✓ Escala gerada: {alocacoes} alocações criadas!")
except Exception as e:
    print(f"✗ Erro ao gerar: {e}")

# ────────────────────────────────────────────────────────────────
# 14. Visualizar Escala criada
# ────────────────────────────────────────────────────────────────

print("\nITENS DA ESCALA:")
print("═" * 60)
for item in escala.itens.select_related('militar', 'calendario_dia').order_by('calendario_dia__data')[:10]:
    print(f"{item.calendario_dia.data.strftime('%d/%m')} | "
          f"{item.militar.nome_guerra:10} | "
          f"{item.calendario_dia.tipo_servico.nome:10}")


# ============================================================================
# EXEMPLOS 3: CONSULTAS ÚTEIS (QUERYS)
# ============================================================================

# ────────────────────────────────────────────────────────────────
# 15. Ver todas as escalas de uma OM
# ────────────────────────────────────────────────────────────────

escalas = Escala.objects.filter(organizacao_militar=om).select_related('tipo_escala')
print(f"Total de escalas da OM: {escalas.count()}")
for esc in escalas:
    print(f"  • {esc.mes:02d}/{esc.ano} - {esc.tipo_escala.nome} ({esc.get_status_display()})")

# ────────────────────────────────────────────────────────────────
# 16. Ver Quadrinho (contagem de serviços) de um militar
# ────────────────────────────────────────────────────────────────

silva = Militar.objects.get(nome_guerra='SILVA')
quadrinhos = silva.quadrinhos.filter(ano=2025)

print(f"\nQUADRINHO DE {silva.nome_guerra} (2025):")
print("═" * 60)
for quad in quadrinhos:
    print(f"{quad.tipo_escala.nome:20} | "
          f"{quad.tipo_servico.nome:10} | "
          f"Quantidade: {quad.quantidade}")

# ────────────────────────────────────────────────────────────────
# 17. Ver ranking de militares (menos serviços primeiro)
# ────────────────────────────────────────────────────────────────

ranking = Quadrinho.obter_ranking(
    tipo_escala=tipo_escala_perm,
    tipo_servico=tipo_preto,
    ano=2025,
    om=om
)

print(f"\nRANKING (Permanência - Preto - 2025):")
print("═" * 60)
for quad in ranking:
    print(f"{quad.militar.nome_guerra:10} | Quantidade: {quad.quantidade}")

# ────────────────────────────────────────────────────────────────
# 18. Ver indisponibilidades ativas em um período
# ────────────────────────────────────────────────────────────────

inicio = date(2025, 1, 1)
fim = date(2025, 1, 31)

indisps = Indisponibilidade.objects.filter(
    data_inicio__lte=fim,
    data_fim__gte=inicio,
    tipo__exclui_do_sorteio=True
).select_related('militar', 'tipo')

print(f"\nINDISPONIBILIDADES (01/01 a 31/01/2025):")
print("═" * 60)
for ind in indisps:
    dias = (ind.data_fim - ind.data_inicio).days + 1
    print(f"{ind.militar.nome_guerra:10} | "
          f"{ind.tipo.nome:15} | "
          f"{ind.data_inicio} a {ind.data_fim} ({dias} dias)")

# ────────────────────────────────────────────────────────────────
# 19. Ver quantas vezes um militar foi escalado em um mês
# ────────────────────────────────────────────────────────────────

costa = Militar.objects.get(nome_guerra='COSTA')
escalados_janeiro = EscalaItem.objects.filter(
    militar=costa,
    calendario_dia__data__month=1,
    calendario_dia__data__year=2025
).count()

print(f"\n{costa.nome_guerra} foi escalado {escalados_janeiro}x em janeiro/2025")

# ────────────────────────────────────────────────────────────────
# 20. Ver estatísticas de uma escala
# ────────────────────────────────────────────────────────────────

from django.db.models import Count

escala = Escala.objects.get(mes=1, ano=2025, organizacao_militar=om)

stats = escala.itens.aggregate(
    total_dias=Count('id'),
    total_militares=Count('militar', distinct=True),
    total_preto=Count('id', filter=Q(calendario_dia__tipo_servico__nome='Preto')),
    total_vermelho=Count('id', filter=Q(calendario_dia__tipo_servico__nome='Vermelho')),
    total_roxo=Count('id', filter=Q(calendario_dia__tipo_servico__nome='Roxo')),
)

print(f"\nESTATÍSTICAS DA ESCALA 01/2025:")
print("═" * 60)
print(f"Total de dias escalados: {stats['total_dias']}")
print(f"Total de militares diferentes: {stats['total_militares']}")
print(f"  • Preto: {stats['total_preto']}")
print(f"  • Vermelho: {stats['total_vermelho']}")
print(f"  • Roxo: {stats['total_roxo']}")


# ============================================================================
# EXEMPLOS 4: OPERAÇÕES ADMINISTRATIVAS
# ============================================================================

# ────────────────────────────────────────────────────────────────
# 21. Publicar uma escala
# ────────────────────────────────────────────────────────────────

escala = Escala.objects.get(mes=1, ano=2025, organizacao_militar=om)
if escala.status == 'rascunho':
    escala.publicar()
    print(f"✓ Escala publicada em {escala.data_publicacao}")
else:
    print(f"Escala já está em status: {escala.get_status_display()}")

# ────────────────────────────────────────────────────────────────
# 22. Resetar Quadrinho de um ano (CUIDADO!)
# ────────────────────────────────────────────────────────────────

from seu_app.signals import resetar_quadrinho_do_ano

# resetar_quadrinho_do_ano(2025)  # Descomente se precisar

# ────────────────────────────────────────────────────────────────
# 23. Desativar um militar (soft delete)
# ────────────────────────────────────────────────────────────────

silva = Militar.objects.get(nome_guerra='SILVA')
silva.ativo = False
silva.save()
print(f"✓ Militar {silva.nome_guerra} desativado")

# ────────────────────────────────────────────────────────────────
# 24. Criar usuário Admin de OM
# ────────────────────────────────────────────────────────────────

usuario_admin = UsuarioCustomizado.objects.create_user(
    username='admin_btlinf01',
    email='admin@btlinf01.mil.br',
    password='senha_forte_123',
    first_name='João',
    last_name='Silva',
    perfil='admin_om',
    om_principal=om,
    ativo=True
)
print(f"✓ Usuário Admin criado: {usuario_admin}")

# ────────────────────────────────────────────────────────────────
# 25. Criar usuário Escalante
# ────────────────────────────────────────────────────────────────

usuario_escal = UsuarioCustomizado.objects.create_user(
    username='escalante_btlinf01',
    email='escalante@btlinf01.mil.br',
    password='senha_forte_456',
    first_name='Maria',
    last_name='Costa',
    perfil='escalante',
    om_principal=om,
    ativo=True
)
print(f"✓ Usuário Escalante criado: {usuario_escal}")

# ────────────────────────────────────────────────────────────────
# 26. Criar usuário Militar
# ────────────────────────────────────────────────────────────────

usuario_mil = UsuarioCustomizado.objects.create_user(
    username='silva_001',
    email='silva@btlinf01.mil.br',
    password='senha_militar_789',
    first_name='João',
    last_name='Silva',
    perfil='militar',
    eh_militar=True,
    militar_associado=silva,
    ativo=True
)
print(f"✓ Usuário Militar criado: {usuario_mil}")


# ============================================================================
# EXEMPLOS 5: VALIDAÇÕES E TESTES
# ============================================================================

# ────────────────────────────────────────────────────────────────
# 27. Testar validações de Militar
# ────────────────────────────────────────────────────────────────

print("\nTESTANDO VALIDAÇÕES:")
print("═" * 60)

# CPF inválido
try:
    militar_invalido = Militar(
        organizacao_militar=om,
        divisao=div_pessoal,
        posto=postos['Sd'],
        nome_guerra='TESTE',
        nome_completo='Teste Inválido',
        cpf='00000000000',  # Todos zeros = inválido
        matricula='TEST001',
        data_nascimento=date(1995, 5, 15)
    )
    militar_invalido.save()
except Exception as e:
    print(f"✓ Validação funcionou: {e}")

# Data de nascimento inválida (menor de idade)
try:
    militar_crianca = Militar(
        organizacao_militar=om,
        divisao=div_pessoal,
        posto=postos['Sd'],
        nome_guerra='CRIANCA',
        nome_completo='Criança Teste',
        cpf='12340987654',
        matricula='CHILD001',
        data_nascimento=date(2010, 5, 15)  # Muito novo
    )
    militar_crianca.save()
except Exception as e:
    print(f"✓ Validação de idade funcionou: {e}")

# ────────────────────────────────────────────────────────────────
# 28. Testar validações de Indisponibilidade
# ────────────────────────────────────────────────────────────────

try:
    ind_invalida = Indisponibilidade(
        militar=militares[0],
        tipo=tipo_ind_ferias,
        data_inicio=date(2025, 2, 1),
        data_fim=date(2025, 1, 1)  # Fim antes do início!
    )
    ind_invalida.save()
except Exception as e:
    print(f"✓ Validação de data funcionou: {e}")

# ────────────────────────────────────────────────────────────────
# 29. Testar permissões de usuário
# ────────────────────────────────────────────────────────────────

print(f"\nPERMISSÕES:")
print("═" * 60)
print(f"Admin pode escalar? {usuario_admin.pode_escalar()}")
print(f"Admin pode administrar? {usuario_admin.pode_administrar()}")
print(f"Escalante pode escalar? {usuario_escal.pode_escalar()}")
print(f"Escalante pode administrar? {usuario_escal.pode_administrar()}")
print(f"Militar pode escalar? {usuario_mil.pode_escalar()}")


print("\n✅ Exemplos executados com sucesso!")
