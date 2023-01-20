from sqlalchemy.dialects.postgresql import UUID
from app import banco
from uuid import uuid1, uuid4
import re


class UserModel(banco.Model):
    __tablename__ = 'users'
    

    id = banco.Column(banco.String(36),default=lambda x:str(uuid1()), primary_key=True)
    username = banco.Column(banco.String(255), nullable=False)
    password = banco.Column(banco.String(64), nullable=False)
    email = banco.Column(banco.String(255), nullable=False)
    phone = banco.Column(banco.Integer(), nullable=False)
    salt = banco.Column(banco.String(36),default=lambda x:str(uuid4()))


    def __init__(self, username, password, email, phone, salt):
        self.username = username
        self.password = password
        self.email = email
        self.phone = phone
        self.salt = salt


    def json(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'phone': self.phone,
            'salt': self.salt
        }

    def assert_password(self, password, *args, **kwargs) -> bool:
        from hashlib import md5
       
        password_with_md5 = password + self.salt
        password_with_md5 = md5(str(password_with_md5).encode('utf-8')).hexdigest()


        return password_with_md5 == self.password
    
    @classmethod
    def email_validator(cls, email):    
        regex =  r"^[A-Za-z0-9](([_.-]?[a-zA-Z0-9]+)*)@([A-Za-z0-9]+)(([.-]?[a-zA-Z0-9]+)*)([.][A-Za-z]{2,4})$"
        if(re.search(regex,email)): 
            return email
        return None


    @classmethod
    def find_user(cls, id):
        user = cls.query.filter_by(id=id).first()  #select * from hoteis where hotel_id = $hotel_id
        if user:
            return user
        return None
    
    @classmethod
    def find_by_login(cls, username):
        user = cls.query.filter_by(username=username).first()  #select * from hoteis where hotel_id = $hotel_id
        if user:
            return user
        return None

    @classmethod
    def get_new_salt(cls, *args, **kwargs):
        return str(uuid4())


    @classmethod
    def password_encrypted(cls, password, salt, *args, **kwargs):
        from hashlib import md5

        return md5(str(password + salt).encode('utf-8')).hexdigest()


    def save_user(self):
        banco.session.add(self)
        banco.session.commit()
    
    
    def delete_user(self):
        banco.session.delete(self)
        banco.session.commit()

