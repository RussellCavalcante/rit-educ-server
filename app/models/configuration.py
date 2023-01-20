from app.models import db, LogicalDomain, List, Dict, Query, validates, pprint


class Configuration(db.Model, LogicalDomain):
    name                    = db.Column(db.String(255), nullable=False)
    description             = db.Column(db.String(255), nullable=True)
    logo                    = db.Column(db.Text(), nullable=False)
    

    @classmethod
    def after_find(cls, models:List, *args, **kwargs) -> List:
        
        from app.models import Profile
        from app.models.configuration_profile import ConfigurationProfile   
      
        relationships = db.session.query(ConfigurationProfile, Profile)\
            .filter(
                Configuration.id.in_(cls.get_attribute_values(models)),
                ConfigurationProfile.configuration_id == Configuration.id,
                ConfigurationProfile.profile_id == Profile.id
            )\
            .all()


        for model in models:
            for configuration_profile, profile in relationships:
                if configuration_profile.configuration_id == model['id']:
                    if not 'profiles' in model:
                        model['profiles'] = []

                    model['profiles'].append(profile.to_dict())
                    

        return models