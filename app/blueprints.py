"""
Importes Externos:
"""
from flask import Blueprint, request

from app.services import DomainServices as Service
from app.utils import verify_request_module
from app.utils.wraps import token_required
from app import config


available_routes = Blueprint('blueprint', __name__)


@available_routes.route('<string:module>', methods=['GET'])
@token_required
def _get(module):    
    #verify_request_module(module)

    service = Service(request, module)

    service.process()

    return service.result


@available_routes.route('<string:module>/<string:function>', methods=['GET'])
@token_required
def _get_with_function(module, function):    
    #verify_request_module(module)

    service = Service(request, module, function=function)

    service.process()

    return service.result


@available_routes.route('selects', methods=['GET'])
@token_required
def _selects():    
    service = Service(request)

    service.selects()

    return service.result


@available_routes.route('<string:module>', methods=['POST'])
@token_required
def _post(module):
    service = Service(request, module)
    
    service.process()

    return service.result


@available_routes.route('<string:module>/<string:function>', methods=['POST'])
@token_required
def _post_with_function(module, function):    

    service = Service(request, module, function=function)

    service.process()

    return service.result


@available_routes.route('batch', methods=['POST'])
@token_required
def _batch():
    service = Service(request)
    
    service.batch()

    return service.result


@available_routes.route('attachment', methods=['POST'])
@token_required
def _attachment():
    from app.services import AttachmentServices as Service
    
    service = Service(request)
    
    service.save()

    return service.result


@available_routes.route('tmp-attachment', methods=['POST'])
@token_required
def _tmp_attachment():
    from app.services import AttachmentServices as Service
    
    service = Service(request)
    
    service.tmp_save()

    return service.result


@available_routes.route('tmp-attachment/<string:transaction_id>', methods=['POST'])
@token_required
def _consolide_transaction_attachment(transaction_id):
    from app.services import AttachmentServices as Service
    
    service = Service(request)
    
    service.tmp_consolide(transaction_id)

    return service.result



@available_routes.route('tmp-attachment/close-transactions', methods=['POST'])
@token_required
def _consolide_lesson_transaction_attachment():
    from app.services import AttachmentServices as Service
    
    service = Service(request)
    
    service.close_transactions()

    return service.result


@available_routes.route('attachment/<string:id>', methods=['GET'])
@token_required
def _download_attachment(id):
    from app.services import AttachmentServices as Service
    
    service = Service(request)
    
    return service.download(id)



@available_routes.route('reset-password', methods=['POST'])
@token_required
def _reset():
    
    from app.services import AuthServices as Service

    service = Service(request)
    
    service.reset()

    return service.result
    


@available_routes.route('<string:module>', methods=['PUT'])
@token_required
def _put(module):
    
    #verify_request_module(module)

    service = Service(request, module)
    
    service.process()

    return service.result


@available_routes.route('<string:module>', methods=['DELETE'])
@token_required
def _delete(module):
    
    #verify_request_module(module)

    service = Service(request, module)
    
    service.process()

    return service.result


@available_routes.route('auth', methods=['POST'])
def _auth():
    
    from app.services.auth import AuthServices

    _auth_services = AuthServices(request)
    
    _auth_services.login()

    return _auth_services.result


@available_routes.route('signup', methods=['POST'])
def _signup():
    
    from app.services.auth import AuthServices

    _auth_services = AuthServices(request)
    
    _auth_services.signup()

    return _auth_services.result


@available_routes.route('forget-password', methods=['POST'])
def _forget():
        
    from app.services.auth import AuthServices

    _auth_services = AuthServices(request)
    
    _auth_services.forget()

    return _auth_services.result