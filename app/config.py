# import os.path
# basedir = os.path.abspath(os.path.dirname(__file__))


from flask import Flask, jsonify
from flask_restful import Resource, Api 
from flask_jwt_extended import JWTManager
from blacklist import BLACKLIST
from flask_cors import CORS
from app.services.user import *
from flask_migrate import Migrate, MigrateCommand
from flask_sqlalchemy import SQLAlchemy
from app import server, jwt, banco
from app.blueprints import avaliable_route


server.register_blueprint(avaliable_route)

# SQLALCHEMY_DATABASE_URI = 'postgres://russellcavalcante:1128@localhost:5432/rit_educ_database'
server.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://russellcavalcante:1128@localhost:5432/rit_educ_database'
server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
SQLALCHEMY_TRACK_MODIFICATIONS = False
server.config['JWT_SECRET_KEY'] = 'DontTellAnyone'
server.config['JWT_BLACKLIST_ENABLED'] = True

@server.before_first_request

def cria_banco():
    banco.create_all()
    


@jwt.token_in_blacklist_loader
def verifica_blacklist(token):
    return token['jti'] in BLACKLIST

@jwt.revoked_token_loader
def token_de_acesso_invalidado():
    return jsonify({'message': 'vc foi deslogado'}), 401


# DEBUG = True


# SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'storage.db')
# server.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://russellcavalcante:1128@localhost:5432/rit_educ_database'
# SQLALCHEMY_TRACK_MODIFICATIONS =  True

# SECRET_KEY = 'UM-NOME-BEM-SEGURO'