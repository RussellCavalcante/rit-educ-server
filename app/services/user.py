from flask_restful import Resource, reqparse
from app.models.user import UserModel
from flask_jwt_extended import create_access_token, jwt_required, get_raw_jwt
from werkzeug.security import safe_str_cmp
from blacklist import BLACKLIST

atributos = reqparse.RequestParser()
atributos.add_argument('username', type=str, required=True, help="campo de nome do usuario e obrigatorio")
atributos.add_argument('password', type=str, required=True, help="campo de senha e obrigatorio")
atributos.add_argument('email', type=str, help="campo de email e obrigatorio")
atributos.add_argument('phone', type=str, help="campo de telefone")

class User(Resource):
    #/usuarios/{user_id}
        
    def get(self, user_id):
        user = UserModel.find_user(user_id)
        if user:
            return user.json()
        return {"message": 'Usuario nao encontrado'}, 404 # not found


    @jwt_required
    def delete(self, user_id):
        user = UserModel.find_user(user_id)
        if user:
            try:
                user.delete_user()   
            except:
                 return {'message': 'Desculpe foi possivel deletar'}, 500
            return {'message': 'User deleted'}
        return {'message': 'User not found.' }, 404

class UserRegister(Resource):
    def post(self):
        dados = atributos.parse_args()

        username = dados['username']
        password = dados['password']
        
        if UserModel.find_by_login(dados['username']):
            return {'message': "Esse usuario '{}' ja existe.".format(dados['username'])}
        
        salt = UserModel.get_new_salt()

        encrypted_password = UserModel.password_encrypted(password, salt)
                
        if not UserModel.email_validator(dados['email']):
            return {'message': "Email '{}' esta invalido.".format(dados["email"])}, 400

        dados = {**dados, **{ 'salt': salt, 'password': encrypted_password }}

        user = UserModel(**dados)

        user.save_user()

        return {'message':'Usuario Criado com sucesso!'}, 201


        

class UserLogin(Resource):


    @classmethod
    def post(cls):
        dados = atributos.parse_args()

        username = dados['username'].strip()
        password = dados['password'].strip()

        user = UserModel.find_by_login(username)

        encrypted_password = UserModel.password_encrypted(password, user.salt)

        if not user.assert_password(password):
            return {'status': False}, 400
    
        token_de_acesso = create_access_token(identity=user.id)
        
        return {'acess_token': token_de_acesso}, 200
            

class UserLogout(Resource):
    @jwt_required
    def post(self):
        jwt_id = get_raw_jwt()['jti']
        BLACKLIST.add(jwt_id)
        return {'message' : 'Deslogado com sucesso!'}, 200