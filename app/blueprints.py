from flask import Flask, jsonify, Blueprint, request

from app.services.user import *
from app import server, banco, config

avaliable_route = Blueprint('avaliable_route', __name__)

@avaliable_route.route('/Login', methods=['POST'])
def Login():    
    from app.services.user import UserLogin

    _login_services = UserLogin()
    
    return _login_services.post()



@avaliable_route.route('/Logout', methods=['POST'])
def Logout():
    from app.services.user import UserLogout

    _logout_service = UserLogout()

    return _logout_service.post()    

@avaliable_route.route('/Login/Cadastro', methods=['POST'])
def register():
    from app.services.user import UserRegister

    _register_service = UserRegister()

    return _register_service.post()    