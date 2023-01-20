
class BaseConfig(object):
    DEBUG_MODE = ('DEV', 'LOCAL', 'DEBUG')

    from os import getenv

    DEBUG = None

    """
    Usuários Responsáveis pelo Sistema:
    """
    APP_USERS_ADMINS = ['russell@resoluteit.com.br']
    EMAIL_SENT_FROM = 'noreply@resoluteit.com.br'
    EMAIL = 'noreply@resoluteit.com.br'
    PASSWORD = "resolute2@2@"

    """
    Dados para geração de tokens JWT
    """
    JWT_EXPIRATION_TIME = int(getenv('JWT_EXPIRATION_TIME', 1440 * 7 * 4))
    JWT_SECRET_KEY = getenv('JWT_SECRET_KEY', 'aula_plus_jwt_secret_key')

    DB_CONVENTION = {
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(column_0_name)s", 
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
        }
    
    UPLOAD_FOLDER       = 'files'
    UPLOAD_CONCLUDED    = 'concluded-files'
    UPLOAD_TMP_FOLDER   = 'tmp-files'
    ALLOWED_EXTENSIONS  = ['txt', 'pdf', 'docx', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'webm', 'doc', 'ppt']


    ADMINISTRATORS_ID               = '04d57019-d565-4396-b965-eff652c2901e'
    SCHOOL_NET_ADMINISTRATOR_ID     = 'c731e359-37de-4328-919a-952dc79dab52'
    SCHOOL_UNIT_ADMINISTRATOR_ID    = 'fe0b5a65-3649-4903-a7f0-cf9094ea903f'
    COORDINATORS_ID                 = 'e137434b-c48d-4377-9466-ae4a432344dd'
    TEACHERS_ID                     = '90462bf5-10a0-48b0-8ef0-e0d79c5e10cf'
    AUXILIARY_ID                    = 'e9b44444-a203-49cd-a820-283bfc066046'
    STUDENTS_ID                     = '344c0d50-1e20-4eed-af4a-ab4639addb40'
