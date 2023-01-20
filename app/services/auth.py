from app.services import DomainServices, logger, pprint, db, ModelStatus
from app.models import User, History, datetime


class AuthServices(DomainServices):
    def __init__(self, request, *args, **kwargs):
        super().__init__(request, *args, **kwargs)


    def login(self, *args, **kwargs):
                
        kwargs = self._get_body_params(exception=True) 
        
        logger.debug("Body da requisição: {}".format(kwargs))

        key_token = kwargs.get('key', None)

        if key_token:
            self._process_result = self.generate_token(key_token)
            return

        username:str = kwargs.get('username', None)
        password:str = kwargs.get('password', None)

        if not username or not password:
            self.raise_error("Verifique o parâmetro 'username' ou 'password' para essa requisição.")
        
        from app.models import User, ProfileUser, Profile

        result = User.query.filter(User.email.ilike(username.strip()), User.active()).first()
        
        if not result:
            self.raise_error("Verifique o nome do Usuário e/ou Senha.")

        logger.info("Usuário em login: {} - {}".format(result.id, result.email))

        if not result.assert_password(password.strip()):
            self.raise_error("Verifique o nome do Usuário e/ou Senha.")

        # Listando e retornando os perfis desse usuário:
        result = db.session.query(Profile, ProfileUser)\
            .filter(ProfileUser.user_id == result.id, ProfileUser.status == ModelStatus.ACTIVE.value, ProfileUser.profile_id == Profile.id)\
            .all()
        
        if not result:
            self.raise_error("Entre em contato com o Administrador do Sistema. Você está sem permissão.")

        self._process_result = [ {'key': profile_user.id, 'profile': profile.name } for profile, profile_user in result ]


    def reset(self, *args, **kwargs):
        self.validate(self._body_params, ['newPassword'])
        
        kwargs = self._get_body_params(exception=True) 

        user = User.query.filter_by(id=kwargs['id']).first()
        
        if not user:
            self.raise_error("Verifique a validade dessa operação.")

        if kwargs.get('currentPassword', None):
            if user.crypt_password(self._body_params['currentPassword'], user.salt) != user.password:
                self.raise_error("A senha atual não corresponde com a cadastrada. Verifique ela, por favor.")
        
        user.meta_attr['currentPwd'] = self._body_params['newPassword']
        user.password = user.crypt_password(self._body_params['newPassword'], user.salt)

        self.add_message("Senha alterada com sucesso!")

        self._process_result = user.id
        self.close_session()


    def signup(self, *args, **kwargs):
        kwargs = self._get_body_params(exception=True) 

        if not len(kwargs.keys()):
            self.raise_error("Verifique os parâmetros da requisição.")
        
        self.validate(
            kwargs, 
            ['USERNAME', 'EMAIL', 'NAME', 'LAST_NAME', 'OAB', 'PLAIN'],
            [''])
        
        if self.__model__.exists(USERNAME=kwargs['USERNAME']):
            self.raise_error(message="Esse nome de Usuário já existe. Insira outro, por favor.") 
        
        if self.__model__.exists(EMAIL=kwargs['EMAIL']):
            self.raise_error(message="Esse e-mail já existe. Insira outro, por favor.") 
        
        password_without_md5 =      self.__model__.generate_password()
        salt =                      self.__model__.generate_salt()
        password_with_md5 =         self.__model__.crypt_password(password_without_md5, salt)

        logger.debug("Senha: '{}'\nSalt: '{}'\n Senha MD5: '{}'".format(password_without_md5, salt, password_with_md5))
        
        # Adicionando às kwargs:
        kwargs['PASSWORD'] =    password_with_md5
        kwargs['SALT'] =        salt
        kwargs['CONF'] = {'bucket': [str(uuid4())]}
        kwargs['DOCUMENT'] = validate_cpf(kwargs.pop('CPF', None))

        # Criando o objeto:
        _object = Users.create(**kwargs)
                
        # Criando o advogado em questão:
        kwargs['USER'] = _object._id
               
        _lawier = Lawyer.create(**kwargs)

        # Enviando o e-mail com a senha gerada:
        self.send_password(_lawier.NAME, _object.USERNAME, _object.EMAIL, password_without_md5)

        self.add_message("Usuário cadastrado com sucesso. A senha gerada será enviada para o e-mail cadastrado.")

        return _object._id


    def forget(self, *args, **kwargs):
        
        kwargs = self._get_body_params(exception=True) 
        
        self.validate(kwargs, attributes=['email'], attributes_real_names=['Email do Usuário'])
      
        user = User.query.filter(User.email == kwargs['email']).first()
        
        if not user:
            self.raise_error(message="Não existe Usuário associado à este e-mail. Tente novamente ou entre em contato com a Administração do Sistema.") 

        new_password    = User.generate_password()
        user.password   = User.crypt_password(new_password, user.salt)

        logger.info("Nova senha: {}".format(new_password))

        self.add_message("Senha enviada para o e-mail!")
        self._process_result = True


    def generate_token(self, key, *args, **kwargs):
        
        from app.models import User, ProfileUser, Profile, Permission, ProfilePermission
        from app.models.profile_user import STUDENTS_ID
        from app.utils.token import generate_token

        logger.debug("Token requerido: {}".format(key))

        # Listando o perfil selecionado e gerando o token
        profile, profile_user, user = db.session.query(Profile, ProfileUser, User)\
            .filter(ProfileUser.id == key, ProfileUser.profile_id == Profile.id, ProfileUser.user_id == User.id)\
            .first()

        logger.info("Usuário escolhendo token: {} e {}".format(profile, profile_user))

        # Pegando as permissões para esse perfil de acesso:
        permissions = Permission.get([ProfilePermission.profile_id == profile.id, \
            ProfilePermission.permission_id == Permission.id, ProfilePermission.status == ModelStatus.ACTIVE.value], cursor_function='all')

        auth_payload = {
            'profile_user_id': profile_user.id, 
            'profile_id': profile.id, 
            'profile': profile.name, 
            'username': user.email, 
            'user_id': user.id,
            'name': user.name, 
            'is_student': profile.id == STUDENTS_ID
            }
        
        permission_payload = {'profile_user_id': profile_user.id, \
            'permissions': [{'id': permission.id, 'name': permission.name} for permission in permissions]}
        
        history = History(type='LOGIN', created_by=profile_user.id)

        history.add()

        self.close_session()

        return {'authToken': generate_token(auth_payload), 'permissionToken': generate_token(permission_payload)}


        
        
