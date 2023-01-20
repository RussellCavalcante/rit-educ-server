from app import db
from app import config
from app.utils import logger, success, clean_session
from app.models import ModelStatus, Domain, Super
from datetime import datetime, timedelta
from app.utils.permissions import get_access_level
from app.utils.exceptions import ApiException
from flask import session
from sqlalchemy.orm import Query



from pprint import pprint


class DomainServices(object):
    __types__                       = {'get': 'find', 'post': 'upsert', 'put': 'upsert', 'delete': 'remove'}
    __request_args__                = ['page', 'size', 'offset', 'q', 'order', 'order_attr', '__model__', 'select', 'select_key', 'select_value']
    __services_dont_clean__         = []
    __model__                       = None


    def __init__(self, 
        request, 
        model:str=None,
        function:str=None,
        *args, 
        **kwargs):

        self._flask_request     = request
        self._process_result    = None
        self._filters           = None
        self._function          = None

        self._now = datetime.now()
        self.__configurations = {}
        self.__messages = []
        
        # Pegando as informações da requisição:
        self.__query_params = self.__get_request_params()
        self._body_params = self._get_body_params(exception=False)
        self._session_objects = {}

        # Se algum modelo for passado no ato da instanciação do serviço:
        if model: self.__model__ = Super.choose_model(model)
        if function: self._function = function


    @property
    def result(self):
        if len(self.__messages):
            return success(self._process_result, "\n".join(self.__messages))
        
        return success(self._process_result)


    @property
    def query_params(self):
        return self.__query_params


    @property
    def filters(self):
        return self._filters


    def is_find(self, type, *args, **kwargs):
        _process_type = type if type is not None else self.__types__[self._flask_request.method.lower()]

        return _process_type in ('find',)

    
    def mount_filters(self, data, *args, **kwargs):
        logger.debug("mount_filters: {}".format(data))
        attributes_with_ilike = []
        add_status = False

        try:
            attributes_with_ilike = self.__model__.__attributes_ilike__
        
        except Exception as err:
            logger.warning("Não foi possível pegar os atributos com ilike: {}".format(err))
        
        logger.debug("Atributos do '{}' que incluiremos ilike: '{}'".format(self.__model__, attributes_with_ilike))
        
        self._filters = []

        # Verificando se há o atributo de busca 'q':
        if data.get('q', None):
            try:
                q:List = self.__model__.q(data['q'])
                self._filters.extend(q)
            except AttributeError as err:

                """
                O modelo não possui uma regra específica para verificação do atributo q
                """
                logger.error("Erro ao incluir 'q' aos filtros da consulta: {}".format(err))

        # Verificando se o status já está definido:
        if not data.get('status', None):
            add_status = True
        
        for key, value in list(data.items()):
            _filter = None

            # Não avaliamos quando os atributos são de requisição:
            if key in self.__request_args__:
                continue
            
            # Avaliando se o atributo deve ser processado como like ou ilike
            if key in attributes_with_ilike:
                try:
                    self._filters.append(getattr(self.__model__, key).ilike("%%%s%%" % str(value)))
                except AttributeError as err:
                    logger.warning("Erro ao incluir '{}' aos filtros da consulta: {}".format(key, err))
           
            else:
                try:
                    
                    """
                    Verificando se a chave inicia com: __contains__, __equal__, __diff__, __less_than__ ou __upper_than__
                    """
                    if key.startswith('__contains__'):
                        self._filters.append(getattr(self.__model__, key.split('__contains__')[-1]).ilike("%%%s%%" % str(value)))
                    
                    elif key.startswith('__equal__'):
                        self._filters.append(getattr(self.__model__, key.split('__equal__')[-1]) == value)
                    
                    elif key.startswith('__diff__'):
                        self._filters.append(getattr(self.__model__, key.split('__diff__')[-1]) != value)

                    else:
                        self._filters.append(getattr(self.__model__, key) == value)

                except AttributeError as err:
                    logger.warning("Erro ao incluir '{}' aos filtros da consulta: {}".format(key, err))

        if add_status:
            try:
                self._filters.append(getattr(self.__model__, 'status') != ModelStatus.DELETED.value)
            except AttributeError as err:
                logger.error("O modelo {} não possui o atributo 'status': {}".format(self.__model__, err))

        return self._filters


    def serialize_return(self, data:list, *args, **kwargs) -> list:
        #logger.debug("Serializando: {}".format(data))

        serialized:list = []

        for element in data:
            if isinstance(element, tuple) or isinstance(element, list):
                element = self.serialize_return(element, *args, **kwargs)
            
            else:
                try:
                    element = element.to_dict()
                except AttributeError:
                    pass
                
            serialized.append(element)

        return serialized       


    def add_created_by(self, data:list, *args, **kwargs) -> list:
        return data
        

    def clean_session(self, *args, **kwargs):
        clean_session()


    def close_session(self, *args, **kwargs):
        self.clean_session()
       

        try:
            db.session.commit()
        except Exception as err:
            self.raise_error(str(err))
        

    def process(self,
        type:str=None, 
        query_params:dict=None,
        body_params:dict=None,
        closing_session:bool=True,
        *args, 
        **kwargs):

        from time import time

        # Marcando o tempo de Processamento:
        _start = time()

        # Escolhendo o modelo adequado:
        if not hasattr(self, '__model__') or getattr(self, '__model__') is None:

            # Tentando pegar o modelo a partir da requisição:
            __model__ = kwargs.get('__model__', None)

            if __model__: 
                from app.models import Domain, ViewDomain

                __model__ = Domain.get_model(__model__)

                if not __model__:
                    self.raise_error("Verifique a validade do parâmetro '__model__'")

            else:
                self.raise_error("Verifique a validade do parâmetro '__model__'")

        if not type: type = self._flask_request.method.lower()

        _process_type = self.__types__[type.lower()]

        logger.debug("Tipo de Processamento: {}".format(_process_type))

        # Parâmetros que serão utilizados no processamento
        params = {}

        # Verificando se a consulta é do tipo find e montando o objeto de filtragem
        if self.is_find(_process_type):
            # Pegando as informações da requisição:
            if not query_params:
                query_params = self._get_query_params()

            # Verificando se o identificador de find_by_id está presente:
            if 'id' in query_params and _process_type is 'find':
                _process_type = 'find_by_id'
            
            self.mount_filters(self._clean(**query_params))

            params = query_params

        else: 
            # Pegando as informações da requisição:
            if not body_params:
                body_params = self._get_body_params()
            
            params = body_params

        # Verificando se o método está implementado:
        if not hasattr(self, _process_type) or not callable(getattr(self, _process_type)):
            raise NotImplementedError("Método '{}' não implementado.".format(self.___types__[_process_type]))

        """
        Fazendo a chamada do self.< (find | upsert | remove) >
        """      
        self._process_result = getattr(self, _process_type)(
            params,
            before_function='before_{}' .format(self._function if self._function else _process_type),
            after_function='after_{}'   .format(self._function if self._function else _process_type),
            *args, 
            **kwargs)

        if closing_session: self.close_session()

        _finish = time()

        logger.debug("Tempo de Execução: {}".format(_finish - _start))


    def find(self, params:dict, before_function:str='before_find', after_function:str='after_find', *args, **kwargs):
        """
        Função para fazer a busca de um modelo na nossa base
        """
        kwargs = {**kwargs, **params}

        logger.debug("Buscando: '{}'".format(self.__model__))
        logger.debug("Atributos p/ 'find': {}".format(kwargs))
        logger.debug("Funções de Ciclo de Vida: {} - {}".format(before_function, after_function))

        # Verificando se há um before find à ser chamado que fará um pré-processamento:                
        if hasattr(self.__model__, before_function) and callable(getattr(self.__model__, before_function)):
            _r = getattr(self.__model__, before_function)(*args, **kwargs)
            
            if isinstance(_r, dict):
                kwargs = _r

            if isinstance(_r, list):
                self._filters.extend(_r)

        """
        Verificando se alguma função específica do modelo deve ser chamada:

        Se não, fazemos a busca convencional com o find.
        """
        query:Query = None

        if not self._function:  
            query = self.__model__.find(*self.filters)

        else:
            if not hasattr(self.__model__, self._function):
                self.raise_error("Verifique a validade da função ('{}') solicitada para a requisição.".format(self._function))

            query = getattr(self.__model__, self._function)(*self.filters, **kwargs)

        # Quando o objeto já é uma lista, podemos inferir o retorno imediato deste
        if isinstance(query, list): return {"data": query, "pages": -1, "total": -1, "size": -1, "page": -1}

        # Verificando se a query está com a formatação correta:
        if not isinstance(query, Query):
            logger.error("O atributo 'query' está com uma instância incorreta: {}".format(type(query)))
            raise RuntimeError("O atributo 'query' está com uma instância incorreta: {}".format(type(query)))
        
        # Adicionando o grupo de acesso à informação:
        ids_ = get_access_level(session['profile_user'])
        
        #query = query.filter()

        # Montando ordenação caso não a possuímos:
        if not query._order_by:
            if 'order' not in kwargs: kwargs['order'] = 'desc'

            if kwargs['order'] not in ('asc', 'desc'): kwargs['order'] = 'desc'
            
            # Verificando se o modelo possui o atributo em questão para fazer a ordenação
            order_attr = self._get_order_attr(*args, **kwargs)
                
            logger.debug("Ordenando pelo '{}' de forma '{}'".format(kwargs.get('order_attr', 'id'), kwargs['order']))
            
            query = query.order_by(getattr(getattr(self.__model__, order_attr), kwargs['order'])())


        """
        Caso exista uma paginação diferente de -1 ou '-1', montar a paginação com o SQLAlchemy 
        """
        if kwargs.get('size', 25) not in (-1, '-1'):
            query = query.paginate(kwargs.get('page', 1), kwargs.get('size', 25), False)

            logger.debug("Objetos listados: {}".format(query.items))

            data = self.serialize_return(query.items)
            pages = query.pages
            size = kwargs.get('size', 25)
            total = query.total
            page = kwargs.get('page', 1)

        else:
            data = self.serialize_return(query.all())
            pages = -1
            size = -1
            total =len(data)
            page = -1

        #data = self.add_created_by(data)

        logger.debug("Objetos serializados: {}".format(len(data)))

        if kwargs.get('select', None) and str(kwargs['select']).lower() in ('1', 'true'):
            data = self.clean_to_select(data, *args, **kwargs)
        
        if len(data):
            if hasattr(self.__model__, after_function) and callable(getattr(self.__model__, after_function)):
                try:
                    _r = getattr(self.__model__, after_function)(data, *args, **kwargs)

                    if _r is not None:
                        data = _r

                except Exception as err:
                    logger.error("Erro na chamda do '{}': {}".format(after_function, err))

                    if config.DEBUG: logger.exception(err)              

            else:
                logger.warning("Modelo '{}' não implementa '{}'".format(self.__model__, after_function))
                
        return {"data": data, "pages": pages, "total": total, "size": size, "page": page}
    

    def find_by_id(self, params:dict, before_function:str='before_find_by_id', after_function:str='after_find_by_id',  *args, **kwargs):

        kwargs = {**kwargs, **params}
        
        # Verificando se há um before find à ser chamado que fará um pré-processamento:                
        if hasattr(self.__model__, before_function) and callable(getattr(self.__model__, before_function)):
            _r = getattr(self.__model__, before_function)(*args, **kwargs)

            if isinstance(_r, dict):
                kwargs = _r

        object = self.__model__.query.filter(*self.filters).first()

        if not object:
            self.raise_error("Verifique o identificador para essa requisição.")

        if hasattr(object, after_function) and callable(getattr(object, after_function)):
            _r = getattr(object, after_function)(*args, **kwargs)

            if isinstance(_r, dict):
                kwargs = _r
        
        object = object.to_dict()

        return object
        

    def clean_to_select(self, 
        data:list, 
        default_values=['name', 'title'],
        *args, 
        **kwargs) -> list:

        key = kwargs.get('select_key', 'id')
        value = kwargs.get('select_value', 'name')

        if not key or not value:
            self.raise_error("Verifique os parâmetros para a funcionalidade do 'select', 'select_key' e 'select_value': '{}', '{}'".format(key, value))

        select_data:list = []

        for element in data:
            if isinstance(element, dict):
                select_data.append({ 'key': element[key], 'value': element[value] })
            
            else:
                select_data.append({ 'key': getattr(element, key), 'value': getattr(element, value) })

        return select_data


    def upsert(self, params, before_function:str='before_upsert', after_function:str='after_upsert', *args, **kwargs):
        logger.debug("Dados para serem persistidos: {}".format(params))

        if isinstance(params, list):
            return [self.__make_upsert(before_function=before_function, after_function=after_function, *args, **param) for param in params]
        
        return self.__make_upsert(before_function=before_function, after_function=after_function, *args, **params)        


    def remove(self, params, *args, **kwargs):

        kwargs = params
        
        if hasattr(self.__model__, 'before_remove') and callable(getattr(self.__model__, 'before_remove')):
            _r = getattr(self.__model__, 'before_remove')(*args, **kwargs)

            if isinstance(_r, dict):
                kwargs = _r
        
        objects_removed = self.__model__.remove(**kwargs)
        
        if objects_removed:
            for object in objects_removed:
                if hasattr(object, 'after_remove') and callable(getattr(object, 'after_remove')):
                    object.after_remove(*args, **kwargs)

        return [object.id for object in objects_removed]
    

    def selects(self, *args, **kwargs):
      
        if not 'modules' in self.__query_params:
            self.raise_error("Verifique os parâmetros modules' para essa requisição.")

        self.__query_params['modules'] = [self.__query_params['modules']]

        # Tratando a query param de entrada:
        if not 'fields' in self.__query_params or not 'modules' in self.__query_params or \
            len(self.__query_params['modules']) > len(self.__query_params['fields']):
            self.raise_error("Verifique os parâmetros 'fields' e 'modules' para essa requisição.")

        if not isinstance(self.__query_params['fields'], list):
            self.__query_params['fields'] = [self.__query_params['fields']]

        if not 'labels' in self.__query_params:
            self.__query_params['labels'] = self.__query_params['fields']

        else:
            if not isinstance(self.__query_params['labels'], list):
                self.__query_params['labels'] = [self.__query_params['labels']]
       
        # Estabilizando o tamanho dos arrays:
        while len(self.__query_params['fields']) > len(self.__query_params['modules']):
            self.__query_params['modules'].append(self.__query_params['modules'][-1])
        
        self._process_result = []


        for module, field, label in zip(self.__query_params['modules'], self.__query_params['fields'], self.__query_params['labels']):
            result = self.get_specify_service(module).__model__\
                .group_by(
                    group={'_id': '${}'.format(field), 'total': {'$sum': 1}, 'label': {'$last': '${}'.format(label)}}
                    )

            if result: result = result

            self._process_result.append(result)


    def batch(self, *args, **kwargs):
        """
        Função para executar um lote de requisições. Estas devem possuir o seguinte corpo:

        `{'requests': {'method': str, 'model': str, 'body_params': {}, 'query_params': {}}[]}`
        """
        from time import time

        # Marcando o tempo de Processamento:
        _start = time()

        if not 'requests' in self._body_params:
            self.raise_error("Verifique o parâmetro 'requests' para esse tipo de requisição.")
        
        processing = []

        for _r in self._body_params['requests']:
            errors = self.validate(_r, attributes=['method', 'model', 'body_params', 'query_params'], exception=False)

            if len(errors):
                self.raise_error("Verifique os parâmetros para a requisição em Batch.")
            
            if 'function' in _r: # Verificando se uma função específica nos foi passada
                self._function = _r['function']

            self.__model__ = Domain.choose_model(_r['model'])

            logger.debug("Atributos da requisição do Pool de Batches: {}".format(_r['body_params']))

            # Processando a requisição:
            self.process(_r['method'], body_params=_r['body_params'], query_params=_r['query_params'], closing_session=False)

            #logger.debug("Resultado do processamento do lote: {}".format(self._process_result))

            # Adicionando o seu resultado:
            processing.append(self._process_result)

            # Limpando o resultado:
            self._process_result = None
            self._function = None

        _finish = time()

        logger.debug("Tempo Total do Batch: {}".format(_finish - _start))
        
        self.close_session()

        self._process_result = processing

        self.add_message("Dados salvos com sucesso!")


    def raise_error(self, message, exception=ApiException, *args, **kwargs):
        self.clean_session()
        raise exception(message)

    
    def _find_by_id(self, *args, **kwargs):
        
        _id = kwargs['id']

        params = self._clean_params(params = self._get_request_params())

        params['id'] = _id
      
        _filter = self._create_filters(params = params)

        _object = self._model.query.filter(*_filter).first()

        if _object:
            _object = _object.to_dict()

        return success(_object)


    def _has_self_find(self):
        
        try:
            
            _function = getattr(self, "find", None)

            if _function:
                return True
            
            return False
        
        except AttributeError:
            
            return False


    def _clean(self, 
        *args, 
        **kwargs):

        try:
            _model_attrs = self.__model__.columns()
        except AttributeError as err:
            logger.warn("{} não possui o atributo e função 'columns': {}".format(self.__model__.__name__, err))
            
            _model_attrs = []

        _services_attrs = self.__request_args__
        
        kwargs = {key: value for key, value in kwargs.items() \
            if \
            key in _model_attrs or \
            key in self.__request_args__ or \
            key in self.__services_dont_clean__ or \
            key.startswith('__contains__') or \
            key.startswith('__equal__') or\
            key.startswith('__diff__') }

        logger.debug("Atributos ao fim da limpeza: {}".format(kwargs))

        return kwargs


    def __get_request_params(self, *args, **kwargs):
        """
        Função para pegar todas as query e url params da requisição.
        """
        _args = {}  

        if self._flask_request.method.lower() == 'get':     

            # Pegando todas as chaves e valores que vieram como args na Requisição:
            keys_values = list(self._flask_request.args.items())
            
            for key, value in keys_values:                   
                _args[key] = value
            
            # Pegando a página e o tamanho
            _size = int(_args.get('size', 10))
            _page = int(_args.get('page', 1))
            _offset = (_page - 1) * _size

            _args['page'] = _page
            _args['size'] = _size
            _args['offset'] = _offset
            
            logger.debug("Dados da Requisição Pré-Processados: {}".format(_args))

        else:
            # Pegando todas as chaves e valores que vieram como args na Requisição:
            keys_values = self._get_body_params(exception=False)

            logger.info("Body Params: {}".format(keys_values))

            if isinstance(keys_values, list):
                _args['list'] = keys_values
            
            else:
                if len(keys_values.keys()):
                    for key, value in keys_values.items():
                        _args[key] = value
            
        logger.info("Dados da Requisição: {}".format(_args))

        return _args


    def _get_body_params(self, exception=True) -> dict:

        try:
            _body = self._flask_request.get_json()

            if _body is None: _body = {}
        except Exception:
            _body = {}        

        if _body is None and exception:
            self.raise_error("Verifique o 'body' da Requisição.")

        return _body
    

    def _get_query_params(self, exception=True) -> dict:
        _args = {} 

        # Pegando todas as chaves e valores que vieram como args na Requisição:
        keys_values = list(self._flask_request.args.items())
        
        for key, value in keys_values:                   
            _args[key] = value
        
        # Pegando a página e o tamanho
        _size = int(_args.get('size', 10))
        _page = int(_args.get('page', 1))
        _offset = (_page - 1) * _size

        _args['page'] = _page
        _args['size'] = _size
        _args['offset'] = _offset
        
        logger.debug("Dados da Requisição Pré-Processados: {}".format(_args))

        return _args


    def _get_filter(self, *args, **kwargs):

        params = kwargs['params']

        attributes_with_ilike = {"name", "alias", "objective", "identity"}

        _filter = []

        params_to_evaulate = list(params.items())
 
        for key, value in params_to_evaulate:
            # Não avaliamos quando os atributos são page ou size:
            if key in ('page', 'size'):
                continue

            try:
                
                if key in attributes_with_ilike:
                    _filter.append( getattr(self._model, key) \
                        .ilike("%%%s%%" % str(value)) )
                
                else:
                    _filter.append(getattr(self._model, key) == value)
            
            except AttributeError:
                continue

        return _filter


    def get_params(self):

        self._data = self._get_body_params()

        if not self._data:
            raise ApiException("Preencha os dados do formulário corretamente.")


    def _clean_params(self, *args, **kwargs):
        """
        Função para limpar os parâmetros que não pertencem ao Modelo e adicionar, se necessário
        o status padrão.;
        """
        params = dict()

        params_to_evaulate = list(kwargs.get('params').items())
 
        for key, value in params_to_evaulate:
            # Não avaliamos quando os atributos são page ou size:
            if key in ('page', 'size'):
                continue

            try:
                getattr(self._model, key)

                params[key] = value
            
            except AttributeError:
                del params[key]

        """
        Verificando se há status nos parâmetros para avaliação. Se não tiver, vamos definir o 
        valor default;
        """
        if not 'status' in params:
            params['status'] = MODELSTATUS.ACTIVE.value

        return params


    def _create_filters(self, *args, **kwargs):
        
        _params = kwargs.get('params')

        _filter = list()
        _special_criteria = None

        try:
        
            _special_criteria = self._model.special_criteria
            
        except AttributeError:
            pass            
        
        for _k, _v in _params.items():
            
            try:
                # Verificando os critérios especiais de filtros:
                if _special_criteria:
                    
                    if _k in _special_criteria:                    
                        
                        if _special_criteria[_k][0] in ('ilike', 'like'):
                            
                            _filter.append(self._model.special_criteria[_key]('%{}%'.format(_v)) )

                        else:
                            _filter.append(
                                getattr(self._model.special_criteria[_key] == _v)
                                )
                            
                        continue
            
                _filter.append( getattr(self._model, _k) == _v )
            
            except AttributeError:
                continue
       
        return _filter


    def __serialize_return(self, data):
        from app.utils import to_dict

        return list(map(lambda obj: to_dict(obj), data))


    def _verify_order(self, query, params, *args, **kwargs):
              
        if 'order' not in params:
            query = query.order_by(self._model.id.desc())
            return
        
        order, attribute = params['order'], 'id'

        # Só decodificamos caso a ordenação seja coerente:
        if order not in ('asc', 'desc'):
            return

        if 'attribute' in params:
            attribute = params['attribute']
        
        # Tentando atribuir essa ordenação:
        try:            
            if order == 'desc':
                query = query.order_by(getattr(self._model, attribute).desc())

            else:
                query = query.order_by(getattr(self._model, attribute).asc())
        
        except AttributeError as err:
            logger.exception(str(err))
            query = query.order_by(self._model.id.desc())



    def _valid(self, *args, **kwargs):
        
        _condition = True

        _regex = kwargs.pop('regex', None)
        _type = kwargs.pop('type', str)
        _params = kwargs.pop('params', self._data)
        _obrigatory = kwargs.pop('obrigatory', True)
        
        # Campo obrigatório:
        _field = kwargs['field']

        # Mensagem padrão de erro:
        _message = kwargs.pop('message', 'Campo {} fora do formato/padrão correto.'.format(_field))

        if _type == str:
            
            if _obrigatory:
                
                if _field not in self._data or \
                    _field in (None, "", self._data[_field].isspace()):

                    _condition = False
                
            
            if _regex:

                from re import match
                
                if not match(r"{}".format(_regex), self._data[_field]):
                    _condition = False

            

        elif _type == int:
            
            if _obrigatory:
                
                if _field not in self._data or \
                    _field in (None, ""):

                    _condition = False

                try:
                    self._data[_field] = int(_field)
                except Exception:
                    _condition = False

        elif _type == dict:
            
            if _obrigatory:
                
                if _field not in self._data or \
                    _field in (None, ""):

                    _condition = False
                
                if isinstance(_field, str):
                    from json import loads

                    try:
                        _field = loads(_field)   
                    
                    except Exception:
                        _condition = False
                

        # Quando algo pode dar errado:
        if not (_field in _params and _condition):
            raise ApiException(_message)



    def _get_order_attr(self, *args, **kwargs):
        if not hasattr(self.__model__, kwargs.get('order_attr', 'id')):
            self.raise_error("Verifique o atributo '{}' para fazer ordenação. Esse recurso não pode ser ordenado por esse atributo.".format(kwargs.get('order_attr', 'id')))

        return kwargs.get('order_attr', 'id')



    def validate(self,
        request_params, 
        attributes=[], 
        exception=True,
        strict="all",
        strict_attr='_id',
        empty_values=(None, '', 'null'),
        attributes_real_names=[],
        exception_message="Verifique os body params da requisição",
        *args, 
        **kwargs):
        
        if not isinstance(attributes, list):
            attributes = [attributes]

        if len(attributes_real_names) and len(attributes) and len(attributes) != len(attributes_real_names):
            raise RuntimeError("Verifique o tamanho dos parâmetros: 'attributes' e 'attributes_real_names'.")

        errors = []

        for index, attr in enumerate(attributes):
            if attr not in request_params or request_params[attr] in empty_values:
                """
                Verificando quando o strict é 'create': sinalizando que só devemos validar tudo
                se estivermos com o atributo 'strict_attr' definido.

                Se o strict for 'all', seremos exigentes para qualquer tipo de objeto. Ou seja,
                qualquer falha e valor faltante será adicionado aos erros.

                Se o strict for 'create', só teremos esse comportamento se o atributo 'strict_attr'
                não estiver definido. Pois se estiver, caracteriza uma atualização.
                """
                if strict is 'all':
                    if len(attributes_real_names): errors.append(attributes_real_names[index])
                    else: errors.append(attr)
                else:
                    if strict_attr not in request_params or request_params[strict_attr] in empty_values:
                        errors.append(attr)
        
        if len(errors) and exception:
            if kwargs.get('or_condition', False):
                if len(errors) == len(attributes):
                    self.raise_error("{} {}".format(exception_message, ", ".join(errors)))

            else:
                self.raise_error("{} {}".format(exception_message, ", ".join(errors)))

        return errors


    def add_message(self, message:str, *args, **kwargs):
        self.__messages.append(message)


    def get_session(self, attr=None, *args, **kwargs):
        
        if attr:
            return session.get(attr, None)
        
        return session


    @classmethod
    def modules(cls, *args, **kwargs):
        return [_class.__name__.lower().split('services')[0] for _class in cls.class_modules()]


    @classmethod
    def class_modules(cls, *args, **kwargs):
        return [_class for _class in DomainServices.__subclasses__()]


    @classmethod
    def get_specify_service(cls, module, *args, **kwargs):
        
        classes_domain = Domain.childs()
        classes_services = cls.class_modules()
        
        # Pegando e Formatando o nome das Classes:
        _classes_name =  {_class.__name__.lower().split('services')[0]: _class for _class in cls.class_modules()}
        
        logger.debug("Servicos Disponiveis: {}".format(_classes_name))

        # Selecionando a classe:
        return _classes_name.get(module, cls)


    def __make_upsert(self, before_function:str='before_upsert', after_function:str='after_upsert', *args, **kwargs):
        """
        Função para tratar o upsert de forma granular.
        """

        logger.debug("Modelo em upsert: {}".format(self.__model__))
        
        if hasattr(self.__model__, before_function) and callable(getattr(self.__model__, before_function)):
            _r = getattr(self.__model__, before_function)(*args, **kwargs)
            
            if isinstance(_r, dict):
                kwargs = _r
        
        if not self._function:  
            if 'id' in kwargs:
                _obj = self.__model__.update(**kwargs)
            
            else:
                _obj = self.__model__.create(**kwargs)

        else:
            if not hasattr(self.__model__, self._function):
                self.raise_error("Verifique a validade da função ('{}') solicitada para a requisição.".format(self._function))

            _obj = getattr(self.__model__, self._function)(**kwargs)

        if not _obj:
            raise RuntimeError("Verificar retorno do método de criação ou atualização.")

        if hasattr(_obj, after_function) and callable(getattr(_obj, after_function)):
            getattr(_obj, after_function)(*args, **kwargs)
        
        return _obj.id


       


from .auth import AuthServices
from .user import UserServices
from .attachment import AttachmentServices
