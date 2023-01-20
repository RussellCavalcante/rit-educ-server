from app import create_app, parse_terminal

#gunicorn -w 4 wsgi:app
app = create_app(with_port=False)
    