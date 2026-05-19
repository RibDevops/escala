"""URLs do módulo escalas (foco atual: cadastros e seleção de OM)."""
from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    # Organizações Militares
    path('organizacoes/', views.organizacao_listar, name='organizacao_listar'),
    path('organizacoes/nova/', views.organizacao_form, name='organizacao_novo'),
    path('organizacoes/<int:om_id>/', views.organizacao_detalhe, name='organizacao_detalhe'),
    path('organizacoes/<int:om_id>/editar/', views.organizacao_form, name='organizacao_editar'),
    path('organizacoes/<int:om_id>/excluir/', views.organizacao_excluir, name='organizacao_excluir'),
    path('om/trocar/', views.organizacao_trocar, name='organizacao_trocar'),

    # Atalho para detalhe da OM ativa
    path('organizacao/', views.organizacao_detalhe, name='organizacao_ativa'),

    # Postos
    path('postos/', views.posto_listar, name='posto_listar'),
    path('postos/novo/', views.posto_form, name='posto_novo'),
    path('postos/<int:posto_id>/editar/', views.posto_form, name='posto_editar'),
    path('postos/<int:posto_id>/excluir/', views.posto_excluir, name='posto_excluir'),

    # Especialidades
    path('especialidades/', views.especialidade_listar, name='especialidade_listar'),
    path('especialidades/novo/', views.especialidade_form, name='especialidade_novo'),
    path(
        'especialidades/<int:especialidade_id>/editar/',
        views.especialidade_form,
        name='especialidade_editar',
    ),
    path(
        'especialidades/<int:especialidade_id>/excluir/',
        views.especialidade_excluir,
        name='especialidade_excluir',
    ),

    # Tipos de Escala
    path(
        'tipos-escala/',
        views.tipo_escala_listar,
        name='tipo_escala_listar',
    ),
    path(
        'tipos-escala/novo/',
        views.tipo_escala_form,
        name='tipo_escala_novo',
    ),
    path(
        'tipos-escala/<int:tipo_id>/editar/',
        views.tipo_escala_form,
        name='tipo_escala_editar',
    ),
    path(
        'tipos-escala/<int:tipo_id>/excluir/',
        views.tipo_escala_excluir,
        name='tipo_escala_excluir',
    ),

    # Tipos de Indisponibilidade
    path(
        'tipos-indisponibilidade/',
        views.tipo_indisponibilidade_listar,
        name='tipo_indisponibilidade_listar',
    ),
    path(
        'tipos-indisponibilidade/novo/',
        views.tipo_indisponibilidade_form,
        name='tipo_indisponibilidade_novo',
    ),
    path(
        'tipos-indisponibilidade/<int:tipo_id>/editar/',
        views.tipo_indisponibilidade_form,
        name='tipo_indisponibilidade_editar',
    ),
    path(
        'tipos-indisponibilidade/<int:tipo_id>/excluir/',
        views.tipo_indisponibilidade_excluir,
        name='tipo_indisponibilidade_excluir',
    ),

    # Divisões
    path('divisoes/', views.divisao_listar, name='divisao_listar'),
    path('divisoes/novo/', views.divisao_form, name='divisao_novo'),
    path('divisoes/<int:divisao_id>/editar/', views.divisao_form, name='divisao_editar'),
    path('divisoes/<int:divisao_id>/excluir/', views.divisao_excluir, name='divisao_excluir'),

    # Militares
    path('militares/', views.militar_listar, name='militar_listar'),
    path('militares/novo/', views.militar_form, name='militar_novo'),
    path('militares/<int:militar_id>/', views.militar_detalhe, name='militar_detalhe'),
    path('militares/<int:militar_id>/editar/', views.militar_form, name='militar_editar'),
    path(
        'militares/<int:militar_id>/excluir/',
        views.militar_excluir,
        name='militar_excluir',
    ),

    # Quadrinho (visão geral e edição manual de saldo/quantidade)
    path('quadrinho/', views.quadrinho_visao, name='quadrinho_visao'),
    path(
        'quadrinho/<int:militar_id>/<int:tipo_escala_id>/'
        '<int:tipo_servico_id>/<int:ano>/editar/',
        views.quadrinho_editar,
        name='quadrinho_editar',
    ),
    path('quadrinho/exportar/', views.quadrinho_exportar, name='quadrinho_exportar'),
    path(
        'quadrinho/<int:militar_id>/<int:tipo_escala_id>/'
        '<int:tipo_servico_id>/<int:ano>/ajax-editar/',
        views.quadrinho_ajax_editar,
        name='quadrinho_ajax_editar',
    ),
    path(
        'quadrinho/<int:militar_id>/<int:tipo_escala_id>/'
        '<int:tipo_servico_id>/<int:ano>/ajax-excluir/',
        views.quadrinho_ajax_excluir,
        name='quadrinho_ajax_excluir',
    ),
    path('quadrinho/ajax-lancamento/', views.lancamento_ajax_criar, name='lancamento_ajax_criar'),

    # Indisponibilidades
    path('indisponibilidades/', views.indisponibilidade_listar, name='indisponibilidade_listar'),
    path('indisponibilidades/nova/', views.indisponibilidade_criar, name='indisponibilidade_criar'),
    path('indisponibilidades/<int:ind_id>/excluir/', views.indisponibilidade_excluir, name='indisponibilidade_excluir'),

    # Escalas
    path('escalas/', views.escala_listar, name='escala_listar'),
    path('escalas/nova/', views.escala_criar, name='escala_criar'),
    path('escalas/configuracao/', views.configuracao_escala, name='configuracao_escala'),
    path('escalas/<int:escala_id>/', views.escala_detalhar, name='escala_detalhar'),
    path('escalas/<int:escala_id>/gerar/', views.escala_gerar, name='escala_gerar'),
    path('escalas/<int:escala_id>/gerar-vertical/', views.escala_gerar_vertical, name='escala_gerar_vertical'),
    path('escalas/<int:escala_id>/limpar/', views.escala_limpar, name='escala_limpar'),
    path('escalas/item/<int:item_id>/forcar/', views.escala_item_forcar, name='escala_item_forcar'),
    path('escalas/item/<int:item_id>/trocar-militar/', views.escala_item_trocar_militar, name='escala_item_trocar_militar'),
    path('escalas/item/<int:item_id>/substituto/', views.escala_item_definir_substituto, name='escala_item_definir_substituto'),
    path('escalas/<int:escala_id>/excluir/', views.escala_excluir, name='escala_excluir'),
    path('escalas/<int:escala_id>/previsao/', views.escala_marcar_previsao, name='escala_marcar_previsao'),
    path('escalas/<int:escala_id>/publicar/', views.escala_publicar, name='escala_publicar'),
    path('escalas/<int:escala_id>/matriz/', views.escala_matriz, name='escala_matriz'),

    # Lançamentos manuais de quadrinho
    path('lancamentos-manuais/', views.lancamento_manual_listar, name='lancamento_manual_listar'),
    path('lancamentos-manuais/novo/', views.lancamento_manual_form, name='lancamento_manual_novo'),
    path('lancamentos-manuais/<int:lancamento_id>/editar/', views.lancamento_manual_form, name='lancamento_manual_editar'),
    path('lancamentos-manuais/<int:lancamento_id>/excluir/', views.lancamento_manual_excluir, name='lancamento_manual_excluir'),

    # Usuários do sistema
    path('usuarios/', views.usuario_listar, name='usuario_listar'),
    path('usuarios/novo/', views.usuario_form, name='usuario_novo'),
    path('usuarios/<int:usuario_id>/editar/', views.usuario_form, name='usuario_editar'),
    path('usuarios/<int:usuario_id>/excluir/', views.usuario_excluir, name='usuario_excluir'),

    # Redirecionamentos legados (mantidos para não quebrar links antigos)
    path('sobreaviso/', views.sobreaviso_publico, name='sobreaviso_publico'),
    path('quadrinho-publico/', views.quadrinho_publico, name='quadrinho_publico'),

    # Páginas públicas dinâmicas por slug de TipoEscala (sem login)
    # Criadas automaticamente ao cadastrar um novo tipo de escala
    # Exemplos: /escala/permanencia/  /escala/eletricista/  /matriz/sobreaviso/
    path('escala/<slug:slug>/', views.escala_publica, name='escala_publica'),
    path('matriz/<slug:slug>/', views.matriz_publica, name='matriz_publica'),

    # Troca de Serviço
    path('troca/', views.troca_listar, name='troca_listar'),
    path('troca/solicitar/', views.troca_solicitar, name='troca_solicitar'),
    path('troca/servicos/', views.troca_servicos_militar, name='troca_servicos_militar'),
    path('troca/<int:troca_id>/aceitar/', views.troca_aceitar, name='troca_aceitar'),
    path('troca/<int:troca_id>/aprovar/', views.troca_aprovar_escalante, name='troca_aprovar_escalante'),
    path('troca/<int:troca_id>/homologar/', views.troca_homologar, name='troca_homologar'),
    path('troca/<int:troca_id>/', views.troca_detalhar, name='troca_detalhar'),
]
