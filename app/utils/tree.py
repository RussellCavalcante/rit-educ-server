from app.models import Domain, uuid4, pprint


def get_tree(name:str, *args, **kwargs) -> dict:
    return {'id': str(uuid4()), 'name': name, 'children': {}}


def get_node(data:Domain, *args, **kwargs) -> dict:
    if isinstance(data, dict):
        data['children'] = {} 
        return data
    
    element = data.to_dict()
    element['children'] = {}

    return element


def add_node() -> dict:
    pass


def process_tree(sub_tree:dict, matrix:list, deep=0, *args, **kwargs):
    """
    Implementação utilizando busca em profundidade para construção de árvores.
    """
    for row in matrix:
        index=0 # Índice da linha
        process_row(sub_tree, row, index)

    sub_tree = {sub_tree['id']: sub_tree}

    # Removendo os índices
    remove_indexes(sub_tree)
    

def process_row(sub_tree:dict, row:tuple, index:int):
    if index == len(row): return
    
    element = row[index]

    id = element['id'] if isinstance(element, dict) else element.id

    if id not in sub_tree['children']:
        sub_tree['children'][id] = get_node(element)

    index += 1    
    process_row(sub_tree['children'][id], row, index)
    

def remove_indexes(sub_tree:dict, path:str=''):
    
    for node in sub_tree.keys():
        #print("Nó: ", path + node)
        
        if 'children' in sub_tree[node]:
            remove_indexes(sub_tree[node]['children'], path + node + ' -> ')
            sub_tree[node]['children'] = list(sub_tree[node]['children'].values())
            #print("Ajustando: ", node)
        
       

