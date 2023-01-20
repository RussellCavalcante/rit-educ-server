import traceback
from app.config import BaseConfig as config


def declare_api_error_handlers(flask_app):
    flask_app.register_error_handler(404, _page_not_found)
    flask_app.register_error_handler(405, _method_not_allowed)
    flask_app.register_error_handler(ApiException, _api_error)
    flask_app.register_error_handler(Exception, _general_error)

    
def _page_not_found(e):
    
    _e = {"code": 404, "title": "Oooops", "message": "Página não encontrada."}
    
    return __output_error(
        _e,
        "Requisição para o Módulo não encontrado")


def _method_not_allowed(e):
    
    _e = {"code": 405, "title": "Oooops", "message": "Verifique o método da requisição."}
    return __output_error(_e, "Método da requisição não permitido.")


def _api_error(e):
    """
    Função para retornar um erro de Api para o usuário final;
    """
    from app.utils import logger

    
    if config.DEBUG:
        logger.exception(e)
   
    # Pegando a pilha de Erro:
    tb = traceback.format_exc()

    # Definindo as saídas padrões para a mensagem de erro:
    return_code = e.code if e.code else 1
    return_title = e.title if e.title else "Oooops"    

    #from app.utils import email

    # Enviando o e-mail para o responsável do Sistema:    
    #email.send(to=config.APP_USERS_ADMINS, subject="Erro na API Pyiose Managment", main_message=str(e) ,secondary_message=tb)

    return __output_error({"code": return_code, "title": return_title, "message": str(e)})


def _general_error(e):
    # Pegando a pilha de Erro:
    tb = traceback.format_exc()
    
    from app.utils import logger
    
    if config.DEBUG:
        logger.exception(e)
    # Enviando o e-mail para o responsável do Sistema:
    #email.send(to=config.APP_USERS_ADMINS, subject="Erro na API Pyiose Managment - Application Error", message=e)
    
    return __output_error(
        {"code": 60, "title": "Oooops", "message": "O Servidor apresentou um comportamento inesperado. Contate o administrador do sistema.", "description": str(e)},
        str(e),
        'exception')


def __output_error(
    error_object,
    message=None,
    logger_level='error',
    *args,
    **kwargs):
    from app.utils import logger, error
    from app.utils import clean_session
    
    clean_session()

    
    if message:
        getattr(logger, logger_level)(message)
    
    return error(**error_object)




class MessageException(Exception):
    def __init__(self, message, code=11, title="Ooops"):
        super().__init__(message)
        
        self.code = code
        self.title = title


class ConnectionException(Exception):
    def __init__(self, message, code=1, title="Ooops"):
        super().__init__(message)
        
        self.code = code
        self.title = title


class ApiException(Exception):
    def __init__(self, message, code=11, title="Ooops"):
        super().__init__(message)
        
        self.code = code
        self.title = title


class ServiceException(Exception):
    def __init__(self, message, code=15, title="Ooops"):
        super().__init__(message)
        
        self.code = code
        self.title = title


