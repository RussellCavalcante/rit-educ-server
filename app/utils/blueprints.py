
def __get_blueprints():
    """
    `Adicionar nessa`, e exlusivamente nessa, função todas as rotas/blueprints:
    """

    # Rotas de Ações:
    from app.blueprints import available_routes
                    
    _all_blueprints = [available_routes]
    
    return _all_blueprints


def declare_api_routes(app, *args, **kwargs):
    """
    Função para declarar as routes da aplicação.

    :app Flask Instance;

    :kwargs `url_prefix` da aplicação;
    """
    with_prefix = None

    # Se o prefixo for passado:
    if 'url_prefix' in kwargs:
        with_prefix = kwargs.get('url_prefix')

    blueprints = __get_blueprints()
    
    for blueprint in blueprints:

        if with_prefix:
            app.register_blueprint(blueprint, url_prefix=with_prefix)

        else:
            app.register_blueprint(blueprint, url_prefix="")

    # Adicionando o Índice:
    app.add_url_rule('/', 'index', __std_index)

    #app.after_request(__after_request)

def __std_index():
    return 'Servidor Aula +'


def __after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')

    print(response.headers)
    return response


