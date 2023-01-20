from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource, Api
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from flask_login import LoginManager
from flask_cors import CORS
from flask_jwt_extended import JWTManager

server = Flask(__name__)
# app.config.from_object('config')
banco = SQLAlchemy()
migrate = Migrate(server, banco)
banco.init_app(server)
api = Api(server)
cors = CORS(server)
jwt = JWTManager(server)
manager = Manager(server)
manager.add_command('db',MigrateCommand)


lm = LoginManager()
lm.init_app(server)


# flask_app = Flask('app_name', config.APP_NAME)
# flask_app.secret_key = 'redefinir secret key'


# from .utils.blueprints import declare_api_routes
# declare_api_routes(app=flask_app)


# from app.models import tables, forms
# from app.controllers import services

from app.models import *
from app.services import *
from app.config import *

