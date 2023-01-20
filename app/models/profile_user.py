from app.utils import logger,  ApiException, parse_datetime
from app.utils.charts import get_new_line_chart
from app.models import db, LogicalDomain, ProfilePermission, SchoolUnitProfileUsers, SchoolUnit, SchoolNet, \
    SchoolNetAdministrator, AdministrationSchoolNet, Administration, Administrator, Domain, ClassesDiscipline, datetime, timedelta
from app.models.enums import ModelStatus

from pprint import pprint, pformat
from sqlalchemy.orm import validates, Query
from sqlalchemy import and_, asc, desc, Date, cast, func, text

from typing import List, Dict
from flask import session


ADMINISTRATORS_ID = '04d57019-d565-4396-b965-eff652c2901e'
SCHOOL_NET_ADMINISTRATOR_ID = 'c731e359-37de-4328-919a-952dc79dab52'
SCHOOL_UNIT_ADMINISTRATOR_ID = 'fe0b5a65-3649-4903-a7f0-cf9094ea903f'
COORDINATORS_ID = 'e137434b-c48d-4377-9466-ae4a432344dd'
TEACHERS_ID = '90462bf5-10a0-48b0-8ef0-e0d79c5e10cf'
AUXILIARY_ID = 'e9b44444-a203-49cd-a820-283bfc066046'
STUDENTS_ID = '344c0d50-1e20-4eed-af4a-ab4639addb40'


class ProfileUser(db.Model, LogicalDomain):
    user_id    = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    profile_id = db.Column(db.String(36), db.ForeignKey('profile.id'), nullable=False)


    @property
    def user(self):
        if not self._user:
            self._user = User.query.filter_by(id=self.user_id).first()
        
        return self._user


    """
    Função para avaliar os perfis
    """
    def is_student(self):
        return self.profile_id == STUDENTS_ID


    def is_teacher(self):
        return self.profile_id == TEACHERS_ID


    def is_school_unit_administrator(self):
        return self.profile_id == SCHOOL_UNIT_ADMINISTRATOR_ID


    
    def is_school_net_administrator(self):
        return self.profile_id == SCHOOL_NET_ADMINISTRATOR_ID



    def is_administrator(self):
        return self.profile_id == ADMINISTRATORS_ID



    def get_my_school_units(self,
        columns=[SchoolUnit], 
        *args, 
        **kwargs) -> Query:
        """
        Função para retornar uma query para listagem de unidades escolares que um dado usuário tem acesso:
        """
        if self.is_administrator():
            return db.session.query(*columns).filter(
                                    Administrator.profile_user_id == self.id,
                                    Administrator.administration_id == Administration.id,
                                    AdministrationSchoolNet.administration_id == Administration.id,
                                    AdministrationSchoolNet.school_network_id == SchoolNet.id,
                                    SchoolUnit.school_net_id == SchoolNet.id
                                )

        
        if self.is_school_net_administrator():
            return db.session.query(*columns).filter(
                                    SchoolNetAdministrator.profile_user_id == self.id,
                                    SchoolNetAdministrator.school_net_id == SchoolNet.id,
                                    SchoolUnit.school_net_id == SchoolNet.id
                                ) 
        

        if self.is_school_unit_administrator():
            return db.session.query(*columns).filter(
                                    SchoolUnitProfileUsers.profile_user_id == self.id,
                                    SchoolUnitProfileUsers.school_unit_id  == SchoolUnit.id
                                ) 


        return db.session.query(*columns).filter(
                                    SchoolUnitProfileUsers.profile_user_id == self.id,
                                    SchoolUnitProfileUsers.school_unit_id  == SchoolUnit.id
                                ) 


    def get_my_disciplines(self, columns=None, *args, **kwargs) -> Query:
        """
        Função para retornar uma Query com as Classes Discipline que esse Usuário
        """
        from app.models import StudentDiscipline, TeacherDiscipline, ClassesDiscipline, SchoolUnitProfileUsers, SchoolUnit, \
            DisciplineGrade, UnitGrade, DisciplinePeriod, SchoolNetAdministrator, SchoolNet, Administrator, AdministrationSchoolNet, Administration

        if not columns: columns = [ClassesDiscipline]

        if self.is_student():
            return db.session.query(*columns) \
                .filter(
                    StudentDiscipline.student_id == self.id,
                    StudentDiscipline.classes_discipline_id == ClassesDiscipline.id,
                )

        
        if self.is_teacher():
           return db.session.query(*columns) \
                .filter(
                    TeacherDiscipline.teacher_id == self.id,
                    TeacherDiscipline.classes_discipline_id == ClassesDiscipline.id,
                )

        """
        Se o usuário for algum perfil administrador
        """
        if self.is_school_unit_administrator():
            return db.session.query(*columns) \
                                .filter(
                                    SchoolUnitProfileUsers.profile_user_id == self.id,
                                    SchoolUnitProfileUsers.school_unit_id == SchoolUnit.id,
                                    UnitGrade.school_unit_id == SchoolUnit.id,                                    
                                    DisciplineGrade.unit_grade_id == UnitGrade.id,
                                    DisciplinePeriod.discipline_grade_id == DisciplineGrade.id,
                                    ClassesDiscipline.discipline_period_id == DisciplinePeriod.id,
                                )

        
        if self.is_school_net_administrator():
            return db.session.query(*columns) \
                                .filter(
                                    SchoolNetAdministrator.profile_user_id == self.id,
                                    SchoolNetAdministrator.school_net_id == SchoolNet.id,
                                    SchoolUnit.school_net_id == SchoolNet.id,
                                    UnitGrade.school_unit_id == SchoolUnit.id,                                    
                                    DisciplineGrade.unit_grade_id == UnitGrade.id,
                                    DisciplinePeriod.discipline_grade_id == DisciplineGrade.id,
                                    ClassesDiscipline.discipline_period_id == DisciplinePeriod.id,
                                )

        
        if self.is_administrator():
            return db.session.query(*columns) \
                                .filter(
                                    Administrator.profile_user_id == self.id,
                                    Administrator.administration_id == Administration.id,
                                    AdministrationSchoolNet.administration_id == Administration.id,
                                    AdministrationSchoolNet.school_network_id == SchoolNet.id,
                                    SchoolUnit.school_net_id == SchoolNet.id,
                                    UnitGrade.school_unit_id == SchoolUnit.id,                                    
                                    DisciplineGrade.unit_grade_id == UnitGrade.id,
                                    DisciplinePeriod.discipline_grade_id == DisciplineGrade.id,
                                    ClassesDiscipline.discipline_period_id == DisciplinePeriod.id,
                                )



    def get_available_school_nets(self, *args, **kwargs) -> List[SchoolNet]:
        """
        Função para listar as redes educacionais disponíveis para um dado usuário.
        """
        filter = []

        if self.profile_id == ADMINISTRATORS_ID:
            pass
            # Pode listar todas as redes:
            #filter =    [   Administrator.profile_user_id == self.id,
            #                Administrator.administration_id == AdministrationSchoolNet.administration_id,
            #                AdministrationSchoolNet.school_network_id == SchoolNet.id,
            #                AdministrationSchoolNet.status != ModelStatus.DELETED.value]

        else:
            # Pode listar apenas as que ele se relaciona:
            filter = [  SchoolNetAdministrator.profile_user_id == self.id, 
                        SchoolNetAdministrator.school_net_id == SchoolNet.id,
                        SchoolNetAdministrator.status != ModelStatus.DELETED.value]

        school_nets = SchoolNet.get(filter, 'all')
        
        return school_nets


    @validates('profile_id')
    def validate_profile_id(self, key, value):
        if value is None:
            raise ApiException("Verifique a validade do Perfil. A chave '{}' não existe.".format(value)) 
        
        from app.models import Profile

        if Profile.exists(id=value) is False:
            raise ApiException("Verifique a validade do Perfil. A chave '{}' não existe.".format(value))
        
        return value

    
    @validates('user_id')
    def validate_user_id(self, key, value):
        from app.models import User
        
        if value is None:
            raise ApiException("Verifique a validade do Usuário. A chave '{}' não existe.".format(value)) 
            
        if User.exists(id=value) is False:
            raise ApiException("Verifique a validade do Usuário. A chave '{}' não existe.".format(value))
        
        return value


    @classmethod
    def after_find(cls, models:List, *args, **kwargs):
        from app.models import Profile, User

        ids = Domain.get_attribute_values(models, 'id')

        # Trazendo os Usuários e Perfis ao qual os modelos se relacionam
        join = db.session.query(ProfileUser.id, User, Profile).filter(
            User.id == ProfileUser.user_id,
            Profile.id == ProfileUser.profile_id,
            ProfileUser.id.in_(ids)
        )

        join = join.all()

        for model in models:
            for id, user, profile in join:
                if id != model['id']: continue
                model['user'] = user.to_dict()
                model['profile'] = profile.to_dict()
        

    def after_find_by_id(self, *args, **kwargs):
        from app.models import Profile, User

        # Trazendo os Usuários e Perfis ao qual os modelos se relacionam
        join = db.session.query(User, Profile).filter(
            User.id == self.user_id,
            Profile.id == self.profile_id,
        )

        join = join.first()

        self.email = join[0].email
        self.profile_name = join[1].name
        

    @classmethod
    def students(cls, *args, **kwargs) -> Query:
        # NOTE Identificador obrigatório de um perfil aluno -> 344c0d50-1e20-4eed-af4a-ab4639addb40
        return cls.query.filter(ProfileUser.profile_id == '344c0d50-1e20-4eed-af4a-ab4639addb40', ProfileUser.status != ModelStatus.DELETED.value)


    @classmethod
    def after_students(cls, models:List, *args, **kwargs) -> List:
        cls.after_find(models, *args, **kwargs)


    @classmethod
    def students_checked(cls, *args, **kwargs) -> Query:
        logger.debug("Carregando todos os alunos e marcando com check.")
        
        from app.models import User, Profile

        return db.session.query(ProfileUser, User, Profile)\
            .join(User, ProfileUser.user_id == User.id) \
            .join(Profile, ProfileUser.profile_id == Profile.id)\
            .filter(ProfileUser.profile_id == STUDENTS_ID)\
            .order_by(asc(User.email))
   

    @classmethod
    def after_students_checked(cls, models:List, *args, **kwargs) -> List:
        logger.debug('after_students_checked')
        data:list = []

        # Listando todos os alunos que foram marcados:
        all_checked = SchoolUnitProfileUsers.query.filter(
            SchoolUnitProfileUsers.profile_user_id.in_(Domain.get_attribute_values([tup[0] for tup in models])),
            SchoolUnitProfileUsers.active()
        )
        
        all_checked = all_checked.all()

        # Listando os checados para a nossa unidade escolar:
        my_checked      = [object.profile_user_id for object in all_checked if object.school_unit_id == kwargs['school_unit_id']]

        # Listando os marcados para outras unidades escolares:
        others_checked  = [object.profile_user_id for object in all_checked if object.school_unit_id != kwargs['school_unit_id']]

        for profile_user, user, profile in models:
            profile_user['user'] = user
            profile_user['profile'] = profile
            
            """
            Montando se este objeto está checado ou bloqueado.

            Casos bloqueados são quando esse objeto está relacionado à outra unidade escolar
            """
            profile_user['__checked__'] = True if profile_user['id'] in my_checked else False
            profile_user['__blocked__'] = True if profile_user['id'] in others_checked else False
            
            data.append(profile_user)
        
        return data


    """
    Funções para visualização de perfis de acesso

    1º usuários elegíveis para administrar rede

    2° usuários elegíveis para administrar unidade
    """
    @classmethod
    def school_net_administrator(cls, *args, **kwargs) -> Query:
        return db.session.query(ProfileUser) \
            .filter(ProfileUser.profile_id == SCHOOL_NET_ADMINISTRATOR_ID, ProfileUser.status != ModelStatus.DELETED.value) \


    @classmethod
    def after_school_net_administrator(cls, models:List, *args, **kwargs) -> List:
        cls.after_find(models, *args, **kwargs)


    @classmethod
    def school_unit_administrator(cls, *args, **kwargs) -> Query:
        """
        Função para carregar os usuários passíveis para receber uma administração de unidade
        """
        return db.session.query(ProfileUser) \
            .filter(ProfileUser.profile_id == SCHOOL_UNIT_ADMINISTRATOR_ID, ProfileUser.active()) \


    @classmethod
    def after_school_unit_administrator(cls, models:List, *args, **kwargs) -> List:
        cls.after_find(models, *args, **kwargs)


    @classmethod
    def school_unit_administrator_checked(cls, *args, **kwargs) -> Query:
        """
        Função para carregar os usuários passíveis para receber uma administração de unidade
        """
        from app.models import SchoolUnitProfileUsers

        left = (
            SchoolUnitProfileUsers.school_unit_id == kwargs['school_unit_id'],
            SchoolUnitProfileUsers.profile_user_id == ProfileUser.id,
            SchoolUnitProfileUsers.active()
        )

        return db.session.query(ProfileUser, SchoolUnitProfileUsers) \
            .outerjoin(SchoolUnitProfileUsers, and_(*left))\
            .filter(ProfileUser.profile_id == SCHOOL_UNIT_ADMINISTRATOR_ID)


    @classmethod
    def after_school_unit_administrator_checked(cls, models:List, *args, **kwargs) -> List:
        data:list = []

        ids = Domain.get_attribute_values([tup[0] for tup in models], 'id')

        for main_object, relationship in models:
            main_object['__checked__'] = True if relationship else False
            data.append(main_object)

        cls.after_find(data, *args, **kwargs)

        return data


    @classmethod
    def coordinators_checked(cls, *args, **kwargs) -> Query:
        """
        Função para carregar os usuários passíveis para receber uma cooordenação de unidade
        """
        from app.models import SchoolUnitProfileUsers

        left = (
            SchoolUnitProfileUsers.school_unit_id == kwargs['school_unit_id'],
            SchoolUnitProfileUsers.profile_user_id == ProfileUser.id,
            SchoolUnitProfileUsers.active()
        )

        return db.session.query(ProfileUser, SchoolUnitProfileUsers) \
            .outerjoin(SchoolUnitProfileUsers, and_(*left))\
            .filter(ProfileUser.profile_id == COORDINATORS_ID)


    @classmethod
    def after_coordinators_checked(cls, models:List, *args, **kwargs) -> List:
        return cls.after_school_unit_administrator_checked(models, *args, **kwargs)


    @classmethod
    def teachers_checked(cls, *args, **kwargs) -> Query:
        """
        Função para carregar os usuários professores que possuem atribuição com alguma Unidade Escolar
        """
        from app.models import User
        
        return db.session.query(ProfileUser)\
            .join(User, ProfileUser.user_id == User.id) \
            .filter(ProfileUser.profile_id == TEACHERS_ID)\
            .order_by(asc(User.email))


    @classmethod
    def after_teachers_checked(cls, models:List, *args, **kwargs) -> List:

        professionals = SchoolUnitProfileUsers.query.filter(
            SchoolUnitProfileUsers.school_unit_id == kwargs['school_unit_id'],
            SchoolUnitProfileUsers.profile_user_id.in_(Domain.get_attribute_values(models)),
            SchoolUnitProfileUsers.active()
        )

        professionals = professionals.all()

        professionals = Domain.get_attribute_values(professionals, 'profile_user_id')

        #pprint(professionals)

        data = []
        
        for model in models:
            model['__checked__'] = True if model['id'] in professionals else False
            data.append(model)

        cls.after_find(data, *args, **kwargs)

        return data


    @classmethod
    def auxiliaries_checked(cls, *args, **kwargs) -> Query:
        """
        Função para carregar os usuários passíveis para receber uma cooordenação de unidade
        """
        from app.models import SchoolUnitProfileUsers

        left = (
            SchoolUnitProfileUsers.school_unit_id == kwargs['school_unit_id'],
            SchoolUnitProfileUsers.profile_user_id == ProfileUser.id,
            SchoolUnitProfileUsers.active()
        )

        return db.session.query(ProfileUser, SchoolUnitProfileUsers) \
            .outerjoin(SchoolUnitProfileUsers, and_(*left))\
            .filter(ProfileUser.profile_id == AUXILIARY_ID)


    @classmethod
    def after_auxiliaries_checked(cls, models:List, *args, **kwargs) -> List:
        return cls.after_school_unit_administrator_checked(models, *args, **kwargs)


    @classmethod
    def administrators(cls, *args, **kwargs) -> Query:
        return db.session.query(ProfileUser) \
            .filter(ProfileUser.profile_id == ADMINISTRATORS_ID, ProfileUser.status != ModelStatus.DELETED.value) \


    @classmethod
    def after_administrators(cls, models:List, *args, **kwargs) -> List:
        cls.after_find(models, *args, **kwargs)



    @classmethod
    def students_class_discipline_checked(cls, *args, **kwargs) -> List:
        """
        Função para carregar os Alunos associados à alguma turma escolar.
        """
        from app.models import SchoolUnitProfileUsers, ClassesDiscipline, StudentDiscipline, SchoolUnit, User

        # 1º: Carregando os estudantes associados às Unidades Escolares
        students = db.session.query(ProfileUser, User, SchoolUnit).filter(
            SchoolUnitProfileUsers.school_unit_id == kwargs['school_unit_id'],
            SchoolUnitProfileUsers.profile_user_id == ProfileUser.id,
            SchoolUnitProfileUsers.school_unit_id == SchoolUnit.id,
            ProfileUser.profile_id == STUDENTS_ID,
            ProfileUser.user_id == User.id,
            SchoolUnitProfileUsers.active(),
            ProfileUser.active()
        )

        students = students.all()

        units =     [tup[2] for tup in students]
        users =     [tup[1] for tup in students]
        students =  [tup[0] for tup in students]

        # 2º: Verificando se esses estudantes possuem relacionamento com a disciplina em questão
        students_disciplines = StudentDiscipline.query.filter(
            StudentDiscipline.classes_discipline_id == kwargs['class_discipline_id'],
            StudentDiscipline.student_id.in_(Domain.get_attribute_values(students))
        )

        students_disciplines = students_disciplines.all()

        #pprint(students_disciplines)

        students = [s.to_dict() for s in students]

        for student, user, unit in zip(students, users, units):
            student['__checked__']      = False
            student['user']             = user.to_dict()
            student['school_unit']      = unit.to_dict()
            for relationship in students_disciplines:
                if relationship.student_id == student['id']: student['__checked__'] = True

        return students
   


    @classmethod
    def teachers_class_discipline_checked(cls, *args, **kwargs) -> List:
        """
        Função para carregar Professores e, caso possua, as suas atribuições à turma/disciplinas
        """
        from app.models import SchoolUnitProfileUsers, ClassesDiscipline, TeacherDiscipline, SchoolUnit
        from app.models.user import User

        # 1º: Carregando os professores associados às Unidades Escolares
        teachers = db.session.query(ProfileUser, User, SchoolUnit).filter(
            SchoolUnitProfileUsers.profile_user_id == ProfileUser.id,
            SchoolUnitProfileUsers.school_unit_id == kwargs['school_unit_id'],
            SchoolUnitProfileUsers.school_unit_id == SchoolUnit.id,
            ProfileUser.profile_id == TEACHERS_ID,
            ProfileUser.user_id == User.id,
            SchoolUnitProfileUsers.active(),
            ProfileUser.active()
        )

        teachers = teachers.all()
        
        units =     [tup[2] for tup in teachers]
        users =     [tup[1] for tup in teachers]
        teachers =  [tup[0] for tup in teachers]

        # 2º: Verificando se esses professores possuem relacionamento com a disciplina em questão
        teachers_disciplines = TeacherDiscipline.query.filter(
            TeacherDiscipline.classes_discipline_id == kwargs['class_discipline_id'],
            TeacherDiscipline.teacher_id.in_(Domain.get_attribute_values(teachers))
        )

        teachers_disciplines = teachers_disciplines.all()

        pprint(teachers_disciplines)

        teachers = [teacher.to_dict() for teacher in teachers]

        for teacher, user, unit in zip(teachers, users, units):
            teacher['__checked__'] = False
            teacher['user'] = user.to_dict()
            teacher['school_unit'] = unit.to_dict()
            for relationship in teachers_disciplines:
                if relationship.teacher_id == teacher['id']: teacher['__checked__'] = True

        return teachers



    @classmethod
    def auxiliaries_class_discipline_checked(cls, *args, **kwargs) -> List:
        """
        Função para listar os professores auxiliares para uma dada turma de disciplina com o check habilitado.

        É necessário a passagem dos atributos: 'school_unit_id' e 'class_discipline_id'
        """
        from app.models import SchoolUnitProfileUsers, ClassesDiscipline, TeacherDiscipline, SchoolUnit, User

        # 1º: Carregando os professores associados às Unidades Escolares
        teachers = db.session.query(ProfileUser, User, SchoolUnit).filter(
            SchoolUnitProfileUsers.profile_user_id == ProfileUser.id,
            SchoolUnitProfileUsers.school_unit_id == kwargs['school_unit_id'],
            SchoolUnitProfileUsers.school_unit_id == SchoolUnit.id,
            ProfileUser.profile_id == AUXILIARY_ID,
            ProfileUser.user_id == User.id,
            SchoolUnitProfileUsers.active(),
            ProfileUser.active()
        )

        teachers = teachers.all()
        
        units =     [tup[2] for tup in teachers]
        users =     [tup[1] for tup in teachers]
        teachers =  [tup[0] for tup in teachers]

        # 2º: Verificando se esses professores possuem relacionamento com a disciplina em questão
        teachers_disciplines = TeacherDiscipline.query.filter(
            TeacherDiscipline.classes_discipline_id == kwargs['class_discipline_id'],
            TeacherDiscipline.teacher_id.in_(Domain.get_attribute_values(teachers))
        )

        teachers_disciplines = teachers_disciplines.all()

        pprint(teachers_disciplines)

        teachers = [teacher.to_dict() for teacher in teachers]

        for teacher, user, unit in zip(teachers, users, units):
            teacher['__checked__'] = False
            teacher['user'] = user.to_dict()
            teacher['school_unit'] = unit.to_dict()
            for relationship in teachers_disciplines:
                if relationship.teacher_id == teacher['id']: teacher['__checked__'] = True

        return teachers


    """
    Funções para auxiliar e visualização das interações de um Perfil com outros Perfis
    """
    def list_my_teachers(self, *args, **kwargs) -> List[Dict]:
        """
        Função para listar os professores de um dado ProfileUser - desde que esse seja um estudante.
        """
        if not self.is_student():
            raise RuntimeError()

        from app.models import StudentDiscipline, TeacherDiscipline, ClassesDiscipline, User, Profile

        teachers = db.session.query(ProfileUser, User.email, Profile.name).filter(
            StudentDiscipline.student_id == self.id,
            StudentDiscipline.classes_discipline_id == ClassesDiscipline.id,
            TeacherDiscipline.classes_discipline_id == ClassesDiscipline.id,
            TeacherDiscipline.teacher_id == ProfileUser.id,
            ProfileUser.user_id == User.id,
            ProfileUser.profile_id == Profile.id,
            Profile.id == TEACHERS_ID
        )

        teachers = teachers.all()

        teachers = [{**tup[0].to_dict(), 'email': tup[1], 'profile': tup[2]} for tup in teachers]
        
        return teachers



    def list_my_students(self, *args, **kwargs) -> List[Dict]:
        """
        Função para listar os alunos de um dado ProfileUser - desde que esse seja um estudante.
        """

        from app.models import StudentDiscipline, TeacherDiscipline, ClassesDiscipline, User, Profile

        objects = db.session.query(ProfileUser, User.email, Profile.name).filter(
            TeacherDiscipline.teacher_id == self.id,
            TeacherDiscipline.classes_discipline_id == ClassesDiscipline.id,
            StudentDiscipline.classes_discipline_id == ClassesDiscipline.id,
            StudentDiscipline.student_id == ProfileUser.id,
            ProfileUser.user_id == User.id,
            ProfileUser.profile_id == Profile.id
        )

        objects = objects.all()

        objects = [{**tup[0].to_dict(), 'email': tup[1], 'profile': tup[2]} for tup in objects]
        
        return objects



    def list_other_students(self, *args, **kwargs) -> List[Dict]:
        """
        Função para listar os outros alunos - cadastrados nas mesmas disciplinas - de um dado ProfileUser - desde que esse seja um estudante.
        """
        if not self.is_student():
            raise RuntimeError()

        from app.models import StudentDiscipline, TeacherDiscipline, ClassesDiscipline, User, Profile

        my_classes = db.session.query(ClassesDiscipline.id).filter(
            StudentDiscipline.student_id == self.id,
            StudentDiscipline.classes_discipline_id == ClassesDiscipline.id
            )
        
        my_classes = [class_id[0] for class_id in my_classes.all()]

        others = db.session.query(ProfileUser, User.email, Profile.name).filter(
            ClassesDiscipline.id.in_(my_classes),
            StudentDiscipline.classes_discipline_id == ClassesDiscipline.id,
            StudentDiscipline.student_id == ProfileUser.id,
            ProfileUser.user_id == User.id,
            ProfileUser.profile_id == Profile.id,
            Profile.id == STUDENTS_ID,
            ProfileUser.id != self.id
        )

        others = others.all()

        others = [{**tup[0].to_dict(), 'email': tup[1], 'profile': tup[2]} for tup in others]
        
        return others


    @classmethod
    def get_my_senders_options(cls, *args, **kwargs) -> List:
        """
        Função para listar quem são as pessoas que esse Profile User pode fazer envio de mensagem.

        Autor: Eduardo
        """
        from app.models import StudentDiscipline, session

        current_profile:cls = session['profile_user']

        objects = []

        if current_profile.is_student():
            objects = current_profile.list_my_teachers()

            other_students = current_profile.list_other_students()

            objects.extend(other_students)
           
        elif current_profile.is_teacher():
            objects = current_profile.list_my_students()
        
        else:
            my_school_units:List[SchoolUnit] = current_profile.get_my_school_units().all()

            matrix_profile_users = [school_unit.get_profile_users().all() for school_unit in my_school_units]

            for array_profile_users in matrix_profile_users:
                for profile_user in array_profile_users:
                    object = profile_user.to_dict()
                    object['email'] = profile_user.user.email
                    object['profile'] = profile_user.profile.name

                    objects.append(object)


        return objects


    @classmethod
    def get_my_newsletter_options(cls, *args, **kwargs) -> List:
        """
        Função para listar quem são os grupos que esse Profile User pode fazer atribuição à Newsletter.

        Autor: Eduardo
        """
        from app.models import TeacherDiscipline, StudentDiscipline, session, Administrator, AdministrationSchoolNet
        group = []
        
        current_profile = session['profile_user']

        if current_profile.is_administrator():

            my_school_nets = SchoolNet.query.filter(
                Administrator.profile_user_id == current_profile.id,
                Administrator.administration_id == AdministrationSchoolNet.administration_id,
                AdministrationSchoolNet.school_network_id == SchoolNet.id
                ).all()

            # Listando o grupo de administradores de rede ao qual eu administro
            for object in my_school_nets:
                group.append({
                    'group_type': 'Administradores da Rede Educacional',
                    'group': object.name, 
                    'profile_users': Domain.get_attribute_values(object.get_administrators().all())                      
                    })

            # Listando os usuários das redes escolares:
            for object in my_school_nets:
                group.append({
                    'group_type': 'Membros da Rede Educacional',
                    'group': object.name, 
                    'profile_users': Domain.get_attribute_values(object.get_profile_users().all())                      
                    })

            # Listando as unidades escolares que esse administrador tem acesso:
            my_school_units = SchoolUnit.query.filter(SchoolUnit.school_net_id.in_(Domain.get_attribute_values(my_school_nets))).all()

            # Listando o grupo de administradores das unidades educacionais:
            for object in my_school_units:
                group.append({
                    'group_type': 'Administradores da Unidade Educacional',
                    'group': object.name, 
                    'profile_users': Domain.get_attribute_values(object.get_administrators().all())                      
                    })

            # Listando os usuários das unidades escolares:
            for object in my_school_units:
                group.append({
                    'group_type': 'Membros da Unidade Educacional',
                    'group': object.name, 
                    'profile_users': Domain.get_attribute_values(object.get_profile_users().all())                      
                    })

            # Membros das disciplinas das redes escolares
            for object in my_school_units:
                disciplines = object.get_disciplines().all()

                for discipline in disciplines:
                    discipline_name = discipline.classe_discipline_name

                    # Listando professores:
                    ids = [id[0] for id in \
                            db.session.query(TeacherDiscipline.teacher_id).filter_by(classes_discipline_id=discipline.id).all()]

                    group.append({
                        'group_type': 'Professores',
                        'group': discipline_name, 
                        'profile_users':  ids
                        })

                for discipline in disciplines:
                    discipline_name = discipline.classe_discipline_name

                    # Listando todos os alunos da disciplina:
                    ids = [id[0] for id in \
                        db.session.query(StudentDiscipline.student_id).filter_by(classes_discipline_id=discipline.id).all()]

                    group.append({
                        'group_type': 'Alunos',
                        'group': discipline_name, 
                        'profile_users': ids                     
                        })

            return group

        if current_profile.is_school_net_administrator():
            """
            Listando as unidades escolares atualmente para esse administrador de rede
            """
            objects = SchoolUnit.query.filter(
                SchoolNetAdministrator.profile_user_id == current_profile.id,
                SchoolNetAdministrator.school_net_id == SchoolNet.id,
                SchoolUnit.school_net_id == SchoolNet.id
                ).all()

            # Listando o grupo de administradores das unidades educacionais:
            for object in objects:
                group.append({
                    'group_type': 'Administradores da Unidade Educacional',
                    'group': object.name, 
                    'profile_users': Domain.get_attribute_values(object.get_administrators().all())                      
                    })

            # Listando os usuários das redes escolares:
            for object in objects:
                group.append({
                    'group_type': 'Membros da Unidade Educacional',
                    'group': object.name, 
                    'profile_users': Domain.get_attribute_values(object.get_profile_users().all())                      
                    })

            my_disciplines = current_profile.get_my_disciplines().all()

            for discipline in my_disciplines:
                discipline_name = discipline.classe_discipline_name

                # Listando professores:
                ids = db.session.query(TeacherDiscipline.teacher_id).filter_by(classes_discipline_id=discipline.id).all()

                group.append({
                    'group_type': 'Professores ',
                    'group': discipline_name, 
                    'profile_users':  [id[0] for id in ids]
                    })

            for discipline in my_disciplines:
                discipline_name = discipline.classe_discipline_name

                # Listando todos os alunos e professores da disciplina:
                ids = db.session.query(StudentDiscipline.student_id).filter_by(classes_discipline_id=discipline.id).all()

                group.append({
                    'group_type': 'Alunos ',
                    'group': discipline_name, 
                    'profile_users':  [id[0] for id in ids]
                    })

            return group

        if current_profile.is_school_unit_administrator():
            my_disciplines = current_profile.get_my_disciplines().all()

            for discipline in my_disciplines:
                discipline_name = discipline.classe_discipline_name

                # Listando professores:
                ids = db.session.query(TeacherDiscipline.teacher_id).filter_by(classes_discipline_id=discipline.id).all()

                group.append({
                    'group_type': 'Professores ',
                    'group': discipline_name, 
                    'profile_users':  [id[0] for id in ids]
                    })

            for discipline in my_disciplines:
                discipline_name = discipline.classe_discipline_name

                # Listando todos os alunos e professores da disciplina:
                ids = db.session.query(StudentDiscipline.student_id).filter_by(classes_discipline_id=discipline.id).all()

                group.append({
                    'group_type': 'Alunos ',
                    'group': discipline_name, 
                    'profile_users':  [id[0] for id in ids]
                    })

            return group     

        
        """
        Caso o usuário seja um Usuário passível de visualizar turmas:
        """
        my_disciplines = current_profile.get_my_disciplines().all()

        for discipline in my_disciplines:

            discipline_name = discipline.classe_discipline_name

            # Listando todos os usuários da disciplina:
            ids = db.session.query(StudentDiscipline.student_id).filter_by(classes_discipline_id=discipline.id).all()
            ids = [id[0] for id in ids]

            group.append({
                'group_type': 'Alunos ',
                'group': discipline_name, 
                'profile_users': ids
                })
                
        if current_profile.is_school_unit_administrator():
            group.append({'group': 'Membros Rede Escolar', 'id': 3, 'profile_users': db.session.query(ProfileUser.id).filter(ProfileUser.profile_id == SCHOOL_NET_ADMINISTRATOR_ID, ProfileUser.active()).all()}) 
        
        if current_profile.is_school_net_administrator():
            group.append({'group': 'Administradores', 'id': 4, 'profile_users': db.session.query(ProfileUser.id).filter(ProfileUser.profile_id == ADMINISTRATORS_ID, ProfileUser.active()).all() }) 

        return group


    @classmethod
    def get_my_configuration(cls, *args, **kwargs) -> List:
        from app.models.profile import Profile
        from app.models.configuration import Configuration
        from app.models.configuration_profile import ConfigurationProfile

        current_profile_user:cls = session['profile_user']

        my_configuration = Configuration.query.filter(
            current_profile_user.profile_id == ConfigurationProfile.profile_id,
            ConfigurationProfile.configuration_id == Configuration.id,
            Configuration.active()
        )
        
        my_configuration = my_configuration.first()
        
        if not my_configuration: return []
        
        return [my_configuration.to_dict()]


    @classmethod
    def dashboard(cls, *args, **kwargs) -> List:
        
        current_profile_user:cls = session['profile_user']
        
        my_school_units:List[SchoolUnit] = current_profile_user.get_my_school_units().all()

        """
        1º: Carregar quantidade de logins efetuados nas unidades escolares que esse usuário administra ou tem acesso;
        1.1º: Logins na semana também;

        2º: Carregar a "frequência" dos alunos das unidades escolares ao qual administramos;

        3º: Carregar as informações de quantidade de alunos, professores e turmas para cada unidade escolar;

        4°: Aulas Ocorrendo nesse momento
        """
        cards = [
            {'label': 'Atendimento Hoje', 'value': 0, 'type': 'card'},
            {'label': 'Atendimento na Semana', 'value': 0, 'type': 'card'},
            {'label': 'Frequência', 'value': get_new_line_chart(title='Frequência dos Alunos'), 'type': 'graphic'},
            {'label': 'Informações Unidades Educacionais', 'value': {}, 'type': 'select'},
            {'label': 'Próximas Aulas', 'value': [], 'type': 'list'}
            ]

        # 1: Carregando logins de hoje e da semana:
        from app.models import History, LessonClassesDiscipline, or_, User, TeacherDiscipline, Lesson
        
        today = datetime.now().date()

        for school_unit in my_school_units:
            subquery = school_unit.get_members(columns=[ProfileUser.id]).subquery()

            cards[0]['value'] += History.query.filter(
                History.created_by.in_(subquery), 
                cast(History.created_at, Date) == today,
                History.type == 'LOGIN'
                ).count()


            cards[1]['value'] += History.query.filter(
                History.created_by.in_(subquery), 
                cast(History.created_at, Date) >= (today-timedelta(days=7)),
                History.type == 'LOGIN'
                ).count()
            

        # 2: Montando a frequência por dia dos alunos
        RANGE = 7

        labels = [today - timedelta(days=x) for x in reversed(range(RANGE))]
        datasets = []
        
        from itertools import cycle

        colors = cycle(['#204051', '#3b6978', '#84a9ac', '#e4e3e3'])
        
        to_date_cast = func.date(History.created_at)

        # Montando por unidade escolar:
        for school_unit in my_school_units:
            
            datasets.append({ 
                'data': [0]*RANGE,
                'label': school_unit.name,
                'borderColor': next(colors),
                'fill': False,
                })

            subquery = school_unit.get_members(columns=[ProfileUser.id]).subquery()
            
            # Agrupando por unidade escolar a frequência dos alunos     
            grouped = db.session.query(to_date_cast, func.count(History.id))\
                .filter(History.created_by.in_(subquery))\
                .group_by(to_date_cast)\
                .order_by(desc(to_date_cast))\
                .limit(RANGE)\
                .all()

            for index, label in enumerate(labels):
                for group in grouped:
                    # Se os dias são iguais
                    if label == group[0]:
                        datasets[-1]['data'][index] += group[1]

        cards[2]['value']['data']['labels'] = [date.strftime('%d/%m') for date in labels]
        cards[2]['value']['data']['datasets'] = datasets

        # 3º: Montando as informações das unidades escolares:
        for school_unit in my_school_units:
            cards[3]['value'][school_unit.name] = []
            {'students': 0, 'teachers': 0, 'classes': 0}

            cards[3]['value'][school_unit.name].append({'label': 'Quantidade de Alunos', 'value': school_unit.get_students().count()})
            cards[3]['value'][school_unit.name].append({'label': 'Quantidade de Professores', 'value': school_unit.get_teachers().count()})
            cards[3]['value'][school_unit.name].append({'label': 'Quantidade de Turmas', 'value': school_unit.get_disciplines().count()})


        # 4º: Montando a quantidade de aulas ocorrendo no momento:
        my_disciplines = current_profile_user.get_my_disciplines(columns=[ClassesDiscipline.id]).all()

        now_datetime = datetime.now()
        now = now_datetime.date()
        inf_hour = (datetime.now() - timedelta(minutes=180)).strftime('%H:%M:%S')
        sup_hour = (datetime.now() + timedelta(minutes=180)).strftime('%H:%M:%S')

        logger.debug("Varrendo aulas ocorrendo em: {}".format([now, inf_hour, sup_hour]))

        """
        or_(
        and_(LessonClassesDiscipline.begin > now), 
        and_(LessonClassesDiscipline.begin == now, LessonClassesDiscipline.hour > inf_hour, LessonClassesDiscipline.hour < sup_hour),
        ),
        """
        lessons = db.session.query(LessonClassesDiscipline, Lesson, ClassesDiscipline, User)\
            .filter(
                ClassesDiscipline.id.in_(my_disciplines),
                LessonClassesDiscipline.classes_discipline_id == ClassesDiscipline.id,
                LessonClassesDiscipline.hour != None,
                LessonClassesDiscipline.begin != None,
                LessonClassesDiscipline.lesson_id == Lesson.id,
                LessonClassesDiscipline.begin == now, 
                LessonClassesDiscipline.hour > inf_hour, 
                Lesson.active(),
                TeacherDiscipline.classes_discipline_id == ClassesDiscipline.id,
                TeacherDiscipline.teacher_id == ProfileUser.id,
                ProfileUser.user_id == User.id
            )\
            .order_by(desc(LessonClassesDiscipline.begin))\
            .order_by(desc(LessonClassesDiscipline.hour))\
            .all()

        hour = (now - timedelta(minutes=10)).strftime('%H:%M:%S')


        for lesson_classes_discipline, lesson, classes_discipline, user in lessons:
            element = {}

            element['school_class_name'] = classes_discipline.school_class.name
            element['school_discipline_name'] = classes_discipline.school_class.name
            element['teacher_name'] = user.name if user.name else user.email
            element['lesson_name'] = lesson.name
            element['lesson_id'] = lesson.id
            
            lesson_datetime = '{}T{}Z'.format(lesson_classes_discipline.begin, lesson_classes_discipline.hour)

            diff = (now_datetime - parse_datetime(lesson_datetime)).total_seconds() / 60.0

            if diff < 10 and diff > 0: element['__init__'] = True
            if diff < 0 and diff > -10: element['__init__'] = True

            #element.append({'label': 'Hora', 'value': '{} {}'.format(lesson_classes_discipline.begin, lesson_classes_discipline.hour)})

            cards[4]['value'].append(element)
        
        
        return cards
            

    @classmethod
    def dashboard_engagement_classes(cls, *args, **kwargs) -> List:
        """
        Função para fazer o cálculo do engajamento das turmas que um dado usuário tem acesso.
        """
        from app.models import StudentLessonClassesDiscipline, LessonClassesDiscipline, ClassesDiscipline, serialize_return, History
        
        TYPE = 'dashboard_engagement_classes'.upper()
        
        _text =\
        """
        SELECT id as classes_discipline_id, SUM(minutes) FROM
                (SELECT q1.id as id, (q1.value::json->'minutes')::text::int as minutes FROM 
                    (SELECT cd.id as id, j.value as value
                    FROM student_lesson_classes_discipline as s, lesson_classes_discipline as lc, classes_discipline as cd
                    JOIN json_each_text(s.meta_attr) j ON true
                    WHERE s.lesson_classes_discipline_id = lc.id AND lc.classes_discipline_id = cd.id AND cd.id = ANY(:ids) 
                    ORDER BY 1) as q1
                WHERE (value::json -> 'minutes')::text != 'null') as q2
                GROUP BY id;
        """
        current_profile_user:cls = session['profile_user']

        my_disciplines = current_profile_user.get_my_disciplines(columns=[ClassesDiscipline.id]).all()
        
        if not len(my_disciplines): return []

        results = db.session.execute(text(_text), {'ids': [tup[0] for tup in my_disciplines]}).fetchall()

        my_disciplines = current_profile_user.get_my_disciplines().all()

        for discipline in my_disciplines:
            discipline.minutes = 0

            for tup in results:
                if tup[0] == discipline.id:
                    discipline.minutes = tup[1] 
        
        data:list = []

        for discipline in my_disciplines:
            data.append({
                'label': '{}'.format(discipline.classe_discipline_name),
                'value': discipline.minutes,
                'id': discipline.id})
        
        # Fazendo a ordenação descrecente
        data.sort(key=lambda element: element['value'], reverse = True)

        # Listando a última iteração que fizemos nessa função
        last_history = History.query.filter(History.created_by == current_profile_user.id, History.type == TYPE)\
            .order_by(desc(History.created_at))\
            .limit(1)\
            .first()
        
        # Adicionando a nova história:
        history = History(type=TYPE, created_by=current_profile_user.id, meta_attr=data)
        history.add()

        # Definindo a evolução de posição das classes no quesito engajamento
        for current_index, current_element in enumerate(data):
            current_element['grow_up'] = '0'

            if last_history and last_history.meta_attr:
                for last_index, last_element in enumerate(last_history.meta_attr):
                    if not current_element['id'] == last_element['id']: continue

                    if current_index > last_index: current_element['grow_up'] = '+ {}'.format(current_index - last_index)
                    elif last_index > current_index: current_element['grow_up'] = '- {}'.format(last_index - current_index)
        
        
        return data
        


    @classmethod
    def dashboard_engagement_school_units(cls, *args, **kwargs) -> List:
        """
        Função para fazer o cálculo do engajamento das unidade escolares que o usuário tem acesso.
        """
        from app.models import StudentLessonClassesDiscipline, LessonClassesDiscipline, ClassesDiscipline, serialize_return, History
        
        TYPE = 'dashboard_engagement_school_units'.upper()

        _text =\
        """
        SELECT id as classes_discipline_id, SUM(minutes) FROM
                (SELECT q1.id as id, (q1.value::json->'minutes')::text::int as minutes FROM 
                    (SELECT cd.id as id, j.value as value
                    FROM student_lesson_classes_discipline as s, lesson_classes_discipline as lc, classes_discipline as cd
                    JOIN json_each_text(s.meta_attr) j ON true
                    WHERE s.lesson_classes_discipline_id = lc.id AND lc.classes_discipline_id = cd.id AND cd.id = ANY(:ids) 
                    ORDER BY 1) as q1
                WHERE (value::json -> 'minutes')::text != 'null') as q2
                GROUP BY id;
        """
        current_profile_user:cls = session['profile_user']

        if not (current_profile_user.is_school_net_administrator() or current_profile_user.is_administrator()):
            return []

        my_disciplines = current_profile_user.get_my_disciplines(columns=[ClassesDiscipline.id]).all()
        
        if not len(my_disciplines): return []

        results = db.session.execute(text(_text), {'ids': [tup[0] for tup in my_disciplines]}).fetchall()

        my_disciplines = current_profile_user.get_my_disciplines().all()
        my_school_units = current_profile_user.get_my_school_units().all()

        for discipline in my_disciplines:
            discipline.minutes = 0

            for tup in results:
                if tup[0] == discipline.id:
                    discipline.minutes = tup[1] 
        
        # Montando o dicionário de unidades escolares:
        school_units_dict = {discipline.id : discipline.school_unit.id for discipline in my_disciplines}
        data = {school_unit.id: {'label': school_unit.name, 'value': 0, 'id': school_unit.id} for school_unit in my_school_units}
        
        for discipline in my_disciplines:
            data[discipline.school_unit.id]['value'] += discipline.minutes

        data = list(data.values())

        # Fazendo a ordenação descrecente
        data.sort(key=lambda element: element['value'], reverse = True)

        # Listando a última iteração que fizemos nessa função
        last_history = History.query.filter(History.created_by == current_profile_user.id, History.type == TYPE)\
            .order_by(desc(History.created_at))\
            .limit(1)\
            .first()
        
        # Adicionando a nova história:
        history = History(type=TYPE, created_by=current_profile_user.id, meta_attr=data)
        history.add()

        # Definindo a evolução de posição das classes no quesito engajamento
        for current_index, current_element in enumerate(data):
            current_element['grow_up'] = '0'

            if last_history and last_history.meta_attr:
                for last_index, last_element in enumerate(last_history.meta_attr):
                    if not current_element['id'] == last_element['id']: continue

                    if current_index > last_index: current_element['grow_up'] = '+ {}'.format(current_index - last_index)
                    elif last_index > current_index: current_element['grow_up'] = '- {}'.format(last_index - current_index)
        
        return data
        

    
