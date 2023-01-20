from app import server, banco

if __name__ == '__main__':
    banco.init_app(server)
    server.run(host = '0.0.0.0', debug=True)