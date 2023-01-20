from app import create_app, db
from app.models import *
from app.models.profile_user import STUDENTS_ID, AUXILIARY_ID, COORDINATORS_ID, TEACHERS_ID, SCHOOL_NET_ADMINISTRATOR_ID, SCHOOL_UNIT_ADMINISTRATOR_ID
from uuid import uuid4
from app.bulk.permissions import create_permissions


ADMINISTRATOR_PROFILE_ID = "04d57019-d565-4396-b965-eff652c2901e"


def init_bulk():

    with create_app(with_port=False).app_context():
        session = db.session

        # Criando Usuário Administrador:
        user = User(id=str(uuid4()), email='admin')
        user.salt = user.generate_salt()
        user.password = user.crypt_password('qwe123', user.salt)

        # Criando o perfil Administrador, Gestor da Rede e Gestor de Unidade:
        profile             = Profile(id=ADMINISTRATOR_PROFILE_ID, name="Administrador", is_system=True)
        profile_net         = Profile(id="c731e359-37de-4328-919a-952dc79dab52", name="Administrador da Rede", is_system=True)
        profile_unit        = Profile(id="fe0b5a65-3649-4903-a7f0-cf9094ea903f", name="Administrador da Unidade", is_system=True)
        
        # Criando o perfil de docente:
        professor =     Profile(      id='90462bf5-10a0-48b0-8ef0-e0d79c5e10cf', name="Docente Professor", is_system=True)
        coordenador =   Profile(      id='e137434b-c48d-4377-9466-ae4a432344dd', name="Docente Coordenador", is_system=True)
        auxiliar =      Profile(      id='e9b44444-a203-49cd-a820-283bfc066046', name="Docente Auxiliar", is_system=True)
        aluno    =      Profile(      id='344c0d50-1e20-4eed-af4a-ab4639addb40', name="Aluno", is_system=True)

        # Associando Perfil Administrador com Usuário
        admin = ProfileUser(id=str(uuid1()), user_id=user.id, profile_id=profile.id)
        
        # Criando as permissões:
        permissions = [Permission(id=str(uuid1()), name=permission, is_system=True, created_by=admin.id) for permission in Permission.possible_permissions()]

        for permission in permissions: permission.set_default_alias()

        # Adicionando ao usuário admin as permissões para todos os recursos da aplicação:
        profile_permissions = [ProfilePermission(profile_id=profile.id, permission_id=permission.id, created_by=admin.id) for permission in permissions]

        # Administração do Sistema
        system_administration = Administration(id=str(uuid4()), name="Administração do Sistema", created_by=admin.id)

        # Responsável pela Administração do Sistema
        system_administrator = Administrator(
            id=str(uuid4()), 
            administration_id=system_administration.id, 
            profile_user_id=admin.id, 
            created_by=admin.id)

        # Inserindo as séries e disciplinas básicas para o Software
        grades = [
            SchoolGrade(id=str(uuid4()), name="Fundamental - 1º Série"),
            SchoolGrade(id=str(uuid4()), name="Fundamental - 2º Série"),
            SchoolGrade(id=str(uuid4()), name="Fundamental - 3º Série"),
            ]

        disciplines = [
            SchoolDiscipline(id=str(uuid4()), name="Matemática"),
            SchoolDiscipline(id=str(uuid4()), name="Português"),
            SchoolDiscipline(id=str(uuid4()), name="Física"),
            SchoolDiscipline(id=str(uuid4()), name="Biologia"),
            SchoolDiscipline(id=str(uuid4()), name="Química"),
        ]

        period = [
            SchoolPeriod(id=str(uuid4()), name="2020", begin='2020-06-30', end='2020-12-24'),
        ]
        
        bulk = [
            user, 
            profile, 
            admin, 
            system_administration, 
            system_administrator, 
            profile_net, 
            profile_unit, 
            professor, 
            coordenador, 
            auxiliar,
            aluno]
        
        bulk.extend(grades)
        bulk.extend(disciplines)
        bulk.extend(period)

        bulk.extend(permissions)
        bulk.extend(profile_permissions)
        
        # Adicionando o usuário criador:
        for object in bulk: object.created_by = admin.id

        session.bulk_save_objects(bulk)

        session.commit()


def complete_permissions():
    with create_app(with_port=False).app_context():
        session = db.session

        # Pegando todas as permissões que a aplicação pode ter
        permissions = Permission.possible_permissions()

        permissions_already_saved = Permission.get(cursor_function='all')
        permissions_already_saved = [permission.name for permission in permissions_already_saved]

        permissions_to_save = list(set(permissions) - set(permissions_already_saved))

        pprint(permissions_to_save)
        input("S?")

        # Carregando o administrador da aplicação:
        admin = ProfileUser.query.filter(User.email=='admin', ProfileUser.user_id == User.id).first()

        permissions_to_save = [Permission(id=str(uuid4()), name=name, is_system=True, created_by=admin.id) for name in permissions_to_save]
        
        # Adicionando ao usuário admin as permissões para todos os recursos da aplicação:
        profile_permissions = [ProfilePermission(profile_id=ADMINISTRATOR_PROFILE_ID, permission_id=permission.id, created_by=admin.id) \
            for permission in permissions_to_save]

        bulk = []
        bulk.extend(permissions_to_save)
        bulk.extend(profile_permissions)

        session.bulk_save_objects(bulk)

        session.commit()


def reset_passwords(new_password='123'):
    """
    Função para redefinir todas as senhas dos usuários da aplicação
    """
    with create_app(with_port=False).app_context():
        session = db.session

        # Pegando todas as permissões que a aplicação pode ter
        permissions = Permission.possible_permissions()

        objects = User.query.filter().all()

        for object in objects:
            object.password   = User.crypt_password(new_password, object.salt)

        session.commit()
