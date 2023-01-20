import enum 


def get_status(value):
    if value == 0: return 'Apagado'
    if value == 1: return 'Ativo'
    if value == 2: return 'Desabilitado'
    if value == 5: return 'Não Lido'

    return value
    

class ModelStatus(enum.Enum):     
    DELETED = 0
    ACTIVE = 1
    DISABLED = 2
    PROCESSING = 4

    NOT_READ = 5

    
