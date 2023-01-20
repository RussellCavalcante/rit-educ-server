from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

"""
Todos os Modelos da Aplicação
"""
from app.models import *

# Contexto da aplicação:
from app import create_app, parse_terminal


if __name__ == '__main__':
    manager = Manager(create_app(with_port=False))
    manager.add_command('db', MigrateCommand)
    manager.run()