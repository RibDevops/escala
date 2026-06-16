"""
Sistema de Escala Militar - Admin, Forms e Signals
Complementa models.py com interface admin e triggers automáticos
"""

# ============================================================================
# admin.py - Interface de administração Django
# ============================================================================

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from .models import (
    UsuarioCustomizado, OrganizacaoMilitar, Divisao, Posto, Especialidade,
    Militar, TipoServico, TipoEscala, CalendarioDia, TipoIndisponibilidade,
    Indisponibilidade, Escala, EscalaItem, Quadrinho
)


@admin.register(UsuarioCustomizado)
class UsuarioCustomizadoAdmin(BaseUserAdmin):
    """Admin para usuários customizados"""
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Configurações da OM', {
            'fields': ('om_principal',)
        }),
        ('Sistema', {
            'fields': ('perfil', 'ativo')
        }),
    )

    list_display = (
        'username', 'get_nome_completo', 'get_perfil_badge',
        'get_om_principal', 'ativo'
    )
    
    list_filter = ('perfil', 'ativo', 'om_principal', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('om_principal', 'first_name')
    
    def get_nome_completo(self, obj):
        return obj.get_full_name() or obj.username
    get_nome_completo.short_description = 'Nome completo'
    
    def get_perfil_badge(self, obj):
        cores = {
            'admin_om': '#dc2626',
            'escalante': '#2563eb',
            'militar': '#10b981',
            'gerente': '#f59e0b',
        }
        cor = cores.get(obj.perfil, '#6b7280')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            cor, obj.get_perfil_display()
        )
    get_perfil_badge.short_description = 'Perfil'
    
    def get_om_principal(self, obj):
        return obj.om_principal.sigla if obj.om_principal else '—'
    get_om_principal.short_description = 'OM Principal'


@admin.register(OrganizacaoMilitar)
class OrganizacaoMilitarAdmin(admin.ModelAdmin):
    """Admin para OMs com hierarquia visual"""
    
    list_display = (
        'sigla', 'nome', 'get_tipo_display', 'get_om_superior',
        'get_qtd_militares', 'ativo'
    )
    
    list_filter = ('tipo', 'ativo', 'om_superior')
    search_fields = ('nome', 'sigla')
    ordering = ('nome',)
    
    fieldsets = (
        ('Identificação', {
            'fields': ('nome', 'sigla', 'tipo')
        }),
        ('Hierarquia', {
            'fields': ('om_superior',)
        }),
        ('Contato', {
            'fields': ('endereco', 'email', 'telefone')
        }),
        ('Comando', {
            'fields': ('comandante',)
        }),
        ('Status', {
            'fields': ('ativo',)
        }),
    )
    
    def get_qtd_militares(self, obj):
        qtd = obj.militares.filter(ativo=True).count()
        return format_html(
            '<span style="background: #dbeafe; color: #0c4a6e; padding: 2px 6px; border-radius: 3px;">{}</span>',
            qtd
        )
    get_qtd_militares.short_description = 'Militares ativos'
    
    def get_om_superior(self, obj):
        if obj.om_superior:
            return obj.om_superior.sigla
        return '—'
    get_om_superior.short_description = 'OM Superior'
    
    def get_tipo_display(self, obj):
        tipos_display = {
            'regimento': '🏛️ Regimento',
            'batalhao': '🎖️ Batalhão',
            'companhia': '🪖 Companhia',
            'pelotao': '👥 Pelotão',
            'secao': '📋 Seção',
            'outro': '❓ Outro',
        }
        return tipos_display.get(obj.tipo, obj.get_tipo_display())
    get_tipo_display.short_description = 'Tipo'


@admin.register(Divisao)
class DivisaoAdmin(admin.ModelAdmin):
    """Admin para Divisões"""
    
    list_display = ('sigla', 'nome', 'get_om', 'chefe', 'ativo')
    list_filter = ('organizacao_militar', 'ativo')
    search_fields = ('nome', 'sigla')
    ordering = ('organizacao_militar', 'nome')
    
    fieldsets = (
        ('Identificação', {
            'fields': ('organizacao_militar', 'nome', 'sigla')
        }),
        ('Detalhes', {
            'fields': ('descricao', 'chefe')
        }),
        ('Status', {
            'fields': ('ativo',)
        }),
    )
    
    def get_om(self, obj):
        return obj.organizacao_militar.sigla
    get_om.short_description = 'OM'


@admin.register(Posto)
class PostoAdmin(admin.ModelAdmin):
    """Admin para Postos militares"""
    
    list_display = ('sigla', 'nome', 'ordem_hierarquica', 'ativo')
    list_filter = ('ativo',)
    ordering = ('ordem_hierarquica',)
    
    fieldsets = (
        ('Identificação', {
            'fields': ('nome', 'sigla')
        }),
        ('Hierarquia', {
            'fields': ('ordem_hierarquica',)
        }),
        ('Status', {
            'fields': ('ativo',)
        }),
    )


@admin.register(Especialidade)
class EspecialidadeAdmin(admin.ModelAdmin):
    """Admin para Especialidades"""
    
    list_display = ('sigla', 'nome', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('nome', 'sigla')
    ordering = ('nome',)


@admin.register(Militar)
class MilitarAdmin(admin.ModelAdmin):
    """Admin para Militares"""
    
    list_display = (
        'nome_guerra', 'get_posto', 'get_especialidade',
        'get_om', 'get_divisao', 'get_idade', 'ativo'
    )
    
    list_filter = (
        'organizacao_militar', 'posto', 'especialidade',
        'divisao', 'ativo', 'data_criacao'
    )
    
    search_fields = (
        'nome_guerra', 'nome_completo', 'cpf', 'matricula'
    )
    
    ordering = ('organizacao_militar', 'nome_guerra')
    
    fieldsets = (
        ('Organização', {
            'fields': ('organizacao_militar', 'divisao')
        }),
        ('Hierarquia e Função', {
            'fields': ('posto', 'especialidade')
        }),
        ('Identificação', {
            'fields': ('nome_guerra', 'nome_completo', 'cpf', 'matricula')
        }),
        ('Dados Pessoais', {
            'fields': ('data_nascimento',)
        }),
        ('Status', {
            'fields': ('ativo',)
        }),
    )
    
    readonly_fields = ('data_criacao', 'data_atualizacao')
    
    def get_posto(self, obj):
        return obj.posto.sigla
    get_posto.short_description = 'Posto'
    
    def get_especialidade(self, obj):
        return obj.especialidade.sigla if obj.especialidade else '—'
    get_especialidade.short_description = 'Esp.'
    
    def get_om(self, obj):
        return obj.organizacao_militar.sigla
    get_om.short_description = 'OM'
    
    def get_divisao(self, obj):
        return obj.divisao.sigla if obj.divisao else '—'
    get_divisao.short_description = 'Div.'
    
    def get_idade(self, obj):
        return obj.obter_idade()
    get_idade.short_description = 'Idade'


@admin.register(TipoServico)
class TipoServicoAdmin(admin.ModelAdmin):
    """Admin para Tipos de Serviço"""
    
    list_display = (
        'nome', 'get_cor_display', 'get_om', 'ordem', 'ativo'
    )
    
    list_filter = ('organizacao_militar', 'ativo')
    ordering = ('organizacao_militar', 'ordem')
    
    fieldsets = (
        ('Identificação', {
            'fields': ('organizacao_militar', 'nome', 'ordem')
        }),
        ('Visualização', {
            'fields': ('cor_hex', 'descricao')
        }),
        ('Status', {
            'fields': ('ativo',)
        }),
    )
    
    def get_cor_display(self, obj):
        return format_html(
            '<div style="width: 20px; height: 20px; background: {}; border-radius: 3px; border: 1px solid #ccc;"></div>',
            obj.cor_hex
        )
    get_cor_display.short_description = 'Cor'
    
    def get_om(self, obj):
        return obj.organizacao_militar.sigla
    get_om.short_description = 'OM'


@admin.register(TipoEscala)
class TipoEscalaAdmin(admin.ModelAdmin):
    """Admin para Tipos de Escala"""
    
    list_display = ('nome', 'ativo', 'get_qtd_escalas')
    list_filter = ('ativo',)
    ordering = ('nome',)
    
    def get_qtd_escalas(self, obj):
        qtd = obj.escalas.count()
        return format_html(
            '<span style="background: #f3e8ff; color: #6d28d9; padding: 2px 6px; border-radius: 3px;">{}</span>',
            qtd
        )
    get_qtd_escalas.short_description = 'Escalas'


@admin.register(CalendarioDia)
class CalendarioDiaAdmin(admin.ModelAdmin):
    """Admin para Calendário"""
    
    list_display = (
        'data', 'get_dia_semana', 'get_tipo_servico',
        'get_origem_display', 'get_om', 'observacao'
    )
    
    list_filter = (
        'organizacao_militar', 'tipo_servico', 'origem_tipo', 'data'
    )
    
    search_fields = ('observacao',)
    ordering = ('-data',)
    
    fieldsets = (
        ('Organização', {
            'fields': ('organizacao_militar',)
        }),
        ('Data e Tipo', {
            'fields': ('data', 'tipo_servico', 'origem_tipo')
        }),
        ('Observação', {
            'fields': ('observacao',)
        }),
    )
    
    def get_dia_semana(self, obj):
        dias = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom']
        return dias[obj.data.weekday()]
    get_dia_semana.short_description = 'Dia'
    
    def get_tipo_servico(self, obj):
        return obj.tipo_servico.nome
    get_tipo_servico.short_description = 'Tipo'
    
    def get_origem_display(self, obj):
        cores = {'AUTO': '#10b981', 'MANUAL': '#f59e0b'}
        cor = cores.get(obj.origem_tipo, '#6b7280')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 6px; border-radius: 3px;">{}</span>',
            cor, obj.get_origem_tipo_display()
        )
    get_origem_display.short_description = 'Origem'
    
    def get_om(self, obj):
        return obj.organizacao_militar.sigla
    get_om.short_description = 'OM'


@admin.register(TipoIndisponibilidade)
class TipoIndisponibilidadeAdmin(admin.ModelAdmin):
    """Admin para Tipos de Indisponibilidade"""
    
    list_display = ('nome', 'exclui_do_sorteio', 'ativo')
    list_filter = ('exclui_do_sorteio', 'ativo')
    ordering = ('nome',)


@admin.register(Indisponibilidade)
class IndisponibilidadeAdmin(admin.ModelAdmin):
    """Admin para Indisponibilidades"""
    
    list_display = (
        'get_militar', 'get_tipo', 'data_inicio', 'data_fim',
        'get_duracao_dias'
    )
    
    list_filter = ('tipo', 'data_inicio', 'data_fim')
    search_fields = ('militar__nome_guerra',)
    ordering = ('-data_inicio',)
    
    fieldsets = (
        ('Militar', {
            'fields': ('militar',)
        }),
        ('Indisponibilidade', {
            'fields': ('tipo', 'data_inicio', 'data_fim')
        }),
        ('Observação', {
            'fields': ('observacao',)
        }),
    )
    
    def get_militar(self, obj):
        return obj.militar.nome_guerra
    get_militar.short_description = 'Militar'
    
    def get_tipo(self, obj):
        return obj.tipo.nome
    get_tipo.short_description = 'Tipo'
    
    def get_duracao_dias(self, obj):
        dias = (obj.data_fim - obj.data_inicio).days + 1
        return format_html(
            '<span style="background: #fee2e2; color: #7f1d1d; padding: 2px 6px; border-radius: 3px;">{} dias</span>',
            dias
        )
    get_duracao_dias.short_description = 'Duração'


@admin.register(Escala)
class EscalaAdmin(admin.ModelAdmin):
    """Admin para Escalas"""
    
    list_display = (
        'get_titulo', 'get_tipo_escala', 'get_status_badge',
        'get_qtd_itens', 'get_om', 'data_criacao'
    )
    
    list_filter = (
        'organizacao_militar', 'tipo_escala', 'status', 'mes', 'ano'
    )
    
    search_fields = ('observacao',)
    ordering = ('-ano', '-mes')
    
    fieldsets = (
        ('Organização', {
            'fields': ('organizacao_militar', 'tipo_escala')
        }),
        ('Período', {
            'fields': ('mes', 'ano')
        }),
        ('Status', {
            'fields': ('status', 'data_publicacao')
        }),
        ('Informações', {
            'fields': ('usuario_criacao', 'observacao')
        }),
    )
    
    readonly_fields = ('usuario_criacao', 'data_criacao', 'data_atualizacao')
    
    def get_titulo(self, obj):
        return f"{obj.mes:02d}/{obj.ano}"
    get_titulo.short_description = 'Período'
    
    def get_tipo_escala(self, obj):
        return obj.tipo_escala.nome
    get_tipo_escala.short_description = 'Tipo'
    
    def get_status_badge(self, obj):
        cores = {
            'rascunho': '#94a3b8',
            'publicada': '#10b981',
            'arquivada': '#6b7280',
        }
        cor = cores.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            cor, obj.get_status_display()
        )
    get_status_badge.short_description = 'Status'
    
    def get_qtd_itens(self, obj):
        qtd = obj.itens.count()
        return format_html(
            '<span style="background: #e0e7ff; color: #3730a3; padding: 2px 6px; border-radius: 3px;">{}</span>',
            qtd
        )
    get_qtd_itens.short_description = 'Itens'
    
    def get_om(self, obj):
        return obj.organizacao_militar.sigla
    get_om.short_description = 'OM'


@admin.register(EscalaItem)
class EscalaItemAdmin(admin.ModelAdmin):
    """Admin para Itens de Escala"""
    
    list_display = (
        'get_militar', 'get_data', 'get_tipo_servico',
        'get_escala', 'observacao'
    )
    
    list_filter = (
        'escala__organizacao_militar', 'escala__tipo_escala',
        'calendario_dia__data'
    )
    
    search_fields = (
        'militar__nome_guerra', 'observacao'
    )
    
    ordering = ('-calendario_dia__data',)
    
    fieldsets = (
        ('Escala', {
            'fields': ('escala',)
        }),
        ('Alocação', {
            'fields': ('militar', 'calendario_dia')
        }),
        ('Observação', {
            'fields': ('observacao',)
        }),
    )
    
    def get_militar(self, obj):
        return obj.militar.nome_guerra
    get_militar.short_description = 'Militar'
    
    def get_data(self, obj):
        return obj.calendario_dia.data.strftime('%d/%m/%Y')
    get_data.short_description = 'Data'
    
    def get_tipo_servico(self, obj):
        return obj.calendario_dia.tipo_servico.nome
    get_tipo_servico.short_description = 'Tipo'
    
    def get_escala(self, obj):
        return f"{obj.escala.mes:02d}/{obj.escala.ano}"
    get_escala.short_description = 'Escala'


@admin.register(Quadrinho)
class QuadrinhoAdmin(admin.ModelAdmin):
    """Admin para Quadrinhos"""
    
    list_display = (
        'get_militar', 'get_tipo_escala', 'get_tipo_servico',
        'ano', 'quantidade', 'data_atualizacao'
    )
    
    list_filter = (
        'militar__organizacao_militar', 'tipo_escala',
        'tipo_servico', 'ano'
    )
    
    search_fields = ('militar__nome_guerra',)
    ordering = ('ano', '-quantidade')
    
    fieldsets = (
        ('Referência', {
            'fields': ('militar', 'tipo_escala', 'tipo_servico', 'ano')
        }),
        ('Contagem', {
            'fields': ('quantidade',)
        }),
    )
    
    readonly_fields = ('data_atualizacao',)
    
    def get_militar(self, obj):
        return obj.militar.nome_guerra
    get_militar.short_description = 'Militar'
    
    def get_tipo_escala(self, obj):
        return obj.tipo_escala.nome
    get_tipo_escala.short_description = 'Tipo Escala'
    
    def get_tipo_servico(self, obj):
        return obj.tipo_servico.nome
    get_tipo_servico.short_description = 'Tipo Serviço'
