
def generate_token(payload:dict, *args, **kwargs) -> str:
    import jwt
    from app.utils import to_dict
    from app import config

    encoded_jwt = jwt.encode({'data': payload}, config.JWT_SECRET_KEY, algorithm='HS256')

    return encoded_jwt.decode('UTF-8')


def decode_token(token, *args, **kwargs):
    return jwt.decode(token, 'secret', algorithms=['HS256'])