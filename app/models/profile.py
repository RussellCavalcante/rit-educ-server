from app.utils import logger,  ApiException
from app.models import db, LogicalDomain, ProfilePermission, SchoolUnitProfileUsers, SchoolUnit, SchoolNet, \
    SchoolNetAdministrator, AdministrationSchoolNet, Administration, Administrator, Domain, ClassesDiscipline, ProfileUser, session
from app.models.enums import ModelStatus
from app.config import BaseConfig as config

from pprint import pprint, pformat
from sqlalchemy.orm import validates, Query
from sqlalchemy import and_, asc, desc
from typing import List, Dict


class Profile(db.Model, LogicalDomain):
    name        = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    is_system   = db.Column(db.Boolean(), nullable=False, default=False)
    
    profile_users = db.relationship('ProfileUser', foreign_keys="[ProfileUser.profile_id]", backref='profile', lazy=True)


    ADMINISTRATORS_ID = 'c0cef0b5-315e-4bb6-91c3-a0409ba4728a'
    SCHOOL_NET_ADMINISTRATOR_ID = '4601b262-f299-4ad6-8b63-47251879cec7'
    STUDENTS_ID = '344c0d50-1e20-4eed-af4a-ab4639addb40'

    
    @classmethod
    def profile_checked(cls, *args, **kwargs) -> Query:
        return cls.query.filter(cls.active())


    @classmethod
    def after_profile_checked(cls, models:List, *args, **kwargs) -> List:
        profile_users = ProfileUser.query.filter_by(user_id=kwargs['user_id'], status=1).all()

        for model in models:
            model['__checked__'] = False
            for profile_user in profile_users:
                if profile_user.profile_id == model['id']: model['__checked__'] = True
        
        return models
        

    @classmethod
    def school_registration_checked(cls, *args, **kwargs) -> Query:
        return cls.query.filter(cls.active(), cls.id.in_([config.TEACHERS_ID, config.STUDENTS_ID]))


    @classmethod
    def after_school_registration_checked(cls, models:List, *args, **kwargs) -> List:
        return cls.after_profile_checked(models, *args, **kwargs)
        

    @classmethod
    def before_find(cls, *args, **kwargs) -> List:
        """
        Usuários que são administradores da rede não podem visualizar perfis "acima" dele
        """
        if session['profile_user'].profile_id == cls.SCHOOL_NET_ADMINISTRATOR_ID:
            return [Profile.id != cls.ADMINISTRATORS_ID, Profile.id != cls.SCHOOL_NET_ADMINISTRATOR_ID]


    def after_remove(self, *args, **kwargs):
        from app.models import User
        # Não podemos permitir a deleção de perfis cujo Usuários estejam atrelados
        users = User.query\
            .filter(*[User.id == ProfileUser.user_id, ProfileUser.profile_id == self.id, ProfileUser.status != ModelStatus.DELETED.value ]).all()
        
        if len(users):
            raise ApiException("Não é possível deletar esse Perfil. Há {} usuário(s) com atribuição para esse Perfil.".format(len(users)))
        

    @classmethod
    def configuration_checked(cls, *args, **kwargs) -> Query:
        return cls.query


    @classmethod
    def after_configuration_checked(cls, models:List, *args, **kwargs) -> List:

        from app.models.configuration import Configuration
        from app.models.configuration_profile import ConfigurationProfile


        relationships = db.session.query(Configuration, ConfigurationProfile)\
            .filter(
                Configuration.id == kwargs['configuration_id'],
                ConfigurationProfile.configuration_id == Configuration.id,
                Configuration.active()
            )\
            .all()


        for model in models:
            model['__checked__'] = False

            for configuration, configuration_profile in relationships:
                if configuration_profile.profile_id == model['id']:
                    model['__checked__'] = True
                    

        return models

