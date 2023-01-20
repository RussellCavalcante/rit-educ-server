import csv

from flask import jsonify, session
from app.utils.exceptions import ApiException


def success(data, message=None, code=1, *args, **kwargs):
    _return = {'code': code, 'message': message, 'data': data}

    _response = jsonify(_return)

    return _response, 200


def error(*args, **kwargs):
    return jsonify(kwargs), 400


def verify_request_module(module, *args, **kwargs):
    from app.services import DomainServices
    from app.utils.exceptions import ApiException

    if module not in DomainServices.modules():
        raise ApiException("Verifique a validade do Módulo.")
   

def to_dict(element, *args, **kwargs):
    """
    Função para converter o objeto em um dicionário serializável.
    """
    _condition_to_dont_cast = kwargs.get('condition_to_dont_cast', [None, str, int, float, dict, list])
    _recursive = kwargs.get('recursive', True)

    # Condição para fazer o Cast:
    cast = lambda value: True if type(value) not in _condition_to_dont_cast else False

    for key, value in element.__dict__.items():
        # Para evitarmos um retorno "None" para o front, alteraremos para "null", como é o padrão js:
        if value is None:
            # value = "null"
            continue

        if condition_to_cast(value):
            value = str(value)

        _dict[key] = value

    return _dict



def remove_non_letters(input_str):
    return ''.join(e for e in input_str if e.isalnum())


def remove_accentuations(input_str):
    import unidecode
    return unidecode.unidecode(input_str)


def process_str_to_boolean(input_str, *args, **kwargs):
    _input_str = str(input_str)
    _input_str = remove_accentuations(process_str(_input_str)).lower()

    if fuzzy_match(_input_str, 'sim', min_score=80):
        return True

    if fuzzy_match(_input_str, 'nao', min_score=80):
        return False
    
    raise RuntimeError("Verifique se '{}' é próximo à 'sim' ou 'não'.")


def process_str(element, *args, **kwargs):
    if not isinstance(element, str):
        logger.warning("O parâmetro 'element' ('{}') não é uma str.".format(element))
        
        return element
    
    if kwargs.get("with_log", False):
        logger.debug("Elemento de entrada: '{}'".format(element))

    element = element.replace("\t", "")
    element = element.replace("\n", "")
    element = element.rstrip()
    element = element.lstrip()

    if kwargs.get("with_log", False):
        logger.debug("Elemento processado: '{}'".format(element))

    # Caso queiramos retornar None quando a str for vazia:   
    if kwargs.get('none', False):
        if element == '':
            element = None

    return element


def process_json(json, inplace=True, *args, **kwargs):
    if not isinstance(json, dict):
        raise RuntimeError("Verifique o tipo de dado do atributo 'json'.")
    
    _json = {}

    for _key, _value in list(json.items()):
        if inplace:
            json[process_str(_key)] = process_str(json.pop(_key))
        else:
            _json[process_str(_key)] = process_str(json.pop(_key))

    if inplace:
        return

    return _json


def insert_without_app_context(data, collection='processes', *args, **kwargs):
    from app import create_app, mongo

    app = create_app(with_port=False)

    with app.app_context():
        getattr(mongo.db, collection).insert_many(data)


def __log():
    from app.config import BaseConfig as config

    """
    Logger compartilhado para toda a Aplicação;
    """
    import logging

    if config.DEBUG:
        #filename='debug.log',
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s (%(filename)s:%(lineno)s): (%(asctime)s) %(message)s", datefmt="%d-%m %H:%M:%S")

    else:    
        logging.basicConfig(level=logging.INFO, format="%(levelname)s (%(filename)s:%(lineno)s): (%(asctime)s) %(message)s", datefmt="%d-%m %H:%M:%S")

    logger = logging.getLogger(__name__)
    logger.debug("Instanciando um Objeto de Logger.")
    
    #logging.getLogger('flask_cors').level = logging.DEBUG

    return logger


def validate_cpf(
    cpf, 
    exception=True,
    exception_message="Verifique a validade do CPF."):
    import re

    # Check if type is str
    if not isinstance(cpf, str):
        if exception: 
            raise RuntimeError("Verifique o tipo de dado para cpf. Ele deve ser String.")
        return False

    # Remove some unwanted characters
    cpf = re.sub("[^0-9]",'',cpf)

    # Checks if string has 11 characters
    if len(cpf) != 11:
        if exception: 
            raise RuntimeError("Verifique o tipo de dado para cpf. Ele deve ser String.")
        return False

    sum = 0
    weight = 10

    """ Calculating the first cpf check digit. """
    for n in range(9):
        sum = sum + int(cpf[n]) * weight

        # Decrement weight
        weight = weight - 1

    verifyingDigit = 11 -  sum % 11

    if verifyingDigit > 9 :
        firstVerifyingDigit = 0
    
    else:
        firstVerifyingDigit = verifyingDigit

    """ Calculating the second check digit of cpf. """
    sum = 0
    weight = 11
    
    for n in range(10):
        sum = sum + int(cpf[n]) * weight

        # Decrement weight
        weight = weight - 1

    verifyingDigit = 11 -  sum % 11

    if verifyingDigit > 9 :
        secondVerifyingDigit = 0
    else:
        secondVerifyingDigit = verifyingDigit

    if cpf[-2:] == "%s%s" % (firstVerifyingDigit,secondVerifyingDigit):
        return cpf
    
    if exception: 
        from app.utils.exceptions import ApiException
        raise ApiException(exception_message)
    
    return False
    

def parse_datetime(
    datetime_str, 
    formats=['%d/%m/%Y %H:%M', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%MZ', '%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%S.%f'], 
    exception=ApiException,
    exception_message="Verifique a formatação da data. Ela deve está no formato: ",
    *args,
    **kwargs):
    from datetime import datetime
    import dateutil.parser

    logger.debug("Parseando: {}".format(datetime_str))

    for __format in formats:
        try:
            return datetime.strptime(datetime_str, __format)         
        except ValueError as err:
            logger.debug("Erro ao tentar fazer o parse da data: {}".format(str(err)))
            
            try:
                return dateutil.parser.parse(datetime_str).replace(tzinfo=None)
            except Exception as err:
                logger.error("Erro na tentativa de parsear para isoformat: {}".format(err))
            
            #if kwargs.get('make_recursion', True):
            #    return parse_datetime(datetime_str.split('+')[0], make_recursion=False) 

    exception_message = exception_message + ", ".join(formats) + "."
    raise exception(exception_message)


def parse_date( 
    datetime_str, 
    formats=['%d/%m/%Y', '%Y-%m-%d'],
    exception=ApiException,
    exception_message="Verifique a formatação da data. Ela deve está no formato: ",
    *args,
    **kwargs):
    from datetime import datetime

    if 'T' in datetime_str: datetime_str = datetime_str.split('T')[0]
    
    for __format in formats:
        try:
            return datetime.strptime(datetime_str, __format)         
        except ValueError as err:
            logger.debug("Erro ao tentar fazer o parse da data: {}".format(str(err)))

    exception_message = exception_message + ", ".join(formats) + "."
    raise exception(exception_message)


def all_subclasses(cls):
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)])


def mount_query(data:dict, model:object, with_status:bool=True, status_attribute:str='status', *args, **kwargs) -> list:
    from app.models import ModelStatus

    logger.debug("Montando query: {}".format(data))

    filters = []
    has_status = False

    for key, value in data.items():        
        # Cláusula mágica - ! diferente
        if key.startswith('!'):
            if key[1:] == status_attribute: has_status = True

            if isinstance(value, list): 
                filters.append(~getattr(model, key[1:]).in_(value))
            else: 
                filters.append(getattr(model, key[1:])!= value) 

        else:
            if key == status_attribute: has_status = True

            if isinstance(value, list): 
                filters.append(getattr(model, key).in_(value))
            else: 
                filters.append(getattr(model, key) == value) 

    if not has_status:
        filters.append(getattr(model, status_attribute) != ModelStatus.DELETED.value)

    return filters


def clean_session(*args, **kwargs):
    session_attrs = list(session.keys())

    logger.debug("Atributos na sessão: {}".format(session_attrs))
    
    # Limpando a sessão:
    for key in session_attrs:
        session.pop(key)

    session.clear()

    return session


def serialize_return(data:list, *args, **kwargs) -> list:
    serialized:list = []

    for element in data:
        if isinstance(element, tuple) or isinstance(element, list):
            element = serialize_return(element, *args, **kwargs)
        
        else:
            try:
                element = element.to_dict()
            except AttributeError:
                pass
            
        serialized.append(element)

    return serialized       


def get_attribute_values(
    data:list=[], 
    attribute:str='id', 
    *args, 
    **kwargs) -> list:

    select_data:list = []

    for element in data:
        if isinstance(element, dict):
            select_data.append(element.get(attribute, None))
        
        else:
            select_data.append(getattr(element, attribute, None))

    return select_data


logger = __log()