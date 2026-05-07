"""
Sistema de Escala Militar - Modelos Django
Suporta múltiplas Organizações Militares (OM) com usuários diferenciados
"""

from typing import Optional

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.text import slugify
from datetime import datetime, timedelta


# ============================================================================
# USUÁRIOS E PERFIS
# ============================================================================

class PerfilUsuario(models.TextChoices):
    """Perfis disponíveis no sistema"""
    ADMIN_OM = "admin_om", "Administrador da OM"
    ESCALANTE = "escalante", "Escalante (Gera escalas)"
    MILITAR = "militar", "Militar (Consulta apenas)"
    GERENTE = "gerente", "Gerente (Leitura e relatórios)"


class UsuarioCustomizado(AbstractUser):
    """Usuário customizado com suporte multi-OM"""
    
    # Campos básicos (herdados de AbstractUser: username, email, password, etc)
    # IMPORTANTE: Os fields 'groups' e 'user_permissions' são herdados de AbstractUser
    # e precisam de related_name para evitar conflitos
    
    # Sobrescrever os fields herdados com related_name customizado
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='Grupos de permissão',
        related_name="usuario_customizado_set"  # ← CUSTOMIZADO
    )
    
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Permissões específicas',
        related_name="usuario_customizado_set"  # ← CUSTOMIZADO
    )
    
    perfil = models.CharField(
        max_length=20,
        choices=PerfilUsuario.choices,
        default=PerfilUsuario.MILITAR,
        help_text="Nível de acesso no sistema"
    )
    
    # Um usuário pode estar vinculado a uma OM principal
    om_principal = models.ForeignKey(
        'OrganizacaoMilitar',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios_principais',
        help_text="OM onde o usuário trabalha principalmente"
    )
    
    # Usuário pode ser militar ou não
    eh_militar = models.BooleanField(
        default=False,
        help_text="Indica se este usuário também é um registro de Militar"
    )
    
    # Ligar a um Militar se for o caso
    militar_associado = models.OneToOneField(
        'Militar',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuario',
        help_text="Se eh_militar=True, referencia ao Militar correspondente"
    )
    
    ativo = models.BooleanField(
        default=True,
        help_text="Soft delete para preservar histórico"
    )
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'usuario_customizado'
        ordering = ['first_name', 'last_name']
        indexes = [
            models.Index(fields=['perfil', 'ativo']),
            models.Index(fields=['om_principal', 'ativo']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_perfil_display()})"
    
    def pode_escalar(self) -> bool:
        """Verifica se o usuário tem permissão para gerar escalas"""
        return self.perfil == PerfilUsuario.ESCALANTE and self.ativo
    
    def pode_administrar(self) -> bool:
        """Verifica se o usuário é admin de OM"""
        return self.perfil == PerfilUsuario.ADMIN_OM and self.ativo
    
    def obter_oms_acesso(self):
        """Retorna as OMs que o usuário pode acessar"""
        if self.pode_administrar():
            # Admin de OM só acessa sua OM principal
            return OrganizacaoMilitar.objects.filter(id=self.om_principal_id, ativo=True)
        elif self.eh_militar and self.militar_associado:
            # Militar só acessa sua própria OM
            return OrganizacaoMilitar.objects.filter(
                id=self.militar_associado.organizacao_militar_id,
                ativo=True
            )
        return OrganizacaoMilitar.objects.none()


# ============================================================================
# ORGANIZAÇÕES MILITARES E ESTRUTURA HIERÁRQUICA
# ============================================================================

class OrganizacaoMilitar(models.Model):
    """OM - Unidade organizacional militar (Batalhão, Companhia, etc.)"""
    
    nome = models.CharField(
        max_length=120,
        help_text="Nome da OM (ex: 1º Batalhão de Infantaria)"
    )
    
    sigla = models.CharField(
        max_length=20,
        unique=True,
        help_text="Sigla/código único (ex: BtlInf01)"
    )
    
    # Uma OM pode estar dentro de outra (hierarquia)
    om_superior = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='om_subordinadas',
        help_text="OM que controla esta (ex: um Batalhão está sob um Regimento)"
    )
    
    tipo = models.CharField(
        max_length=50,
        choices=[
            ('regimento', 'Regimento'),
            ('batalhao', 'Batalhão'),
            ('companhia', 'Companhia'),
            ('pelotao', 'Pelotão'),
            ('secao', 'Seção'),
            ('outro', 'Outro'),
        ],
        default='outro'
    )
    
    endereco = models.CharField(
        max_length=200,
        blank=True,
        help_text="Localização da OM"
    )
    
    telefone = models.CharField(
        max_length=20,
        blank=True
    )
    
    email = models.EmailField(
        blank=True,
        help_text="E-mail de contato da OM"
    )
    
    comandante = models.CharField(
        max_length=120,
        blank=True,
        help_text="Nome do comandante atual"
    )

    logo = models.ImageField(
        upload_to='oms/logos/',
        blank=True,
        null=True,
        help_text="Brasão/distintivo da OM (substitui a estrela amarela na navbar)"
    )

    ativo = models.BooleanField(
        default=True,
        help_text="Soft delete"
    )
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'organizacao_militar'
        ordering = ['nome']
        indexes = [
            models.Index(fields=['sigla']),
            models.Index(fields=['ativo', 'om_superior']),
        ]
        verbose_name_plural = "Organizações Militares"
    
    def __str__(self):
        return f"{self.sigla} - {self.nome}"
    
    def obter_hierarquia_completa(self) -> list:
        """Retorna a cadeia de OMs acima desta (do topo até esta)"""
        cadeia = [self]
        om_atual = self.om_superior
        while om_atual:
            cadeia.insert(0, om_atual)
            om_atual = om_atual.om_superior
        return cadeia


class Divisao(models.Model):
    """
    Divisão - Agrupamento dentro de uma OM
    (ex: Divisão de Pessoal, Divisão de Operações)
    """
    
    organizacao_militar = models.ForeignKey(
        OrganizacaoMilitar,
        on_delete=models.CASCADE,
        related_name='divisoes'
    )
    
    nome = models.CharField(
        max_length=100,
        help_text="Ex: Divisão de Pessoal, Divisão de Operações"
    )
    
    sigla = models.CharField(
        max_length=20,
        help_text="Ex: DPE, DOP"
    )
    
    descricao = models.TextField(
        blank=True,
        help_text="Descrição das responsabilidades"
    )
    
    chefe = models.CharField(
        max_length=120,
        blank=True,
        help_text="Nome do chefe da divisão"
    )
    
    ativo = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'divisao'
        ordering = ['organizacao_militar', 'nome']
        unique_together = ['organizacao_militar', 'sigla']
        indexes = [
            models.Index(fields=['organizacao_militar', 'ativo']),
        ]
    
    def __str__(self):
        return f"{self.sigla} - {self.nome} ({self.organizacao_militar.sigla})"


class Posto(models.Model):
    """Hierarquia militar (Soldado, Cabo, Sargento, Tenente, etc.)"""
    
    nome = models.CharField(
        max_length=60,
        unique=True,
        help_text="Ex: Soldado, Cabo, Sargento, Tenente"
    )
    
    sigla = models.CharField(
        max_length=10,
        unique=True,
        help_text="Ex: Sd, Cb, Sgt, Tte"
    )
    
    ordem_hierarquica = models.PositiveIntegerField(
        unique=True,
        help_text="Ordem na hierarquia (1=menor, 20=maior)"
    )
    
    ativo = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'posto'
        ordering = ['ordem_hierarquica']
        indexes = [
            models.Index(fields=['ordem_hierarquica']),
        ]
    
    def __str__(self):
        return f"{self.sigla} - {self.nome}"


class Especialidade(models.Model):
    """Especialidade/função do militar (Piloto, Mecânico, Enfermeiro, etc.)"""
    
    nome = models.CharField(
        max_length=80,
        unique=True,
        help_text="Ex: Piloto, Mecânico de Motores"
    )
    
    sigla = models.CharField(
        max_length=15,
        unique=True,
        help_text="Ex: PLT, MEC"
    )
    
    descricao = models.TextField(
        blank=True,
        help_text="Descrição de responsabilidades e requisitos"
    )
    
    ativo = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'especialidade'
        ordering = ['nome']
        verbose_name_plural = "Especialidades"
    
    def __str__(self):
        return f"{self.sigla} - {self.nome}"


# ============================================================================
# MILITARES
# ============================================================================

class Militar(models.Model):
    """
    Entidade central: um militar pertence a uma OM e pode ter múltiplas
    especialidades ao longo do tempo
    """
    
    # Vínculo organizacional
    organizacao_militar = models.ForeignKey(
        OrganizacaoMilitar,
        on_delete=models.PROTECT,  # Não deletar OM se houver militares
        related_name='militares',
        help_text="OM à qual o militar pertence"
    )
    
    divisao = models.ForeignKey(
        Divisao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='militares',
        help_text="Divisão dentro da OM"
    )
    
    # Dados hierárquicos e funcionais
    posto = models.ForeignKey(
        Posto,
        on_delete=models.PROTECT,
        related_name='militares'
    )
    
    especialidade = models.ForeignKey(
        Especialidade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='militares'
    )
    
    # Identificação
    nome_guerra = models.CharField(
        max_length=40,
        help_text="Nome de guerra do militar (aparece nas escalas)"
    )
    
    nome_completo = models.CharField(
        max_length=120,
        help_text="Nome completo para registros oficiais"
    )
    
    cpf = models.CharField(
        max_length=11,
        unique=True,
        help_text="CPF sem formatação"
    )
    
    matricula = models.CharField(
        max_length=20,
        unique=True,
        help_text="Matrícula militar/ID único da OM"
    )
    
    data_nascimento = models.DateField(
        help_text="Data de nascimento"
    )

    data_ultima_promocao = models.DateField(
        null=True,
        blank=True,
        help_text=(
            "Data da última promoção ao posto atual. "
            "Usada como critério de antiguidade quando dois militares têm o mesmo posto: "
            "a data mais antiga indica o militar mais antigo."
        )
    )

    # Vínculo com usuário do sistema (login próprio do militar)
    user = models.OneToOneField(
        'escalas.UsuarioCustomizado',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='militar',
        help_text="Usuário Django vinculado a este militar (para auto-serviço)"
    )

    # Status
    ativo = models.BooleanField(
        default=True,
        help_text="Soft delete para manter histórico de escalas"
    )
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'militar'
        ordering = ['organizacao_militar', 'nome_guerra']
        unique_together = ['organizacao_militar', 'matricula']
        indexes = [
            models.Index(fields=['organizacao_militar', 'ativo']),
            models.Index(fields=['nome_guerra']),
            models.Index(fields=['cpf']),
        ]
    
    def __str__(self):
        return f"{self.nome_guerra} ({self.posto.sigla})"
    
    def limpar(self):
        """Validação customizada"""
        from django.utils.text import slugify
        
        # Validar CPF (simplificado)
        if len(self.cpf) != 11:
            raise ValidationError("CPF deve ter 11 dígitos")
        
        if not self.cpf.isdigit():
            raise ValidationError("CPF deve conter apenas dígitos")
        
        # Validar data de nascimento (maior de idade)
        hoje = timezone.now().date()
        idade_minima = 18
        data_minima = datetime(
            hoje.year - idade_minima, hoje.month, hoje.day
        ).date()
        
        if self.data_nascimento > data_minima:
            raise ValidationError(f"Militar deve ter no mínimo {idade_minima} anos")
    
    def save(self, *args, **kwargs):
        self.limpar()
        # Garantir que divisao pertence à mesma OM
        if self.divisao and self.divisao.organizacao_militar_id != self.organizacao_militar_id:
            raise ValidationError("Divisão deve pertencer à mesma OM")
        super().save(*args, **kwargs)
    
    def obter_idade(self) -> int:
        """Retorna a idade atual do militar"""
        hoje = timezone.now().date()
        return (
            hoje.year - self.data_nascimento.year -
            ((hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day))
        )


# ============================================================================
# CONFIGURAÇÃO DE ESCALAS
# ============================================================================

class TipoServico(models.Model):
    """
    Tipo de serviço por dia: Preto (seg-sex), Vermelho (sáb-dom), Roxo (feriados)
    Configurável por OM
    """
    
    organizacao_militar = models.ForeignKey(
        OrganizacaoMilitar,
        on_delete=models.CASCADE,
        related_name='tipos_servico',
        help_text="Cada OM pode customizar seus tipos de serviço"
    )
    
    nome = models.CharField(
        max_length=40,
        help_text="Ex: Preto, Vermelho, Roxo, Normal"
    )
    
    cor_hex = models.CharField(
        max_length=7,
        help_text="Cor em hex (ex: #000000)",
        default='#000000'
    )
    
    descricao = models.TextField(
        blank=True,
        help_text="Ex: 'Segunda a sexta - dias úteis'"
    )
    
    ordem = models.PositiveIntegerField(
        default=0,
        help_text="Ordem de exibição"
    )
    
    ativo = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'tipo_servico'
        ordering = ['organizacao_militar', 'ordem']
        unique_together = ['organizacao_militar', 'nome']
        indexes = [
            models.Index(fields=['organizacao_militar', 'ativo']),
        ]
    
    def __str__(self):
        return f"{self.nome} ({self.organizacao_militar.sigla})"


class TipoEscala(models.Model):
    """Tipo de escala: Permanência, Sobreaviso, etc."""
    
    nome = models.CharField(
        max_length=60,
        unique=True,
        help_text="Ex: Permanência, Sobreaviso, Serviço Administrativo"
    )

    slug = models.SlugField(
        max_length=80,
        unique=True,
        blank=True,
        help_text="URL amigável gerada automaticamente do nome (ex: permanencia). "
                  "Não altere após criação para não quebrar links existentes.",
    )
    
    descricao = models.TextField(
        blank=True,
        help_text="Explicação do tipo de escala"
    )

    folga_minima_horas = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Folga mínima específica para este tipo de escala (horas). "
            "Se vazio, usa a configuração global da OM."
        )
    )

    ativo = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'tipo_escala'
        ordering = ['nome']
    
    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.nome) or f'tipo-{self.pk or "novo"}'
            slug = base
            n = 1
            while TipoEscala.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_escala_publica_url(self):
        return f'/escala/{self.slug}/'

    def get_matriz_publica_url(self):
        return f'/matriz/{self.slug}/'

    def folga_efetiva_dias(self, config=None) -> int:
        """Retorna a folga mínima em dias: usa o override do tipo ou o global da OM."""
        if self.folga_minima_horas is not None:
            return max(1, self.folga_minima_horas // 24)
        if config is not None:
            return config.folga_minima_dias
        return 2  # padrão seguro


class CalendarioDia(models.Model):
    """
    Calendário com tipificação de dias (preto, vermelho, roxo)
    Um por OM para permitir configurações diferentes
    """
    
    ORIGEM_TIPO = [
        ('AUTO', 'Automático (segunda a sexta / sábado e domingo)'),
        ('MANUAL', 'Manual (feriado móvel ou ajuste especial)'),
    ]
    
    organizacao_militar = models.ForeignKey(
        OrganizacaoMilitar,
        on_delete=models.CASCADE,
        related_name='calendario_dias',
        help_text="Cada OM tem seu próprio calendário"
    )
    
    data = models.DateField(
        help_text="Data do dia"
    )
    
    tipo_servico = models.ForeignKey(
        TipoServico,
        on_delete=models.PROTECT,
        related_name='dias_calendario',
        help_text="Tipo de serviço para este dia"
    )
    
    origem_tipo = models.CharField(
        max_length=10,
        choices=ORIGEM_TIPO,
        default='AUTO',
        help_text="Como o tipo foi definido"
    )
    
    observacao = models.CharField(
        max_length=120,
        blank=True,
        help_text="Ex: 'Carnaval 2025', 'Feriado antecipado'"
    )
    
    class Meta:
        db_table = 'calendario_dia'
        ordering = ['organizacao_militar', 'data']
        unique_together = ['organizacao_militar', 'data']
        indexes = [
            models.Index(fields=['organizacao_militar', 'data']),
            models.Index(fields=['data', 'tipo_servico']),
        ]
    
    def __str__(self):
        return f"{self.data.strftime('%d/%m/%Y')} - {self.tipo_servico.nome} ({self.organizacao_militar.sigla})"
    
    @staticmethod
    def gerar_calendario_automatico(om: OrganizacaoMilitar, ano: int) -> None:
        """
        Gera o calendário automático para um ano inteiro:
        - Segunda a sexta = TipoServico 'Preto' (ou o primeiro cadastrado)
        - Sábado e domingo = TipoServico 'Vermelho' (ou o segundo)
        """
        from datetime import date, timedelta
        
        # Obter tipos de serviço (assumindo ordem: preto, vermelho, roxo)
        tipos = om.tipos_servico.filter(ativo=True).order_by('ordem')
        if tipos.count() < 2:
            raise ValidationError("OM deve ter pelo menos 2 tipos de serviço configurados")
        
        tipo_semana = tipos[0]  # Preto
        tipo_fim_semana = tipos[1]  # Vermelho
        
        # Gerar 365/366 dias do ano
        data_inicio = date(ano, 1, 1)
        data_fim = date(ano, 12, 31)
        data_atual = data_inicio
        
        while data_atual <= data_fim:
            # 5 = sábado, 6 = domingo
            if data_atual.weekday() in [5, 6]:
                tipo = tipo_fim_semana
            else:
                tipo = tipo_semana
            
            CalendarioDia.objects.get_or_create(
                organizacao_militar=om,
                data=data_atual,
                defaults={'tipo_servico': tipo, 'origem_tipo': 'AUTO'}
            )
            
            data_atual += timedelta(days=1)


class TipoIndisponibilidade(models.Model):
    """Tipos de indisponibilidade: Férias, Licença, Missão, Dispensa, etc."""
    
    nome = models.CharField(
        max_length=60,
        unique=True,
        help_text="Ex: Férias, Licença Médica, Missão"
    )
    
    descricao = models.TextField(
        blank=True
    )
    
    exclui_do_sorteio = models.BooleanField(
        default=True,
        help_text="Se True, militar com este tipo não pode ser escalado"
    )
    
    ativo = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'tipo_indisponibilidade'
        ordering = ['nome']
        verbose_name_plural = "Tipos de Indisponibilidade"
    
    def __str__(self):
        return self.nome


class Indisponibilidade(models.Model):
    """Períodos em que um militar não pode ser escalado"""
    
    militar = models.ForeignKey(
        Militar,
        on_delete=models.CASCADE,
        related_name='indisponibilidades'
    )
    
    tipo = models.ForeignKey(
        TipoIndisponibilidade,
        on_delete=models.PROTECT,
        related_name='indisponibilidades'
    )
    
    data_inicio = models.DateField(
        help_text="Primeira data indisponível"
    )
    
    data_fim = models.DateField(
        help_text="Última data indisponível"
    )
    
    observacao = models.TextField(
        blank=True,
        help_text="Motivo adicional"
    )
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'indisponibilidade'
        ordering = ['-data_inicio']
        indexes = [
            models.Index(fields=['militar', 'data_inicio', 'data_fim']),
        ]
    
    def __str__(self):
        return f"{self.militar.nome_guerra} - {self.tipo.nome} ({self.data_inicio} a {self.data_fim})"
    
    def limpar(self):
        """Validação customizada"""
        if self.data_fim < self.data_inicio:
            raise ValidationError("Data de fim não pode ser antes da data de início")
    
    def save(self, *args, **kwargs):
        self.limpar()
        super().save(*args, **kwargs)
    
    def militar_disponivel_em(data: timezone.now().date()) -> bool:
        """Verifica se o militar está disponível em uma data específica"""
        return not self.indisponibilidades.filter(
            data_inicio__lte=data,
            data_fim__gte=data,
            tipo__exclui_do_sorteio=True
        ).exists()


# ============================================================================
# ESCALAS
# ============================================================================

class Escala(models.Model):
    """Cabeçalho da escala mensal para um tipo de escala específico"""
    
    STATUS_CHOICES = [
        ('rascunho', 'Rascunho'),
        ('previsao', 'Previsão'),
        ('publicada', 'Escala (Oficial)'),
        ('arquivada', 'Arquivada'),
    ]
    
    organizacao_militar = models.ForeignKey(
        OrganizacaoMilitar,
        on_delete=models.CASCADE,
        related_name='escalas',
        help_text="Cada OM tem suas próprias escalas"
    )
    
    tipo_escala = models.ForeignKey(
        TipoEscala,
        on_delete=models.PROTECT,
        related_name='escalas'
    )
    
    mes = models.PositiveIntegerField(
        help_text="Mês (1-12)"
    )
    
    ano = models.PositiveIntegerField(
        help_text="Ano (ex: 2025)"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='rascunho'
    )
    
    usuario_criacao = models.ForeignKey(
        UsuarioCustomizado,
        on_delete=models.SET_NULL,
        null=True,
        related_name='escalas_criadas'
    )
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    data_publicacao = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data em que foi publicada"
    )
    
    observacao = models.TextField(
        blank=True,
        help_text="Observações gerais sobre a escala"
    )
    
    class Meta:
        db_table = 'escala'
        ordering = ['-ano', '-mes']
        unique_together = ['organizacao_militar', 'tipo_escala', 'mes', 'ano']
        indexes = [
            models.Index(fields=['organizacao_militar', 'status']),
            models.Index(fields=['ano', 'mes']),
        ]
    
    def __str__(self):
        return f"{self.organizacao_militar.sigla} - {self.tipo_escala.nome} ({self.mes:02d}/{self.ano})"
    
    def marcar_previsao(self):
        """Marca como Previsão (fase intermediária antes de virar Escala oficial)."""
        if self.status not in ('rascunho', 'publicada'):
            raise ValidationError(
                "Só é possível marcar como Previsão a partir de Rascunho ou Escala (Oficial)."
            )
        self.status = 'previsao'
        self.save()

    def publicar(self):
        """Muda status para Escala (Oficial) e registra data."""
        if self.status not in ('rascunho', 'previsao'):
            raise ValidationError(
                "Apenas escalas em Rascunho ou Previsão podem virar Escala (Oficial)."
            )

        self.status = 'publicada'
        self.data_publicacao = timezone.now()
        self.save()

    @property
    def eh_previsao(self) -> bool:
        return self.status == 'previsao'

    @property
    def eh_oficial(self) -> bool:
        return self.status == 'publicada'
    
    def limpar(self):
        """Validação customizada"""
        if not (1 <= self.mes <= 12):
            raise ValidationError("Mês deve estar entre 1 e 12")
        if self.ano < 2000 or self.ano > 2100:
            raise ValidationError("Ano deve estar entre 2000 e 2100")
    
    def save(self, *args, **kwargs):
        self.limpar()
        super().save(*args, **kwargs)
    
    def obter_intervalo_datas(self) -> tuple:
        """Retorna (data_inicio, data_fim) do mês/ano"""
        from datetime import date
        import calendar
        
        primeiro_dia = date(self.ano, self.mes, 1)
        ultimo_dia_mes = calendar.monthrange(self.ano, self.mes)[1]
        ultimo_dia = date(self.ano, self.mes, ultimo_dia_mes)
        
        return (primeiro_dia, ultimo_dia)


class EscalaItem(models.Model):
    """Cada alocação: um militar em um dia para uma escala"""
    
    escala = models.ForeignKey(
        Escala,
        on_delete=models.CASCADE,
        related_name='itens'
    )
    
    militar = models.ForeignKey(
        Militar,
        on_delete=models.PROTECT,
        related_name='escalas_itens'
    )
    
    calendario_dia = models.ForeignKey(
        CalendarioDia,
        on_delete=models.PROTECT,
        related_name='escalas_itens'
    )
    
    observacao = models.CharField(
        max_length=200,
        blank=True,
        help_text="Ex: 'Substitui...' ou 'Justificativa de troca'"
    )

    forcar_escala = models.BooleanField(
        default=False,
        help_text=(
            "Quando marcado, ignora a regra de folga mínima para este item. "
            "Use para situações excepcionais (serviços consecutivos por necessidade operacional)."
        )
    )

    substituto = models.ForeignKey(
        Militar,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='escalas_como_substituto',
        help_text="Militar que substituiu o escalado original na Escala Oficial.",
    )

    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'escala_item'
        ordering = ['calendario_dia__data', 'militar__nome_guerra']
        unique_together = ['escala', 'calendario_dia']
        indexes = [
            models.Index(fields=['escala', 'militar']),
            models.Index(fields=['calendario_dia']),
        ]
    
    def __str__(self):
        return f"{self.militar.nome_guerra} - {self.calendario_dia.data.strftime('%d/%m/%Y')}"
    
    def limpar(self):
        """Validação customizada"""
        # Verificar se militar pertence à mesma OM da escala
        if self.militar.organizacao_militar_id != self.escala.organizacao_militar_id:
            raise ValidationError("Militar deve pertencer à mesma OM da escala")
        
        # Verificar se dia pertence à mesma OM
        if self.calendario_dia.organizacao_militar_id != self.escala.organizacao_militar_id:
            raise ValidationError("Dia deve pertencer à mesma OM da escala")
        
        # Verificar se militar está disponível naquele dia
        if not self.militar_disponivel_naquele_dia():
            raise ValidationError("Militar tem indisponibilidade registrada para este dia")
    
    def save(self, *args, **kwargs):
        self.limpar()
        super().save(*args, **kwargs)
    
    def militar_disponivel_naquele_dia(self) -> bool:
        """Verifica se o militar está disponível no dia da escala"""
        return not self.militar.indisponibilidades.filter(
            data_inicio__lte=self.calendario_dia.data,
            data_fim__gte=self.calendario_dia.data,
            tipo__exclui_do_sorteio=True
        ).exists()


# ============================================================================
# QUADRINHO - CONTAGEM E BALANCEAMENTO
# ============================================================================

class Quadrinho(models.Model):
    """
    Contagem de serviços por militar, tipo de escala, tipo de serviço e ano.
    Base para balanceamento automático das escalas.
    """
    
    militar = models.ForeignKey(
        Militar,
        on_delete=models.CASCADE,
        related_name='quadrinhos'
    )
    
    tipo_escala = models.ForeignKey(
        TipoEscala,
        on_delete=models.CASCADE,
        related_name='quadrinhos'
    )
    
    tipo_servico = models.ForeignKey(
        TipoServico,
        on_delete=models.CASCADE,
        related_name='quadrinhos'
    )
    
    ano = models.PositiveIntegerField(
        help_text="Ano da contagem"
    )
    
    quantidade = models.PositiveIntegerField(
        default=0,
        help_text="Serviços contabilizados pelo sistema (pode ser sobrescrito manualmente)"
    )

    ajuste_inicial = models.PositiveIntegerField(
        default=0,
        help_text="Saldo inicial vindo do controle anterior (legado, antes deste sistema)"
    )

    data_atualizacao = models.DateTimeField(auto_now=True)

    @property
    def total(self) -> int:
        """Soma do ajuste inicial (legado) + quantidade contada pelo sistema."""
        return (self.ajuste_inicial or 0) + (self.quantidade or 0)
    
    class Meta:
        db_table = 'quadrinho'
        unique_together = ['militar', 'tipo_escala', 'tipo_servico', 'ano']
        ordering = ['ano', '-quantidade']
        indexes = [
            models.Index(fields=['militar', 'ano']),
            models.Index(fields=['tipo_escala', 'tipo_servico', 'ano']),
        ]
    
    def __str__(self):
        return (
            f"{self.militar.nome_guerra} - {self.tipo_escala.nome} - "
            f"{self.tipo_servico.nome} ({self.ano}): {self.quantidade}x"
        )
    
    @staticmethod
    def incrementar(
        militar: Militar,
        tipo_escala: TipoEscala,
        tipo_servico: TipoServico,
        ano: int,
        quantidade: int = 1
    ) -> 'Quadrinho':
        """
        Incrementa a contagem de serviços de um militar.
        Se não existir, cria.
        """
        quadrinho, _ = Quadrinho.objects.get_or_create(
            militar=militar,
            tipo_escala=tipo_escala,
            tipo_servico=tipo_servico,
            ano=ano,
            defaults={'quantidade': 0}
        )
        
        quadrinho.quantidade += quantidade
        quadrinho.save()
        
        return quadrinho
    
    @staticmethod
    def obter_ranking(
        tipo_escala: TipoEscala,
        tipo_servico: TipoServico,
        ano: int,
        om: OrganizacaoMilitar = None
    ) -> models.QuerySet:
        """
        Retorna militares ordenados por quantidade (menor primeiro).
        Útil para o algoritmo de geração automática.
        """
        qs = Quadrinho.objects.filter(
            tipo_escala=tipo_escala,
            tipo_servico=tipo_servico,
            ano=ano
        ).order_by('quantidade')
        
        if om:
            qs = qs.filter(militar__organizacao_militar=om)
        
        return qs


# ============================================================================
# CONFIGURAÇÃO DE REGRAS DA ESCALA
# ============================================================================

class ConfiguracaoEscala(models.Model):
    """
    Configuração de regras operacionais da escala por OM.
    Permite ajustar folga mínima e regras de bloqueio sem alterar o código.
    """

    organizacao_militar = models.OneToOneField(
        OrganizacaoMilitar,
        on_delete=models.CASCADE,
        related_name='configuracao_escala',
        help_text="OM à qual esta configuração se aplica"
    )

    folga_minima_horas = models.PositiveIntegerField(
        default=48,
        help_text=(
            "Horas mínimas de folga exigidas após um serviço ou retorno de "
            "férias/indisponibilidade antes de novo serviço. "
            "Exemplo: 48 = dois dias de folga."
        )
    )

    duracao_servico_horas = models.PositiveIntegerField(
        default=24,
        help_text=(
            "Duração padrão de um serviço em horas. "
            "Usado para calcular quando o militar fica livre após o serviço."
        )
    )

    bloquear_pre_ferias = models.BooleanField(
        default=True,
        help_text=(
            "Se ativado, bloqueia serviços que terminariam dentro do período "
            "de folga mínima antes do início de uma férias/indisponibilidade."
        )
    )

    bloquear_pos_ferias = models.BooleanField(
        default=True,
        help_text=(
            "Se ativado, bloqueia serviços dentro do período de folga mínima "
            "após o retorno de férias/indisponibilidade."
        )
    )

    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'configuracao_escala'
        verbose_name = 'Configuração de Escala'
        verbose_name_plural = 'Configurações de Escala'

    def __str__(self):
        return f"Config {self.organizacao_militar.sigla} (folga {self.folga_minima_horas}h)"

    @classmethod
    def obter_para_om(cls, om: OrganizacaoMilitar) -> 'ConfiguracaoEscala':
        """Retorna (ou cria com padrões) a configuração da OM."""
        config, _ = cls.objects.get_or_create(organizacao_militar=om)
        return config

    @property
    def folga_minima_dias(self) -> int:
        return max(1, self.folga_minima_horas // 24)

    @property
    def duracao_servico_dias(self) -> int:
        return max(1, self.duracao_servico_horas // 24)


# ============================================================================
# PONTEIRO DE COLUNA — continuidade do algoritmo entre meses
# ============================================================================

class PonteiroEscala(models.Model):
    """
    Persiste o estado do ponteiro BASE→TOPO entre meses.

    Um registro por (OM, TipoServico): guarda o último militar escalado
    naquele tipo de serviço para que o mês seguinte retome de onde parou.
    """

    organizacao_militar = models.ForeignKey(
        OrganizacaoMilitar,
        on_delete=models.CASCADE,
        related_name='ponteiros_escala',
    )

    tipo_servico = models.ForeignKey(
        TipoServico,
        on_delete=models.CASCADE,
        related_name='ponteiros_escala',
    )

    ultimo_militar = models.ForeignKey(
        Militar,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text='Último militar escalado neste tipo de serviço.',
    )

    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ponteiro_escala'
        unique_together = ['organizacao_militar', 'tipo_servico']
        verbose_name = 'Ponteiro de Escala'
        verbose_name_plural = 'Ponteiros de Escala'

    def __str__(self):
        mil = self.ultimo_militar.nome_guerra if self.ultimo_militar else '—'
        return (
            f'Ponteiro {self.organizacao_militar.sigla} '
            f'/ {self.tipo_servico.nome} → {mil}'
        )

    @classmethod
    def obter_ultimo_id(cls, om: 'OrganizacaoMilitar', tipo_servico: 'TipoServico') -> Optional[int]:
        """Retorna o pk do último militar escalado, ou None."""
        try:
            p = cls.objects.get(organizacao_militar=om, tipo_servico=tipo_servico)
            return p.ultimo_militar_id
        except cls.DoesNotExist:
            return None

    @classmethod
    def salvar(cls, om: 'OrganizacaoMilitar', tipo_servico: 'TipoServico', militar_id: Optional[int]):
        """Cria ou atualiza o ponteiro."""
        cls.objects.update_or_create(
            organizacao_militar=om,
            tipo_servico=tipo_servico,
            defaults={'ultimo_militar_id': militar_id},
        )
