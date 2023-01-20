from app.utils import logger,  ApiException
from app.models import db, LogicalDomain, ProfileUser, ProfilePermission, SchoolUnitProfileUsers, SchoolUnit, SchoolNet, \
    SchoolNetAdministrator, AdministrationSchoolNet, Administration, Administrator, Domain, ClassesDiscipline, ProfileUser, session, or_, \
    TeacherDiscipline, StudentDiscipline
from app.models.enums import ModelStatus, get_status
from app.config import BaseConfig as config

from pprint import pprint, pformat
from sqlalchemy.orm import validates, Query
from sqlalchemy import func
from sqlalchemy import and_, asc, desc
from typing import List, Dict


class User(db.Model, LogicalDomain):
    email       = db.Column(db.String(255), nullable=False)
    password    = db.Column(db.String(100), nullable=False)
    name        = db.Column(db.String(255), nullable=True)
    born        = db.Column(db.Date(), nullable=True)
    salt        = db.Column(db.String(40), unique=True, nullable=False)
    
    profile_users = db.relationship('ProfileUser', foreign_keys="[ProfileUser.user_id]", backref='user', lazy=True)

    __dont_return__ = ['password', 'salt']
    __additional_permissions__ = ['recovery-password', 'block-user'] 



    @classmethod
    def after_find(cls, users, *args, **kwargs):
        from app.models import Profile
        
        ids = Domain.get_attribute_values(users, 'id')

        # Trazendo os perfis ao qual os usuários fazem parte
        where = [ProfileUser.user_id.in_(ids), ProfileUser.profile_id == Profile.id, ProfileUser.status != ModelStatus.DELETED.value]

        join = db.session.query(ProfileUser, Profile).filter(*where).all()

        for user in users:
            # Adicionando o status do usuário:
            user['__status'] = get_status(user['status'])

            user['profile'] = []
            user['profile_user'] = []

            for profile_user, profile in join:
                if profile_user.user_id == user['id']: 
                    user['profile'].append(profile.to_dict())
                    user['profile_user'].append(profile_user.to_dict())

        from app.models import Person
        
        # Trazendo as pessoas relacionadas a esse usuário
        where = [Person.user_id.in_(ids)]
        
        join = db.session.query(Person).filter(*where).all()

        for user in users:
            user['person'] = None

            for person in join:
                if person.user_id == user['id']: 
                    user['person'] = person.to_dict()


    def after_upsert(self, *args, **kwargs):
        pass
        

    @classmethod
    def create(cls, *args, **kwargs):
        if kwargs.get('__update__', None) and kwargs['__update__'] in ('true', 1):
            
            if not (kwargs.get('id', None) and kwargs.get('email', None) and kwargs.get('meta_attr', None)):
                raise ApiException("Verifique a validade dessa operação.")

            user = User.query.filter_by(id=kwargs['id']).first()

            if not user:
                raise ApiException("Verifique a validade dessa operação.")

            # Verificando se não estaremos chocando
            other_user = User.query.filter(User.id!=user.id, User.email == kwargs['email']).first()

            if other_user:
                raise ApiException("Já existe esse e-mail associado à outro Usuário.")

            user.email = kwargs['email']
            user.meta_attr = kwargs['meta_attr']
            return user

        from flask import session
        from datetime import datetime
        from uuid import uuid1

        kwargs['email'] = kwargs['email'].strip()

        if ' ' in kwargs['email']:
            raise ApiException("Verifique o nome do Usuário. Ele não pode conter espaços.")

        if cls.query.filter(cls.email.ilike(kwargs['email']), cls.active()).first():
            raise ApiException("Já existe uma pessoa cadastrada com esse Usuário de Acesso. Por favor, entre com outro.")

        user_creator = session['profile_user'].id

        logger.info("Usuário '{}' criando: '{}'".format(user_creator, cls))
        kwargs.pop('created_by', None)
        kwargs.pop('created_at', None)
                
        new_user = User(id=kwargs.pop('id', str(uuid1())), created_by=user_creator, created_at=datetime.now())

        columns = cls.columns()

        for key, value in kwargs.items():
            if key not in columns: continue
            setattr(new_user, key, value)
   
        new_user.password   = User.generate_password()
        
        if not new_user.meta_attr:
            new_user.meta_attr = {}

        new_user.meta_attr['currentPwd'] = new_user.password # TODO Remoção
        new_user.salt       = User.generate_salt()
        new_user.password   = User.crypt_password(new_user.password, new_user.salt)
        
        new_user.add()

        return new_user


    @validates('collaborator_id')
    def validate_collaborator_id(self, key, value):
        if value is None:
            return value
            
        from app.models import Collaborator
        if not Collaborator.exists(id=value):
            raise ApiException("Verifique a validade do Colaborador. A chave '{}' não existe.".format(value))
        return value

    
    @validates('username')
    def validate_username(self, key, value):
        user = User.query.filter(User.username == value, User.id != self.id, User.status != ModelStatus.DELETED.value).first()

        if user: raise ApiException("Verifique a validade do Usuário. O nome do usuário '{}' já está associado à outro Usuário.".format(value))
        
        return value


    @validates('born')
    def validate_born(self, key, value):
        if value is None:
            return None
        
        from app.utils import parse_date
        
        value = parse_date(value)
        
        return value


    def assert_password(self, password, *args, **kwargs) -> bool:
        password_with_md5 = self.crypt_password(password, self.salt)

        return password_with_md5 == self.password


    @classmethod
    def generate_password(cls, len_of_password=6, *args, **kwargs):
        from string import ascii_letters, digits
        from random import choice
        from app.utils import logger

        # Todos os caracteres disponíveis para str:
        allChars = list(ascii_letters) + list(digits)

        passphrase = []

        for i in range(len_of_password):

            tmp = choice(allChars)
            passphrase.append(tmp)

        res = "".join(passphrase)

        logger.info("Password '{}' gerado.".format(res))

        return res


    @classmethod
    def crypt_password(cls, password_without_crypt, salt, *args, **kwargs):
        from hashlib import md5
        from app.utils import logger

        logger.debug("Senha e salt: '{}' - '{}'".format(password_without_crypt, salt))

        password_md5 = password_without_crypt + salt
        password_md5 = md5(str(password_md5).encode('utf-8')).hexdigest()
        
        return password_md5
    

    @classmethod
    def generate_salt(cls, *args, **kwargs):
        from uuid import uuid4
        return str(uuid4())


    def send_password(self,
        password,
        assunto='Senha Criada - R-Desvio', 
        *args, 
        **kwargs):
        
        from app import config
        from app.services.email import EmailService
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart('alternative')
        msg['To'] = self.EMAIL
        msg['From'] = config.EMAIL_SENT_FROM
        msg['Subject'] = assunto
        
        body = "Olá {}, como vai?\n\nSegue a senha criada para o seu usuário: {}\n\nAtenciosamente,"\
            .format(self.USERNAME, password)

        mime = MIMEText(body, 'plain')
        msg.attach(mime)
        
        
        email_service = EmailService()
        email_service.send_smtp(
            config.EMAIL_SENT_FROM, 
            self.EMAIL, 
            msg.as_string())


    @classmethod
    def list_school_register(cls, *args, **kwargs) -> Query:
        """
        Função para listar os usuários com os seus registros escolares.
        """
        from app.models import SchoolUnitProfileUsers, SchoolUnit

        # Devemos verificar o nível de acesso desse usuário:
        current_profile_user:ProfileUser = session['profile_user']

        my_school_units = current_profile_user.get_my_school_units(columns=[SchoolUnit.id]).all()

        print(my_school_units)

        return db.session.query(User, ProfileUser.id, ProfileUser.profile_id) \
            .filter(
                User.id == ProfileUser.user_id,
                ProfileUser.profile_id.in_([config.TEACHERS_ID, config.STUDENTS_ID]),
                SchoolUnitProfileUsers.profile_user_id == ProfileUser.id,
                SchoolUnitProfileUsers.school_unit_id.in_(my_school_units),
                SchoolUnitProfileUsers.active(),
                User.active(),
                ProfileUser.active(),
            )\
            .order_by(desc(ProfileUser.profile_id))\
            .order_by(asc(User.email))

    
    @classmethod
    def after_list_school_register(cls, models:List, *args, **kwargs) -> List:
        # Contando as matrículas:

        _count_student_registration = db.session.query(StudentDiscipline.student_id, func.count(StudentDiscipline.student_id).label('student_registration'))\
            .group_by(StudentDiscipline.student_id).all()

        _count_teacher_registration = db.session.query(TeacherDiscipline.teacher_id, func.count(TeacherDiscipline.teacher_id).label('teacher_registration'))\
            .group_by(TeacherDiscipline.teacher_id).all()

        # Acumulando os valores:
        _count = {**{tup[0]: tup[1] for tup in _count_student_registration}, **{tup[0]: tup[1] for tup in _count_teacher_registration} }

        for user, profile_user_id, profile_id in models:
            user['count'] = _count.get(profile_user_id, 0)
            user['profile_user_id'] = profile_user_id
            user['profile_id'] = profile_id
            user['__is_teacher__'] = profile_id == config.TEACHERS_ID
        
        return [t[0] for t in models]


    @classmethod
    def students(cls, *args, **kwargs) -> Query:
        # NOTE Identificador obrigatório de um perfil aluno -> 344c0d50-1e20-4eed-af4a-ab4639addb40
        return cls.query.filter(ProfileUser.user_id == User.id, ProfileUser.profile_id == Profile.STUDENTS_ID, ProfileUser.status != ModelStatus.DELETED.value)


    @classmethod
    def after_students(cls, models:List, *args, **kwargs) -> List:
        cls.after_find(models, *args, **kwargs)

    
    @classmethod
    def get_by_profile_user_id(cls, id:str, *args, **kwargs):
        from app.models.profile_user import ProfileUser

        return User.query.filter(ProfileUser.id == id, ProfileUser.user_id == cls.id).first()


    @classmethod
    def q(cls, value, *args, **kwargs) -> List:
        from sqlalchemy import or_
        
        return [or_(*[
            cls.email.ilike("%%%s%%" % str(value)),
            cls.name.ilike("%%%s%%" % str(value))
        ])]