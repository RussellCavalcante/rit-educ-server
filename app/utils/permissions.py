from typing import Union, List

from app.utils import logger
from app.utils.exceptions import ApiException
from app.models import ProfileUser, SchoolUnitProfileUsers, SchoolNetAdministrator, Domain, pprint


def get_access_level(profile_user:ProfileUser, *args, **kwargs) -> List[str]:
    """
    Função para verificar qual o nível de acesso de um dado perfil/usuário.

    O retorno dessa função são os identificadores dos usários donos dos objetos que esse Usuário, `profile_user`, pode visualizar.
    """
    logger.debug("get_access_level(): {}".format(profile_user))

    object = SchoolNetAdministrator.get([SchoolNetAdministrator.profile_user_id == profile_user.id])

    logger.debug("É um Administrador de Rede? {}".format(object))

    if object: return get_access_data(object)

    object = SchoolUnitProfileUsers.get([profile_user.id == SchoolUnitProfileUsers.profile_user_id])

    if object: return get_access_data(object)

    return []


def get_access_data(data:Union[SchoolNetAdministrator, SchoolUnitProfileUsers], *args, **kwargs) -> List[str]:
    return get_data_creators(data.access_data())


def get_data_creators(data:List[str], *args, **kwargs) -> List[str]:
    # Pegando todos os profile_users relacionados com as unidades em questão:
    all_profile_users_related = SchoolUnitProfileUsers.get([SchoolUnitProfileUsers.school_unit_id.in_(data)], cursor_function='all')

    return [profile_user.profile_user_id for profile_user in all_profile_users_related]
