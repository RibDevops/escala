"""Context processor que injeta a OM ativa e a lista de OMs disponíveis."""
from .models import Indisponibilidade, OrganizacaoMilitar, PerfilUsuario


SESSION_KEY_OM = 'om_id_ativa'


def obter_om_da_sessao(request):
    """
    Resolve a OM ativa a partir da sessão, com fallback.

    Para usuários com perfil 'militar', a OM é sempre a do próprio militar —
    eles não podem trocar de OM via sessão.
    """
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return None

    # Militar comum: OM fixada pelo vínculo, nunca pela sessão
    if getattr(request.user, 'perfil', None) == PerfilUsuario.MILITAR:
        try:
            om = request.user.militar.organizacao_militar
            request.session[SESSION_KEY_OM] = om.id  # mantém sessão consistente
            return om
        except Exception:
            pass

    om_id = request.session.get(SESSION_KEY_OM)
    if om_id:
        om = OrganizacaoMilitar.objects.filter(id=om_id, ativo=True).first()
        if om:
            return om

    # fallback: primeira OM ativa
    om = OrganizacaoMilitar.objects.filter(ativo=True).order_by('id').first()
    if om:
        request.session[SESSION_KEY_OM] = om.id
    return om


def om_context(request):
    """
    Disponibiliza `om_ativa`, `oms_disponiveis` e `militar_do_usuario`
    em todos os templates.

    Regras de visibilidade de OMs:
    - perfil 'militar': vê apenas a própria OM (sem switcher)
    - demais perfis: vêem todas as OMs ativas (switcher habilitado)
    """
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {'om_ativa': None, 'oms_disponiveis': [], 'militar_do_usuario': None}

    om_ativa = obter_om_da_sessao(request)

    # Militar comum não deve ver nem poder trocar para outras OMs
    if getattr(request.user, 'perfil', None) == PerfilUsuario.MILITAR:
        oms = [om_ativa] if om_ativa else []
    else:
        oms = list(OrganizacaoMilitar.objects.filter(ativo=True).order_by('sigla'))

    # Militar vinculado ao usuário logado (None se for escalante/admin/etc.)
    militar_do_usuario = None
    try:
        militar_do_usuario = request.user.militar
    except Exception:
        pass

    pode_decidir_indisponibilidade = (
        getattr(request.user, 'is_superuser', False)
        or getattr(request.user, 'perfil', None) in (
            PerfilUsuario.ESCALANTE,
            PerfilUsuario.CHEFE,
            PerfilUsuario.ADJUNTO,
            PerfilUsuario.ADMIN_OM,
        )
    ) and getattr(request.user, 'ativo', True)

    indisponibilidades_pendentes_count = 0
    if pode_decidir_indisponibilidade and om_ativa:
        indisponibilidades_pendentes_count = Indisponibilidade.objects.filter(
            militar__organizacao_militar=om_ativa,
            status=Indisponibilidade.STATUS_PENDENTE,
        ).count()

    return {
        'om_ativa': om_ativa,
        'oms_disponiveis': oms,
        'militar_do_usuario': militar_do_usuario,
        'indisponibilidades_pendentes_count': indisponibilidades_pendentes_count,
    }
