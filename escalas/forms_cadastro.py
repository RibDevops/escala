"""ModelForms simples para os cadastros básicos."""
from datetime import date

from django import forms
from django.core.exceptions import ValidationError

from .models import (
    Divisao,
    Especialidade,
    Indisponibilidade,
    Militar,
    OrganizacaoMilitar,
    Posto,
    Quadrinho,
    TipoEscala,
    TipoIndisponibilidade,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class BootstrapFormMixin:
    """Aplica `form-control`/`form-select` em todos os widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            css = widget.attrs.get('class', '')
            if isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs['class'] = (css + ' form-select').strip()
            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs['class'] = (css + ' form-check-input').strip()
            elif isinstance(widget, forms.Textarea):
                widget.attrs['class'] = (css + ' form-control').strip()
            else:
                widget.attrs['class'] = (css + ' form-control').strip()


# ---------------------------------------------------------------------------
# Organização Militar
# ---------------------------------------------------------------------------

class OrganizacaoMilitarForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = OrganizacaoMilitar
        fields = [
            'nome', 'sigla', 'tipo', 'comandante',
            'endereco', 'telefone', 'email', 'logo',
        ]


# ---------------------------------------------------------------------------
# Posto
# ---------------------------------------------------------------------------

class PostoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Posto
        fields = ['nome', 'sigla', 'ordem_hierarquica', 'ativo']


# ---------------------------------------------------------------------------
# Especialidade
# ---------------------------------------------------------------------------

class EspecialidadeForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Especialidade
        fields = ['nome', 'sigla', 'descricao', 'ativo']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3}),
        }


# ---------------------------------------------------------------------------
# Tipo de Indisponibilidade
# ---------------------------------------------------------------------------

class TipoIndisponibilidadeForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = TipoIndisponibilidade
        fields = ['nome', 'descricao', 'exclui_do_sorteio', 'ativo']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3}),
        }


# ---------------------------------------------------------------------------
# Tipo de Escala
# ---------------------------------------------------------------------------

class TipoEscalaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = TipoEscala
        fields = ['nome', 'descricao', 'folga_minima_horas', 'ativo']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3}),
            'folga_minima_horas': forms.NumberInput(attrs={'min': 0, 'max': 720, 'placeholder': 'Padrão da OM (ex: 48)'}),
        }
        help_texts = {
            'nome': 'Ex.: Permanência, Sobreaviso, Serviço Administrativo, Voo Operacional.',
            'descricao': 'Explicação resumida do que envolve este tipo de escala.',
            'folga_minima_horas': 'Deixe em branco para usar a configuração global da OM. Preencha para substituir (ex: 48 = 2 dias).',
        }

    def clean_nome(self):
        nome = (self.cleaned_data.get('nome') or '').strip()
        if not nome:
            raise ValidationError('Informe o nome do tipo de escala.')
        qs = TipoEscala.objects.filter(nome__iexact=nome)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Já existe um tipo de escala com esse nome.')
        return nome


# ---------------------------------------------------------------------------
# Divisão
# ---------------------------------------------------------------------------

class DivisaoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Divisao
        fields = ['nome', 'sigla', 'descricao', 'chefe', 'ativo']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3}),
        }


# ---------------------------------------------------------------------------
# Militar
# ---------------------------------------------------------------------------

class MilitarForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Militar
        fields = [
            'posto', 'especialidade', 'divisao',
            'nome_guerra', 'nome_completo',
            'cpf', 'matricula', 'data_nascimento',
            'data_ultima_promocao', 'nota',
            'tipos_escala',
            'username_ldap',
            'ativo',
        ]
        widgets = {
            'data_nascimento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'data_ultima_promocao': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'nota': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '10', 'placeholder': 'Ex: 8.75'}),
            'cpf': forms.TextInput(attrs={'placeholder': 'somente números (11 dígitos)'}),
            'nome_guerra': forms.TextInput(attrs={'placeholder': 'Ex: SILVA'}),
            'username_ldap': forms.TextInput(attrs={'placeholder': 'Ex: nome.sobrenome'}),
            'tipos_escala': forms.CheckboxSelectMultiple(),
        }
        labels = {
            'data_ultima_promocao': 'Última promoção',
            'nota': 'Nota do curso',
            'username_ldap': 'Username de rede (LDAP)',
            'tipos_escala': 'Participa das escalas',
        }

    def __init__(self, *args, om=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.om = om
        self.fields['posto'].queryset = Posto.objects.filter(ativo=True).order_by(
            'ordem_hierarquica'
        )
        self.fields['especialidade'].queryset = Especialidade.objects.filter(
            ativo=True
        ).order_by('nome')
        self.fields['especialidade'].required = False
        self.fields['divisao'].required = False
        self.fields['tipos_escala'].required = False
        from .models import TipoEscala
        self.fields['tipos_escala'].queryset = TipoEscala.objects.filter(ativo=True).order_by('nome')
        if om is not None:
            self.fields['divisao'].queryset = Divisao.objects.filter(
                organizacao_militar=om, ativo=True
            ).order_by('nome')
        else:
            self.fields['divisao'].queryset = Divisao.objects.none()

    def clean_cpf(self):
        cpf = (self.cleaned_data.get('cpf') or '').strip()
        cpf = ''.join(filter(str.isdigit, cpf))
        if len(cpf) != 11:
            raise ValidationError('CPF deve conter exatamente 11 dígitos.')
        qs = Militar.objects.filter(cpf=cpf)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Já existe um militar cadastrado com este CPF.')
        return cpf

    def clean_matricula(self):
        matricula = (self.cleaned_data.get('matricula') or '').strip()
        if not matricula:
            raise ValidationError('Matrícula é obrigatória.')
        if self.om is not None:
            qs = Militar.objects.filter(
                organizacao_militar=self.om, matricula=matricula
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(
                    'Já existe um militar com esta matrícula nesta OM.'
                )
        return matricula

    def clean_data_nascimento(self):
        data_nascimento = self.cleaned_data.get('data_nascimento')
        if data_nascimento:
            hoje = date.today()
            idade = (
                hoje.year - data_nascimento.year
                - ((hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day))
            )
            if idade < 18:
                raise ValidationError('Militar deve ter no mínimo 18 anos.')
        return data_nascimento


# ---------------------------------------------------------------------------
# Quadrinho (saldo inicial + ajuste manual da quantidade)
# ---------------------------------------------------------------------------

class QuadrinhoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Quadrinho
        fields = ['ajuste_inicial', 'quantidade']
        widgets = {
            'ajuste_inicial': forms.NumberInput(attrs={'min': 0}),
            'quantidade': forms.NumberInput(attrs={'min': 0}),
        }
        labels = {
            'ajuste_inicial': 'Saldo inicial (legado)',
            'quantidade': 'Quantidade pelo sistema',
        }
        help_texts = {
            'ajuste_inicial': (
                'Quantos serviços o militar já tinha antes do sistema entrar no ar. '
                'Ex.: se em abril ele já tinha 4 serviços Preto, coloque 4 aqui.'
            ),
            'quantidade': (
                'Total contado automaticamente pelo sistema. Pode ser sobrescrito '
                'manualmente quando necessário.'
            ),
        }


# ---------------------------------------------------------------------------
# Escala (criação/edição de cabeçalho)
# ---------------------------------------------------------------------------

MESES = [
    (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
    (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
    (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro'),
]


class EscalaCriarForm(BootstrapFormMixin, forms.Form):
    """Formulário simplificado para criar cabeçalho de escala."""
    tipo_escala = forms.ModelChoiceField(
        queryset=TipoEscala.objects.filter(ativo=True),
        label='Tipo de Escala',
        empty_label='Selecione…',
    )
    mes = forms.ChoiceField(choices=MESES, label='Mês')
    ano = forms.IntegerField(
        min_value=2020,
        max_value=2100,
        label='Ano',
        widget=forms.NumberInput(attrs={'min': 2020, 'max': 2100}),
    )
    observacao = forms.CharField(
        required=False,
        label='Observação',
        widget=forms.Textarea(attrs={'rows': 2}),
    )

    def __init__(self, *args, **kwargs):
        from datetime import date
        super().__init__(*args, **kwargs)
        hoje = date.today()
        self.fields['mes'].initial = hoje.month
        self.fields['ano'].initial = hoje.year


# ---------------------------------------------------------------------------
# Indisponibilidade — registro pelo escalante ou pelo próprio militar
# ---------------------------------------------------------------------------

class LancamentoManualForm(BootstrapFormMixin, forms.ModelForm):
    """Formulário para registro manual de quadrinho (lastro, atestado, férias, etc.)."""

    class Meta:
        from .models import LancamentoManualQuadrinho
        model = LancamentoManualQuadrinho
        fields = ['militar', 'tipo_escala', 'tipo_servico', 'ano', 'tipo', 'label', 'quantidade', 'observacao']
        labels = {
            'militar': 'Militar',
            'tipo_escala': 'Tipo de Escala',
            'tipo_servico': 'Tipo de Serviço',
            'ano': 'Ano',
            'tipo': 'Categoria',
            'label': 'Descrição na matriz',
            'quantidade': 'Quantidade de serviços',
            'observacao': 'Observação (interna)',
        }
        help_texts = {
            'label': 'Texto exibido na célula — ex: "Lastro", "Férias jan/25", "Atestado mar/25"',
            'quantidade': 'Quantos serviços este lançamento representa. Lastro +3 → coloque 3.',
        }
        widgets = {
            'observacao': forms.Textarea(attrs={'rows': 2}),
            'ano': forms.NumberInput(attrs={'min': 2020, 'max': 2040}),
            'quantidade': forms.NumberInput(attrs={'min': 1, 'max': 50}),
        }

    def __init__(self, *args, om=None, **kwargs):
        super().__init__(*args, **kwargs)
        from datetime import date
        from .models import OrganizacaoMilitar, Militar, TipoEscala, TipoServico
        if om:
            self.fields['militar'].queryset = (
                Militar.objects.filter(organizacao_militar=om, ativo=True)
                .select_related('posto')
                .order_by('posto__ordem_hierarquica', 'nome_guerra')
            )
            self.fields['tipo_servico'].queryset = TipoServico.objects.filter(
                organizacao_militar=om, ativo=True
            ).order_by('ordem')
        self.fields['tipo_escala'].queryset = TipoEscala.objects.filter(ativo=True).order_by('nome')
        if not self.instance.pk:
            self.fields['ano'].initial = date.today().year
            self.fields['quantidade'].initial = 1

    def clean_quantidade(self):
        v = self.cleaned_data.get('quantidade')
        if v is None or v < 1:
            raise ValidationError('A quantidade deve ser pelo menos 1.')
        return v


class UsuarioForm(BootstrapFormMixin, forms.ModelForm):
    """Formulário para criação/edição de usuários (autenticação via LDAP)."""

    class Meta:
        from .models import UsuarioCustomizado
        model = UsuarioCustomizado
        fields = ['username', 'first_name', 'last_name', 'perfil', 'om_principal', 'ativo']
        labels = {
            'username': 'Nome de usuário (login LDAP)',
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
            'perfil': 'Papel / Nível de acesso',
            'om_principal': 'OM principal',
            'ativo': 'Ativo',
        }
        help_texts = {
            'username': 'Deve corresponder exatamente ao login da rede (LDAP).',
            'perfil': 'Define o que o usuário pode fazer no sistema.',
            'om_principal': 'OM à qual este usuário pertence.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import OrganizacaoMilitar
        self.fields['om_principal'].queryset = OrganizacaoMilitar.objects.filter(ativo=True).order_by('nome')
        self.fields['om_principal'].required = False
        self.fields['first_name'].required = False
        self.fields['last_name'].required = False

    def clean_username(self):
        from .models import UsuarioCustomizado
        username = (self.cleaned_data.get('username') or '').strip().lower()
        if not username:
            raise ValidationError('Informe o nome de usuário.')
        qs = UsuarioCustomizado.objects.filter(username=username)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Já existe um usuário com este nome de login.')
        return username


class IndisponibilidadeRegistrarForm(BootstrapFormMixin, forms.ModelForm):
    """
    Formulário para registrar indisponibilidade.
    - data_fim é opcional: se omitida, o sistema usa data_inicio (1 dia).
    - Escalante: campo `militar` é um dropdown filtrado pela OM.
    - Militar logado: campo `militar` é ocultado (preenchido automaticamente).
    """

    class Meta:
        model = Indisponibilidade
        fields = ['militar', 'tipo', 'data_inicio', 'data_fim', 'observacao']
        widgets = {
            'data_inicio': forms.DateInput(attrs={'type': 'date'}),
            'data_fim': forms.DateInput(attrs={
                'type': 'date',
                'placeholder': 'Deixe em branco para registrar 1 dia',
            }),
            'observacao': forms.Textarea(attrs={'rows': 2}),
        }
        labels = {
            'militar': 'Militar',
            'tipo': 'Tipo de indisponibilidade',
            'data_inicio': 'Data de início',
            'data_fim': 'Data de fim',
            'observacao': 'Observação (opcional)',
        }

    def __init__(self, *args, om=None, militar_fixo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo'].queryset = TipoIndisponibilidade.objects.filter(ativo=True)
        self.fields['data_fim'].required = False
        self.fields['data_fim'].help_text = 'Deixe em branco para registrar apenas 1 dia.'
        if om:
            self.fields['militar'].queryset = (
                Militar.objects.filter(organizacao_militar=om, ativo=True)
                .select_related('posto')
                .order_by('posto__ordem_hierarquica', 'data_ultima_promocao', 'nome_guerra')
            )
        if militar_fixo:
            self.fields['militar'].initial = militar_fixo
            self.fields['militar'].widget = forms.HiddenInput()
            self.fields['militar'].required = False

    def clean(self):
        cleaned = super().clean()
        ini = cleaned.get('data_inicio')
        fim = cleaned.get('data_fim')
        if ini and not fim:
            cleaned['data_fim'] = ini
            self._data_fim_ajustada = True
        elif ini and fim and fim < ini:
            raise ValidationError('Data de fim não pode ser anterior à data de início.')
        else:
            self._data_fim_ajustada = False
        return cleaned
