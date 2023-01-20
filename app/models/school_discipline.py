from app.models import db, Domain, LogicalDomain, ApiException, List, Dict, Query, validates, pprint, pformat, and_, asc, desc
from app.models.enums import ModelStatus


class SchoolDiscipline(db.Model, LogicalDomain):
    # Modelo de Disciplina Escolar. P.e.: Metemática, Português, Geografia
    name                = db.Column(db.String(100), nullable=False)
    description         = db.Column(db.String(255), nullable=True)    


    @classmethod
    def after_find(cls, models:list, *args, **kwargs):
        """
        Carregando objetos que se relacionam com esse modelo: Turma e Série.
        """
        from app.models import SchoolClass, SchoolGrade

        # Carregando as turmas e a série das disciplinas:
        ids = Domain.get_attribute_values(models, 'id')

        join_school_classes = db.session.query(SchoolClass) \
            .filter(
                SchoolClass.school_discipline_id == cls.id,
                SchoolClass.status != ModelStatus.DELETED.value,
                cls.id.in_(ids)
            )\
            .all()
        
        join_school_grades = db.session.query(SchoolGrade) \
            .filter(
                cls.school_grade_id == SchoolGrade.id,
                SchoolGrade.status != ModelStatus.DELETED.value,
                cls.id.in_(ids)
            )\
            .all()

        """
        Montando os objetos:
        """
        for _school_grade in join_school_grades:
            for _object in models:
                if _object['school_grade_id'] == _school_grade.id:
                    _object['school_grade'] = _school_grade.to_dict()


        for _object in models:
            _object['school_class'] = []
        

        for _join in join_school_classes:
            for _object in models:
                if _join.school_discipline_id == _object['id']:
                    _object['school_class'].append(_join.to_dict())


        for _object in models:
            _object['begin'] = _object['begin'] + 'T00:00:00'
            _object['end'] = _object['end'] + 'T00:00:00'


    @classmethod
    def before_create(cls, *args, **kwargs):
        if cls.get([cls.name == kwargs['name'], cls.status != ModelStatus.DELETED.value], with_status=False):
            raise ApiException("Já existe uma Disciplina com esse nome.")

    
    @classmethod
    def active_periods(cls, *args, **kwargs) -> Query:
        input("...")
        #return cls.query.filter(DisciplinePeriod.dis == cls.id, SchoolDisciplinePeriod.status == ModelStatus.ACTIVE.value)


