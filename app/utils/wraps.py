from threading import Thread, Timer
from functools import wraps 
from pprint import pprint
from flask import request, session, current_app

from app.utils import logger
from app.utils.permissions import get_access_level
from app.utils.exceptions import ApiException


def _call_with_future(fn, future, args, kwargs):
    try:
        result = fn(*args, **kwargs)
        future.set_result(result)
    except Exception as exc:
        future.set_exception(exc)


def threaded_with_return(fn):
    def wrapper(*args, **kwargs):
        from concurrent.futures import Future
        
        future = Future()
        
        Thread(target=_call_with_future, args=(fn, future, args, kwargs)).start()
        
        return future
    return wrapper


def threaded(fn):
    def wrapper(*args, **kwargs):
        Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper


def threaded_with_timer(fn):
    def wrapper(*args, **kwargs):

        time = kwargs.get('wake_up')

        if not time:
            time = 5
        
        Timer(time, fn, args=args, kwargs=kwargs).start()

    return wrapper


def token_required(f):
    '''
    1º: Verifique se ele contém o cabeçalho "Authorization" com uma string parecida com um token JWT
    2º: Valide que o JWT não está expirado ou válido.
    3º: Se tudo for válido, o usuário associado será consultado no banco de dados e retornará à função que o decorador está envolvendo.
    '''
    from app.utils import logger
    from app.utils.exceptions import ApiException
 

    @wraps(f)
    def _verify(*args, **kwargs):
                
        auth_headers = request.headers.get('Authorization', '').split()
        
        if len(auth_headers) != 2:
            raise ApiException("Verifique o parâmetro 'Authorization' no cabeçalho da Requisição.")

        import jwt

        try:
            token = auth_headers[1]
            
            data = jwt.decode(token, current_app.config['JWT_SECRET_KEY'])
            
            from app.models import db, User, ProfileUser, Permission, ProfilePermission, ModelStatus

            user, profile_user = db.session.query(User, ProfileUser)\
                .filter(ProfileUser.id == data['data']['profile_user_id'], ProfileUser.user_id == User.id)\
                .first()
            
            if not user:
                raise ApiException("Você está sem acesso ou permissão. Refaça o seu login ou entre em contato com o administrador do Sistema.", 1)
            
            session['user'] =  user.to_dict()
            session['profile_user'] = profile_user

            print(get_access_level(profile_user))  

            return f(*args, **kwargs)

        except jwt.ExpiredSignatureError:
            raise ApiException('Refaça o seu login, por favor.')

        except ApiException as e:
            raise e
                    
        except jwt.InvalidTokenError as e:
            logger.exception("Erro de Token Inválido: {}".format(e))
            raise ApiException("Verifique a validade do seu Token JWT")



    return _verify
