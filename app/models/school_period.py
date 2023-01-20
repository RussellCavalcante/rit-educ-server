from app.models import db, Domain, LogicalDomain, ApiException, List, Dict, Query, validates, pprint, pformat, and_, asc, desc
from app.models import SchoolDiscipline, DisciplineGrade, parse_date
from app.models.enums import ModelStatus


class SchoolPeriod(db.Model, LogicalDomain):
    name                    = db.Column(db.String(255), nullable=True)
    description             = db.Column(db.String(255), nullable=True)
    begin                   = db.Column(db.Date(), nullable=True)
    end                     = db.Column(db.Date(), nullable=False)


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
    def before_remove(cls, *args, **kwargs):
        from app.models import DisciplinePeriod

        if DisciplinePeriod.exists(school_period_id=kwargs['id']):
            raise ApiException("Não é possível realizar essa operação. Existem Disciplinas relacionadas à esse Período.")


    @classmethod
    def relationship_school_discipline_school_period(cls, *args, **kwargs) -> Query:
        """
        Função para carregar os períodos atrelados à alguma disciplina.
        """
        left_condition_1 = [
            SchoolDisciplinePeriod.school_period_id == SchoolPeriod.id,
            SchoolDisciplinePeriod.school_discipline_id == kwargs['school_discipline_id'], 
            SchoolDisciplinePeriod.status != ModelStatus.DELETED.value]

        return db.session.query(cls, SchoolDiscipline.id) \
            .join(SchoolDisciplinePeriod, and_(*left_condition_1), isouter=True)\
            .join(SchoolDiscipline, SchoolDiscipline.id == SchoolDisciplinePeriod.school_discipline_id, isouter=True)\

    
    @classmethod
    def after_relationship_school_discipline_school_period(cls, models:List, *args, **kwargs) -> List:
        logger.debug('after_relationship_school_discipline_school_period')
        data:list = []

        pprint(models)
        #input("...")

        ids = Domain.get_attribute_values([tup[0] for tup in models], 'id')

        for main_object, relationship_id in models:
            main_object['__checked__'] = True if relationship_id else False
            data.append(main_object)

        return data

