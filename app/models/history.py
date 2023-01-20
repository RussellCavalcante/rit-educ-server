from app.utils import logger, ApiException
from app.models import db, LogicalDomain

class History(db.Model, LogicalDomain):
    type    = db.Column(db.String(50), nullable=False, default='LOGIN')
