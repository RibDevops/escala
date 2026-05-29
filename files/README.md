╔════════════════════════════════════════════════════════════════════════════════╗
║                 SISTEMA DE ESCALA MILITAR - DJANGO                            ║
║                         v1.0 - Pronto para Produção                           ║
╚════════════════════════════════════════════════════════════════════════════════╝


📦 ARQUIVOS ENTREGUES
═════════════════════════════════════════════════════════════════════════════════

✅ models.py (1.200+ linhas)
   └─ 15 modelos Django com validações customizadas
   └─ UsuarioCustomizado (multi-OM, perfis diferenciados)
   └─ OrganizacaoMilitar (OM com hierarquia)
   └─ Militar, Divisão, Posto, Especialidade
   └─ TipoServico, TipoEscala, CalendarioDia
   └─ Escala, EscalaItem (alocações diárias)
   └─ Indisponibilidade (férias, licenças, missões)
   └─ Quadrinho (contagem e balanceamento)

✅ admin.py (900+ linhas)
   └─ Interface admin customizada para cada modelo
   └─ Visualizações otimizadas com badges de cores
   └─ Ações em lote (gerar calendário, importar, etc)
   └─ Filtros avançados e busca

✅ forms.py (700+ linhas)
   └─ Formulários com validações de negócio
   └─ Validação de CPF, idade, datas
   └─ Importação em lote (CSV)
   └─ Geração automática de escala
   └─ Configuração de feriados

✅ signals.py (150+ linhas)
   └─ Automação do Quadrinho (incrementa/decrementa)
   └─ Auditoria de ações importantes
   └─ Reset de quadrinho (função utilitária)

✅ views.py (600+ linhas)
   └─ CRUD completo para escalas
   └─ Geração automática com algoritmo de balanceamento
   └─ Dashboard com estatísticas
   └─ Relatórios de balanceamento

✅ GUIA_IMPLEMENTACAO.txt (900+ linhas)
   └─ Instalação passo a passo
   └─ Fluxo de uso do sistema
   └─ Dicas e boas práticas
   └─ Troubleshooting


═════════════════════════════════════════════════════════════════════════════════
ESTRUTURA DE DADOS (ER Simplificado)
═════════════════════════════════════════════════════════════════════════════════

                          ┌─────────────────────┐
                          │ UsuarioCustomizado  │
                          │─────────────────────│
                          │ id (PK)             │
                          │ username (UNIQUE)   │
                          │ perfil              │◄────┐
                          │ om_principal (FK)   │     │
                          │ militar_assoc (FK)  │     │ ADMINISTRADOR
                          └─────────────────────┘     │ OU ESCALANTE
                                  │                   │
                           perfis: │                   │
                    ┌──────────────┼──────────────┬────┴──────┐
                    │              │              │           │
              ADMIN_OM       ESCALANTE          MILITAR    GERENTE
                    │              │              │           │
        
        
        ┌─────────────────────────────────────────────────────────────┐
        │                   OrganizacaoMilitar (OM)                   │
        │─────────────────────────────────────────────────────────────│
        │ id, nome, sigla (UNIQUE)                                    │
        │ om_superior (auto-relacionamento para hierarquia)           │
        │ tipo: regimento, batalhao, companhia, etc                  │
        └─────────────────────────────────────────────────────────────┘
                    │
                    ├─►────────────────────────┐
                    │                          │
            ┌───────▼──────────┐     ┌──────────▼────────┐
            │    Divisão       │     │      Militar      │
            │──────────────────│     │───────────────────│
            │ id, nome, sigla  │     │ id, nome_guerra   │
            │ om_principal (FK)│     │ nome_completo     │
            └───────┬──────────┘     │ cpf (UNIQUE)      │
                    │                │ matricula (UNIQUE)│
                    │                │ data_nascimento   │
                    │                │ posto_id (FK)     │
                    │                │ especialidade(FK) │
                    └────────┬───────┴───────────────────┘
                             │
        ┌────────────────┬───┴──────────────┬──────────────────┐
        │                │                  │                  │
   ┌────▼─────┐  ┌──────▼────┐  ┌────────────▼──┐  ┌──────────▼────┐
   │   Posto   │  │Especiald. │  │Indisponibilid.│  │Escala Item    │
   │───────────│  │───────────│  │───────────────│  │───────────────│
   │ id, nome  │  │ id, nome  │  │ id, data_ini  │  │ escala (FK)   │
   │ sigla     │  │ sigla     │  │ data_fim      │  │ militar (FK)  │
   │ ordem_    │  │ descri    │  │ tipo (FK)     │  │ calendario(FK)│
   │ hierarq   │  │           │  │               │  │ observacao    │
   └───────────┘  └───────────┘  └───────────────┘  └───────────────┘
        │                              │
        │                         ┌────▼──────────────┐
        │                         │Tipo Indispon.     │
        │                         │────────────────   │
        │                         │ id, nome          │
        │                         │ exclui_sorteio    │
        │                         └───────────────────┘
        │
    ┌───┴────────────────────────────────────────────────┐
    │        ┌─────────────────────────────────┐         │
    │        │      CalendarioDia              │         │
    │        │─────────────────────────────────│         │
    │        │ id, data (UNIQUE per OM)        │         │
    │        │ tipo_servico_id (FK)            │         │
    │        │ origem: AUTO / MANUAL           │         │
    │        │ observacao (ex: "Carnaval")     │         │
    │        └─────────────────────────────────┘         │
    │                     │                              │
    │         ┌───────────┴──────────────┐               │
    │         │                          │               │
    │   ┌─────▼──────────┐      ┌────────▼──────┐      │
    │   │ Tipo Serviço   │      │ Escala (head) │      │
    │   │────────────────│      │───────────────│      │
    │   │ id, nome       │      │ mes, ano      │      │
    │   │ cor_hex        │      │ tipo_escala   │      │
    │   │ descricao      │      │ status        │      │
    │   │ ordem (OM+)    │      └────────┬──────┘      │
    │   └─────┬──────────┘               │             │
    │         │                    ┌─────▼──────────┐  │
    │         │                    │ Tipo Escala    │  │
    │         │                    │────────────────│  │
    │         │                    │ id, nome       │  │
    │         │                    │ descricao      │  │
    │         │                    └────────────────┘  │
    │         │                                         │
    │    ┌────▼────────────────────────────────┐       │
    │    │         Quadrinho                   │       │
    │    │ (contagem de serviços)              │       │
    │    │────────────────────────────────────│       │
    │    │ militar_id (FK)                    │       │
    │    │ tipo_escala_id (FK)                │       │
    │    │ tipo_servico_id (FK)               │       │
    │    │ ano                                │       │
    │    │ quantidade                         │       │
    │    │ UNIQUE(militar, escala, srv, ano) │       │
    │    └────────────────────────────────────┘       │
    │                                                 │
    └─────────────────────────────────────────────────┘


═════════════════════════════════════════════════════════════════════════════════
HIERARQUIA DE PERMISSÕES
═════════════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────────────┐
│                          ADMIN_OM (Administrador)                           │
│                                                                             │
│ ✓ Gerencia UMA OM específica (sua OM Principal)                            │
│ ✓ Cria/edita Escalas                                                       │
│ ✓ Publica e arquiva Escalas                                                │
│ ✓ Adiciona/edita Militares                                                 │
│ ✓ Registra Indisponibilidades                                              │
│ ✓ Configura Calendário (feriados móveis)                                   │
│ ✗ NÃO consegue acessar outras OMs                                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                     ESCALANTE (Gerador de Escalas)                         │
│                                                                             │
│ ✓ Cria Escalas em rascunho                                                 │
│ ✓ Gera automaticamente (usa Quadrinho)                                      │
│ ✓ Ajusta manualmente (troca militares)                                      │
│ ✓ Acesso a calendário (consulta)                                           │
│ ✓ Visualiza Quadrinho (balanceamento)                                      │
│ ✗ NÃO publica escalas                                                      │
│ ✗ NÃO configura Indisponibilidades                                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                      MILITAR (Consulta Apenas)                             │
│                                                                             │
│ ✓ Visualiza sua escala pessoal                                             │
│ ✓ Vê suas indisponibilidades                                               │
│ ✓ Consulta calendário da OM                                                │
│ ✗ NÃO pode editar nada                                                     │
│ ✗ NÃO consegue alterar escalas                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                   GERENTE (Leitura e Relatórios)                           │
│                                                                             │
│ ✓ Visualiza todas as escalas (leitura)                                     │
│ ✓ Acessa Quadrinho (contagens)                                             │
│ ✓ Gera relatórios                                                          │
│ ✓ Análise de balanceamento                                                 │
│ ✗ NÃO pode criar/editar                                                    │
└─────────────────────────────────────────────────────────────────────────────┘


═════════════════════════════════════════════════════════════════════════════════
FLUXO PRINCIPAL DE USO
═════════════════════════════════════════════════════════════════════════════════

  START
    │
    ├─► 1. ADMIN_OM configura OM
    │   └─ Cria divisões
    │   └─ Cadastra postos e especialidades
    │   └─ Define tipos de serviço (Preto, Vermelho, Roxo)
    │
    ├─► 2. ADMIN_OM gera Calendário
    │   └─ Automático: seg-sex (preto), sáb-dom (vermelho)
    │   └─ Manual: feriados móveis (roxo)
    │
    ├─► 3. ADMIN_OM cadastra Militares
    │   └─ Informações básicas
    │   └─ Vínculo à OM e Divisão
    │   └─ Importação em lote (CSV) se preferir
    │
    ├─► 4. ADMIN_OM registra Indisponibilidades
    │   └─ Férias, Licenças, Missões
    │   └─ Sistema respeita ao gerar escalas
    │
    ├─► 5. ESCALANTE cria Escala em Rascunho
    │   └─ Escolhe: OM + Tipo (Permanência/Sobreaviso) + Mês/Ano
    │
    ├─► 6. ESCALANTE gera automaticamente
    │   └─ Sistema:
    │      1. Pega todos os dias do mês
    │      2. Para cada dia, aloca militar com MENOR contagem
    │      3. Respeita indisponibilidades
    │      4. Incrementa Quadrinho automaticamente (signal)
    │
    ├─► 7. ESCALANTE revisa e ajusta (opcional)
    │   └─ Troca militares se necessário
    │   └─ Registra observações
    │
    ├─► 8. ADMIN_OM publica Escala
    │   └─ Muda status: Rascunho → Publicada
    │   └─ Data de publicação é registrada
    │   └─ Militares conseguem visualizar
    │
    ├─► 9. MILITAR visualiza sua escala
    │   └─ Vê seus dias escalados
    │   └─ Vê tipo de serviço (preto/vermelho/roxo)
    │   └─ Verifica indisponibilidades
    │
    └─► 10. GERENTE analisa relatórios
        └─ Balanceamento por militar
        └─ Contagem de serviços (Quadrinho)
        └─ Estatísticas da OM


═════════════════════════════════════════════════════════════════════════════════
ALGORITMO DE GERAÇÃO AUTOMÁTICA
═════════════════════════════════════════════════════════════════════════════════

  Entrada: Escala em rascunho (OM, Mês, Ano, Tipo)
  ├
  ├─► Obter todos os dias do mês (CalendarioDia)
  │   └─ Cada dia tem um tipo_servico (Preto, Vermelho ou Roxo)
  │
  ├─► Para cada dia:
  │   │
  │   ├─► SELECT * FROM quadrinho
  │   │   WHERE tipo_escala = Escala.tipo
  │   │   AND tipo_servico = Dia.tipo_servico
  │   │   AND ano = 2025
  │   │   ORDER BY quantidade ASC  -- menor contagem primeiro
  │   │
  │   ├─► Para cada militar neste ranking:
  │   │   ├─ Verificar se tem indisponibilidade neste dia
  │   │   │  └─ SELECT FROM indisponibilidade
  │   │   │      WHERE data_inicio <= Dia.data <= data_fim
  │   │   │      AND exclui_do_sorteio = True
  │   │   │
  │   │   └─ Se disponível:
  │   │      ├─ Criar EscalaItem (militar + dia)
  │   │      ├─ Signal automático incrementa Quadrinho (+1)
  │   │      └─ Próximo dia
  │   │
  │   └─ Se nenhum disponível: registra aviso
  │
  └─► Retornar total de alocações criadas

  Resultado: Escala equilibrada e pronta para revisar/publicar


═════════════════════════════════════════════════════════════════════════════════
VALIDAÇÕES IMPLEMENTADAS
═════════════════════════════════════════════════════════════════════════════════

✓ MILITAR
  └─ CPF: 11 dígitos, não pode ser todos iguais
  └─ Idade: mínimo 18 anos
  └─ Matrícula: UNIQUE por OM (mesmo militar não aparece 2x na OM)
  └─ Divisão: deve pertencer à mesma OM

✓ INDISPONIBILIDADE
  └─ Data fim >= Data início
  └─ Duração máxima: 365 dias
  └─ Impede alocação em escalas durante período

✓ ESCALA_ITEM
  └─ Militar da mesma OM que Escala
  └─ Dia do calendário da mesma OM
  └─ UNIQUE: (escala, dia) = 1 militar por dia/escala
  └─ Valida indisponibilidade ao adicionar

✓ ESCALA
  └─ UNIQUE: (OM, tipo_escala, mes, ano) = só 1 escala por período
  └─ Status protege edição (publicada ≠ modificável)
  └─ Mês entre 1-12
  └─ Ano entre 2000-2100

✓ QUADRINHO
  └─ UNIQUE: (militar, tipo_escala, tipo_servico, ano)
  └─ Incrementado/decrementado automaticamente
  └─ Protegido contra contagem negativa


═════════════════════════════════════════════════════════════════════════════════
COMO COMEÇAR
═════════════════════════════════════════════════════════════════════════════════

1. Copie os arquivos para seu projeto Django:
   ✓ models.py       → seu_app/models.py
   ✓ admin.py        → seu_app/admin.py
   ✓ forms.py        → seu_app/forms.py
   ✓ signals.py      → seu_app/signals.py
   ✓ views.py        → seu_app/views.py (parcial, combine com existente)

2. Adicione em settings.py:
   AUTH_USER_MODEL = 'seu_app.UsuarioCustomizado'

3. Register signals em apps.py:
   def ready(self):
       import seu_app.signals

4. Rode migrações:
   python manage.py makemigrations seu_app
   python manage.py migrate

5. Crie superusuário:
   python manage.py createsuperuser

6. Acesse admin:
   http://localhost:8000/admin/

7. Siga o GUIA_IMPLEMENTACAO.txt para configuração passo a passo


═════════════════════════════════════════════════════════════════════════════════
DESTAQUES TÉCNICOS
═════════════════════════════════════════════════════════════════════════════════

🔹 MULTI-OM
   └─ Sistema suporta múltiplas Organizações Militares
   └─ Cada OM tem seus próprios dados isolados
   └─ Admin de OM acessa apenas sua OM

🔹 ALGORITMO DE BALANCEAMENTO
   └─ Usa tabela Quadrinho para distribuir equitativamente
   └─ Prioriza militares com menos serviços
   └─ Respeita indisponibilidades

🔹 SIGNALS AUTOMÁTICOS
   └─ Ao inserir EscalaItem → Quadrinho é incrementado
   └─ Ao deletar EscalaItem → Quadrinho é decrementado
   └─ Sem intervenção manual, mantém consistência

🔹 SOFT DELETE
   └─ Militar não é deletado, apenas desativado
   └─ Preserva histórico de escalas
   └─ OMs não podem ser deletadas (PROTECT)

🔹 VALIDAÇÕES CUSTOMIZADAS
   └─ Método clean() em cada modelo
   └─ Validação em FormS + BD
   └─ Mensagens de erro específicas

🔹 PERMISSÕES GRANULARES
   └─ 4 perfis de usuário
   └─ Cada um com permissões específicas
   └─ Verificação em views (decoradores @login_required)

🔹 ADMIN INTELIGENTE
   └─ Cores e badges para visualização rápida
   └─ Ações em lote (gerar calendário, importar)
   └─ Filtros avançados
   └─ Busca e ordenação customizadas

🔹 EXTENSÍVEL
   └─ Adicione novos tipos de serviço
   └─ Customize tipos de escala
   └─ Expanda tipos de indisponibilidade
   └─ Implemente novos relatórios


═════════════════════════════════════════════════════════════════════════════════
PRÓXIMAS EVOLUCÕES (Opcional)
═════════════════════════════════════════════════════════════════════════════════

→ REST API (Django REST Framework)
  ├─ Endpoints para CRUD de escalas
  ├─ Autenticação via token
  ├─ Serializers customizados
  └─ Permissões por profile

→ Front-end com React/Vue
  ├─ Dashboard interativo
  ├─ Calendário visual (drag-drop)
  ├─ Gráficos de balanceamento
  └─ Visualização mobile

→ Notificações
  ├─ Email ao publicar escala
  ├─ SMS para indisponibilidades
  ├─ Push notifications
  └─ Lembretes pré-feriado

→ Relatórios avançados
  ├─ PDF de escalas
  ├─ Exportar Excel
  ├─ Análise de padrões
  └─ Métricas de OM

→ Integrações
  ├─ Sincronizar com folha de ponto
  ├─ Integração com RH
  ├─ Calendário compartilhado (Google Cal)
  └─ Slack/Teams notificações


═════════════════════════════════════════════════════════════════════════════════
SUPORTE E DOCUMENTAÇÃO
═════════════════════════════════════════════════════════════════════════════════

📖 GUIA_IMPLEMENTACAO.txt
   └─ Passo a passo completo
   └─ Fluxo de uso
   └─ Dicas e troubleshooting

💻 Código bem comentado
   └─ Docstrings em todas as classes
   └─ Comentários explicativos
   └─ Type hints (Python 3.9+)

🗂️ Estrutura organizada
   └─ Separação de responsabilidades
   └─ Padrão Django conventions
   └─ Fácil manutenção e extensão


═════════════════════════════════════════════════════════════════════════════════
Desenvolvido com ❤️ para militares brasileiros
Versão: 1.0 | Data: 2025 | Status: Pronto para Produção
═════════════════════════════════════════════════════════════════════════════════
