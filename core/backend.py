
import logging

from django.contrib.auth import get_user_model
from django_auth_ldap.backend import LDAPBackend

logger = logging.getLogger(__name__)


class CustomLDAPBackend(LDAPBackend):
    """
    Backend LDAP que somente autentica usuários
    previamente cadastrados localmente.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):

        if not username or not password:
            return None

        UserModel = get_user_model()

        # Verifica se existe usuário local
        try:
            local_user = UserModel.objects.get(username=username)
        except UserModel.DoesNotExist:
            logger.warning(
                "LDAP LOGIN NEGADO: usuário local inexistente: %s",
                username,
            )
            return None

        # Opcional: impedir login de usuários inativos
        if not local_user.is_active:
            logger.warning(
                "LDAP LOGIN NEGADO: usuário inativo: %s",
                username,
            )
            return None

        logger.info(
            "LDAP LOGIN: tentando autenticação LDAP para %s",
            username,
        )

        # Chama autenticação LDAP real
        user = super().authenticate(
            request,
            username=username,
            password=password,
            **kwargs
        )

        if user is None:
            logger.warning(
                "LDAP LOGIN FALHOU: credenciais inválidas: %s",
                username,
            )
        else:
            logger.info(
                "LDAP LOGIN SUCESSO: %s",
                username,
            )

        return user

