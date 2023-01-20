from app import db, session, config
from app.utils import logger, all_subclasses, ApiException, mount_query, parse_datetime, parse_date, parse_datetime, serialize_return, get_attribute_values
from app.utils.models import Super
from uuid import uuid4, uuid1
from datetime import datetime, date, timedelta, timezone
import pytz
from pprint import pprint, pformat
from functools import reduce


from flask import has_request_context
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import validates, Query
from sqlalchemy import and_, or_, asc, desc, func
from typing import List, Dict



"""
Classes de Domínio da Aplicação
"""
class Domain(Super):
    id          = db.Column(db.String(40), primary_key=True, default=lambda new_id: str(uuid1()))
    created_at  = db.Column(db.DateTime(), nullable=False, default=lambda new_datetime: datetime.now())
    meta_attr   = db.Column(db.JSON(), nullable=True, default={})


    __attributes_ilike__    = ['name']
    __without_attrs__       = []

    @declared_attr
    def created_by(cls):
        return db.Column(db.String(40), nullable=False) # db.ForeignKey('profile_user.id'),

    
    def __init__(self, *args, **kwargs):
        self.populate(kwargs, *args)
    

    @classmethod
    def columns(cls, *args, **kwargs) -> list:
        from sqlalchemy import inspect
        mapper = inspect(cls)        
        return [attr.key for attr in mapper.attrs]


    @classmethod
    def attributes(cls, *args, **kwargs) -> list:
        return {key: cls.__table__.columns.get(key, None) for key in cls.columns()}


    @classmethod
    def find(cls, *args, **kwargs) -> Query:
        return cls.query.filter(*args)

    
    @classmethod
    def exists(cls,
        *args,
        **kwargs) -> bool:
        
        return cls.query.filter_by(**kwargs).first() is not None


    @classmethod
    def create(cls, *args, **kwargs):
        user_creator = session['profile_user'].id

        logger.info("Usuário '{}' criando: '{}'".format(user_creator, cls))
        kwargs.pop('created_by', None)
        kwargs.pop('created_at', None)
        
        new_object = cls(
            id=kwargs.pop('id', str(uuid1())), 
            created_by=user_creator, 
            created_at=datetime.now()
            )

        columns = cls.columns()

        logger.debug("Dados sendo salvos: '{}': '{}'\n".format(cls, kwargs))
        
        for key, value in kwargs.items():
            if key not in columns: continue
            setattr(new_object, key, value)
        
        logger.debug("Objecto Final: '{}': '{}'\n".format(cls, new_object.to_dict()))

        new_object.add()

        db.session.flush()

        return new_object


    @classmethod
    def update(cls, *args, **kwargs):
        model = cls.query.filter_by(id=kwargs['id']).first()

        # Tratando as vezes em que o identificador é gerado nos clientes:
        if not model:
            return cls.create(*args, **kwargs)

        if hasattr(model, 'is_system') and model.is_system:
            logger.warning("Modelo de Sistêma. Não é possível atualizá-lo.")
            return model
        
        kwargs.pop('id', None)
        kwargs.pop('created_by', None)
        kwargs.pop('created_at', None)
        kwargs.pop('deleted_by', None)
        kwargs.pop('deleted_at', None)

        columns = cls.columns()

        logger.debug("Dados sendo salvos: '{}': '{}'\n".format(cls, kwargs))

        for key, value in kwargs.items():
            if key not in columns: continue
            setattr(model, key, value)
        
        logger.debug("Objecto Final: '{}': '{}'\n".format(cls, model.to_dict()))

        return model


    @classmethod
    def remove(cls, *args, **kwargs):
        if 'id' in kwargs: 
            model = cls.query.filter_by(id=kwargs['id']).first()
            db.session.delete(model)
            return model

        else:
            models = cls.query.filter_by(**kwargs).all()

            for model in models:
                logger.warning("Deletando: {}".format(model))
                db.session.delete(model)
            
            return models


    @classmethod
    def q(cls, value:str, *args, **kwargs) -> List:
        from sqlalchemy import or_, inspect
        from sqlalchemy.types import Integer, Float, Boolean, DateTime, Date, String
        
        columns = cls.columns()

        # Escolhendo as colunas alvo:
        #columns = [getattr(cls, column).property.columns[0].type for column in cls.c] #if getattr(cls, column).property.columns[0].type]
        columns = [column.name for column in cls.__table__.columns if isinstance(column.type, String)] #if getattr(cls, column).property.columns[0].type]

        query = [getattr(cls, column).ilike("%%%s%%" % value) for column in columns]
        return [or_(*query)]


    @classmethod
    def duplicate(cls, *args, **kwargs):
        model = cls.query.filter_by(id=kwargs['id']).first()

        if not model:
            return ApiException("Verifique o atributo 'id' para essa ação. Não existe um '{}' para '{}'".format(cls.__name__, kwargs['id']))

        if hasattr(model, 'is_system') and model.is_system:
            logger.warning("Modelo de Sistema. Não é possível duplicá-lo.")
            return model

        new_model = cls(**model.to_dict())
        new_model.id = str(uuid1())
        new_model.created_by = session['user']['id']
        new_model.created_at = datetime.now()
        new_model.meta_attr = {'duplicated_from': model.id}

        if hasattr(new_model, 'name'):
            new_model.name = new_model.name + ' - Duplicado!'

        logger.debug("Objeto duplicado: '{}': '{}'\n".format(cls.__name__, new_model.to_dict()))

        new_model.add()

        return new_model

    
    def add(self, *args, **kwargs):
        """
        Função para adicionar um dado objeto à sessão.
        """
        from app import db
        logger.debug("Adicionando: '{}'".format(self))
        db.session.add(self)


    def validate(self, *args, **kwargs):
       pass     


    def populate(self, data:dict, *args, **kwargs):
        """
        Função para popular os atributos de um objeto
        """
        self_attributes = self.columns()

        for key, value in data.items():
            if key not in self_attributes: continue
            setattr(self, key, value)


    @staticmethod
    def get_attribute_values(data:[], attribute:str='id', *args, **kwargs) -> list:
        select_data:list = []

        for element in data:
            if isinstance(element, dict):
                select_data.append(element[attribute])
            
            else:
                select_data.append(getattr(element, attribute))

        return select_data



class LogicalDomain(Domain):
    status      = db.Column(db.Integer(), default=1)
    deleted_at  = db.Column(db.DateTime(), nullable=True)


    @declared_attr
    def deleted_by(cls):
        return db.Column(db.String(40), nullable=True) # db.ForeignKey('profile_user.id'),


    @classmethod
    def remove(cls, *args, **kwargs) -> list:
        user_deletor = session['profile_user'].id

        query = mount_query(kwargs, cls)
        
        models = cls.query.filter(*query).all()
        
        logger.debug("Executando remoção lógica nos Objetos:\n{}".format(pformat(models)))

        for model in models:
            model.status = ModelStatus.DELETED.value
            model.deleted_by = kwargs.pop('created_by', user_deletor)
            model.deleted_at = datetime.now()

        return models
    
    
    @classmethod
    def exists(cls,
        status=True,
        *args,
        **kwargs) -> bool:

        if not has_request_context():
            return None

        if status: 
            kwargs['status'] = ModelStatus.ACTIVE.value
        
        return cls.query.filter_by(**kwargs).first() is not None


    @classmethod
    def get(cls, 
        filter:List=[], 
        cursor_function:str='first', 
        with_status=True,
        *args, 
        **kwargs):
        
        if len(filter):
            if with_status: filter.append(cls.status == ModelStatus.ACTIVE.value)
            return getattr(cls.query.filter(*filter), cursor_function)()

        if with_status: kwargs['status'] = ModelStatus.ACTIVE.value
        
        return getattr(cls.query.filter_by(**kwargs), cursor_function)()


    @classmethod
    def active(cls, *args, **kwargs):
        return cls.status != ModelStatus.DELETED.value


    @staticmethod
    def getAll(cls, data:[], *args, **kwargs) -> List:
        return cls.get(data, cursor_function='all', *args, **kwargs)



class ViewDomain(Super):
    pass



class AccessibleDomain(LogicalDomain):
    pass



class Attachment(db.Model, LogicalDomain):
    # Modelo de Administração do Sistema
    name        = db.Column(db.String(100), nullable=False)
    cdn_link    = db.Column(db.TEXT(), nullable=False)
    format      = db.Column(db.String(100), nullable=False)
    validate    = db.Column(db.Integer, nullable=True) # Tempo de Validade do Anexo
    size        = db.Column(db.Float, nullable=False)


    @property
    def is_video(self):
        return 'webm' in self.format or 'mp4' in self.format


    @classmethod
    def is_pdf(cls):
        return cls.format.in_("application/pdf", "pdf") 


    @classmethod
    def is_doc(cls):
        return cls.format.in_(["application/pdf", "pdf", "doc", "docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]) 


    def after_remove(self, *args, **kwargs):

        # Removendo o anexo do seus respectivos relacionamentos:
        LibraryAttachment.query.filter(LibraryAttachment.attachment_id == self.id).delete()
        ActivityAttachment.query.filter(ActivityAttachment.attachment_id == self.id).delete()
        LessonAttachment.query.filter(LessonAttachment.attachment_id == self.id).delete()

        from os import remove

        logger.debug("Apagando arquivo: {}".format(self.cdn_link))

        try:
            remove(self.cdn_link) 
        except Exception as err:
            logger.error('Não foi possível deletar o arquivo no FS: {}'.format(self.cdn_link))
            logger.exception(err)
               
   
    @classmethod
    def library_checked(cls, *args, **kwargs) -> Query:
        return db.session.query(cls) \
                    .filter(cls.active(), cls.is_doc()) \
                    .order_by(asc(cls.name))


    @classmethod
    def after_library_checked(cls, models:List, *args, **kwargs) -> List:
        
        ids = Domain.get_attribute_values(models)

        library_attachments = LibraryAttachment.query.filter(
            LibraryAttachment.library_id == kwargs['library_id'],
            LibraryAttachment.attachment_id.in_(ids)
        )

        library_attachments = library_attachments.all()
        
        for model in models:
            model['__checked__']    = False
            
            for library_attachment in library_attachments:
                if library_attachment.attachment_id == model['id']: model['__checked__'] = True

        return models


    @classmethod
    def activity_checked(cls, *args, **kwargs) -> Query:
        return db.session.query(cls) \
                    .filter(cls.active(), cls.created_by == session['profile_user'].id) \
                    .order_by(asc(cls.name))


    @classmethod
    def after_activity_checked(cls, models:List, *args, **kwargs) -> List:
        ids = Domain.get_attribute_values(models)

        attachments = ActivityAttachment.query.filter(
            ActivityAttachment.activity_id == kwargs['activity_id'],
            ActivityAttachment.attachment_id.in_(ids)
        )

        attachments = attachments.all()
        
        for model in models:
            model['__checked__']    = False
            
            for attachment in attachments:
                if attachment.attachment_id == model['id']: model['__checked__'] = True

        return models


    @classmethod
    def lesson_checked(cls, *args, **kwargs) -> Query:
        return db.session.query(cls) \
                    .filter(cls.active(), cls.created_by == session['profile_user'].id) \
                    .order_by(desc(cls.created_at))\
                    .order_by(asc(cls.name))


    @classmethod
    def after_lesson_checked(cls, models:List, *args, **kwargs) -> List:
        ids = Domain.get_attribute_values(models)

        lesson_attachments = LessonAttachment.query.filter(
            LessonAttachment.lesson_id == kwargs['lesson_id'],
            LessonAttachment.attachment_id.in_(ids)
        )

        lesson_attachments = lesson_attachments.all()
        
        for model in models:
            model['__checked__']    = False
            model['__main_attachment__'] = False
            model['__can_update_main_attachment__'] = False

            for lesson_attachment in lesson_attachments:
                if lesson_attachment.attachment_id == model['id']: 
                    model['__checked__'] = True
                    model['__can_update_main_attachment__'] = True
                    model['lesson_attachment_id'] = lesson_attachment.id
                    
                    if lesson_attachment.main_attachment:
                        model['__main_attachment__'] = True
                    

        return models


    @classmethod
    def report_attachment_use(cls, *args, **kwargs) -> Query:
        """
        Função para listar a utilização corrente de armazenamento
        """
        profile_user:ProfileUser = session['profile_user']

        my_school_units = profile_user.get_my_school_units().all()
        my_school_units = Domain.get_attribute_values(my_school_units)
        
        profile_users_id = db.session.query(SchoolUnitProfileUsers.profile_user_id).filter(SchoolUnitProfileUsers.school_unit_id.in_(my_school_units)).all()
        profile_users_id = [tup[0] for tup in profile_users_id]
        
        return Attachment.query.filter(Attachment.created_by.in_(profile_users_id), Attachment.active())


    @classmethod
    def after_report_attachment_use(cls, models:List, *args, **kwargs) -> Dict:
        import operator
        
        response = dict()

        # Montando o campo de valores totais:
        response['total'] = reduce(operator.add, map(lambda object: object['size'], models))
        response['total_format'] = {object['format']: {'total': 0, 'format': object['format'], 'objects': []} for object in models}
        
        for model in models:
            response['total_format'][model['format']]['total'] += model['size']
            response['total_format'][model['format']]['objects'].append({'id': model['id'], 'name': model['name']})
        
        response['total_format'] = list(response['total_format'].values())

        # Montando o campo dos últimos 15 dias de informações de volume:
        now = datetime.now()

        X = [(now - timedelta(days=i)).date() for i in range(15)]
        y = [0 for i in range(15)]

        for index, _date in enumerate(X):
            for model in models:
                if model['created_at'].split('T')[0] == str(_date):
                    y[index] += model['size']
        
        X.reverse()
        y.reverse()
        X = [_date.strftime('%d/%m/%y') for _date in X]

        response['total_graphic_15'] = [X,y]

        return response



class Newsletter(db.Model, LogicalDomain):
    title                   = db.Column(db.String(150), nullable=False)
    description             = db.Column(db.String(255), nullable=False)


    @classmethod
    def before_create(cls, *args, **kwargs):
        if not kwargs['profile_users'] or not len(kwargs['profile_users']):
            raise ApiException("Verifique o grupo de Usuários para a criação do informativo.")


    def after_upsert(self, *args, **kwargs):
        
        """
        Adicionando o informativo para os usuários que devem ter essa informação:
        """
        if kwargs.get('profile_users', None):
            for profile_user in kwargs['profile_users']:
                NewsletterProfileUser.create(newsletter_id=self.id, profile_user_id=profile_user)

            # Criando também para você mesmo:
            NewsletterProfileUser.create(newsletter_id=self.id, profile_user_id=session['profile_user'].id)

    
    @classmethod
    def list_my_newsletter(cls, *args, **kwargs) -> Query:
        return cls.query.filter(
            NewsletterProfileUser.profile_user_id == session['profile_user'].id,
            NewsletterProfileUser.newsletter_id == cls.id,
            cls.active()
        )

    

class NewsletterProfileUser(db.Model, Domain):
    newsletter_id       = db.Column(db.String(36), db.ForeignKey('newsletter.id'), nullable=False)
    profile_user_id     = db.Column(db.String(36), db.ForeignKey('profile_user.id'), nullable=False)


    @classmethod
    def after_find(cls, models:List, *args, **kwargs):
        objects = Newsletter.query.filter(Newsletter.id.in_(Domain.get_attribute_values(models, 'newsletter_id'))).all()

        for model in models:
            for object in objects:
                if model['newsletter_id'] != object.id: continue
                model['newsletter'] = object.to_dict()



class TypeParameter(db.Model, LogicalDomain):
    name                    = db.Column(db.String(150), nullable=False)
    description             = db.Column(db.String(255), nullable=True)


    @validates('name')
    def validate_name(self, key, value):
        if TypeParameter.exists(name=value):
            raise ApiException("Verifique a validade do Tipo do Parâmetro. O nome '{}' já existe.".format(value))
        return value



class Parameters(db.Model, LogicalDomain):
    name                    = db.Column(db.String(150), nullable=False)
    description             = db.Column(db.String(255), nullable=True)
    type_parameter_id       = db.Column(db.String(36), db.ForeignKey('type_parameter.id'), nullable=False)


"""
Modelos de Mensagem
"""
class Message(db.Model, LogicalDomain):
    title                   = db.Column(db.String(150), nullable=False)
    description             = db.Column(db.String(255), nullable=True)
    to                      = db.Column(db.String(36), db.ForeignKey('profile_user.id'), nullable=False)
    lesson_id               = db.Column(db.String(36), db.ForeignKey('lesson.id'), nullable=True)
    type                    = db.Column(db.String(150), nullable=True)


    @classmethod
    def after_find(cls, models:List, *args, **kwargs) -> List:
        # Listando os usuários que me enviaram essa mensagem
        from app.models.profile_user import STUDENTS_ID

        ids = Domain.get_attribute_values(models, 'created_by')

        profile_users = ProfileUser.get([ProfileUser.id.in_(ids)], with_status=False, cursor_function='all')
        profile_users = [object.to_dict() for object in profile_users]

        ProfileUser.after_find(profile_users)
        
        for model in models:
            for profile_user in profile_users:
                if model['created_by'] != profile_user['id']: continue

                _owner = profile_user['profile']['name'] if profile_user['profile']['name'] else profile_user['user']['email']
                model['owner'] = _owner

        return models


    @classmethod
    def before_upsert(cls, *args, **kwargs):
        # Casos em que estamos criando uma Mensagem:
        if not kwargs.get('status', None): kwargs['status'] = ModelStatus.NOT_READ.value
        if not kwargs.get('type', None): kwargs['type'] = 'NORMAL'

        if not ProfileUser.query.filter_by(id=kwargs['to']).first():
            target = User.query.filter_by(email=kwargs['to']).first()
            
            if not target:
                raise ApiException("Verifique a validade do remetente.")
            
       
        return kwargs


    @classmethod
    def check_questions_to_teacher(cls, *args, **kwargs) -> Query:
        return Message.query.filter(Message.lesson_id == kwargs['lesson_id'], Message.to == kwargs['to'], Message.status != ModelStatus.DELETED.value)\
            .order_by(desc(Message.created_at))\

    
    @classmethod
    def after_check_questions_to_teacher(cls, models, *args, **kwargs) -> List:

        ids = Domain.get_attribute_values(models, 'created_by')

        profile_users = ProfileUser.get([ProfileUser.id.in_(ids)], with_status=False, cursor_function='all')
        profile_users = [object.to_dict() for object in profile_users]

        ProfileUser.after_find(profile_users)
        
        for model in models:
            for profile_user in profile_users:
                if model['created_by'] != profile_user['id']: continue
                model['__created_by'] = profile_user['user']['email'] + " - " + profile_user['profile']['name'] 


    @classmethod
    def check_questions_to_student(cls, *args, **kwargs) -> Query:
        return Message.query.filter(Message.lesson_id == kwargs['lesson_id'], Message.to == kwargs['to'], Message.status != ModelStatus.DELETED.value)\
            .order_by(desc(Message.created_at))
    

    @classmethod
    def after_check_questions_to_student(cls, models, *args, **kwargs) -> List:
        cls.after_check_questions_to_teacher(models, *args, **kwargs)
        

"""
Modelos de Anotação de um Usuário em uma Aula
"""
class Annotation(db.Model, LogicalDomain):
    title                   = db.Column(db.String(150), nullable=False)
    description             = db.Column(db.String(255), nullable=False)
    
    lesson_classes_discipline_id    = db.Column(db.String(36), db.ForeignKey('lesson_classes_discipline.id'), nullable=False)
    student_id                      = db.Column(db.String(36), db.ForeignKey('student_discipline.id'), nullable=False)





""" 
Classes Relacionadas aos Modelos de Atividade:
"""
class Activity(db.Model, LogicalDomain):
    name        = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    begin       = db.Column(db.Date(), nullable=True)
    end         = db.Column(db.Date(), nullable=True)
    obrigatory  = db.Column(db.Boolean(), nullable=False, default=False)
    class_id    = db.Column(db.String(36), db.ForeignKey('classes_discipline.id'), nullable=False)


    @validates('begin')
    def validate_begin(self, key, value):
        if value is None:
            raise ApiException("Verifique a validade do atributo 'begin'. Ele deve ser data ISO-8601.")
        
        value = parse_date(value)
        
        return value


    @validates('end')
    def validate_end(self, key, value):
        if value is None:
            raise ApiException("Verifique a validade do atributo 'end'. Ele deve ser data ISO-8601.")
        
        value = parse_date(value)
        
        return value


    @classmethod
    def before_find(cls, *args, **kwargs) -> List:
        """
        Retornando uma query para extensão na consulta. Só consultar as atividades ao qual o Usuário pode visualizar.
        """
        current_profile_user:ProfileUser = session['profile_user']

        my_disciplines = current_profile_user.get_my_disciplines().all()
        my_disciplines = Domain.get_attribute_values(my_disciplines)

        #if current_profile_user.is_student(): 
        #    _filter.extend([StudentDiscipline.student_id == current_profile_user.id, StudentDiscipline.classes_discipline_id == ClassesDiscipline.id])

        #else:
        #    _filter.extend([TeacherDiscipline.classes_discipline_id == ClassesDiscipline.id, TeacherDiscipline.teacher_id == current_profile_user.id])
        _filter = [ClassesDiscipline.id.in_(my_disciplines)]
        _filter.append(Activity.class_id == ClassesDiscipline.id)   

        return _filter


    @classmethod
    def after_find(cls, models:List, *args, **kwargs) -> List:
        ids = Domain.get_attribute_values(models, 'class_id')

        # Verificando a validade da atividade:
        now = datetime.now()

        for model in models:
            model['__disabled__']  = False

            if model['end'] and parse_datetime(model['end']).date() < now.date():
                model['__disabled__'] = True


        # Selecionando a disciplina dos modelos de Atividade
        objects = db.session\
            .query(ClassesDiscipline.id, SchoolClass.name, SchoolDiscipline.name, SchoolGrade.name, SchoolUnit.name)\
            .filter(
                ClassesDiscipline.id.in_(ids),
                ClassesDiscipline.school_class_id           == SchoolClass.id,
                ClassesDiscipline.discipline_period_id      == DisciplinePeriod.id,
                DisciplinePeriod.school_period_id           == SchoolPeriod.id,
                DisciplinePeriod.discipline_grade_id        == DisciplineGrade.id,
                DisciplineGrade.school_discipline_id        == SchoolDiscipline.id,
                DisciplineGrade.unit_grade_id               == UnitGrade.id,
                UnitGrade.school_grade_id                   == SchoolGrade.id,
                UnitGrade.school_unit_id                    == SchoolUnit.id,
            )\
        
        objects = objects.all()
        
        for model in models:
            for tup in objects:
                if tup[0] != model['class_id']: continue
                model['class'] = '{} - {} - {} - {}'.format(*tup[1:])

        # Caso o usuário seja um aluno e solicite a informação agrupada por classe
        if kwargs.get('tree', False) and session['profile_user'].is_student():
            
            # Carregando as informações de atividade que o usuário está executando no momento
            objects = db.session.query(ActivityStudent)\
                .filter(ActivityStudent.student_id == session['profile_user'].id, ActivityStudent.activity_id.in_(Domain.get_attribute_values(models, 'id'))).all()

            for model in models:
                for object in objects:
                    if object.activity_id != model['id']: continue
                    model['ActivityStudent'] = object.to_dict()

            # Montando a árvore alinhada com o identificador da classe desse aluno
            Tree = {}

            for model in models:
                if model['class'] not in Tree: Tree[model['class']] = []
                Tree[model['class']].append(model)
           
            return [Tree]

        return models


    @classmethod
    def exercise_checked(cls, *args, **kwargs) -> Query:
        return cls.query.filter(cls.active())


    @classmethod
    def after_exercise_checked(cls, models:List, *args, **kwargs) -> List:
        ids = Domain.get_attribute_values(models)

        activity_exercises = ActivityExercise.query.filter(
            ActivityExercise.exercise_id == kwargs['exercise_id'],
            ActivityExercise.activity_id.in_(ids)
        )

        activity_exercises = activity_exercises.all()

        for main_object in models:
            main_object['__checked__'] = False
            for activity_exercise in activity_exercises:
                if activity_exercise.activity_id != main_object['id']: continue
                main_object['__checked__'] = True
                main_object['rate'] = activity_exercise.rate if activity_exercise.rate is None else float(activity_exercise.rate)
                main_object['activity_exercise_id'] = activity_exercise.id

        pprint(models)

        return models

    
    @classmethod
    def activities_to_start(cls, *args, **kwargs) -> Query:
        
        my_disciplines = session['profile_user'].get_my_disciplines().all()
        now = datetime.now().date()

        return db.session.query(cls, ClassesDiscipline)\
            .filter(
                cls.begin <= now,
                cls.end  >= now,
                ClassesDiscipline.id == cls.class_id,
                ClassesDiscipline.id.in_(Domain.get_attribute_values(my_disciplines)))\
            .order_by(asc(cls.name))\

    
    @classmethod
    def after_activities_to_start(cls, models:List, *args, **kwargs) -> List:
        classes_discipline = [object[1] for object in models]
        classes_discipline = ClassesDiscipline.after_find(classes_discipline)

        models = [object[0] for object in models]
                
        data:list = []

        ids = Domain.get_attribute_values(models, 'id')

        for main_object, classes_discipline in zip(models, classes_discipline):
            main_object['classes_discipline'] = classes_discipline
            data.append(main_object)

        models = data

        for model in models:
            model['qtd_students_do_exercise'] = ActivityStudent.query.filter(ActivityStudent.activity_id == model['id'], ActivityStudent.active()).count()
            model['qtd_students'] = StudentDiscipline.query.filter(StudentDiscipline.classes_discipline_id == model['classes_discipline']['id']).count()

            model['progress'] = (model['qtd_students_do_exercise']/model['qtd_students']) * 100

        return models



class ActivityStudent(db.Model, LogicalDomain):
    activity_id         = db.Column(db.String(36), db.ForeignKey('activity.id'), nullable=False)
    student_id          = db.Column(db.String(36), db.ForeignKey('profile_user.id'), nullable=False)
    begin               = db.Column(db.DateTime(), nullable=False)
    end                 = db.Column(db.DateTime(), nullable=True)
    progress            = db.Column(db.Float(), nullable=True)
    rate                = db.Column(db.Float(), nullable=True)


    @validates('begin')
    def validate_begin(self, key, value):
        if value is None:
            raise ApiException("Verifique a validade do atributo 'begin'. Ele deve ser data ISO-8601.")
        
        value = parse_datetime(value)
        
        return value
    

    @validates('end')
    def validate_end(self, key, value):
        if value is None: 
            return None
        
        value = parse_datetime(value)
        
        return value
    

    @classmethod
    def before_upsert(cls, *args, **kwargs):
        activities = ActivityStudent.get(filter=[ActivityStudent.activity_id == kwargs['activity_id'], ActivityStudent.student_id == kwargs['student_id']])

        if activities: 
            #raise ApiException("Essa Atividade já foi iniciada.")
            kwargs['id'] = activities.id
            return kwargs


    @classmethod
    def after_find(cls, models:List, *args, **kwargs):
        ids = Domain.get_attribute_values(models, 'id')

        # Selecionando a disciplina dos modelos de Atividade
        objects = db.session\
            .query(cls.id, User)\
            .filter(
                cls.id.in_(ids),
                cls.created_by == ProfileUser.id,
                ProfileUser.user_id == User.id
            )\
        
        objects = objects.all()

        for model in models:
            for tup in objects:
                if tup[0] != model['id']: continue
                model['User'] = tup[1].to_dict()



class ActivityAttachment(db.Model, Domain):
    activity_id         = db.Column(db.String(36), db.ForeignKey('activity.id'), nullable=False)
    attachment_id       = db.Column(db.String(36), db.ForeignKey('attachment.id'), nullable=False) # Modelo de anexo


    @classmethod
    def after_find(cls, models:List, *args, **kwargs):
        ids = Domain.get_attribute_values(models, 'id')

        # Selecionando a disciplina dos modelos de Atividade
        objects = db.session\
            .query(ActivityAttachment.id, Activity, Attachment)\
            .filter(
                ActivityAttachment.id.in_(ids),
                ActivityAttachment.attachment_id == Attachment.id,
                ActivityAttachment.activity_id == Activity.id
            )\
        
        objects = objects.all()

        for model in models:
            for tup in objects:
                if tup[0] != model['id']: continue
                model['Activity'] = tup[1].to_dict()
                model['Attachment'] = tup[2].to_dict()



class ActivityStudentAttachment(db.Model, Domain):
    activity_student_id = db.Column(db.String(36), db.ForeignKey('activity_student.id'), nullable=False)
    attachment_id       = db.Column(db.String(36), db.ForeignKey('attachment.id'), nullable=False) # Modelo de anexo


    @classmethod
    def before_find(cls, *args, **kwargs) -> List:
        if kwargs.get('activity_id', None):
            return [
                ActivityStudent.activity_id == kwargs['activity_id'],
                ActivityStudent.id == cls.activity_student_id
            ]
            

    @classmethod
    def after_find(cls, models:List, *args, **kwargs):
        ids = Domain.get_attribute_values(models, 'id')

        # Selecionando a disciplina dos modelos de Atividade
        objects = db.session\
            .query(cls.id, Attachment, User.name, User.email)\
            .filter(
                cls.id.in_(ids),
                cls.attachment_id == Attachment.id,
                cls.created_by == ProfileUser.id,
                ProfileUser.user_id == User.id
            )\
        
        objects = objects.all()

        for model in models:
            for tup in objects:
                if tup[0] != model['id']: continue
                model['Attachment'] = tup[1].to_dict()
                model['user_name'] = tup[2]
                model['user_email'] = tup[3]

        


class Exercise(db.Model, LogicalDomain):
    name        = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(255), nullable=True)


    @classmethod
    def after_find(cls, models:List, *args, **kwargs):
        pprint(models)



class ActivityExercise(db.Model, Domain):
    activity_id         = db.Column(db.String(36), db.ForeignKey('activity.id'), nullable=False)
    exercise_id         = db.Column(db.String(36), db.ForeignKey('exercise.id'), nullable=False) 
    rate                = db.Column(db.DECIMAL(), nullable=True)

    @classmethod
    def before_upsert(cls, *args, **kwargs):
        current_relantionship = ActivityExercise.query.filter_by(activity_id=kwargs['activity_id'], exercise_id=kwargs['exercise_id']).first()
        
        if not current_relantionship or current_relantionship.id == kwargs['id']: return 

        raise ApiException("Não é possível ter uma atividade atribuída duas vezes à um mesmo exercício.")


    @classmethod
    def list_exercices_to_activity(cls, *args, **kwargs) -> Query:
        return db.session.query(Exercise)\
            .filter(
                ActivityExercise.activity_id == kwargs['activity_id'], 
                ActivityExercise.exercise_id == Exercise.id)


    @classmethod
    def after_list_exercices_to_activity(cls, models:List, *args, **kwargs) -> List:
        
        for exercise in models:
            exercise['itens'] = {}

            itens = db.session.query(ExerciseItem, ExerciseItemChoice).filter(ExerciseItem.exercise_id == exercise['id'], ExerciseItemChoice.exercise_item_id == ExerciseItem.id).all()

            # Adicionando os itens ao exercício
            if len(itens):
                for exercice_item, exercise_item_choince in itens:
                    if exercice_item.id not in exercise['itens']:
                        exercise['itens'][exercice_item.id] = exercice_item.to_dict()
                        exercise['itens'][exercice_item.id]['choices'] = []

                    exercise['itens'][exercice_item.id]['choices'].append(exercise_item_choince.to_dict())

                # Removendo o índice
                exercise['itens'] = list(exercise['itens'].values())


        #from app.utils.tree import get_tree, process_tree

        #Tree = get_tree('Exercícios da Atividade')

        #process_tree(Tree, models)

        #return Tree



class ExerciseItem(db.Model, LogicalDomain):
    name                = db.Column(db.String(255), nullable=False)
    description         = db.Column(db.String(255), nullable=True)
    exercise_id         = db.Column(db.String(36), db.ForeignKey('exercise.id'), nullable=False) 
    order               = db.Column(db.Integer(), nullable=False, default=1)


    @classmethod
    def after_find(cls, models:List, *args, **kwargs) -> List:
        
        # Listando todas as escolhas de cada item
        ids = Domain.get_attribute_values(models)

        choices = ExerciseItemChoice.query.filter(
            ExerciseItemChoice.exercise_item_id.in_(ids),
            ExerciseItemChoice.active()
        )

        choices = choices.all()

        for model in models:
            model['choices'] = [choice.to_dict() for choice in choices if choice.exercise_item_id == model['id']]
        


    def after_upsert(self, *args, **kwargs):
        """
        Verificando se o atributo 'choices' veio definido na requisição. Se sim, vamos criar os 'ExerciseItemChoice' a partir destes
        """
        if kwargs.get('choices', None):
            #pprint(kwargs)

            # 1º Verificando quais identificadores estão na base que não estão na requisição.
            choices_already_saved = ExerciseItemChoice.get([ExerciseItemChoice.exercise_item_id == self.id], cursor_function='all')

            logger.debug("Já persistidos: {}".format(choices_already_saved))

            # 2º Estes objetos serão excluídos.
            ids_choices_already_saved = Domain.get_attribute_values(choices_already_saved)
            ids_choices_request = Domain.get_attribute_values(kwargs['choices'])

            logger.debug("Presentes na requisição: {}".format(ids_choices_request))


            ids_to_remove = list(set(ids_choices_already_saved) - set(ids_choices_request))
            logger.debug("Removendo: {}".format(ids_to_remove))

            if len(ids_to_remove): ExerciseItemChoice.remove(id=ids_to_remove)

            for choice in kwargs['choices']:
                new_choice = ExerciseItemChoice.update(**choice)

        #input("...")



    def after_remove(self, *args, **kwargs):
        """
        Após a deleção de um item do colégio, devemos fazer a remoção das escolhas à ele atribuídas.
        """
        ExerciseItemChoice.remove(exercise_item_id=kwargs['id'])
        


class ExerciseItemChoice(db.Model, LogicalDomain):
    name                        = db.Column(db.String(255), nullable=False)
    description                 = db.Column(db.String(255), nullable=True)
    correct                     = db.Column(db.Boolean, nullable=False)
    exercise_item_id            = db.Column(db.String(36), db.ForeignKey('exercise_item.id'), nullable=False) 



class Library(db.Model, LogicalDomain):
    name        = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(255), nullable=True)


    @classmethod
    def before_find(cls, *args, **kwargs) -> List:
        current_profile_user:ProfileUser = session['profile_user']

        _subquery = current_profile_user.get_my_school_units(columns=[SchoolUnit.id]).subquery()

        return [
            SchoolUnit.id.in_(_subquery),
            UnitGrade.school_unit_id == SchoolUnit.id,
            UnitGradeLibrary.unit_grade_id == UnitGrade.id,
            UnitGradeLibrary.library_id == cls.id
        ]


    @classmethod
    def after_find(cls, models:List, *args, **kwargs) -> List:
        #current_profile_user:ProfileUser = session['profile_user']

        #if not (current_profile_user.is_student() and current_profile_user.is_teacher()):
        return models



class LibraryAttachment(db.Model, Domain):
    library_id          = db.Column(db.String(36), db.ForeignKey('library.id'), nullable=False)
    attachment_id       = db.Column(db.String(36), db.ForeignKey('attachment.id'), nullable=False) # Modelo de anexo


    @classmethod
    def before_find(cls, *args, **kwargs) -> Query:
        current_profile_user:ProfileUser = session['profile_user']

        _subquery = current_profile_user.get_my_school_units(columns=[SchoolUnit.id]).subquery()

        _subquery = db.session.query(cls.id).filter(
            cls.library_id == Library.id,
            cls.attachment_id == Attachment.id,
            UnitGradeLibrary.library_id == Library.id,
            UnitGradeLibrary.unit_grade_id == UnitGrade.id,
            UnitGrade.school_unit_id == SchoolUnit.id,
            SchoolUnit.id.in_(_subquery),
            ).all()

        return [cls.id.in_(_subquery)]
        

        #return cls.query.filter(cls.id.in_(['12s']))

        #input("...") #.order_by(asc(Attachment.name))\


    @classmethod
    def after_find(cls, models:List, *args, **kwargs) -> List:
        
        attachments = Attachment.query.filter(Attachment.id.in_(get_attribute_values(models, 'attachment_id'))).all()
        libraries = Library.query.filter(Library.id.in_(get_attribute_values(models, 'library_id')))
        
        """
        Fazendo a adição da biblioteca e material
        """
        for model in models:
            for attachment in attachments:
                if model['attachment_id'] == attachment.id:
                    model['attachment'] = attachment.to_dict()
            
            for library in libraries:
                if model['library_id'] == library.id:
                    model['library'] = library.to_dict()


        return models



class Lesson(db.Model, LogicalDomain):
    # Modelo de Aula: Professores criam salas de aula
    name        = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    type        = db.Column(db.String(30), nullable=False)


    @classmethod
    def live(cls, *args, **kwargs):
        return cls.type == 'AO_VIVO'
    

    @classmethod
    def lessons_to_start(cls, *args, **kwargs) -> Query:
        
        current_profile_user = session['profile_user']

        # Listando as turmas que possuem aulas cadastradas:

        if current_profile_user.is_student():
            my_disciplines = StudentDiscipline.list_my_disciplines(current_profile_user.id).all()

        else:
            my_disciplines = TeacherDiscipline.list_my_disciplines(current_profile_user.id).all()

        classes_disciplines_id = Domain.get_attribute_values(my_disciplines, 'id')

        return db.session.query(cls, LessonClassesDiscipline, ClassesDiscipline)\
            .join(LessonClassesDiscipline, LessonClassesDiscipline.lesson_id == cls.id)\
            .join(ClassesDiscipline, and_(LessonClassesDiscipline.classes_discipline_id == ClassesDiscipline.id, cls.classes_discipline_id.in_(classes_disciplines_id)))\
            .filter(
                cls.hour!=None,
                )\
            .order_by(asc(cls.begin))\
            .order_by(asc(cls.hour))
       
    
    @classmethod
    def after_lessons_to_start(cls, models:List, *args, **kwargs) -> List:
       
        classes_discipline = [object[2] for object in models]
        classes_discipline = ClassesDiscipline.after_find(classes_discipline)

        models = [(object[0], object[1]) for object in models]
                
        data:list = []

        ids = Domain.get_attribute_values([tup[0] for tup in models], 'id')

        for tup, classes_discipline in zip(models, classes_discipline):
            # Lesson, LessonClassesDiscipline, ClassesDiscipline
            main_object, lesson = tup
            main_object['classes_discipline'] = classes_discipline
            main_object['lesson'] = lesson

            data.append(main_object)

        return data


    @classmethod
    def before_find(cls, *args, **kwargs) -> List:
        """
        Retornando filtros para a extensão da consulta. Só consultar as aulas passíveis de visualização
        """
        current_profile_user:ProfileUser = session['profile_user']

        _filter = []

        if current_profile_user.is_student(): raise Exception()
        
        else:
            if current_profile_user.is_teacher():
                _filter = [
                    TeacherDiscipline.teacher_id == current_profile_user.id,
                    TeacherDiscipline.classes_discipline_id == ClassesDiscipline.id,
                    LessonClassesDiscipline.classes_discipline_id == ClassesDiscipline.id,
                    LessonClassesDiscipline.lesson_id == Lesson.id
                ]
                #

            
            elif current_profile_user.is_school_unit_administrator():
                _filter.extend([   
                    SchoolUnitProfileUsers.profile_user_id == current_profile_user.id,
                    SchoolUnitProfileUsers.school_unit_id == UnitGrade.school_unit_id,
                    DisciplineGrade.unit_grade_id == UnitGrade.id,
                    DisciplinePeriod.discipline_grade_id == DisciplineGrade.id,
                    ClassesDiscipline.discipline_period_id == DisciplinePeriod.id,
                    LessonClassesDiscipline.classes_discipline_id == ClassesDiscipline.id, 
                    LessonClassesDiscipline.lesson_id == Lesson.id
                    ])


            elif current_profile_user.is_school_net_administrator():
                _filter.extend([   
                    SchoolNetAdministrator.profile_user_id == current_profile_user.id,
                    SchoolNetAdministrator.school_net_id == SchoolUnit.school_net_id,
                    UnitGrade.school_unit_id == SchoolUnit.id,
                    DisciplineGrade.unit_grade_id == UnitGrade.id,
                    DisciplinePeriod.discipline_grade_id == DisciplineGrade.id,
                    ClassesDiscipline.discipline_period_id == DisciplinePeriod.id,
                    LessonClassesDiscipline.classes_discipline_id == ClassesDiscipline.id, 
                    LessonClassesDiscipline.lesson_id == Lesson.id
                    ])
                
                       
            elif current_profile_user.is_administrator():
                _filter.extend([ 
                    Administrator.profile_user_id == current_profile_user.id,
                    Administrator.administration_id == Administration.id,
                    AdministrationSchoolNet.administration_id == Administration.id,
                    AdministrationSchoolNet.school_network_id == SchoolNet.id,
                    SchoolUnit.school_net_id == SchoolNet.id,
                    UnitGrade.school_unit_id == SchoolUnit.id,
                    DisciplineGrade.unit_grade_id == UnitGrade.id,
                    DisciplinePeriod.discipline_grade_id == DisciplineGrade.id,
                    ClassesDiscipline.discipline_period_id == DisciplinePeriod.id,
                    LessonClassesDiscipline.classes_discipline_id == ClassesDiscipline.id, 
                    LessonClassesDiscipline.lesson_id == Lesson.id
                    ])

        return _filter


    @classmethod
    def after_find(cls, models:List, *args, **kwargs) -> List:
       
        # Caso o usuário seja um aluno e solicite a informação agrupada por classe
        if kwargs.get('tree', False) and session['profile_user'].is_student():
            # Selecionando a disciplina dos modelos de Atividade
            objects = db.session\
                .query(Lesson.id, SchoolClass.name, SchoolDiscipline.name, SchoolGrade.name, SchoolUnit.name)\
                .filter(
                    Lesson.id.in_(Domain.get_attribute_values(models, 'id')),
                    Lesson.id == LessonClassesDiscipline.lesson_id,
                    ClassesDiscipline.id == LessonClassesDiscipline.classes_discipline_id,
                    ClassesDiscipline.school_class_id           == SchoolClass.id,
                    ClassesDiscipline.discipline_period_id      == DisciplinePeriod.id,
                    DisciplinePeriod.school_period_id           == SchoolPeriod.id,
                    DisciplinePeriod.discipline_grade_id        == DisciplineGrade.id,
                    DisciplineGrade.school_discipline_id        == SchoolDiscipline.id,
                    DisciplineGrade.unit_grade_id               == UnitGrade.id,
                    UnitGrade.school_grade_id                   == SchoolGrade.id,
                    UnitGrade.school_unit_id                    == SchoolUnit.id,
                )\
                .order_by(Lesson.id)
            
            objects = objects.all()

            for model in models:
                for tup in objects:
                    if tup[0] != model['id']: continue
                    model['class'] = '{} - {} - {} - {}'.format(*tup[1:])
                        
            # Montando a árvore alinhada com o identificador da classe desse aluno
            Tree = {}

            for model in models:
                if model['class'] not in Tree: Tree[model['class']] = []
                Tree[model['class']].append(model)
           
            return [Tree]


        """
        Adicionando os relacionamento das aulas com as disciplinas
        """
        ids = get_attribute_values(models)

        relantionships = LessonClassesDiscipline.query.filter(LessonClassesDiscipline.lesson_id.in_(ids)).all()

        for model in models:
            model['lesson_classes_disciplines'] = []
            model['__type'] = 'Aula ao vivo' if model['type'] == 'AO_VIVO' else 'Aula Gravada'
            
            for lesson_classes_discipline in relantionships:
                if lesson_classes_discipline.lesson_id == model['id']:
                    
                    name = '{} - {}'.format(
                        lesson_classes_discipline.classes_discipline.school_class.name,
                        lesson_classes_discipline.classes_discipline.school_discipline.name)

                    model['lesson_classes_disciplines'].append({
                            'label': name,
                            'begin': lesson_classes_discipline.cast_date(lesson_classes_discipline.begin),
                            'hour': lesson_classes_discipline.hour
                        })

        """
        Retornando os materiais já persistidos para essa aula
        """
        relantionships = LessonAttachment.query.filter(LessonAttachment.lesson_id.in_(ids), LessonAttachment.main_attachment==True)\
            .order_by(asc(LessonAttachment.created_at))\
            .all()

        for model in models:
            model['__can_play__'] = False
            
            for lesson_attachment in relantionships:
                if lesson_attachment.lesson_id == model['id'] and \
                    lesson_attachment.main_attachment:

                    # Se esse anexo ainda estiver em processamento, devemos redefinir o status:
                    if lesson_attachment.attachment.status == ModelStatus.PROCESSING.value:
                        model['__type'] = 'Processando Vídeo'

                    else:
                        model['__can_play__'] = True
                        model['attachment_id'] = lesson_attachment.attachment_id

        return models


    @classmethod
    def check_student_lesson_report(cls, *args, **kwargs) -> Query:
        """
        Função para retornar o reporte de aulas que um aluno já assistiu
        """
        from app.models import Lesson, StudentLessonClassesDiscipline, LessonClassesDiscipline, StudentDiscipline

        my_disciplines = session['profile_user'].get_my_disciplines().all()
        my_disciplines = Domain.get_attribute_values(my_disciplines)

        return db.session.query(Lesson)\
            .filter(
                StudentDiscipline.classes_discipline_id.in_(my_disciplines),
                StudentDiscipline.student_id == session['profile_user'].id,
                LessonClassesDiscipline.classes_discipline_id == StudentDiscipline.classes_discipline_id,
                LessonClassesDiscipline.lesson_id == Lesson.id
            )


    @classmethod
    def after_check_student_lesson_report(cls, models, *args, **kwargs) -> List:
        """
        Função para executar uma busca por interação entre o usuário e a
        respectiva aula.

        Caso o usuário não tenha interação, marcaremos contadores
        """
        Tree = {
            'lessons_set': [object['id'] for object in models],
            'lessons': [{'id': object['id'], 'name': object['name']} for object in models], 
            'interactions': []
            }

        lesson_ids = Domain.get_attribute_values(models)

        interactions = db.session.query(StudentLessonClassesDiscipline, Lesson.name)\
            .filter(
                StudentLessonClassesDiscipline.lesson_classes_discipline_id == LessonClassesDiscipline.id,
                LessonClassesDiscipline.lesson_id.in_(lesson_ids),
                LessonClassesDiscipline.lesson_id == Lesson.id
            )\
            .all()

        for object in interactions:
            pass

        #pprint(interactions)
        #input("...")
        

    def after_find_by_id(self, *args, **kwargs):
        """
        Metodo que faz a incrementação para o tipo de buscas 'after_find_by_id'.

        Listaremos as turmas associadas à essa aula, os alunos dessas turmas e as interações desse alunos com as turmas.
        """
        objects = db.session.query(ProfileUser, User).filter(
                LessonClassesDiscipline.lesson_id == kwargs['id'],
                LessonClassesDiscipline.classes_discipline_id == ClassesDiscipline.id,
                TeacherDiscipline.classes_discipline_id == ClassesDiscipline.id,
                TeacherDiscipline.teacher_id == ProfileUser.id,
                ProfileUser.user_id == User.id
                ).first()

        self.teacher_id = objects[0].id
        
        objects = db.session.query(ClassesDiscipline, LessonClassesDiscipline)\
            .filter(
                LessonClassesDiscipline.lesson_id == self.id,
                LessonClassesDiscipline.classes_discipline_id == ClassesDiscipline.id,
            )\
            .all()

        
        """
        Montando uma árvore agrupada por turma ao qual essa aula se relaciona.

        Esse elemento possuirá a disciplina em questão e os estudantes dela mesma.
        """
        Tree = {classe_discipline.id: {'students': [], 'name': classe_discipline.classe_discipline_name, 'LessonClassesDiscipline': lesson_classes_discipline.to_dict()} \
            for classe_discipline, lesson_classes_discipline in objects}


        """
        Adicionando os alunos inscritos à essa aula a partir do relacionamento entre a turma e a aula
        """
        for classes_discipline, lesson_classes_discipline in objects:
            
            # Carregando todos os alunos em questão:
            students = db.session.query(StudentDiscipline, ProfileUser, User)\
                .filter(
                    StudentDiscipline.classes_discipline_id == classes_discipline.id,
                    StudentDiscipline.student_id == ProfileUser.id,
                    ProfileUser.user_id == User.id
                )\
                .all()
            
            for student_discipline, profile_user, user in students:
                object = {'ProfileUser': profile_user.to_dict(), 'User': user.to_dict()}

                # Carregando a interação corrente desse usuário no loop
                interaction = StudentLessonClassesDiscipline.query\
                    .filter_by(
                        lesson_classes_discipline_id=lesson_classes_discipline.id, 
                        student_id=student_discipline.id)\
                    .first()
                
                if interaction:
                    object['Interaction'] = interaction.to_dict()
                
                Tree[classes_discipline.id]['students'].append(object)

        
        """
        Desmontando o índice da árvore:
        """
        Tree = list(Tree.values())

        #pprint(Tree)
        
        """
        Montando a interação estatística da aula:
        """
        for object in Tree:
            object['total_students'] = len(object['students'])

            students_with_audience = list(filter(lambda student: student.get('Interaction', None), object['students']))
            students_with_not_audience = list(filter(lambda student: not student.get('Interaction', None), object['students']))

            if not object['total_students']:
                object['audicence'] = 0
            
            else:
                object['audicence'] = "%.2f" % float(len(students_with_audience)/object['total_students'] * 100)
            
            object['total_students_dont'] = len(students_with_not_audience)
            object['students_dont'] = students_with_not_audience
            object['total_students_do'] = len(students_with_audience)
            object['students_do'] = students_with_audience

        self.details = Tree


    @classmethod
    def lessons_to_start(cls, *args, **kwargs) -> Query:
               
        current_profile_user:ProfileUser = session['profile_user']
             
        if current_profile_user.is_teacher():
            my_disciplines = TeacherDiscipline.list_my_disciplines(current_profile_user.id)

        elif current_profile_user.is_school_unit_administrator():
            my_disciplines = ClassesDiscipline.query \
                                .filter(
                                    SchoolUnitProfileUsers.profile_user_id == current_profile_user.id,
                                    SchoolUnitProfileUsers.school_unit_id == SchoolUnit.id,
                                    UnitGrade.school_unit_id == SchoolUnit.id,                                    
                                    DisciplineGrade.unit_grade_id == UnitGrade.id,
                                    DisciplinePeriod.discipline_grade_id == DisciplineGrade.id,
                                    ClassesDiscipline.discipline_period_id == DisciplinePeriod.id,
                                )

        elif current_profile_user.is_school_net_administrator():
            my_disciplines = ClassesDiscipline.query \
                                .filter(
                                    SchoolNetAdministrator.profile_user_id == current_profile_user.id,
                                    SchoolNetAdministrator.school_net_id == SchoolNet.id,
                                    SchoolUnit.school_net_id == SchoolNet.id,
                                    UnitGrade.school_unit_id == SchoolUnit.id,                                    
                                    DisciplineGrade.unit_grade_id == UnitGrade.id,
                                    DisciplinePeriod.discipline_grade_id == DisciplineGrade.id,
                                    ClassesDiscipline.discipline_period_id == DisciplinePeriod.id,
                                )

        elif current_profile_user.is_administrator():
            my_disciplines = ClassesDiscipline.query \
                                .filter(
                                    Administrator.profile_user_id == current_profile_user.id,
                                    Administrator.administration_id == Administration.id,
                                    AdministrationSchoolNet.administration_id == Administration.id,
                                    AdministrationSchoolNet.school_network_id == SchoolNet.id,
                                    SchoolUnit.school_net_id == SchoolNet.id,
                                    UnitGrade.school_unit_id == SchoolUnit.id,                                    
                                    DisciplineGrade.unit_grade_id == UnitGrade.id,
                                    DisciplinePeriod.discipline_grade_id == DisciplineGrade.id,
                                    ClassesDiscipline.discipline_period_id == DisciplinePeriod.id,
                                )

        my_disciplines = my_disciplines.all()
        
        logger.debug("Disciplinas ao qual o Usuário pode ver informações: {}".format(my_disciplines))

        ids = Domain.get_attribute_values(my_disciplines, 'id')

        return db.session.query(Lesson)\
            .filter(
                LessonClassesDiscipline.classes_discipline_id.in_(ids),
                LessonClassesDiscipline.lesson_id == Lesson.id,
                LessonClassesDiscipline.begin != None,
                LessonClassesDiscipline.hour != None,
            )\
            .order_by(desc(LessonClassesDiscipline.begin))\
            .order_by(desc(LessonClassesDiscipline.hour))\
            .order_by(desc(Lesson.name))\

    
    @classmethod
    def after_lessons_to_start(cls, models:List, *args, **kwargs) -> List:
        
        # Montando uma 'árvore' de acordo com a aula e relacionamento com suas disciplinas
        Tree = {object['id']: {**object, 'childs': []} for object in models}

        # Devemos adicionar: turmas da aula, professor
        for lesson in models:

            # Turma, Identificador do Professor e Usuário dele:
            __classes = db.session.query(ClassesDiscipline, ProfileUser.id, User.email, LessonClassesDiscipline).filter(
                LessonClassesDiscipline.lesson_id == lesson['id'],
                LessonClassesDiscipline.begin != None,
                LessonClassesDiscipline.hour != None,
                LessonClassesDiscipline.classes_discipline_id == ClassesDiscipline.id,
                TeacherDiscipline.teacher_id == ProfileUser.id,
                ProfileUser.id == session['profile_user'].id, # As vezes, podemos ter dois professores em uma mesma turma
                ProfileUser.user_id == User.id
                )
            
            __classes = __classes.all()

            #pprint(__classes)
            #input("...")

            # Filtrando turmas e professor
            __lesson_classe_disciplines  = [tup[3] for tup in __classes]
            __teacher_names              = [tup[2] for tup in __classes]
            __teacher_ids                = [tup[1] for tup in __classes]
            __classes                   = [tup[0] for tup in __classes]
            __classes                   = [object.to_dict() for object in __classes]

            __classes = ClassesDiscipline.after_find(__classes)

            for _class, __teacher_name, __teacher_id, __lesson_classe_discipline in zip(__classes, __teacher_names , __teacher_ids, __lesson_classe_disciplines):
                _class_name = '{} - {} - {}'.format(
                    _class['school_class']['name'],
                    _class['school_discipline']['name'],
                    _class['school_grade']['name'],
                )

                Tree[lesson['id']]['childs'].append({
                    'teacher_name': __teacher_name,
                    'teacher_id':   __teacher_id,
                    'begin': __lesson_classe_discipline.begin,
                    'hour': __lesson_classe_discipline.hour,
                    'validate': __lesson_classe_discipline.validate,
                    'lesson_discipline_id': __lesson_classe_discipline.id,
                    'class_name':               _class_name,
                    'school_class_name':        _class['school_class']['name'],
                    'school_discipline_name':   _class['school_discipline']['name'],
                    'school_grade_name':        _class['school_grade']['name']
                })

        Tree = list(Tree.values())
      
        # Verificando se o elemento pode ser inicializado para uma aula:
        now = datetime.now()

        for lesson in Tree:
            lesson['__init__'] = False
            
            for child in lesson['childs']:
                
                if not child['begin'] or not child['hour']: continue

                lesson_datetime = '{}T{}Z'.format(child['begin'], child['hour'])
                
                print("Inicio e fim: ", lesson_datetime)

                diff = (now - parse_datetime(lesson_datetime)).total_seconds() / 60.0

                if diff < 10 and diff > 0: lesson['__init__'] = True
                if diff < 0 and diff > -10: lesson['__init__'] = True
        
        # Carregando os insights de cada aula:
        for lesson in Tree:
            for child in lesson['childs']:
                lesson_discipline_id = child['lesson_discipline_id']
                
                # Alunos matriculados nessa turma:
                total_students = db.session.query(ProfileUser.id, User.email, User.id)\
                    .filter(
                        lesson_discipline_id == LessonClassesDiscipline.id,
                        LessonClassesDiscipline.classes_discipline_id == StudentDiscipline.classes_discipline_id,
                        StudentDiscipline.student_id == ProfileUser.id,
                        ProfileUser.user_id == User.id
                    )\
                    .all()

                # Alunos que interagiram com a aula:
                total_students_interact = db.session.query(StudentDiscipline.student_id)\
                    .distinct(StudentDiscipline.student_id)\
                    .filter(
                        StudentLessonClassesDiscipline.lesson_classes_discipline_id == lesson_discipline_id,
                        StudentLessonClassesDiscipline.student_id == StudentDiscipline.id,
                        LessonClassesDiscipline.classes_discipline_id == StudentDiscipline.classes_discipline_id,
                        StudentDiscipline.student_id == ProfileUser.id,
                        ProfileUser.user_id == User.id
                    )\
                    .all()

                total_students_interact = [tup[0] for tup in total_students_interact]

                child['total_students'] = total_students
                child['total_students_interact'] = total_students_interact
                
        #pprint(Tree)

        return Tree




class LessonClassesDiscipline(db.Model, Domain):
    # Relacionamento entre uma Disciplina propriamente dita e uma aula
    classes_discipline_id   = db.Column(db.String(36), db.ForeignKey('classes_discipline.id'), nullable=False)
    lesson_id               = db.Column(db.String(36), db.ForeignKey('lesson.id'), nullable=False)
    begin                   = db.Column(db.Date(), nullable=True)
    hour                    = db.Column(db.String(15), nullable=True)
    validate                = db.Column(db.Integer, nullable=True)


    @classmethod
    def before_upsert(cls, *args, **kwargs):

        # Verificando se a aula está pronta para receber essa atribuição
        if not Lesson.exists(id=kwargs['lesson_id']):
            raise ApiException("Verifique a validade da aula para essa ação.")
        
        current = cls.query.filter_by(classes_discipline_id=kwargs['classes_discipline_id'], lesson_id=kwargs['lesson_id']).first()

        if current:
            kwargs['id'] = current.id
            return kwargs 
            #raise ApiException("Essa Disciplina já possui essa Aula.")
        

    @classmethod
    def student_lessons(cls, *args, **kwargs) -> Query:
        """
        Função para listar, para um dado usuário estudante, as aulas agrupadas pelas suas turmas. Cada tipo de usuário terá uma maneira de 
        visualizar esses dados.
        """        
        current_profile_user:ProfileUser = session['profile_user']

        logger.debug("Perfil da requisição: {}".format(current_profile_user.profile_id))

        my_disciplines = current_profile_user.get_my_disciplines(columns=[ClassesDiscipline.id]).all()
        
        return db.session.query(LessonClassesDiscipline, Lesson, ClassesDiscipline, StudentDiscipline, ProfileUser, User)\
            .filter(
                ClassesDiscipline.id.in_(my_disciplines),
                LessonClassesDiscipline.classes_discipline_id == ClassesDiscipline.id,
                LessonClassesDiscipline.lesson_id == Lesson.id,
                Lesson.active(),
                TeacherDiscipline.classes_discipline_id == ClassesDiscipline.id,
                TeacherDiscipline.teacher_id == ProfileUser.id,
                ProfileUser.user_id == User.id,
                StudentDiscipline.classes_discipline_id == ClassesDiscipline.id,
                StudentDiscipline.student_id == current_profile_user.id
            )\
            .order_by(desc(LessonClassesDiscipline.begin))\
            .order_by(desc(LessonClassesDiscipline.hour))\


    @classmethod
    def after_student_lessons(cls, models:List, *args, **kwargs) -> List:

        
        classes_discipline              = [objects[2] for objects in models]
        
        ClassesDiscipline.get_classe_discipline_name(classes_discipline)

        #pprint(classes_discipline)
        #input("...")
                        
        # Montando a árvore alinhada com o identificador da classe desse aluno
        Tree = {}

        # Montando uma 'árvore' de acordo com a aula e relacionamento com suas disciplinas
        Tree = {object['id']: {
            'id': object['id'], 
            'name': object['name'], 
            'school_discipline_name': object['school_discipline_name'],
            'childs': []
            } for object in classes_discipline}

        # Verificando a hora e data dessa aula: 
        now = datetime.now()
           
       
        for tup, classe_discipline in zip(models, classes_discipline):
            #LessonClassesDiscipline, Lesson, ClassesDiscipline, StudentDiscipline, ProfileUser, User
            lesson_classes_discipline, lesson, _, student_discipline, teacher_profile_user, user = tup

            """
            Informações necessárias para adentrar à uma aula

            'teacherId': element['teacher_id'],
            'lessonDisciplineId': element.id,
            'studentDisciplineId': element['student_discipline_id']
            """

            lesson_classes_discipline['Lesson'] = lesson
            lesson_classes_discipline['student_discipline_id'] = student_discipline['id']
            lesson_classes_discipline['teacher_id'] = teacher_profile_user['id']
            lesson_classes_discipline['teacher_name'] = user['email']

            """
            Verificando se podemos assitir à aula propriamente dita.
            """
            lesson_classes_discipline['__can_play__'] = False

            if lesson_classes_discipline.get('begin', None) and lesson_classes_discipline.get('hour', None):
                lesson_datetime = parse_datetime('{}T{}Z'.format(lesson_classes_discipline['begin'].split('T')[0], lesson_classes_discipline['hour']))

                if lesson['type'] == 'AO_VIVO':

                    diff = (now - lesson_datetime).total_seconds() / 60.0

                    logger.debug("Diferenca entre o atual e a hora da aula ({}): {}".format(lesson['name'], diff))

                    if (diff < 10 and diff > 0) or (diff < 0 and diff > -10):
                        lesson_classes_discipline['__can_play__'] = True

                else:

                    """
                    Devemos verificar a data de lançamento da aula gravada e se a aula ainda está dentro da sua validade
                    """
                    if now > lesson_datetime:

                        lesson_classes_discipline['__can_play__'] = True

            Tree[classe_discipline['id']]['childs'].append(lesson_classes_discipline)

        Tree = list(Tree.values())

        return Tree



    @classmethod
    def lessons_to_start(cls, *args, **kwargs) -> Query:
        """
        Função para listar, para um dado usuário, as aulas que estão para iniciar. Cada tipo de usuário terá uma maneira de 
        visualizar esses dados.
        """        
        current_profile_user:ProfileUser = session['profile_user']
            
        my_disciplines = current_profile_user.get_my_disciplines().all()
        
        my_disciplines = Domain.get_attribute_values(my_disciplines, 'id')

        now = datetime.now().date()
        hour = (datetime.now() - timedelta(minutes=10)).strftime('%H:%M:%S')

        return db.session.query(LessonClassesDiscipline, Lesson, ClassesDiscipline, User)\
            .filter(
                ClassesDiscipline.id.in_(my_disciplines),
                LessonClassesDiscipline.classes_discipline_id == ClassesDiscipline.id,
                LessonClassesDiscipline.hour != None,
                LessonClassesDiscipline.begin != None,
                or_(and_(LessonClassesDiscipline.begin > now), and_(LessonClassesDiscipline.begin == now, LessonClassesDiscipline.hour > hour)),
                LessonClassesDiscipline.lesson_id == Lesson.id,
                Lesson.active(),
                TeacherDiscipline.classes_discipline_id == ClassesDiscipline.id,
                TeacherDiscipline.teacher_id == ProfileUser.id,
                ProfileUser.user_id == User.id
            )\
            .order_by(asc(LessonClassesDiscipline.begin))\
            .order_by(asc(LessonClassesDiscipline.hour))
                
    
    @classmethod
    def after_lessons_to_start(cls, models:List, *args, **kwargs) -> List:
        
        classes_discipline  = ClassesDiscipline.after_find([objects[2] for objects in models])

        data:List = []

        for tup, classe_discipline in zip(models, classes_discipline):
            lesson_classes_discipline, lesson, _, user = tup

            lesson_classes_discipline['Lesson'] = lesson
            lesson_classes_discipline['Teacher'] = user
            lesson_classes_discipline['classe_discipline'] = classe_discipline
            data.append(lesson_classes_discipline)

        
        return data

   
    @classmethod
    def report_lesson_classes_discipline(cls, *args, **kwargs) -> Query:
        return db.session.query(cls, Lesson.name, ProfileUser.id, User.email, User.id)\
            .filter(
                cls.classes_discipline_id == StudentDiscipline.classes_discipline_id,
                cls.lesson_id == Lesson.id,
                StudentDiscipline.student_id == ProfileUser.id,
                ProfileUser.user_id == User.id
            )

    
    @classmethod
    def after_report_lesson_classes_discipline(cls, models:List, *args, **kwargs) -> List:
        """
        Metodo que faz a incrementação para o tipo de buscas 'after_find_by_id'.

        Listaremos as turmas associadas à essa aula, os alunos dessas turmas e as interações desse alunos com as turmas.
        """

        Tree = {object[0]['id']: {
            'lesson_classes_discipline_id': object[0]['id'],
            'classes_discipline_id': object[0]['classes_discipline_id'],
            'lesson_name': object[1],
            'lesson_id': object[0]['lesson_id'],
            'hour': object[0]['hour'],
            'begin': object[0]['begin'],
            'students':[]} \
            for object in models}

        # Adicionando os estudantes de cada aula:
        for lesson_classes_discipline, _, profile_user_id, email, user_id in models:
            Tree[lesson_classes_discipline['id']]['students'].append({
                'profile_user_id': profile_user_id,
                'email': email,
                'user_id': user_id,
                'has_interact': False # Atributo que armazenará se o aluno interagiu com a aula ou não
            })

        Tree = list(Tree.values())

        # Verificando os estudantes que possuíram algum tipo de interação com a aula:
        for model in Tree:
            interaction = db.session.query(StudentDiscipline.student_id)\
                .filter(
                    StudentLessonClassesDiscipline.student_id == StudentDiscipline.id,
                    StudentLessonClassesDiscipline.lesson_classes_discipline_id == model['lesson_classes_discipline_id']
                )\
                .all()

            interaction = [tup[0] for tup in interaction] if len(interaction) else interaction

            for student in model['students']:
                if student['profile_user_id'] in interaction:
                    student['has_interact'] = True

        # Montando valores absolutos de interação e audiência:
        for model in Tree:
            model['interact']       = [object for object in model['students'] if object['has_interact']]
            model['not_interact']   = [object for object in model['students'] if not object['has_interact']]
        
        Tree = {'lessons': Tree, 'total_interact': 0, 'total_not_interact': 0, 'total_students': 0, 'total_lessons': len(Tree)}

        # Calculando a quantidade de interações total
        for model in Tree['lessons']:
            Tree['total_interact'] += len(model['interact'])
            Tree['total_not_interact'] += len(model['not_interact'])
            Tree['total_students'] += len(model['students'])

        Tree['audience'] = Tree['total_interact']/Tree['total_students']

        return Tree


    @validates('begin')
    def validate_begin(self, key, value):
        if value is None:
            return 

        # raise ApiException("Verifique a validade do atributo 'begin'. Ele deve ser data ISO-8601.")
        value = parse_date(value)
        
        return value


    @validates('validate')
    def validate_validate(self, key, value):
        #TODO Fazer a validação da quantidade de dias. Não pode ser maior que o período da aula
        
        return value


    @classmethod
    def get_my_next_lesson_to_start(cls, *args, **kwargs) -> List:
        """
        Função para listar, para um dado usuário, a próxima aula que será iniciada.

        Utilizada na listagem da dashboard
        """        
        current_profile_user = session['profile_user']
            
        my_disciplines = current_profile_user.get_my_disciplines().all()
        
        my_disciplines = Domain.get_attribute_values(my_disciplines, 'id')

        now = datetime.now().date()

        hour = (datetime.now() - timedelta(minutes=10)).strftime('%H:%M:%S')
        
        if current_profile_user.is_student():
            next_lesson = db.session.query(LessonClassesDiscipline, Lesson, ClassesDiscipline, User.name, User.email, ProfileUser.id, StudentDiscipline.id)\
                .filter(
                    ClassesDiscipline.id.in_(my_disciplines),
                    LessonClassesDiscipline.classes_discipline_id == ClassesDiscipline.id,
                    LessonClassesDiscipline.hour != None,
                    LessonClassesDiscipline.begin != None,
                    or_(and_(LessonClassesDiscipline.begin > now), and_(LessonClassesDiscipline.begin == now, LessonClassesDiscipline.hour > hour)),
                    LessonClassesDiscipline.lesson_id == Lesson.id,
                    Lesson.active(),
                    Lesson.live(),
                    TeacherDiscipline.classes_discipline_id == ClassesDiscipline.id,
                    TeacherDiscipline.teacher_id == ProfileUser.id,
                    ProfileUser.user_id == User.id,
                    StudentDiscipline.classes_discipline_id == ClassesDiscipline.id,
                    StudentDiscipline.student_id == current_profile_user.id
                )

        else:
            next_lesson = db.session.query(LessonClassesDiscipline, Lesson, ClassesDiscipline, User.name, User.email, ProfileUser.id, TeacherDiscipline.id)\
                .filter(
                    ClassesDiscipline.id.in_(my_disciplines),
                    LessonClassesDiscipline.classes_discipline_id == ClassesDiscipline.id,
                    LessonClassesDiscipline.hour != None,
                    LessonClassesDiscipline.begin != None,
                    or_(and_(LessonClassesDiscipline.begin > now), and_(LessonClassesDiscipline.begin == now, LessonClassesDiscipline.hour > hour)),
                    LessonClassesDiscipline.lesson_id == Lesson.id,
                    Lesson.active(),
                    Lesson.live(),
                    TeacherDiscipline.classes_discipline_id == ClassesDiscipline.id,
                    TeacherDiscipline.teacher_id == ProfileUser.id,
                    ProfileUser.user_id == User.id,
                    TeacherDiscipline.classes_discipline_id == ClassesDiscipline.id,
                    TeacherDiscipline.teacher_id == current_profile_user.id
                )
        
        next_lesson = next_lesson\
            .order_by(asc(LessonClassesDiscipline.begin))\
            .order_by(asc(LessonClassesDiscipline.hour))\
            .first()

        if not next_lesson: 
            return [None]
                
        object = next_lesson[0].to_dict()

        # Verificando a hora e data dessa aula: 
        now = datetime.now()
        lesson_datetime = parse_datetime('{}T{}Z'.format(object['begin'].split('T')[0], object['hour']))
        
        diff = (now - lesson_datetime).total_seconds() / 60.0
        
        #print(next_lesson[1].name, next_lesson[0].begin, next_lesson[0].hour)
        #input("...")

        # O tempo atual é bem maior que a hora de início da aula
        if diff > 10 and current_profile_user.is_student(): 
            return [None]
        
        object['Lesson'] = next_lesson[1].to_dict()
        object['ClassesDiscipline'] = next_lesson[2].classe_discipline_name
        object['teacher_name'] = next_lesson[3]
        object['teacher_user'] = next_lesson[4]
        object['teacher_id'] = next_lesson[5]
        object['student_discipline_id'] = next_lesson[6]
        object['__init__'] = False

        if diff > -10:
            object['__init__'] = True
            
        return [object]



class LessonAttachment(db.Model, Domain):
    lesson_id           = db.Column(db.String(36), db.ForeignKey('lesson.id'), nullable=False)
    attachment_id       = db.Column(db.String(36), db.ForeignKey('attachment.id'), nullable=False) # Modelo de anexo
    main_attachment     = db.Column(db.Boolean(), nullable=True, default=False)


    @property
    def attachment(self) -> Domain:
        if not hasattr(self, '_attachment'):
            self._attachment = Attachment.query\
                .filter(self.attachment_id == Attachment.id).first()

        return self._attachment


    @classmethod
    def before_upsert(cls, *args, **kwargs):

        """
        Em casos onde estamos definindo o anexo como conteúdo principal de uma aula, devemos permitir somente vídeos.
        """
        if kwargs.get('main_attachment', None):
            attachment = Attachment.query.filter(cls.attachment_id == Attachment.id, cls.id == kwargs['id']).first()
            
            if not attachment.is_video:
                raise ApiException("Não é possível definir esse Anexo como conteúdo principal da Aula. Só é possível vídeos para essa ação.")
        

    @classmethod
    def after_find(cls, models:List, *args, **kwargs):
        ids = Domain.get_attribute_values(models, 'id')

        # Selecionando a disciplina dos modelos de Atividade
        objects = db.session\
            .query(cls.id, Attachment)\
            .filter(
                cls.id.in_(ids),
                cls.attachment_id == Attachment.id,
            )
        
        objects = objects.all()

        for model in models:
            for tup in objects:
                if tup[0] != model['id']: continue
                model['Attachment'] = tup[1].to_dict()



class StudentLessonClassesDiscipline(db.Model, Domain):
    # Modelo de Interação entre um Estudante e a sua respectiva aula
    lesson_classes_discipline_id    = db.Column(db.String(36), db.ForeignKey('lesson_classes_discipline.id'), nullable=False)
    student_id                      = db.Column(db.String(36), db.ForeignKey('student_discipline.id'), nullable=False)


    @classmethod
    def before_find(cls, *args, **kwargs):
        # Verificando se a interação existe. Se ela não existir, devemos criá-la:
        if kwargs.get('with_create', None):
            kwargs.pop('with_create')
            current = StudentLessonClassesDiscipline.query.filter_by(**kwargs).first()

            if not current:
                current = StudentLessonClassesDiscipline.create(**kwargs)
                db.session.flush()
        


"""
Modelos de Domínio Escolar
"""
class SchoolUnit(db.Model, LogicalDomain):
    # Modelo de Unidade Escolar
    name        = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    school_net_id   = db.Column(db.String(36), db.ForeignKey('school_net.id'), nullable=False)


    def get_disciplines(self, 
        available=True,
        query:List=None, 
        *args, 
        **kwargs) -> Query:

        from app.models.classes_discipline import ClassesDiscipline

        if not query:
            query = [ClassesDiscipline]

        _filter = [
            UnitGrade.school_unit_id                == self.id,
            UnitGrade.school_grade_id               == SchoolGrade.id,
            DisciplineGrade.unit_grade_id           == UnitGrade.id,
            DisciplineGrade.school_discipline_id    == SchoolDiscipline.id,
            DisciplinePeriod.discipline_grade_id    == DisciplineGrade.id,
            DisciplinePeriod.school_period_id       == SchoolPeriod.id,
            ClassesDiscipline.discipline_period_id  == DisciplinePeriod.id,
            ClassesDiscipline.school_class_id       == SchoolClass.id
            ]

        if available:
            #_filter.append(SchoolPeriod.valid())
            pass

        query = db.session.query(*query).filter(*_filter)

        return query
        

    def get_profile_users(self) -> Query:
        """
        Função para listar os profile users de uma dada unidade escolar
        """
        return ProfileUser.query.filter(SchoolUnitProfileUsers.school_unit_id == self.id, SchoolUnitProfileUsers.profile_user_id == ProfileUser.id, ProfileUser.active())

    
    def get_administrators(self, *args, **kwargs) -> Query:
        """
        Função para listar os profile users administradores de uma dada unidade educacional
        """
        return ProfileUser.query.filter(
            SchoolUnitProfileUsers.school_unit_id == self.id, 
            SchoolUnitProfileUsers.profile_user_id == ProfileUser.id, 
            ProfileUser.active(),
            ProfileUser.profile_id == config.SCHOOL_UNIT_ADMINISTRATOR_ID)



    def get_members(self, columns:List=None, *args, **kwargs) -> Query:
        """
        Função para listar os profile users de uma dada unidade escolar
        """
        if not columns: columns = [ProfileUser]

        return db.session.query(*columns).filter(
            SchoolUnitProfileUsers.school_unit_id == self.id, 
            SchoolUnitProfileUsers.profile_user_id == ProfileUser.id, 
            SchoolUnitProfileUsers.active(),
            ProfileUser.active()
            )
    

    def get_teachers(self, columns:List=None, *args, **kwargs) -> Query:
        """
        Função para listar os profile users de uma dada unidade escolar que são professores
        """
        if not columns: columns = [ProfileUser]

        return db.session.query(*columns).filter(
            SchoolUnitProfileUsers.school_unit_id == self.id, 
            SchoolUnitProfileUsers.profile_user_id == ProfileUser.id, 
            SchoolUnitProfileUsers.active(),
            ProfileUser.active(),
            ProfileUser.profile_id == config.TEACHERS_ID
            )


    def get_students(self, columns:List=None, *args, **kwargs) -> Query:
        """
        Função para listar os profile users de uma dada unidade escolar que são alunos
        """
        if not columns: columns = [ProfileUser]

        return db.session.query(*columns).filter(
            SchoolUnitProfileUsers.school_unit_id == self.id, 
            SchoolUnitProfileUsers.profile_user_id == ProfileUser.id, 
            SchoolUnitProfileUsers.active(),
            ProfileUser.active(),
            ProfileUser.profile_id == config.STUDENTS_ID
            )


    def get_current_lessons(self, *args, **kwargs) -> List:
        """
        Função para listar as aulas em andamento em uma dada unidade educacional
        """
        raise NotImplementedError()
    

    @classmethod
    def before_remove(*args, **kwargs):
        if UnitGrade.exists(school_unit_id=kwargs['id']):
            raise ApiException("Não é possível deletar essa Unidade Escolar. Há Séries Escolares relacionadas à ela.")
        
        if SchoolUnitProfileUsers.exists(school_unit_id=kwargs['id']):
            raise ApiException("Não é possível deletar essa Unidade Escolar. Há Alunos, Professores ou Coordenadores relacionadas à ela.")


    @classmethod
    def school_unit_checked(cls, *args, **kwargs) -> Query:
        return db.session.query(cls).filter(cls.active())


    @classmethod
    def after_school_unit_checked(cls, models:List, *args, **kwargs) -> List:
        ids = get_attribute_values(models)

        join = UnitGrade.query.filter(UnitGrade.school_unit_id.in_(ids), UnitGrade.school_grade_id == kwargs['school_grade_id']).all()

        for main_object in models:
            main_object['__checked__'] = False
            
            for relationship in join:
                if relationship.school_unit_id == main_object['id']:
                    main_object['__checked__'] = True

        return models


    @classmethod
    def school_grade_checked(cls, *args, **kwargs) -> Query:
        """
        Função para carregar as séries de uma unidade escolar
        """
        logger.debug("Carregando todos os séries marcadas para alguma Unidade Escolar: {}".format(kwargs['school_unit_id']))
        
        left_condition_1 = (UnitGrade.school_unit_id == kwargs['school_unit_id'], UnitGrade.status != ModelStatus.DELETED.value)
        #left_condition_2 = (UnitGrade.school_grade_id == SchoolGrade.id)

        return db.session.query(cls, UnitGrade) \
            .join(UnitGrade, and_(*left_condition_1), isouter=True)\
            #.join(SchoolGrade, and_(*left_condition_2), isouter=True)


    @classmethod
    def after_school_grade_checked(cls, models:List, *args, **kwargs) -> List:
        """
        Função para ser executada após carregar as séries de uma unidade escolar.
        """
        logger.debug('after_school_grade_checked')
        data:list = []

        #pprint(models)
        #input("...")

        ids = Domain.get_attribute_values([tup[0] for tup in models], 'id')

        for main_object, relationship_id in models:
            main_object['__checked__'] = True if relationship_id else False
            data.append(main_object)

        return data



    def access_data(self, *args, **kwargs) -> List[str]:
        return [self.id]


    @classmethod
    def user_checked(cls, *args, **kwargs) -> Query:
        current_profile_user:ProfileUser = session['profile_user']

        return cls.query.filter(cls.id.in_(current_profile_user.get_my_school_units(columns=[SchoolUnit.id]).subquery()))


    @classmethod
    def after_user_checked(cls, models:List, *args, **kwargs) -> List:
        
        current_profile_user:ProfileUser = session['profile_user']

        # Se o usuário for um aluno ou professor, devemos assinalá-lo à unidade que ele se relaciona
        relantionships = SchoolUnitProfileUsers.query.filter(
            SchoolUnitProfileUsers.profile_user_id == ProfileUser.id,
            ProfileUser.user_id == kwargs['user_id'], 
            SchoolUnitProfileUsers.active()).all()
                
        for school_unit in models:
            school_unit['__checked__'] = False

            for r in relantionships:
                if school_unit['id'] == r.school_unit_id: 
                    school_unit['__checked__'] = True
                    

        return models



class SchoolGrade(db.Model, LogicalDomain):
    # Modelo de Série ou Ano Escolar. P.e.: 1º ano, 2º ano, 5º Série, 4º Série
    name            = db.Column(db.String(100), nullable=False)
    description     = db.Column(db.String(255), nullable=True)
    

    @classmethod
    def school_grade_school_unit_checked(cls, *args, **kwargs) -> Query:
        """
        Função para carregar as séries marcando as que estão associadas à alguma unidade escolar, passada como parâmetro
        'school_unit_id' na requisição.
        """
        logger.debug("Carregando todos os séries marcadas para alguma Unidade Escolar: {}".format(kwargs['school_unit_id']))

        left_condition_1 = [UnitGrade.school_grade_id == SchoolGrade.id, UnitGrade.school_unit_id == kwargs['school_unit_id'], UnitGrade.status != ModelStatus.DELETED.value]
        left_condition_2 = [UnitGrade.school_unit_id == SchoolUnit.id]

        return db.session.query(cls, UnitGrade, SchoolUnit) \
            .join(UnitGrade, and_(*left_condition_1), isouter=True)\
            .join(SchoolUnit, *left_condition_2, isouter=True)\


    @classmethod
    def after_school_grade_school_unit_checked(cls, models:List, *args, **kwargs) -> List:
        """
        Função para ser executada após carregar as séries de uma unidade escolar.

        Essa função além de adicionar quem está marcado ou não para uma unidade escolar, também informará quais
        as disciplinas correntes para esse elemento.
        """
        logger.debug('after_school_grade_checked')
        data:list = []


        ids = Domain.get_attribute_values([tup[0] for tup in models], 'id')

        """
        Será efetuada uma redução para uma lista de elementos contendo as informações necessárias
        
        Será adicionado todas as disciplinas disponíveis para atribuição na Série

        Será verificado quais disciplinas já foram marcadas para uma dada Série.
        """
        disciplines = [object.to_dict() for object in SchoolDiscipline.get(cursor_function='all')]
       
        disciplines_id = Domain.get_attribute_values(disciplines, 'id')
        
        for main_object, school_grade_school_unit, school_unit in models:
            main_object['__checked__'] = True if school_grade_school_unit and school_unit else False

            main_object['disciplines'] = [{**object, '__checked__': False} for object in list(disciplines)]

            disciplines_checked = []
            """
            Se o objeto já estiver relacionado com a unidade escolar, devemos verificar quais disciplinas já podem estar também.
            """
            if school_grade_school_unit:
                # Verificando quais possuem algum relacionamento com disciplina
                disciplines_checked = SchoolGradeSchoolDiscipline.get(
                    [SchoolGradeSchoolDiscipline.school_discipline_id.in_(disciplines_id),
                    SchoolGradeSchoolDiscipline.grade_unit_id == school_grade_school_unit['id']],
                    cursor_function='all'
                    )

                # Listando as disciplinas associadas:
                disciplines_checked = Domain.get_attribute_values(disciplines_checked, 'school_discipline_id') 

                for discipline in main_object['disciplines']:
                    if discipline['id'] in disciplines_checked: discipline['__checked__'] = True

            main_object['disciplines_checked'] = disciplines_checked
           
            data.append(main_object)

        return data


    @classmethod
    def after_find(cls, models:list, *args, **kwargs):

        # Carregando as turmas e a série das disciplinas:
        ids = Domain.get_attribute_values(models, 'id')

        """
        join_SchoolDiscipline = db.session.query(SchoolDiscipline, DisciplineGrade) \
            .filter(
                UnitGrade.school_grade_id.in_(ids),
                DisciplineGrade.school_discipline_id == SchoolDiscipline.id,
                DisciplineGrade.status != ModelStatus.DELETED.value,
            )\
            .all()
        """

        join_SchoolUnit = db.session.query(SchoolUnit, UnitGrade) \
            .filter(
                UnitGrade.school_grade_id.in_(ids),
                UnitGrade.school_unit_id == SchoolUnit.id,
            )\
            .all()

        """
        Relacionamento Série e Unidade Escolar
        """
        for _object in models: _object['school_unit'] = []

        for join_object in join_SchoolUnit:
            unit, relantionship = join_object
            
            for _object in models:
                if _object['id'] == relantionship.school_grade_id:
                    _object['school_unit'].append(unit.to_dict())

        """
        Relacionamento Série e Disciplina
        """
        for _object in models: _object['school_discipline'] = []

        """
        for join_object in join_SchoolDiscipline:
            discipline, relantionship = join_object

            for _object in models:
                if _object['id'] == relantionship.school_grade_id:
                    _object['school_discipline'].append(discipline.to_dict())
        """


    @classmethod
    def before_create(cls, *args, **kwargs):
        if cls.get([cls.name == kwargs['name'], cls.status != ModelStatus.DELETED.value], with_status=False):
            raise ApiException("Já existe uma Série com esse nome.")


    @classmethod
    def before_remove(cls, *args, **kwargs):
        if UnitGrade.exists(school_grade_id=kwargs['id']):
            raise ApiException("Não é possível realizar essa operação. Existem Unidades Escolares relacionadas à essa Série.")



class UnitGrade(db.Model, Domain):
    """
    Relacionamento entre série escolar e unidade escolar.

    Unidades escolares podem ter ou não algumas séries.
    """
    school_grade_id   = db.Column(db.String(36), db.ForeignKey('school_grade.id'), nullable=False) # Modelo de Série
    school_unit_id  = db.Column(db.String(36), db.ForeignKey('school_unit.id'), nullable=False) # Modelo de Unidade Escolar
    

    @classmethod
    def unit_grade_checked(cls, *args, **kwargs) -> Query:

        # Quem são os UnitGrade marcados p/ uma Disciplina?
        left = (
            DisciplineGrade.unit_grade_id == cls.id, 
            DisciplineGrade.school_discipline_id == kwargs['school_discipline_id']
            )

        return db.session.query(cls, DisciplineGrade) \
            .outerjoin(DisciplineGrade, and_(*left))\
            .join(SchoolUnit, cls.school_unit_id == SchoolUnit.id)\
            .join(SchoolGrade, cls.school_grade_id == SchoolGrade.id)\
            .order_by(asc(SchoolUnit.name))\
            .order_by(asc(SchoolGrade.name))


    @classmethod
    def after_unit_grade_checked(cls, models:List, *args, **kwargs) -> List:
        data:list = []

        ids = Domain.get_attribute_values([tup[0] for tup in models], 'id')

        # Listando os objetos que se relacionam com um UnitGrade
        objects = db.session.query(UnitGrade.id, SchoolGrade, SchoolUnit).filter(
            UnitGrade.school_grade_id == SchoolGrade.id,
            UnitGrade.school_unit_id == SchoolUnit.id,
            UnitGrade.id.in_(ids)
        )

        objects = objects.all()

        for main_object, relationship in models:
            main_object['__checked__'] = True if relationship else False
            
            for complementaries in objects: 
                id, school_grade, school_unit = complementaries
                if id!=main_object['id']: continue           
                main_object['school_grade'] = school_grade.to_dict()
                main_object['school_unit'] = school_unit.to_dict()
            
            data.append(main_object)

        return data


    @classmethod
    def before_remove(cls, *args, **kwargs):

        current:cls = cls.query.filter_by(**kwargs).first()

        if DisciplineGrade.exists(unit_grade_id=current.id):
            raise ApiException("Não é possível realizar essa operação. Existem Disciplinas associados à esse relacionamento entre Série e Unidade Escolar.")
        
        if UnitGradeLibrary.exists(unit_grade_id=current.id):
            raise ApiException("Não é possível realizar essa operação. Existem Acervos associados à esse relacionamento entre Série e Unidade Escolar.")



    @classmethod
    def library_checked(cls, *args, **kwargs) -> Query:
        return db.session.query(cls, SchoolGrade, SchoolUnit) \
                    .join(SchoolGrade, cls.school_grade_id == SchoolGrade.id) \
                    .join(SchoolUnit, cls.school_unit_id == SchoolUnit.id) \
                    .order_by(asc(SchoolUnit.name))


    @classmethod
    def after_library_checked(cls, models:List, *args, **kwargs) -> List:
        
        ids = Domain.get_attribute_values([tup[0] for tup in models])

        library_grades = UnitGradeLibrary.query.filter(
            UnitGradeLibrary.library_id == kwargs['library_id'],
            UnitGradeLibrary.unit_grade_id.in_(ids)
        )

        library_grades = library_grades.all()
        
        for model, school_grade, school_unit in models:
            model['__checked__']    = False
            model['school_grade']   = school_grade
            model['school_unit']    = school_unit

            for library_grade in library_grades:
                if library_grade.unit_grade_id == model['id']: 
                    model['__checked__'] = True

        return [tup[0] for tup in models]



class DisciplineGrade(db.Model, Domain):
    """
    Relacionamento entre Disciplina (Matemática, Português e etc), Unidade Escolar e uma dada Série Escolar (1º Ano, 2º Ano e ect)
    de uma Unidade Escolar
    """
    unit_grade_id         = db.Column(db.String(36), db.ForeignKey('unit_grade.id'), nullable=False)
    school_discipline_id  = db.Column(db.String(36), db.ForeignKey('school_discipline.id'), nullable=False)


    @classmethod
    def before_remove(cls, *args, **kwargs):
                        
        current:cls = cls.query.filter_by(**kwargs).first()

        if DisciplinePeriod.exists(discipline_grade_id=current.id):
            raise ApiException("Não é possível realizar essa operação. Existem Períodos associados à esse relacionamento entre Disciplina e Série e Unidade Escolar.")
        

    @classmethod
    def period_checked(cls, *args, **kwargs) -> Query:

        query = db.session.query(cls) \
            .join(SchoolDiscipline, cls.school_discipline_id == SchoolDiscipline.id)\
            .join(UnitGrade, cls.unit_grade_id == UnitGrade.id)\
            .join(SchoolGrade, UnitGrade.school_grade_id == SchoolGrade.id)\
            .join(SchoolUnit, UnitGrade.school_unit_id == SchoolUnit.id)\
            .order_by(asc(SchoolUnit.name))\
            .order_by(asc(SchoolGrade.name))\
            .order_by(asc(SchoolDiscipline.name))\

        
        return query
            

    @classmethod
    def after_period_checked(cls, models:List, *args, **kwargs) -> List:
        data:list = []

        ids = Domain.get_attribute_values(models, 'id')

        objects_to_be_checked = DisciplinePeriod.query \
            .filter(DisciplinePeriod.school_period_id == kwargs['school_period_id'], DisciplinePeriod.discipline_grade_id.in_(ids)).all()

        for model in models:
            model['__checked__'] = False
            for checked in objects_to_be_checked:
                if checked.discipline_grade_id != model['id']: continue
                model['__checked__'] = True

        # Listando os objetos que se relacionam com um Discipline Grade
        objects = db.session.query(DisciplineGrade.id, SchoolDiscipline, SchoolGrade, SchoolUnit).filter(
            DisciplineGrade.id.in_(ids),
            DisciplineGrade.school_discipline_id == SchoolDiscipline.id,
            DisciplineGrade.unit_grade_id == UnitGrade.id,
            UnitGrade.school_grade_id == SchoolGrade.id,
            UnitGrade.school_unit_id == SchoolUnit.id,
        )

        objects = objects.all()

        for main_object in models:
            for id, school_discipline, school_grade, school_unit in objects:
                if id != main_object['id']: continue
                main_object['school_discipline']    = school_discipline.to_dict()
                main_object['school_grade']         = school_grade.to_dict()
                main_object['school_unit']          = school_unit.to_dict()
            
            data.append(main_object)

        return data



class DisciplinePeriod(db.Model, Domain):
    """
    Relacionamento entre uma disciplina escolar (Matemática, Português e etc) de uma Unidade Educacional e um Período Escolar
    """
    discipline_grade_id     = db.Column(db.String(36), db.ForeignKey('discipline_grade.id'), nullable=False)
    school_period_id        = db.Column(db.String(36), db.ForeignKey('school_period.id'), nullable=False)


    @classmethod
    def before_remove(cls, *args, **kwargs):
                        
        current:cls = cls.query.filter_by(**kwargs).first()

        if ClassesDiscipline.exists(discipline_period_id=current.id):
            raise ApiException("Não é possível realizar essa operação. Existem Turmas associados à esse relacionamento entre Período e Disciplina, Série e Unidade Escolar.")
        
        
    @classmethod
    def classes_checked(cls, *args, **kwargs) -> Query:

        # Quem são as classes marcadas para essa Disciplia/Serie/Unidade Escolar?
        left = (
            ClassesDiscipline.discipline_period_id == cls.id, 
            ClassesDiscipline.school_class_id == kwargs['school_class_id']
            )

        return db.session.query(cls, ClassesDiscipline) \
            .outerjoin(ClassesDiscipline, and_(*left))\
            .join(SchoolPeriod, DisciplinePeriod.school_period_id == SchoolPeriod.id)\
            .join(DisciplineGrade, cls.discipline_grade_id == DisciplineGrade.id)\
            .join(SchoolDiscipline, DisciplineGrade.school_discipline_id == SchoolDiscipline.id)\
            .join(UnitGrade, DisciplineGrade.unit_grade_id == UnitGrade.id)\
            .join(SchoolGrade, UnitGrade.school_grade_id == SchoolGrade.id)\
            .join(SchoolUnit, UnitGrade.school_unit_id == SchoolUnit.id)\
            .order_by(asc(SchoolUnit.name))\
            .order_by(asc(SchoolGrade.name))\
            .order_by(asc(SchoolDiscipline.name))\
            .order_by(desc(SchoolPeriod.name))\



    @classmethod
    def after_classes_checked(cls, models:List, *args, **kwargs) -> List:
        data:list = []

        ids = Domain.get_attribute_values([tup[0] for tup in models], 'id')
      
        # Listando os objetos que se relacionam com um Discipline Grade
        objects = db.session.query(DisciplinePeriod.id, SchoolPeriod, SchoolDiscipline, SchoolGrade, SchoolUnit)\
            .filter(
                cls.school_period_id == SchoolPeriod.id,
                cls.discipline_grade_id == DisciplineGrade.id,
                DisciplineGrade.school_discipline_id == SchoolDiscipline.id,
                DisciplineGrade.unit_grade_id == UnitGrade.id,
                UnitGrade.school_grade_id == SchoolGrade.id,
                UnitGrade.school_unit_id == SchoolUnit.id,
                cls.id.in_(ids)
            )


        for main_object, relationship in models:
            for id, school_period, school_discipline, school_grade, school_unit in objects:
                if main_object['id'] != id: continue

                main_object['__checked__'] = True if relationship else False
                main_object['school_period']        = school_period.to_dict()
                main_object['school_discipline']    = school_discipline.to_dict()
                main_object['school_grade']         = school_grade.to_dict()
                main_object['school_unit']          = school_unit.to_dict()
        
                data.append(main_object)

        return data



class SchoolUnitProfileUsers(db.Model, LogicalDomain):
    # Usuários que se relacionam com a Unidade Escolar
    school_unit_id   = db.Column(db.String(36), db.ForeignKey('school_unit.id'), nullable=False)
    profile_user_id  = db.Column(db.String(36), db.ForeignKey('profile_user.id'), nullable=False)


    @classmethod
    def before_upsert(cls, *args, **kwargs):

        transaction_profile_user = ProfileUser.query.filter_by(id=kwargs['profile_user_id']).first()
      
        if transaction_profile_user.is_student():

            """
            Quando o profile_user em transação é um estudante, devemos permitir este somente em uma unidade escolar
            """
            current_school_unit = cls.query.filter(cls.profile_user_id == transaction_profile_user.id, cls.active()).first()

            if current_school_unit and current_school_unit.school_unit_id != kwargs['school_unit_id']:
                raise ApiException("Um estudante só pode está matriculado em uma Unidade Escolar.")
        
        
    @classmethod
    def before_remove(cls, *args, **kwargs):
        current:cls = cls.query.filter_by(status=ModelStatus.ACTIVE.value , **kwargs).first()

        # Verificando se esse usuário é um aluno. Se for, devemos avaliar se este está matriculado em alguma disciplina
        profile_user:ProfileUser = ProfileUser.query.filter_by(id=current.profile_user_id).first()

        logger.debug("Perfil Afetado: {} - {}".format(profile_user, profile_user.is_student()))

        if profile_user.is_student():
            if StudentDiscipline.exists(student_id=profile_user.id):
                raise ApiException("Não é possível realizar essa operação. Esse Aluno está matriculado à disciplinas dessa Unidade Escolar.")
        

        elif profile_user.is_teacher():
            if TeacherDiscipline.exists(teacher_id=profile_user.id):
                raise ApiException("Não é possível realizar essa operação. Esse Professor está matriculado à disciplinas dessa Unidade Escolar.")
        
        
    @classmethod
    def after_find(cls, models:list, *args, **kwargs):

        ids = Domain.get_attribute_values(models, 'id')

        # Trazendo os Usuários e Perfis ao qual os modelos se relacionam
        join = db.session.query(ProfileUser, User, Profile).filter(*[
            SchoolUnitProfileUsers.profile_user_id == ProfileUser.id,
            ProfileUser.user_id == User.id,
            ProfileUser.profile_id == Profile.id,
            SchoolUnitProfileUsers.id.in_(ids)
        ]).all()

        for objects in join:
            profile_user, user, profile = objects

            for model in models:
                if model['profile_user_id'] == profile_user.id:
                    model['profile_user'] = profile_user.to_dict()
                    model['profile_user']['user'] = user.to_dict()
                    model['profile_user']['profile'] = profile.to_dict()


    @classmethod
    def students(cls, *args, **kwargs) -> Query:
        logger.debug("Carregando alunos matriculados.")
        
        # NOTE Identificador obrigatório de um perfil aluno -> 344c0d50-1e20-4eed-af4a-ab4639addb40
        return cls.query.filter(
            SchoolUnitProfileUsers.profile_user_id == ProfileUser.id,
            ProfileUser.profile_id == '344c0d50-1e20-4eed-af4a-ab4639addb40', 
            SchoolUnitProfileUsers.status != ModelStatus.DELETED.value,
            ProfileUser.status != ModelStatus.DELETED.value
            )


    def access_data(self, *args, **kwargs) -> List[str]:
        school_unit = SchoolUnit.get([SchoolUnit.id == self.school_unit_id])
        return school_unit.access_data()


    @classmethod
    def report_teachers(cls, *args, **kwargs) -> Query:
        """
        Função para listar os professores dado à visualização
        do usuário requisitante.
        """
        from app.models.profile_user import TEACHERS_ID
        from app.models.user import User

        profile_user:ProfileUser = session['profile_user']

        my_school_units = profile_user.get_my_school_units().all()
        my_school_units = Domain.get_attribute_values(my_school_units)
        
        # Selecionando os professores das unidades escolares ao qual temos acesso
        profile_users_id = db.session.query(SchoolUnitProfileUsers.profile_user_id)\
            .filter(
                SchoolUnitProfileUsers.school_unit_id.in_(my_school_units),
                SchoolUnitProfileUsers.profile_user_id == ProfileUser.id,
                ProfileUser.profile_id == TEACHERS_ID
                )

        profile_users_id = profile_users_id.all()
        profile_users_id = list(set([tup[0] for tup in profile_users_id]))
        
        return  cls.query.filter(            
            cls.profile_user_id.in_(profile_users_id), 
            cls.active()
            )


    @classmethod
    def after_report_teachers(cls, models:List, *args, **kwargs) -> List:
        
        pprint(models)

        # Listando a quantidade de aula dos professores
        all_lessons = db.session.query(Lesson.created_by, func.count(Lesson.id))\
            .filter(Lesson.created_by.in_(Domain.get_attribute_values(models, 'profile_user_id')))\
            .group_by(Lesson.created_by)\
            .all()


        all_activities = db.session.query(Activity.created_by, func.count(Activity.id))\
            .filter(Activity.created_by.in_(Domain.get_attribute_values(models, 'profile_user_id')))\
            .group_by(Activity.created_by)\
            .all()
        
        # Montando um objecto indexado pelo identificador do Professor:
        Tree = {}

        for model in models:
            if model['profile_user_id'] not in Tree: Tree[model['profile_user_id']] = model

        models = list(Tree.values())
        
        for model in models:
            model['lessons'] = 0
            model['activities'] = 0

            for tup in all_lessons: # (id, quantidade)
                if tup[0] == model['profile_user_id']:
                    model['lessons'] = tup[1]

            for tup in all_activities:
                if tup[0] == model['profile_user_id']:
                    model['activities'] = tup[1]

            model['total'] = model['activities']  + model['lessons']
            model['teacher'] = User.get_by_profile_user_id(model['profile_user_id']).to_dict()

        sorted(models, key=lambda x: x['total'])

        return models


    @classmethod
    def get_my_informations(cls, *args, **kwargs) -> Query:
        """
        Função para fazer o retorno das informações pessoais de um estudante ou professor
        """
        current_profile_user:ProfileUser = session['profile_user']

        return db.session.query(SchoolUnit).filter(SchoolUnit.id == cls.school_unit_id, cls.profile_user_id == current_profile_user.id)


    @classmethod
    def after_get_my_informations(cls, models:List, *args, **kwargs) -> List:
        current_profile_user:ProfileUser = session['profile_user']
        
        my_disciplines = current_profile_user.get_my_disciplines().all()
        
        #ClassesDiscipline.after_find(my_disciplines)

        models[0]['classes_disciplines']    = serialize_return(my_disciplines)
        models[0]['profile_user']           = current_profile_user.to_dict()
        models[0]['user']                   =  current_profile_user.user.to_dict()

        if current_profile_user.is_student():
            
            # Total de aulas do aluno:
            _total_lessons = Lesson.query.filter(
                Lesson.id == LessonClassesDiscipline.lesson_id,
                LessonClassesDiscipline.classes_discipline_id == ClassesDiscipline.id,
                StudentDiscipline.classes_discipline_id == ClassesDiscipline.id,
                ClassesDiscipline.id.in_(get_attribute_values(my_disciplines)),
                )\
                .count()
            
            # Total de aulas assistidas
            _watched_lessons = Lesson.query.filter(
                Lesson.id == LessonClassesDiscipline.lesson_id,
                LessonClassesDiscipline.classes_discipline_id == ClassesDiscipline.id,
                StudentDiscipline.classes_discipline_id == ClassesDiscipline.id,
                ClassesDiscipline.id.in_(get_attribute_values(my_disciplines)),
                StudentLessonClassesDiscipline.student_id == StudentDiscipline.id,
                StudentLessonClassesDiscipline.lesson_classes_discipline_id == LessonClassesDiscipline.id
                )\
                .count()       

            models[0]['graphic'] = [['Aulas', 'Aulas p/ Assistir'], [_total_lessons, (_total_lessons-_watched_lessons)]]

        else:
            models[0]['graphic'] = [['Aulas', 'Aulas p/ Assistir'], [5, 3]]
  
        """
        Premissas: um aluno só pode está matriculado a uma disciplina
        """       

        return models


    @classmethod
    def list_student_informations(cls, *args, **kwargs) -> Query:
        """
        Função para fazer o retorno das informações pessoais de um estudante
        """
        current_profile_user:ProfileUser = session['profile_user']

        return db.session.query(SchoolUnit).filter(SchoolUnit.id == cls.school_unit_id, cls.profile_user_id == current_profile_user.id)

    
    @classmethod
    def after_list_student_informations(cls, models:List, *args, **kwargs) -> List:
        
        current_profile_user:ProfileUser = session['profile_user']

        my_disciplines = current_profile_user.get_my_disciplines().all()

        my_disciplines = serialize_return(my_disciplines)

        ClassesDiscipline.after_find(my_disciplines)

        #pprint(my_disciplines)        

        """
        Premissas: um aluno só pode está matriculado a uma disciplina
        """
        models[0]['classes_disciplines'] = my_disciplines
        models[0]['profile_user'] = current_profile_user.to_dict()
        models[0]['user'] =  current_profile_user.user.to_dict()

        return models
           


class TeacherDiscipline(db.Model, Domain):
    # Relacionamento entre uma Turma e um Professor de uma unidade educacional:
    classes_discipline_id   = db.Column(db.String(36), db.ForeignKey('classes_discipline.id'), nullable=False)
    teacher_id              = db.Column(db.String(36), db.ForeignKey('profile_user.id'), nullable=False)


    @classmethod
    def before_upsert(cls, *args, **kwargs):

        """
        NOTE Importante notar que não é possível existir dois professores para uma mesma disciplina
        """
        current_teacher = TeacherDiscipline.query\
            .filter(cls.classes_discipline_id == kwargs['classes_discipline_id'], cls.teacher_id != kwargs['teacher_id'] ).first()

        if current_teacher:
            raise ApiException("Só é possível ter um professor matriculado à disciplina.")

        current = cls.query.filter_by(classes_discipline_id=kwargs['classes_discipline_id'], teacher_id=kwargs['teacher_id']).first()
        
        if current: 
            user = User.query.filter(current.teacher_id==ProfileUser.id, ProfileUser.user_id == User.id).first()
            raise ApiException("O professor(a) '{}' já se encontra matriculado à Disciplina.".format(user.email))
    

    @classmethod
    def list_my_disciplines(cls, teacher_id:str, *args, **kwargs) -> Query:
        return ClassesDiscipline.query \
            .filter(
                cls.teacher_id == teacher_id,
                cls.classes_discipline_id == ClassesDiscipline.id,
            )


    @classmethod
    def list_my_students(cls, teacher_id:str, *args, **kwargs) -> Query:
        return db.session.query(StudentDiscipline, ClassesDiscipline) \
            .filter(
                cls.teacher_id == teacher_id,
                cls.classes_discipline_id == ClassesDiscipline.id,
                StudentDiscipline.classes_discipline_id == ClassesDiscipline.id,
            )


    @classmethod
    def after_list_my_disciplines(cls, models:List, *args, **kwargs) -> List:
        pass

    
    @classmethod
    def after_find(cls, models:list, *args, **kwargs):
        ids = Domain.get_attribute_values(models, 'id')

        # Trazendo os Usuários e Perfis ao qual os modelos se relacionam
        join = db.session.query(TeacherDiscipline.id, User, SchoolDiscipline, SchoolPeriod, SchoolClass).filter(
            TeacherDiscipline.teacher_id == ProfileUser.id,
            ProfileUser.user_id == User.id,
            TeacherDiscipline.classes_discipline_id == ClassesDiscipline.id,
            ClassesDiscipline.school_class_id == SchoolClass.id,
            ClassesDiscipline.discipline_period_id == DisciplinePeriod.id,
            DisciplinePeriod.school_period_id == SchoolPeriod.id,
            DisciplinePeriod.discipline_grade_id == DisciplineGrade.id,
            DisciplineGrade.school_discipline_id == SchoolDiscipline.id,
            TeacherDiscipline.id.in_(ids)
        )
        
        join = join.all()

        pprint(join)

        for teacher_discipline in models:
            for tup in join:
                if tup[0]!=teacher_discipline['id']: continue
                for object in list(tup)[1:]:
                    teacher_discipline[object.__tablename__] = object.to_dict()



class StudentDiscipline(db.Model, Domain):
    # Relacionamento entre um Turma e um Aluno de uma unidade educacional:
    classes_discipline_id   = db.Column(db.String(36), db.ForeignKey('classes_discipline.id'), nullable=False)
    student_id              = db.Column(db.String(36), db.ForeignKey('profile_user.id'), nullable=False)


    @classmethod
    def after_find(cls, models:List, *args, **kwargs) -> List:
        objects = db.session.query(StudentDiscipline.id, ProfileUser, User)\
            .filter(StudentDiscipline.id.in_(Domain.get_attribute_values(models)), StudentDiscipline.student_id == ProfileUser.id, ProfileUser.user_id == User.id)\
            .all()

        for model in models:
            for tup in objects:
                if tup[0]!=model['id']:continue
                model['profile_user'] = tup[1].to_dict()
                model['user'] = tup[2].to_dict()


    @classmethod
    def before_upsert(cls, *args, **kwargs):
        current = cls.query.filter_by(classes_discipline_id=kwargs['classes_discipline_id'], student_id=kwargs['student_id']).first()

        if current: raise ApiException("Esse aluno já se encontra matriculado à essa Disciplina.")

        """
        Uma vez matriculado à uma disciplina de uma dada série, o aluno não pode conter matrículas para disciplinas de séries à frente.
        Ou menores.

        Por exemplo, não é possível um aluno que já possui uma matrícula para a 4º série receber uma nova matrícula de uma disciplina
        de outra série.
        """
        current_registration = cls.query.filter_by(student_id=kwargs['student_id']).first()

        # Casos em que é a primeira matrícula do aluno:
        if not current_registration: return

        # Verificando qual a série dessa disciplina ao qual estamos fazendo a associação com o aluno:
        target_school_grade = SchoolGrade.query.filter(
            ClassesDiscipline.id == kwargs['classes_discipline_id'],
            ClassesDiscipline.discipline_period_id == DisciplinePeriod.id,
            DisciplinePeriod.discipline_grade_id == DisciplineGrade.id,
            DisciplineGrade.unit_grade_id == UnitGrade.id,
            UnitGrade.school_grade_id == SchoolGrade.id
            ).first()

        student_school_grade = SchoolGrade.query.filter(
            ClassesDiscipline.id == current_registration.classes_discipline_id,
            ClassesDiscipline.discipline_period_id == DisciplinePeriod.id,
            DisciplinePeriod.discipline_grade_id == DisciplineGrade.id,
            DisciplineGrade.unit_grade_id == UnitGrade.id,
            UnitGrade.school_grade_id == SchoolGrade.id
            ).first()

        #print(target_school_grade.name, student_school_grade.name)

        if target_school_grade.id != student_school_grade.id:
            user = User.query.filter(ProfileUser.id == kwargs['student_id'], ProfileUser.user_id == User.id).first()

            user_name = user.name if user.name else user.email
            
            raise ApiException("O estudante '{}' já se encontra matriculado em disciplina(s) da '{}'. Não é possível matriculá-lo em disciplinas de outros períodos escolares."\
                .format(user_name, student_school_grade.name))
            

    @classmethod
    def list_my_disciplines(cls, student_id:str, *args, **kwargs) -> Query:
        return ClassesDiscipline.query \
            .filter(
                cls.student_id == student_id,
                cls.classes_discipline_id == ClassesDiscipline.id,
            )


    @classmethod
    def list_my_teachers(cls, student_id:str, *args, **kwargs) -> Query:
        return TeacherDiscipline.query \
            .filter(
                cls.student_id == student_id,
                cls.classes_discipline_id == ClassesDiscipline.id,
                TeacherDiscipline.classes_discipline_id == ClassesDiscipline.id,
            )



class UnitGradeLibrary(db.Model, Domain):
    library_id          = db.Column(db.String(36), db.ForeignKey('library.id'), nullable=False)
    unit_grade_id       = db.Column(db.String(36), db.ForeignKey('unit_grade.id'), nullable=False) # Modelo de sére/unidade educacional



"""
Modelos Intrísecos ao Modulo de Gestor de Rede
"""
class SchoolNet(db.Model, LogicalDomain):
    # Modelo de Rede Escolar
    name        = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)


    @classmethod
    def before_remove(cls, *args, **kwargs):
        if SchoolUnit.exists(school_net_id=kwargs['id']):
            raise ApiException("Não é possível excluir essa Rede Escolar. Há Unidades Escolares relacionadas à ela.")


    def get_profile_users(self) -> Query:
        """
        Função para listar os profile users de uma dada rede escolar
        """
        return ProfileUser.query.filter(
            SchoolUnit.school_net_id == self.id,
            SchoolUnitProfileUsers.school_unit_id == SchoolUnit.id, 
            SchoolUnitProfileUsers.profile_user_id == ProfileUser.id)


    def get_administrators(self, *args, **kwargs) -> Query:
        """
        Função para listar os profile users administradores de uma dada unidade educacional
        """
        return ProfileUser.query.filter(
            SchoolUnit.school_net_id == self.id,
            SchoolUnitProfileUsers.school_unit_id == SchoolUnit.id, 
            SchoolUnitProfileUsers.profile_user_id == ProfileUser.id,
            ProfileUser.profile_id == config.SCHOOL_NET_ADMINISTRATOR_ID
            )


    @classmethod
    def find(cls, *args, **kwargs) -> Query:
                
        # Carregando as redes que o usuário pode visualizar:
        profile_user:ProfileUser = session['profile_user']

        school_nets = profile_user.get_available_school_nets()

        ids = Domain.get_attribute_values(school_nets, 'id')
        
        logger.debug("Filtrando as redes disponíveis para um dado usuário: {}".format(ids))

        args = [*args, SchoolNet.id.in_(ids)]

        return cls.query.filter(*args)


    @classmethod
    def after_find(cls, models:list, *args, **kwargs):
        # Adicionando a estrutura de árvore 
        return [{**element, 'childs': cls.childs(element['id']) } for element in models]
     
    
    @classmethod
    def childs(cls, id:str, *args, **kwargs) -> List[dict]:
        return [model.to_dict() for model in SchoolUnit.query.filter(*[SchoolUnit.school_net_id == id, SchoolUnit.status != ModelStatus.DELETED.value]).all()]
        

    def after_remove(self, *args, **kwargs):
        """
        Validando deleções de redes escolares
        """
        # Não podemos permitir a deleção de Redes Educacionais se estas estiverem associadas à Administrações
        objects = Administration.query\
            .filter(*[
                Administration.id == AdministrationSchoolNet.administration_id, 
                AdministrationSchoolNet.school_network_id == self.id, 
                Administration.status != ModelStatus.DELETED.value,
                AdministrationSchoolNet.status != ModelStatus.DELETED.value]).all()
        
        if len(objects):
            names = [obj.name for obj in objects]
            raise ApiException("Não é possível deletar essa Rede Educacional. Há {} administradora(s) relacionada à ela: {}"\
                .format(len(objects), ', '.join(names)))


        # Não podemos permitir a deleção de Redes Educacionais se estas estiverem associadas à Unidades Educacionais
        objects = SchoolUnit.query\
            .filter(*[
                SchoolUnit.school_net_id == self.id, 
                SchoolUnit.status != ModelStatus.DELETED.value ]).all()
        
        if len(objects):
            names = [obj.name for obj in objects]
            raise ApiException("Não é possível deletar essa Rede Educacional. Há {} Unidade(s) relacionada(s) à ela: {}"\
                .format(len(objects), ', '.join(names)))


    def access_data(self, *args, **kwargs) -> List[str]:
        """
        Função que retorna todos os identificadores dos filhos dessa rede escolar.
        """
        childs = self.childs(self.id)
        return [data['id'] for data in childs]



class SchoolNetAdministrator(db.Model, LogicalDomain):
    # Usuário administrador da Rede Escolar
    school_net_id   = db.Column(db.String(36), db.ForeignKey('school_net.id'), nullable=False)
    profile_user_id     = db.Column(db.String(36), db.ForeignKey('profile_user.id'), nullable=False)


    def access_data(self, *args, **kwargs) -> List[str]:
        school_net = SchoolNet.get([SchoolNet.id == self.school_net_id])
        return school_net.access_data()




"""
Modelos Intrísecos ao Modulo de Admininstração
"""
class AdministrationSchoolNet(db.Model, LogicalDomain):
    # Relacionamento entre a administração e a Rede
    administration_id   = db.Column(db.String(36), db.ForeignKey('administration.id'), nullable=False)
    school_network_id   = db.Column(db.String(36), db.ForeignKey('school_net.id'), nullable=False)



class Administration(db.Model, LogicalDomain):
    # Modelo de Administração do Sistema
    name        = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)


    @classmethod
    def before_remove(cls, *args, **kwargs):
        if AdministrationSchoolNet.exists(administration_id=kwargs['id']):
            raise ApiException("Não é possível deletar essa Administração. Há Rede(s) atribuidas à ela.")



class Administrator(db.Model, LogicalDomain):
    # Usuário administrador do Modelo de Administração do Sistema
    administration_id   = db.Column(db.String(36), db.ForeignKey('administration.id'), nullable=False)
    profile_user_id     = db.Column(db.String(36), db.ForeignKey('profile_user.id'), nullable=False)



class Integrations(db.Model, LogicalDomain):
    name                = db.Column(db.String(100), nullable=False)
    domain              = db.Column(db.String(255), nullable=False)
    administration_id   = db.Column(db.String(36), db.ForeignKey('administration.id'), nullable=False)

    #TODO adicionar is_inboud



class IntegrationsTokens(db.Model, LogicalDomain):
    integrations_id     = db.Column(db.String(36), db.ForeignKey('integrations.id'), nullable=False)

    # Tempo, em ms, de validade do token de integração
    validate            = db.Column(db.Integer, nullable=True)



class Ticket(db.Model, LogicalDomain):
    # Modelo de Abertura de Chamado
    response_of             = db.Column(db.String(36), db.ForeignKey('ticket.id'), nullable=True)
    title                   = db.Column(db.String(150), nullable=False)
    description             = db.Column(db.String(255), nullable=True)
    administration_id       = db.Column(db.String(36), db.ForeignKey('administration.id'), nullable=False)



class TicketAttachment(db.Model, LogicalDomain):
    # Modelo de Anexo ao Ticket de Chamado
    integrations_id     = db.Column(db.String(36), db.ForeignKey('integrations.id'), nullable=False)
    attachment_id       = db.Column(db.String(36), db.ForeignKey('attachment.id'), nullable=False)

    #NOTE Integrar com serviço de arquivos


"""
Módulo de Controle de Acesso
"""

class Person(db.Model, LogicalDomain):
    name        = db.Column(db.String(100), nullable=False)
    last_name   = db.Column(db.String(100), nullable=False)
    born        = db.Column(db.Date(),      nullable=False)
    document    = db.Column(db.String(11),  nullable=False)
    user_id     = db.Column(db.String(36), db.ForeignKey('user.id'))

    
    @validates('user_id')
    def validate_user_id(self, key, value):
        if value is None:
            raise ApiException("Verifique a validade do Usuário. A chave '{}' não existe.".format(value)) 
            
        if not User.exists(id=value):
            raise ApiException("Verifique a validade do Usuário. A chave '{}' não existe.".format(value))
        
        return value

    
    @validates('born')
    def validate_born(self, key, value):
        if value is None:
            raise ApiException("Verifique a validade do Nascimento.") 

        if isinstance(value, str):
            try:
                value = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").date()
            except ValueError:
                value = value.split('T')[0]
                try:
                    value = datetime.strptime(value, "%Y-%m-%d").date()
                except ValueError:
                    raise ApiException("Verifique a formatação do atributo de Nascimento: '{}'".format(value))
            
               
        return value



class ProfilePermission(db.Model, LogicalDomain):
    permission_id   = db.Column(db.String(36), db.ForeignKey('permission.id'), nullable=False)
    profile_id      = db.Column(db.String(36), db.ForeignKey('profile.id'), nullable=False)



class Permission(db.Model, LogicalDomain):
    name        = db.Column(db.String(150), unique=True, nullable=False)
    alias       = db.Column(db.String(150), nullable=True)
    function    = db.Column(db.String(255), nullable=True)
    is_system   = db.Column(db.Boolean(), nullable=False, default=False)
        
    __dict_permissions__ = {
        'create':       'Criar', 
        'find':         'Listar', 
        'find_by_id':   'Listar Algum(a)', 
        'remove':       'Remover', 
        'update':       'Atualizar', 
        'duplicate':'Duplicar'
        }


    def set_default_alias(self, *args, **kwargs):
        model, permission = self.name.split('#')
                
        self.alias = "{} {}".format(self.__dict_permissions__.get(permission, permission), model.capitalize()) 


    @classmethod
    def possible_permissions(cls,
        std_permissions=('create', 'find', 'find_by_id', 'remove', 'update', 'duplicate'),
        *args, 
        **kwargs) -> list:
        """
        Função para montar todas as permissões possíveis da aplicação
        """
        models = Domain.childs()

        # Filtrando somente os modelos que são persistíveis
        models = [model for model in models if hasattr(model, '__tablename__')]

        # Filtrando o nome das tabelas
        models = [model.__tablename__ for model in models]

        # Adicionando as permissões para cada modelo:
        return ["{}#{}".format(model, permission_name) for model in models for permission_name in std_permissions]


    def after_remove(self, *args, **kwargs):
        if self.is_system:
            raise ApiException("Não é possível deletar permissões de sistema.")
        
        profiles = Profile.query\
            .filter(*[Profile.id == ProfilePermission.profile_id, ProfilePermission.permission_id == self.id, ProfilePermission.status != ModelStatus.DELETED.value ]).all()

        if len(profiles):
            raise ApiException("Não é possível deletar essa Permissão. Há {} perfil(is) com atribuição para essa Permissão.".format(len(profiles)))


from app.models.school_discipline import SchoolDiscipline
from app.models.school_class import SchoolClass
from app.models.school_period import SchoolPeriod

from app.models.classes_discipline import ClassesDiscipline
from app.models.profile_user import ProfileUser
from app.models.profile import Profile
from app.models.user import User
from app.models.history import History
from app.models.configuration import Configuration
from app.models.configuration_profile import ConfigurationProfile
from app.models.enums import ModelStatus
