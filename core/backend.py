"""
Backend de autenticação LDAP customizado.

Fluxo:
  1. Recebe username + password da tela de login
  2. Verifica se existe um UsuarioCustomizado local com esse username
  3. Se existir, delega a autenticação para o LDAPBackend (django-auth-ldap)
  4. Após autenticação bem-sucedida, propaga first_name/last_name para o
     registro Militar vinculado (se houver), mantendo os dados sincronizados.

Isso garante que apenas militares/usuários previamente cadastrados
consigam autenticar via LDAP — não cria contas automaticamente.

Para habilitar: instale django-auth-ldap e descomente as configurações
em core/settings.py (seção LDAP).

Sincronização de nome:
  - AUTH_LDAP_USER_ATTR_MAP mapeia givenName→first_name, sn→last_name, mail→email
  - AUTH_LDAP_ALWAYS_UPDATE_USER = True faz o django-auth-ldap atualizar o
    UsuarioCustomizado a cada login.
  - O signal `_sincronizar_militar_pos_ldap` (registrado abaixo) ouve o signal
    `populate_user` do django-auth-ldap e atualiza o Militar vinculado com o
    nome recém-sincronizado do AD.
"""

import logging

from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


def _ldap_available():
    try:
        from django_auth_ldap.backend import LDAPBackend  # noqa: F401
        return True
    except ImportError:
        return False


def _registrar_signal_ldap():
    """
    Registra signal populate_user do django-auth-ldap para propagar
    first_name/last_name do AD para o registro Militar vinculado.

    Chamado somente quando o pacote django-auth-ldap está disponível.
    O signal é disparado pelo LDAPBackend após atualizar o UsuarioCustomizado
    com os atributos do AD (via AUTH_LDAP_USER_ATTR_MAP).
    """
    try:
        from django_auth_ldap.backend import populate_user
    except ImportError:
        return

    from django.dispatch import receiver

    @receiver(populate_user)
    def _sincronizar_militar_pos_ldap(sender, user, ldap_user, **kwargs):
        """
        Após o django-auth-ldap preencher first_name/last_name no usuário,
        propaga esses valores para o registro Militar vinculado (se existir).
        Atualiza apenas nome_completo (campo livre); nome_guerra é intocável
        pois é o nome operacional definido pelo administrador.
        """
        try:
            militar = getattr(user, 'militar', None)
            if militar is None:
                return

            novo_nome = f"{user.first_name} {user.last_name}".strip()
            if not novo_nome:
                return

            if militar.nome_completo != novo_nome:
                type(militar).objects.filter(pk=militar.pk).update(
                    nome_completo=novo_nome
                )
                logger.info(
                    "LDAP sync: Militar %s → nome_completo atualizado: '%s'",
                    militar.nome_guerra,
                    novo_nome,
                )
        except Exception:
            logger.exception(
                "LDAP sync: erro ao propagar nome para Militar (user=%s)", user.username
            )


class CustomLDAPBackend:
    """
    Wrapper sobre LDAPBackend que exige que o usuário já exista localmente.

    Usado em AUTHENTICATION_BACKENDS junto com ModelBackend:
        AUTHENTICATION_BACKENDS = [
            'core.backend.CustomLDAPBackend',
            'django.contrib.auth.backends.ModelBackend',
        ]
    """

    def __init__(self):
        # Registra o signal apenas uma vez quando o backend é instanciado
        if _ldap_available():
            _registrar_signal_ldap()

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not _ldap_available():
            return None

        from django_auth_ldap.backend import LDAPBackend

        UserModel = get_user_model()

        # Pré-requisito: o usuário deve existir no banco local
        try:
            UserModel.objects.get(username=username)
        except UserModel.DoesNotExist:
            return None

        # Autenticação via LDAP (atualiza first_name/last_name via AUTH_LDAP_USER_ATTR_MAP)
        backend = LDAPBackend()
        return backend.authenticate(request, username=username, password=password, **kwargs)

    def get_user(self, user_id):
        if not _ldap_available():
            return None

        from django_auth_ldap.backend import LDAPBackend
        return LDAPBackend().get_user(user_id)
