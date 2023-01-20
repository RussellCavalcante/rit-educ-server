from os import environ
from app import create_app, parse_terminal
import sys

if __name__ == '__main__':
    app, port = create_app(**parse_terminal())
    app.run(host='0.0.0.0', port=port)
