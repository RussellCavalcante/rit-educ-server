from app import create_app, db
from app.models import *
from uuid import uuid4
from pprint import pprint


def create_permissions(
    created_by=None, 
    type_permissions=('create', 'find', 'find_by_id', 'remove', 'update'),
    commiting=False,
    *args,
    **kwargs) -> list:

    models = Domain.childs()

    # Filtrando somente os modelos que são persistíveis
    models = [model for model in models if hasattr(model, '__tablename__')]

    # Filtrando o nome das tabelas
    models = [model.__tablename__ for model in models]

    # Adicionando as permissões para cada modelo:
    permissions = ["{}#{}".format(model, permission_name) for model in models for permission_name in type_permissions]
    
    if commiting:            
        with create_app(with_port=False).app_context():
            session = db.session

            permissions = [Permission(name=permission, is_system=True, created_by=created_by) for permission in permissions]

            Permission.query.delete()

            session.bulk_save_objects(permissions)

            session.commit()

    return permissions