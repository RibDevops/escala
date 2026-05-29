"""Context processor que injeta a OM ativa e a lista de OMs disponíveis."""
from .models import OrganizacaoMilitar


SESSION_KEY_OM = 'om_id_ativa'


def obter_om_da_sessao(request):
    """Resolve a OM ativa a partir da sessão, com fallback."""
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return None

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
    """Disponibiliza `om_ativa`, `oms_disponiveis` e `militar_do_usuario` em todos os templates."""
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {'om_ativa': None, 'oms_disponiveis': [], 'militar_do_usuario': None}

    om_ativa = obter_om_da_sessao(request)
    oms = list(OrganizacaoMilitar.objects.filter(ativo=True).order_by('sigla'))

    # Militar vinculado ao usuário logado (None se for escalante/admin)
    militar_do_usuario = None
    try:
        militar_do_usuario = request.user.militar
    except Exception:
        pass

    return {
        'om_ativa': om_ativa,
        'oms_disponiveis': oms,
        'militar_do_usuario': militar_do_usuario,
    }
