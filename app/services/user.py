from app.services import DomainServices, logger
from app.models import User
from pprint import pprint


class UserServices(DomainServices):
    __model__ = User

    
    def __init__(self, request, *args, **kwargs):
        super().__init__(request, *args, **kwargs)


    def after_find(self, data, *args, **kwargs):
        pprint(data)

        
    def reset(self, *args, **kwargs):
        
        self.validate(self._body_params, ['CURRENT_PASSWORD', 'NEW_PASSWORD'])
        # Padrão de mensagem: {'CURRENT_PASSWORD': '', 'NEW_PASSWORD': ''}
        
        user = self.get_session()['log']['user']

        if user.crypt_password(self._body_params['CURRENT_PASSWORD'], user.SALT) != \
            user.PASSWORD:

            self.raise_error("A senha atual não corresponde à cadastrada. Verifique ela, por favor.")
        
        user.PASSWORD = user.crypt_password(self._body_params['NEW_PASSWORD'], user.SALT)

        self.add_message("Senha alterada com sucesso.")

        self._process_result = user._id

        user.save()


    def send_password(
        self,
        username, 
        email, 
        password,
        assunto='Senha Criada - Resolute', 
        *args, 
        **kwargs):
        
        from app import config
        from app.services.email import EmailService
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        # Construct email
        msg = MIMEMultipart('alternative')
        msg['To'] = email
        msg['From'] = config.EMAIL_SENT_FROM
        msg['Subject'] = assunto
        
        body = "Olá {}, como vai?\n\nSegue a senha criada para acesso: {}\n\nAtenciosamente,"\
            .format(username, password)

        mime = MIMEText(body, 'plain')
        msg.attach(mime)        
        
        email_service = EmailService()
        email_service.send_smtp(
            config.EMAIL_SENT_FROM, 
            email, 
            msg.as_string())


