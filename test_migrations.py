#!/usr/bin/env python
"""
TESTE DE MIGRAÇÕES - Sistema de Escala Militar Django

Execute isto no shell Django para verificar se tudo está funcionando:

$ python manage.py shell < test_migrations.py

Ou copie e cole no shell interativo:
$ python manage.py shell
>>> exec(open('test_migrations.py').read())
"""

import sys
from django.contrib.auth.models import Group, Permission
from django.utils import timezone
from datetime import date

print("\n" + "="*70)
print("TESTE DE MIGRAÇÕES - Sistema de Escala Militar")
print("="*70 + "\n")

# ════════════════════════════════════════════════════════════════════════════
# TEST 1: Verificar importação de modelos
# ════════════════════════════════════════════════════════════════════════════

print("TEST 1: Importando modelos...")
try:
    from escalas.models import (
        UsuarioCustomizado, OrganizacaoMilitar, Divisao, Posto, Especialidade,
        Militar, TipoServico, TipoEscala, CalendarioDia, TipoIndisponibilidade,
        Indisponibilidade, Escala, EscalaItem, Quadrinho
    )
    print("  ✓ Todos os modelos importados com sucesso!\n")
except Exception as e:
    print(f"  ✗ ERRO ao importar: {e}\n")
    sys.exit(1)


# ════════════════════════════════════════════════════════════════════════════
# TEST 2: Verificar grupos e permissões (related_name fix)
# ════════════════════════════════════════════════════════════════════════════

print("TEST 2: Testando related_name em groups/permissions...")
try:
    # Criar grupo de teste
    test_group, created = Group.objects.get_or_create(name='TestGroup')
    if created:
        print(f"  → Criado grupo: {test_group}")
    else:
        print(f"  → Grupo existente: {test_group}")
    
    print("  ✓ Groups funcionando corretamente!\n")
except Exception as e:
    print(f"  ✗ ERRO com groups: {e}\n")
    sys.exit(1)


# ════════════════════════════════════════════════════════════════════════════
# TEST 3: Criar UsuarioCustomizado
# ════════════════════════════════════════════════════════════════════════════

print("TEST 3: Criando UsuarioCustomizado...")
try:
    usuario, created = UsuarioCustomizado.objects.get_or_create(
        username='teste_sistema',
        defaults={
            'email': 'teste@sistema.com',
            'first_name': 'Teste',
            'last_name': 'Sistema',
            'perfil': 'admin_om',
            'ativo': True
        }
    )
    
    if created:
        usuario.set_password('senha_teste_123')
        usuario.save()
        print(f"  → Usuário criado: {usuario}")
    else:
        print(f"  → Usuário existente: {usuario}")
    
    # Testar adição ao grupo
    usuario.groups.add(test_group)
    print(f"  → Adicionado ao grupo: {test_group}")
    
    print("  ✓ UsuarioCustomizado funcionando!\n")
except Exception as e:
    print(f"  ✗ ERRO com UsuarioCustomizado: {e}\n")
    sys.exit(1)


# ════════════════════════════════════════════════════════════════════════════
# TEST 4: Criar OrganizacaoMilitar
# ════════════════════════════════════════════════════════════════════════════

print("TEST 4: Criando OrganizacaoMilitar...")
try:
    om, created = OrganizacaoMilitar.objects.get_or_create(
        sigla='TESTE01',
        defaults={
            'nome': 'Batalhão Teste',
            'tipo': 'batalhao',
            'comandante': 'Cap. Teste'
        }
    )
    
    if created:
        print(f"  → OM criada: {om}")
    else:
        print(f"  → OM existente: {om}")
    
    usuario.om_principal = om
    usuario.save()
    
    print("  ✓ OrganizacaoMilitar funcionando!\n")
except Exception as e:
    print(f"  ✗ ERRO com OM: {e}\n")
    sys.exit(1)


# ════════════════════════════════════════════════════════════════════════════
# TEST 5: Criar Posto
# ════════════════════════════════════════════════════════════════════════════

print("TEST 5: Criando Posto...")
try:
    posto, created = Posto.objects.get_or_create(
        sigla='Sd',
        defaults={
            'nome': 'Soldado',
            'ordem_hierarquica': 1
        }
    )
    
    if created:
        print(f"  → Posto criado: {posto}")
    else:
        print(f"  → Posto existente: {posto}")
    
    print("  ✓ Posto funcionando!\n")
except Exception as e:
    print(f"  ✗ ERRO com Posto: {e}\n")
    sys.exit(1)


# ════════════════════════════════════════════════════════════════════════════
# TEST 6: Criar Especialidade
# ════════════════════════════════════════════════════════════════════════════

print("TEST 6: Criando Especialidade...")
try:
    espec, created = Especialidade.objects.get_or_create(
        sigla='TST',
        defaults={
            'nome': 'Teste'
        }
    )
    
    if created:
        print(f"  → Especialidade criada: {espec}")
    else:
        print(f"  → Especialidade existente: {espec}")
    
    print("  ✓ Especialidade funcionando!\n")
except Exception as e:
    print(f"  ✗ ERRO com Especialidade: {e}\n")
    sys.exit(1)


# ════════════════════════════════════════════════════════════════════════════
# TEST 7: Criar Divisão
# ════════════════════════════════════════════════════════════════════════════

print("TEST 7: Criando Divisão...")
try:
    divisao, created = Divisao.objects.get_or_create(
        organizacao_militar=om,
        sigla='TST',
        defaults={
            'nome': 'Divisão Teste'
        }
    )
    
    if created:
        print(f"  → Divisão criada: {divisao}")
    else:
        print(f"  → Divisão existente: {divisao}")
    
    print("  ✓ Divisão funcionando!\n")
except Exception as e:
    print(f"  ✗ ERRO com Divisão: {e}\n")
    sys.exit(1)


# ════════════════════════════════════════════════════════════════════════════
# TEST 8: Criar Militar
# ════════════════════════════════════════════════════════════════════════════

print("TEST 8: Criando Militar...")
try:
    militar, created = Militar.objects.get_or_create(
        organizacao_militar=om,
        cpf='12345678901',
        defaults={
            'nome_guerra': 'TESTE',
            'nome_completo': 'Militar Teste',
            'matricula': 'TESTE001',
            'data_nascimento': date(1995, 5, 15),
            'posto': posto,
            'divisao': divisao,
            'ativo': True
        }
    )
    
    if created:
        print(f"  → Militar criado: {militar}")
    else:
        print(f"  → Militar existente: {militar}")
    
    print("  ✓ Militar funcionando!\n")
except Exception as e:
    print(f"  ✗ ERRO com Militar: {e}\n")
    sys.exit(1)


# ════════════════════════════════════════════════════════════════════════════
# TEST 9: Criar Tipos de Serviço
# ════════════════════════════════════════════════════════════════════════════

print("TEST 9: Criando Tipos de Serviço...")
try:
    tipo_preto, created = TipoServico.objects.get_or_create(
        organizacao_militar=om,
        nome='Preto',
        defaults={
            'cor_hex': '#000000',
            'descricao': 'Segunda a sexta'
        }
    )
    print(f"  → {tipo_preto}")
    
    tipo_vermelho, created = TipoServico.objects.get_or_create(
        organizacao_militar=om,
        nome='Vermelho',
        defaults={
            'cor_hex': '#FF0000',
            'descricao': 'Sábado e domingo'
        }
    )
    print(f"  → {tipo_vermelho}")
    
    print("  ✓ Tipos de Serviço funcionando!\n")
except Exception as e:
    print(f"  ✗ ERRO com TipoServico: {e}\n")
    sys.exit(1)


# ════════════════════════════════════════════════════════════════════════════
# TEST 10: Criar Tipo de Escala
# ════════════════════════════════════════════════════════════════════════════

print("TEST 10: Criando Tipo de Escala...")
try:
    tipo_escala, created = TipoEscala.objects.get_or_create(
        nome='Permanência',
        defaults={
            'descricao': 'Militar fica o dia todo'
        }
    )
    
    if created:
        print(f"  → Tipo criado: {tipo_escala}")
    else:
        print(f"  → Tipo existente: {tipo_escala}")
    
    print("  ✓ Tipo de Escala funcionando!\n")
except Exception as e:
    print(f"  ✗ ERRO com TipoEscala: {e}\n")
    sys.exit(1)


# ════════════════════════════════════════════════════════════════════════════
# TEST 11: Gerar Calendário
# ════════════════════════════════════════════════════════════════════════════

print("TEST 11: Gerando Calendário...")
try:
    dias_existentes = CalendarioDia.objects.filter(
        organizacao_militar=om,
        data__year=2025
    ).count()
    
    if dias_existentes == 0:
        CalendarioDia.gerar_calendario_automatico(om, 2025)
        print("  → Calendário 2025 gerado")
    else:
        print(f"  → Calendário já existe ({dias_existentes} dias)")
    
    print("  ✓ Calendário funcionando!\n")
except Exception as e:
    print(f"  ✗ ERRO com Calendário: {e}\n")
    sys.exit(1)


# ════════════════════════════════════════════════════════════════════════════
# TEST 12: Criar Escala
# ════════════════════════════════════════════════════════════════════════════

print("TEST 12: Criando Escala...")
try:
    escala, created = Escala.objects.get_or_create(
        organizacao_militar=om,
        tipo_escala=tipo_escala,
        mes=1,
        ano=2025,
        defaults={
            'status': 'rascunho',
            'usuario_criacao': usuario
        }
    )
    
    if created:
        print(f"  → Escala criada: {escala}")
    else:
        print(f"  → Escala existente: {escala}")
    
    print("  ✓ Escala funcionando!\n")
except Exception as e:
    print(f"  ✗ ERRO com Escala: {e}\n")
    sys.exit(1)


# ════════════════════════════════════════════════════════════════════════════
# RESULTADO FINAL
# ════════════════════════════════════════════════════════════════════════════

print("="*70)
print("✅ TODOS OS TESTES PASSARAM!")
print("="*70)
print("\nSeu sistema de escala está pronto para usar!")
print("\nProximos passos:")
print("  1. Crie um superusuário: python manage.py createsuperuser")
print("  2. Acesse admin: http://localhost:8000/admin/")
print("  3. Comece a usar o sistema!")
print("\n" + "="*70 + "\n")
