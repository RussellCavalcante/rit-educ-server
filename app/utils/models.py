
from app.utils import ApiException, all_subclasses
from datetime import datetime, date


class Super(object):
    
    @classmethod
    def find(cls, *args, **kwargs):
        raise NotImplementedError()

    
    @classmethod
    def create(cls, *args, **kwargs):
        raise NotImplementedError()

    
    @classmethod
    def update(cls, *args, **kwargs):
        raise NotImplementedError()


    @classmethod
    def remove(cls, *args, **kwargs):
        raise NotImplementedError()

    
    @classmethod
    def choose_model(cls, model_name:str, *args, **kwargs):
        subclasses = [_class for _class in cls.childs()]

        # Pegando e Formatando o nome das Classes:
        _classes_name =  {_class.__name__.lower(): _class for _class in subclasses}

        if model_name.lower() not in _classes_name:
            raise ApiException('Esse recurso não está disponível no momento.')
        
        # Selecionando a classe:
        return _classes_name[model_name.lower()]
    

    @classmethod
    def childs(cls, directs=False, *args, **kwargs):
        if directs: return [_class for _class in cls.__subclasses__()]

        return all_subclasses(cls)
        

    def to_dict(self, exclude_keys=('_sa_instance_state'), *args, **kwargs) -> dict:
        """
        Função para serializar um objecto
        """
        _dict = {}

        condition_to_cast = lambda value: True if not isinstance(value, str) and not isinstance(value, int) and not isinstance(value, float) and not isinstance(value, dict) and not isinstance(value, list) and value is not None else False
        
        for key, value in self.__dict__.items():
            if (hasattr(self, '__dont_return__') and key in self.__dont_return__) or key in exclude_keys: continue

            #print(key, value)

            if condition_to_cast(value):
                # NOTE: Adicionar funções de casting:
                if isinstance(value, datetime): value = self.cast_datetime(value)
                elif isinstance(value, date): value = self.cast_date(value)
                else: value = str(value)
                #print(value, type(value))

            _dict[key] = value

        return _dict


    def cast_datetime(self, date, *args, **kwargs) -> str:
        import pytz
    
        _new_date = pytz.UTC.localize(date)
        _new_date = _new_date.isoformat()
        _new_date = _new_date.split('+')[0] + '-03:00'
        #print(_new_date) # Iso format: 2020-06-23T21:21:16.090278+00:00
        #input("...")

        return _new_date #strftime('%d/%m/%Y')

    
    def cast_date(self, date, *args, **kwargs) -> str:
        #import pytz
        
        #_new_date = datetime.combine(date, datetime.min.time())
        #_new_date = pytz.UTC.localize(_new_date)
        #logger.debug("Nova data: {} - {}".format(date, _new_date))
        if not date: 
            return None
            
        return '{}T{}'.format(date, '00:00:00-03:00')#.isoformat() #strftime('%d/%m/%Y')

