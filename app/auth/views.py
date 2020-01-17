from flask import current_app, render_template, redirect, request, url_for, flash
from . import auth
from .. import db
from ..account.models import User
from ..account.forms import SetupForm, LoginForm
from core import accepted_methods, translate, valid_ext, stop_server
from flask_login import current_user, login_user, logout_user, login_required


@auth.route('/login', methods=accepted_methods)
def login():
    admin = User.query.filter_by(role_id=3).first()

    if admin is None:
        return redirect(url_for('account.setup'))

    login = LoginForm()

    if login.validate_on_submit():
        user = User.query.filter_by(username=login.username.data).first()
        if user is not None and user.verify_password(login.password.data):
            login_user(user)
            if current_user.role.name is 'Administrator':
                next = request.args.get('next')
                if next is None or not next.startswith('/'):
                    next = url_for('account.index')
                return redirect(next)
            return redirect(url_for('main.savecomic'))
        flash('Login failed')
    return render_template('admin/login.html', login=login)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth.route('/forgot')
def forgot():
    return render_template('admin/login.html')


@auth.route('/shutdown', methods=accepted_methods)
def shutdown():
    stop_server()
    return '[\033[1;32mSYSTEM\033[0m] Shutting down application'