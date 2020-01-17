from flask import render_template
from . import account


@account.app_errorhandler(404)
def not_found(e):
    return render_template('admin/404.html')

@account.app_errorhandler(500)
def server_error(e):
    return render_template('admin/500.html')