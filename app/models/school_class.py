from app.models import db, Domain, LogicalDomain, ApiException, List, Dict, Query, validates, pprint, pformat, and_, asc, desc
from app.models import SchoolDiscipline, DisciplineGrade
from app.models.enums import ModelStatus


class SchoolClass(db.Model, LogicalDomain):
    # Modelo de Turma Escolar. P.e.: Metemática Tuma A, Português Turma B, Geografia Turma C
    name                    = db.Column(db.String(100), nullable=False)
    description             = db.Column(db.String(255), nullable=True)


    @classmethod
    def before_remove(cls, *args, **kwargs):
        from app.models import ClassesDiscipline

        if ClassesDiscipline.exists(school_class_id=kwargs['id']):
            raise ApiException("Não é possível realizar essa operação. Existem Disciplinas Escolares relacinadas à essa Turma.")


        # Verificando se há alunos e professores associados à essa Turma


    @classmethod
    def after_find(cls, models:List, *args, **kwargs):
        """
        Carregando objetos que se relacionam com esse modelo: Disciplina.
        """
        ids = Domain.get_attribute_values(models, 'id')

        join_school_discipline = db.session.query(SchoolDiscipline) \
            .filter(
                cls.discipline_id == DisciplineGrade.id,
                DisciplineGrade.school_discipline_id == SchoolDiscipline.id,
                DisciplineGrade.status != ModelStatus.DELETED.value,
                cls.id.in_(ids)
            )\
            .all()

        """
        Montando os objetos:
        """
        for _join in join_school_discipline:
            for _object in models:
                if _object['school_discipline_id'] == _join.id:
                    _object['school_discipline'] = _join.to_dict()


