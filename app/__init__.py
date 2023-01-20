from os import environ, getenv
from typing import Text
from flask import Flask, request, jsonify, Blueprint, current_app, make_response, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from flask_migrate import Migrate
from flask_cors import CORS as Cors
from app.config import BaseConfig as config


db_metadata = MetaData(naming_convention=config.DB_CONVENTION)
db = SQLAlchemy(metadata=db_metadata)
migrate = Migrate()


def parse_terminal(*args, **kwargs):
    import argparse

    import os
    import sys

    parser = argparse.ArgumentParser(description='List the content of a folder')

    parser.add_argument('-env',
                        type=str,
                        default='DEBUG',
                        required=False,
                        help='Ambiente da aplicação')

    return vars(parser.parse_args())
    

def create_app(
    app_name:Text='RIT_EDUC', 
    with_port:bool=True, 
    default_port:int=5000,
    *args, 
    **kwargs):
    
    global db
    global migrate

    config.APP_ENV  = kwargs.get('env', getenv('APP_ENV', 'DEBUG'))
    config.APP_NAME = "%s_%s" % (app_name, config.APP_ENV)
    config.DEBUG    = True if config.APP_ENV in config.DEBUG_MODE else False

    config.DATABASE_URI_ENV = '%s_DATABASE_URL' % (config.APP_NAME)
    config.DB_NAME  = config.APP_NAME.lower()
    # config.SQLALCHEMY_DATABASE_URI = getenv(config.DATABASE_URI_ENV)
    config.SQLALCHEMY_DATABASE_URI = 'postgres://russellcavalcante:1128@localhost:5432/riteduc'

    if not config.SQLALCHEMY_DATABASE_URI: raise RuntimeError("Verifique o caminho para o banco de dados. Variável de ambiente necessária: '{}'".format(config.DATABASE_URI_ENV))
    
    flask_app = Flask(kwargs.get('app_name', config.APP_NAME))
    flask_app.secret_key = 'redefinir secret key'

    Cors(flask_app)

    # Inicializando as variáveis configuradoras da aplicação:
    flask_app.config.from_object(config)
    
    """
    Declarando as Rotas:
    """
    from .utils.blueprints import declare_api_routes
    declare_api_routes(app=flask_app, url_prefix='/api')

    """
    Declarando os capturadores de erros:
    """
    from .utils.exceptions import declare_api_error_handlers
    declare_api_error_handlers(flask_app)
   
    db.init_app(flask_app)
    migrate.init_app(flask_app, db)

    print("Banco: ", config.SQLALCHEMY_DATABASE_URI)
    
    if not with_port: return flask_app

    return flask_app, default_port