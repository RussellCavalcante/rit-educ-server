from app.models import db, Domain, LogicalDomain, ApiException, List, Dict, Query, validates, pprint, pformat, and_, asc, desc, session
from app.models import SchoolDiscipline, DisciplineGrade, StudentDiscipline, SchoolClass, SchoolPeriod, SchoolDiscipline, SchoolGrade, SchoolUnit,\
    DisciplinePeriod, UnitGrade, TeacherDiscipline
from app.models.enums import ModelStatus


class ClassesDiscipline(db.Model, Domain):
    """
    Relacionamento entre uma Turma Escolar (SchoolClass) e a Disciplina Associada ao Período, Série e Unidade escolar
    """
    discipline_period_id    = db.Column(db.String(36), db.ForeignKey('discipline_period.id'), nullable=False)
    school_class_id         = db.Column(db.String(36), db.ForeignKey('school_class.id'), nullable=False) 


    lesson_classes_discipline = db.relationship('LessonClassesDiscipline', backref='classes_discipline', lazy=True)


    @classmethod
    def before_remove(cls, *args, **kwargs):
        
        # Não podemos permitir remoções quando há matriculas ativas
        
        current:cls = cls.query.filter_by(**kwargs).first()

        if StudentDiscipline.exists(classes_discipline_id=current.id):
            raise ApiException("Não é possível realizar essa operação. Existem alunos matriculados à essa Disciplina ({})".format(current.classe_discipline_name))
        
        if TeacherDiscipline.exists(classes_discipline_id=current.id):
            raise ApiException("Não é possível realizar essa operação. Existem professores matriculados à essa Disciplina ({})".format(current.classe_discipline_name))


    @classmethod
    def my_classes_disciplines(cls, *args, **kwargs) -> Query:

        current_profile_user = session['profile_user']

        # Listando as turmas que possuem aulas cadastradas:

        if current_profile_user.is_student():
            my_disciplines = StudentDiscipline.list_my_disciplines(current_profile_user.id).all()

        else:
            my_disciplines = TeacherDiscipline.list_my_disciplines(current_profile_user.id).all()

        classes_disciplines_id = Domain.get_attribute_values(my_disciplines, 'id')

        return db.session.query(cls, SchoolClass, SchoolPeriod, SchoolDiscipline, SchoolGrade, SchoolUnit)\
            .filter(
                ClassesDiscipline.id.in_(classes_disciplines_id),
                ClassesDiscipline.school_class_id           == SchoolClass.id,
                ClassesDiscipline.discipline_period_id      == DisciplinePeriod.id,
                DisciplinePeriod.school_period_id           == SchoolPeriod.id,
                DisciplinePeriod.discipline_grade_id        == DisciplineGrade.id,
                DisciplineGrade.school_discipline_id        == SchoolDiscipline.id,
                DisciplineGrade.unit_grade_id               == UnitGrade.id,
                UnitGrade.school_grade_id                   == SchoolGrade.id,
                UnitGrade.school_unit_id                    == SchoolUnit.id,
            )\
            .order_by(asc(SchoolUnit.name)) \
            .order_by(asc(SchoolGrade.name))


    @classmethod
    def after_my_classes_disciplines(cls, models:List, *args, **kwargs) -> List:
        from app.models import User, ProfileUser

        data:List = []
        
        for model, school_class, school_period, school_discipline, school_grade, school_unit in models:
            model['school_class'] = school_class
            model['school_period'] = school_period
            model['school_discipline'] = school_discipline
            model['school_grade'] = school_grade
            model['school_unit'] = school_unit

            # Pegando o professor:
            _user = User.query.filter(
                    TeacherDiscipline.classes_discipline_id     == model['id'],
                    TeacherDiscipline.teacher_id                == ProfileUser.id,
                    ProfileUser.user_id                         == User.id
                ).first()

            model['teacher'] = _user.to_dict() if _user else _user

            data.append(model)

        return data

    
    @classmethod
    def teacher_classes_disciplines(cls, *args, **kwargs) -> Query:
        current_profile_user = session['profile_user']

        # Listando as turmas que possuem aulas cadastradas:

        if current_profile_user.is_student():
            my_disciplines = StudentDiscipline.list_my_disciplines(current_profile_user.id).all()

        else:
            my_disciplines = TeacherDiscipline.list_my_disciplines(current_profile_user.id).all()

        classes_disciplines_id = Domain.get_attribute_values(my_disciplines, 'id')

        return db.session.query(cls, SchoolClass, SchoolPeriod, SchoolDiscipline, SchoolGrade, SchoolUnit)\
            .filter(
                ClassesDiscipline.id.in_(classes_disciplines_id),
                ClassesDiscipline.school_class_id           == SchoolClass.id,
                ClassesDiscipline.discipline_period_id      == DisciplinePeriod.id,
                DisciplinePeriod.school_period_id           == SchoolPeriod.id,
                DisciplinePeriod.discipline_grade_id        == DisciplineGrade.id,
                DisciplineGrade.school_discipline_id        == SchoolDiscipline.id,
                DisciplineGrade.unit_grade_id               == UnitGrade.id,
                UnitGrade.school_grade_id                   == SchoolGrade.id,
                UnitGrade.school_unit_id                    == SchoolUnit.id
            )\
            .order_by(asc(SchoolUnit.name)) \
            .order_by(asc(SchoolGrade.name))


    @classmethod
    def after_teacher_classes_disciplines(cls, models:List, *args, **kwargs) -> List:
        from app.models import ProfileUser, User, Activity, ActivityStudent, Lesson, LessonClassesDiscipline, StudentLessonClassesDiscipline

        data:List = []
        
        for model, school_class, school_period, school_discipline, school_grade, school_unit in models:
            model['school_class'] = school_class
            model['school_period'] = school_period
            model['school_discipline'] = school_discipline
            model['school_grade'] = school_grade
            model['school_unit'] = school_unit

            data.append(model)

        models = data

        # Listando os alunos de cada disciplina
        for model in models:
            users = User.query.filter(
                StudentDiscipline.classes_discipline_id == model['id'], 
                StudentDiscipline.student_id == ProfileUser.id,
                ProfileUser.user_id == User.id
                )

            model['qtd_students'] = users.count()
        
        
        # Verificando a quantidade de atividades da turma e as devidas interações dos alunos com ela
        for model in models:
            activities = db.session.query(Activity, ActivityStudent)\
                .join(ActivityStudent, ActivityStudent.activity_id == Activity.id, isouter=True)\
                .filter(Activity.class_id == model['id'])\
                .all()
            
            lessons = db.session.query(Lesson, StudentLessonClassesDiscipline)\
                .filter(
                    LessonClassesDiscipline.classes_discipline_id == model['id'],
                    LessonClassesDiscipline.lesson_id == Lesson.id,
                    )\
                .all()
            
            # Montando as atividades:
            model['activities'] = len(set([tup[0].id for tup in activities]))
            model['lessons'] = len(set([tup[0].id for tup in lessons]))


        return data

    
    @classmethod
    def before_find(cls, *args, **kwargs) -> List:
        from app.models import ProfileUser

        profile_user:ProfileUser = session['profile_user']

        my_disciplines = profile_user.get_my_disciplines().all()

        return [ClassesDiscipline.id.in_(Domain.get_attribute_values(my_disciplines))]
        

    @classmethod
    def after_find(cls, models:list, *args, **kwargs):

        ids = Domain.get_attribute_values(models, 'id')

        objects = db.session.query(ClassesDiscipline.id, SchoolUnit, SchoolGrade, SchoolPeriod, SchoolDiscipline, SchoolClass)\
            .filter(
                ClassesDiscipline.id.in_(ids),
                ClassesDiscipline.school_class_id           == SchoolClass.id,
                ClassesDiscipline.discipline_period_id      == DisciplinePeriod.id,
                DisciplinePeriod.school_period_id           == SchoolPeriod.id,
                DisciplinePeriod.discipline_grade_id        == DisciplineGrade.id,
                DisciplineGrade.school_discipline_id        == SchoolDiscipline.id,
                DisciplineGrade.unit_grade_id               == UnitGrade.id,
                UnitGrade.school_grade_id                   == SchoolGrade.id,
                UnitGrade.school_unit_id                    == SchoolUnit.id
            )\
        
        for model in models:
            for join in objects:
                if join[0] != model['id']: continue
                for instance in join[1:]: model[instance.__tablename__] = instance.to_dict()

        return models


    @classmethod
    def lesson_checked(cls, *args, **kwargs) -> Query:
        """
        Função utilizada na tela de Aulas para poder marcar as Turmas atualmente marcadas para alguma dada Aula.

        Filtrar as turmas ao qual o professor pode visualizar.
        """
        current_profile_user:ProfileUser = session['profile_user']
                
        return cls.query\
            .join(SchoolClass, cls.school_class_id == SchoolClass.id)\
            .filter(cls.id.in_(Domain.get_attribute_values(current_profile_user.get_my_disciplines().all())))\
            .order_by(desc(SchoolClass.name))


    @classmethod
    def after_lesson_checked(cls, models:List, *args, **kwargs):        
        ids = Domain.get_attribute_values(models)

        from app.models import LessonClassesDiscipline
        
        objects = LessonClassesDiscipline.query.filter(
            LessonClassesDiscipline.lesson_id == kwargs['lesson_id'],
            LessonClassesDiscipline.classes_discipline_id.in_(ids)
        )

        objects = objects.all()
        
        for model in models:
            model['__checked__']    = False
            
            for object in objects:
                if object.classes_discipline_id == model['id']: 
                    model['__checked__'] = True
                    model['validate'] = object.validate
                    model['hour'] =     object.hour
                    model['begin'] =    object.cast_date(object.begin) 


        cls.after_find(models, *args, **kwargs)

        return models


    @classmethod
    def list_others_lessons(cls, *args, **kwargs) -> List:
        """
        Função chamada na tela de aula para listar as aulas, de outras disciplinas, ocorrendo no mesmo dia.
        """
        current_classes_discipline = cls.query.filter_by(id=kwargs['classes_discipline_id']).first()
        current_school_unit:SchoolUnit = current_classes_discipline.school_unit

        date_to_check = kwargs.get('begin', None)

        if not date_to_check:
            raise ApiException("É necessário informar uma data válida para essa função.")
        
        from app.utils import parse_date
        from app.models import Lesson, LessonClassesDiscipline

        date_to_check = parse_date(date_to_check) 

        """
        Listando todas as disciplinas com aulas marcadas para esse mesmo dia. A disciplina deve ser da mesma unidade escolar, pois os alunos
        pertencem à unidades escolares.
        """
        classes_disciplines_on_school_unit = current_school_unit.get_disciplines(query=[cls.id]).all()

        query = db.session.query(ClassesDiscipline, LessonClassesDiscipline, Lesson)\
            .filter(
                cls.id.in_(classes_disciplines_on_school_unit),
                LessonClassesDiscipline.classes_discipline_id == cls.id,
                LessonClassesDiscipline.lesson_id == Lesson.id,
                Lesson.active(),
                LessonClassesDiscipline.begin == date_to_check
            )\
            .order_by(asc(LessonClassesDiscipline.hour))

        query = query.all()

        data:List = []

        for classes_discipline, lesson_classes_discipline, lesson in query:
            data.append({
                'school_discipline': classes_discipline.school_discipline.name,
                'school_grade': classes_discipline.school_grade.name,
                'hour': lesson_classes_discipline.hour,
                'begin': lesson_classes_discipline.cast_date(lesson_classes_discipline.begin),
                'lesson': lesson.name
            })

        return data

    
    @classmethod
    def user_checked(cls, *args, **kwargs) -> Query:
        """
        Função para retornar as disciplinas escolares ao qual um dado usuário está matriculado
        """
        from app.models import ProfileUser, SchoolUnit

        current_profile_user:ProfileUser = session['profile_user']

        my_school_units = current_profile_user.get_my_school_units(columns=[SchoolUnit.id]).subquery()
                
        return cls.query\
            .filter(
                ClassesDiscipline.school_class_id           == SchoolClass.id,
                ClassesDiscipline.discipline_period_id      == DisciplinePeriod.id,
                DisciplinePeriod.school_period_id           == SchoolPeriod.id,
                DisciplinePeriod.discipline_grade_id        == DisciplineGrade.id,
                DisciplineGrade.school_discipline_id        == SchoolDiscipline.id,
                DisciplineGrade.unit_grade_id               == UnitGrade.id,
                UnitGrade.school_grade_id                   == SchoolGrade.id,
                UnitGrade.school_unit_id.in_(my_school_units)
            )\
            .order_by(desc(SchoolClass.name))


    @classmethod
    def after_user_checked(cls, models:List, *args, **kwargs):   
        from app.models import ProfileUser, User

        profile_user = ProfileUser.query.filter(
            User.id == kwargs['user_id'],
            ProfileUser.user_id == User.id,
            ).first()

        models = cls.after_find(models, *args, **kwargs)

        if profile_user.is_student():
            registrations = db.session.query(ClassesDiscipline.id)\
                .filter(
                    ClassesDiscipline.id == StudentDiscipline.classes_discipline_id,
                    StudentDiscipline.student_id == ProfileUser.id, 
                    ProfileUser.user_id == kwargs['user_id']).all()

        else:

            # Carregando os registros atuais de matrícula do professor:
            registrations = db.session.query(ClassesDiscipline.id)\
                .filter(
                    ClassesDiscipline.id == TeacherDiscipline.classes_discipline_id,
                    TeacherDiscipline.teacher_id == ProfileUser.id, 
                    ProfileUser.user_id == kwargs['user_id']).all()

            # Carregando quais as disciplinas que já possuem um professor matriculado que não seja o nosso user_id
            disciplines_has_other_teacheres = db.session.query(ClassesDiscipline.id)\
                .filter(
                    ClassesDiscipline.id == TeacherDiscipline.classes_discipline_id,
                    TeacherDiscipline.teacher_id == ProfileUser.id,
                    ProfileUser.user_id != kwargs['user_id'],
                    ProfileUser.active()
                ).all()

            disciplines_has_other_teacheres = [t[0] for t in disciplines_has_other_teacheres]

            for model in models:
                model['__blocked__'] = False

                # Se essa disciplina está na lista de disciplinas com outros professores:
                if model['id'] in disciplines_has_other_teacheres:
                    model['__blocked__'] = True


        registrations = [t[0] for t in registrations]
        
        for model in models:
            model['__checked__'] = False
           
            for r in registrations:
                if model['id'] in registrations: 
                    model['__checked__'] = True

        return models


    @classmethod
    def get_classe_discipline_name(cls, models:List, *args, **kwargs):
        
        objects = db.session.query(ClassesDiscipline.id, SchoolClass.name, SchoolPeriod.name, SchoolDiscipline.name, SchoolGrade.name, SchoolUnit.name)\
            .filter(
                ClassesDiscipline.id.in_(Domain.get_attribute_values(models, 'id')),
                ClassesDiscipline.school_class_id           == SchoolClass.id,
                ClassesDiscipline.discipline_period_id      == DisciplinePeriod.id,
                DisciplinePeriod.school_period_id           == SchoolPeriod.id,
                DisciplinePeriod.discipline_grade_id        == DisciplineGrade.id,
                DisciplineGrade.school_discipline_id        == SchoolDiscipline.id,
                DisciplineGrade.unit_grade_id               == UnitGrade.id,
                UnitGrade.school_grade_id                   == SchoolGrade.id,
                UnitGrade.school_unit_id                    == SchoolUnit.id
            )\
            .all()

        for model in models:
            for tup in objects:
                if tup[0] != model['id']: continue
                model['name'] = '{} - {} - {} - {} - {}'.format(*tup[1:])
                model['school_discipline_name'] = tup[3]
    
    @property
    def classe_discipline_name(self) -> str:
        
        objects = db.session.query(SchoolClass.name, SchoolPeriod.name, SchoolDiscipline.name, SchoolGrade.name, SchoolUnit.name)\
            .filter(
                ClassesDiscipline.id                        == self.id,
                ClassesDiscipline.school_class_id           == SchoolClass.id,
                ClassesDiscipline.discipline_period_id      == DisciplinePeriod.id,
                DisciplinePeriod.school_period_id           == SchoolPeriod.id,
                DisciplinePeriod.discipline_grade_id        == DisciplineGrade.id,
                DisciplineGrade.school_discipline_id        == SchoolDiscipline.id,
                DisciplineGrade.unit_grade_id               == UnitGrade.id,
                UnitGrade.school_grade_id                   == SchoolGrade.id,
                UnitGrade.school_unit_id                    == SchoolUnit.id
            )\
            .first()

        return '{} - {} - {} - {} - {}'.format(*objects)

    
    @property
    def school_class(self) -> Domain:
        if not hasattr(self, '_school_class'):
            self._school_class = SchoolClass.query\
                .filter(
                    ClassesDiscipline.id                        == self.id,
                    ClassesDiscipline.school_class_id           == SchoolClass.id,
                ).first()

        return self._school_class


    @property
    def school_discipline(self) -> Domain:
        if not hasattr(self, '_school_discipline'):

            self._school_discipline = SchoolDiscipline.query\
                .filter(
                        ClassesDiscipline.id                        == self.id,
                        ClassesDiscipline.school_class_id           == SchoolClass.id,
                        ClassesDiscipline.discipline_period_id      == DisciplinePeriod.id,
                        DisciplinePeriod.school_period_id           == SchoolPeriod.id,
                        DisciplinePeriod.discipline_grade_id        == DisciplineGrade.id,
                        DisciplineGrade.school_discipline_id        == SchoolDiscipline.id,
                ).first()

        return self._school_discipline


    @property
    def school_grade(self) -> Domain:
        if not hasattr(self, '_school_grade'):

            self._school_grade = SchoolGrade.query\
                .filter(
                        ClassesDiscipline.id                == self.id,
                        ClassesDiscipline.school_class_id           == SchoolClass.id,
                        ClassesDiscipline.discipline_period_id      == DisciplinePeriod.id,
                        DisciplinePeriod.school_period_id           == SchoolPeriod.id,
                        DisciplinePeriod.discipline_grade_id        == DisciplineGrade.id,
                        DisciplineGrade.school_discipline_id        == SchoolDiscipline.id,
                        DisciplineGrade.unit_grade_id               == UnitGrade.id,
                        UnitGrade.school_grade_id                   == SchoolGrade.id,
                ).first()

        return self._school_grade


    @property
    def school_unit(self) -> Domain:
        if not hasattr(self, '_school_unit'):

            self._school_unit = SchoolUnit.query\
                .filter(
                    ClassesDiscipline.id                == self.id,
                    ClassesDiscipline.school_class_id           == SchoolClass.id,
                    ClassesDiscipline.discipline_period_id      == DisciplinePeriod.id,
                    DisciplinePeriod.school_period_id           == SchoolPeriod.id,
                    DisciplinePeriod.discipline_grade_id        == DisciplineGrade.id,
                    DisciplineGrade.school_discipline_id        == SchoolDiscipline.id,
                    DisciplineGrade.unit_grade_id               == UnitGrade.id,
                    UnitGrade.school_grade_id                   == SchoolGrade.id,
                    UnitGrade.school_unit_id                    == SchoolUnit.id
                ).first()

        return self._school_unit


    @classmethod
    def complete_query(cls) -> List:
        return [ClassesDiscipline.school_class_id           == SchoolClass.id,
                ClassesDiscipline.discipline_period_id      == DisciplinePeriod.id,
                DisciplinePeriod.school_period_id           == SchoolPeriod.id,
                DisciplinePeriod.discipline_grade_id        == DisciplineGrade.id,
                DisciplineGrade.school_discipline_id        == SchoolDiscipline.id,
                DisciplineGrade.unit_grade_id               == UnitGrade.id,
                UnitGrade.school_grade_id                   == SchoolGrade.id,
                UnitGrade.school_unit_id                    == SchoolUnit.id]
