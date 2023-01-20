from app.models import db, Domain, List, Dict, Query, validates, pprint


class ConfigurationProfile(db.Model, Domain):
    configuration_id    = db.Column(db.String(36), db.ForeignKey('configuration.id'), nullable=False)
    profile_id          = db.Column(db.String(36), db.ForeignKey('profile.id'), nullable=False)
    
    

    