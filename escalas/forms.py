"""
Sistema de Escala Militar - Django Forms
Formulários customizados com validações de negócio
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta

from .models import (
    UsuarioCustomizado, Militar, Especialidade, Divisao, Posto,
    Indisponibilidade, TipoIndisponibilidade, Escala, EscalaItem,
    TipoServico, CalendarioDia, OrganizacaoMilitar
)


# ============================================================================
# USUÁRIOS
# ============================================================================

class UsuarioCustomizadoCriacaoForm(UserCreationForm):
    """Formulário de criação de novo usuário"""
    
    email = forms.EmailField(
        required=True,
        help_text='Email para contato'
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label='Primeiro nome'
    )
    
    last_name = forms.CharField(
        max_length=150,
        required=True,
        label='Sobrenome'
    )
    
    om_principal = forms.ModelChoiceField(
        queryset=OrganizacaoMilitar.objects.filter(ativo=True),
        required=False,
        label='OM Principal',
        help_text='Selecione a OM onde o usuário atuará'
    )
    
    perfil = forms.ChoiceField(
        choices=[('', '--- Selecione um perfil ---')] + list(UsuarioCustomizado.PerfilUsuario.choices),
        label='Perfil de acesso'
    )
    
    class Meta:
        model = UsuarioCustomizado
        fields = ('username', 'email', 'first_name', 'last_name', 'perfil', 'om_principal')
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validar se perfil foi selecionado
        if not cleaned_data.get('perfil'):
            raise ValidationError('Você deve selecionar um perfil de acesso.')
        
        # Se é admin de OM, precisa ter OM principal
        if cleaned_data.get('perfil') == 'admin_om' and not cleaned_data.get('om_principal'):
            raise ValidationError('Administrador de OM deve ter uma OM principal selecionada.')
        
        return cleaned_data


class UsuarioCustomizadoAlteracaoForm(UserChangeForm):
    """Formulário para alterar usuário existente"""
    
    perfil = forms.ChoiceField(
        choices=UsuarioCustomizado.PerfilUsuario.choices,
        label='Perfil de acesso'
    )
    
    om_principal = forms.ModelChoiceField(
        queryset=OrganizacaoMilitar.objects.filter(ativo=True),
        required=False,
        label='OM Principal'
    )
    
    ativo = forms.BooleanField(
        required=False,
        label='Ativo',
        help_text='Desmarque para desativar o usuário'
    )
    
    class Meta:
        model = UsuarioCustomizado
        fields = ('username', 'email', 'first_name', 'last_name', 'perfil', 'om_principal', 'ativo')


# ============================================================================
# MILITARES
# ============================================================================

class MilitarForm(forms.ModelForm):
    """Formulário para criar/editar Militar"""
    
    cpf = forms.CharField(
        max_length=11,
        help_text='Digite o CPF sem formatação (apenas números)'
    )
    
    matricula = forms.CharField(
        max_length=20,
        help_text='Matrícula única na OM'
    )
    
    data_nascimento = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Data de nascimento'
    )
    
    class Meta:
        model = Militar
        fields = (
            'organizacao_militar', 'divisao', 'posto', 'especialidade',
            'nome_guerra', 'nome_completo', 'cpf', 'matricula',
            'data_nascimento', 'ativo'
        )
        widgets = {
            'nome_guerra': forms.TextInput(attrs={'placeholder': 'Ex: SILVA'}),
            'nome_completo': forms.TextInput(attrs={'placeholder': 'Ex: João da Silva Santos'}),
            'organizacao_militar': forms.Select(),
            'divisao': forms.Select(),
            'posto': forms.Select(),
            'especialidade': forms.Select(),
        }
    
    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        
        # Remover formatação se tiver
        cpf = cpf.replace('.', '').replace('-', '')
        
        if len(cpf) != 11:
            raise ValidationError('CPF deve ter 11 dígitos.')
        
        if not cpf.isdigit():
            raise ValidationError('CPF deve conter apenas números.')
        
        # Validação simples de CPF (todos iguais = inválido)
        if cpf == cpf[0] * 11:
            raise ValidationError('CPF inválido (todos os dígitos são iguais).')
        
        return cpf
    
    def clean_data_nascimento(self):
        data_nasc = self.cleaned_data.get('data_nascimento')
        
        # Deve ser maior de idade (18 anos)
        hoje = timezone.now().date()
        idade_minima = 18
        
        data_limite = datetime(
            hoje.year - idade_minima, hoje.month, hoje.day
        ).date()
        
        if data_nasc > data_limite:
            raise ValidationError(
                f'Militar deve ter no mínimo {idade_minima} anos de idade.'
            )
        
        return data_nasc
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validar se divisão pertence à mesma OM
        om = cleaned_data.get('organizacao_militar')
        divisao = cleaned_data.get('divisao')
        
        if om and divisao and divisao.organizacao_militar_id != om.id:
            raise ValidationError(
                'A divisão selecionada não pertence à OM escolhida.'
            )
        
        return cleaned_data


class MilitarImportacaoForm(forms.Form):
    """Formulário para importação em lote de militares (CSV)"""
    
    arquivo_csv = forms.FileField(
        help_text='Arquivo CSV com colunas: nome_guerra, nome_completo, cpf, matricula, posto, especialidade, data_nascimento'
    )
    
    organizacao_militar = forms.ModelChoiceField(
        queryset=OrganizacaoMilitar.objects.filter(ativo=True),
        label='OM destino',
        help_text='Todos os militares serão vinculados a esta OM'
    )
    
    def clean_arquivo_csv(self):
        arquivo = self.cleaned_data['arquivo_csv']
        
        if not arquivo.name.endswith('.csv'):
            raise ValidationError('O arquivo deve ser um CSV.')
        
        # Verificar tamanho (máx 5MB)
        if arquivo.size > 5 * 1024 * 1024:
            raise ValidationError('Arquivo muito grande (máx 5MB).')
        
        return arquivo


# ============================================================================
# INDISPONIBILIDADES
# ============================================================================

class IndisponibilidadeForm(forms.ModelForm):
    """Formulário para registrar indisponibilidade de militar"""
    
    data_inicio = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Data de início'
    )
    
    data_fim = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Data de fim'
    )
    
    tipo = forms.ModelChoiceField(
        queryset=TipoIndisponibilidade.objects.filter(ativo=True),
        label='Tipo de indisponibilidade'
    )
    
    class Meta:
        model = Indisponibilidade
        fields = ('militar', 'tipo', 'data_inicio', 'data_fim', 'observacao')
        widgets = {
            'observacao': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')
        
        if data_inicio and data_fim:
            if data_fim < data_inicio:
                raise ValidationError(
                    'A data de fim não pode ser anterior à data de início.'
                )
            
            # Validar se não passa de 365 dias
            duracao = (data_fim - data_inicio).days
            if duracao > 365:
                raise ValidationError(
                    'Indisponibilidade não pode ser superior a 365 dias.'
                )
        
        return cleaned_data


class IndisponibilidadeEmMassaForm(forms.Form):
    """Formulário para registrar indisponibilidades em lote"""
    
    militares = forms.ModelMultipleChoiceField(
        queryset=Militar.objects.filter(ativo=True),
        widget=forms.CheckboxSelectMultiple,
        label='Selecione os militares'
    )
    
    tipo = forms.ModelChoiceField(
        queryset=TipoIndisponibilidade.objects.filter(ativo=True),
        label='Tipo de indisponibilidade'
    )
    
    data_inicio = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Data de início'
    )
    
    data_fim = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Data de fim'
    )
    
    observacao = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        label='Observação (opcional)'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')
        
        if data_inicio and data_fim and data_fim < data_inicio:
            raise ValidationError(
                'A data de fim não pode ser anterior à data de início.'
            )
        
        return cleaned_data


# ============================================================================
# ESCALAS
# ============================================================================

class EscalaForm(forms.ModelForm):
    """Formulário para criar/editar cabeçalho de Escala"""
    
    mes = forms.IntegerField(
        min_value=1,
        max_value=12,
        help_text='Mês (1-12)'
    )
    
    ano = forms.IntegerField(
        min_value=2000,
        max_value=2100,
        help_text='Ano (ex: 2025)'
    )
    
    class Meta:
        model = Escala
        fields = (
            'organizacao_militar', 'tipo_escala', 'mes', 'ano',
            'status', 'observacao'
        )
        widgets = {
            'observacao': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validar única combinação (OM + tipo_escala + mes + ano)
        om = cleaned_data.get('organizacao_militar')
        tipo = cleaned_data.get('tipo_escala')
        mes = cleaned_data.get('mes')
        ano = cleaned_data.get('ano')
        
        if om and tipo and mes and ano:
            existe = Escala.objects.filter(
                organizacao_militar=om,
                tipo_escala=tipo,
                mes=mes,
                ano=ano
            ).exists()
            
            if existe and not self.instance.pk:  # Se é criação (não edição)
                raise ValidationError(
                    f'Já existe escala para este período e tipo.'
                )
        
        return cleaned_data


class EscalaItemForm(forms.ModelForm):
    """Formulário para adicionar militar a uma escala em um dia específico"""
    
    militar = forms.ModelChoiceField(
        queryset=Militar.objects.filter(ativo=True),
        label='Militar'
    )
    
    calendario_dia = forms.ModelChoiceField(
        queryset=CalendarioDia.objects.all(),
        label='Data'
    )
    
    class Meta:
        model = EscalaItem
        fields = ('militar', 'calendario_dia', 'observacao')
        widgets = {
            'observacao': forms.TextInput(attrs={
                'placeholder': 'Ex: Substitui tal militar'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        
        militar = cleaned_data.get('militar')
        data_dia = cleaned_data.get('calendario_dia')
        
        # Verificar se militar tem indisponibilidade
        if militar and data_dia:
            tem_indisponibilidade = militar.indisponibilidades.filter(
                data_inicio__lte=data_dia.data,
                data_fim__gte=data_dia.data,
                status=Indisponibilidade.STATUS_APROVADA,
                tipo__exclui_do_sorteio=True
            ).exists()
            
            if tem_indisponibilidade:
                raise ValidationError(
                    f'{militar.nome_guerra} tem indisponibilidade em {data_dia.data.strftime("%d/%m/%Y")}.'
                )
        
        return cleaned_data


class GeracaoAutomaticaEscalaForm(forms.Form):
    """
    Formulário para gerar escala automaticamente usando o Quadrinho
    para balanceamento
    """
    
    escala = forms.ModelChoiceField(
        queryset=Escala.objects.filter(status='rascunho'),
        label='Escala (rascunho)',
        help_text='Apenas escalas em rascunho podem ser preenchidas'
    )
    
    incluir_indisponibilidades = forms.BooleanField(
        required=False,
        initial=True,
        label='Respeitar indisponibilidades',
        help_text='Se marcado, não alocar militares indisponíveis'
    )
    
    usar_quadrinho = forms.BooleanField(
        required=False,
        initial=True,
        label='Usar Quadrinho para balanceamento',
        help_text='Prioriza militares com menos serviços'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        
        escala = cleaned_data.get('escala')
        if escala and escala.itens.exists():
            raise ValidationError(
                'Esta escala já possui itens. Limpe antes de gerar automaticamente.'
            )
        
        return cleaned_data


class PublicarEscalaForm(forms.Form):
    """Formulário simples para confirmar publicação de escala"""
    
    confirmar = forms.BooleanField(
        required=True,
        label='Tenho certeza que desejo publicar esta escala',
        help_text='Escalas publicadas não podem ser alteradas'
    )
    
    motivo = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        label='Motivo da publicação (opcional)'
    )


# ============================================================================
# CALENDÁRIO
# ============================================================================

class ConfigurarFeriadoForm(forms.ModelForm):
    """Formulário para configurar feriado móvel no calendário"""
    
    data = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Data do feriado'
    )
    
    tipo_servico = forms.ModelChoiceField(
        queryset=TipoServico.objects.filter(ativo=True),
        label='Tipo de serviço (normalmente Roxo)'
    )
    
    observacao = forms.CharField(
        max_length=120,
        help_text='Ex: "Carnaval 2025", "Corpus Christi"'
    )
    
    class Meta:
        model = CalendarioDia
        fields = ('data', 'tipo_servico', 'observacao')
    
    def clean_tipo_servico(self):
        tipo = self.cleaned_data['tipo_servico']
        
        # Validar se pertence à mesma OM
        # (será preenchido no view)
        
        return tipo


class GerarCalendarioForm(forms.Form):
    """Formulário para gerar calendário automático de um ano"""
    
    organizacao_militar = forms.ModelChoiceField(
        queryset=OrganizacaoMilitar.objects.filter(ativo=True),
        label='Organização Militar'
    )
    
    ano = forms.IntegerField(
        min_value=2020,
        max_value=2100,
        initial=timezone.now().year,
        label='Ano'
    )
    
    sobrescrever = forms.BooleanField(
        required=False,
        initial=False,
        label='Sobrescrever dias existentes',
        help_text='Se marcado, irá substituir dias já configurados'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        
        om = cleaned_data.get('organizacao_militar')
        ano = cleaned_data.get('ano')
        
        # Verificar se tem tipos de serviço configurados
        if om and om.tipos_servico.filter(ativo=True).count() < 2:
            raise ValidationError(
                'A OM deve ter pelo menos 2 tipos de serviço configurados antes de gerar calendário.'
            )
        
        return cleaned_data
