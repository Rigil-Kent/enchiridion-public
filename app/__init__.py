from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from flask_moment import Moment
from config import config
from flask_login import LoginManager
from flask_assets import Environment, Bundle
from flask_pagedown import PageDown


mail = Mail()
moment = Moment()
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
pagedown = PageDown()


def create_app(config_name):
    # from InstagramAPI import InstagramAPI
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    mail.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    assets = Environment(app)
    assets.url = app.static_url_path
    assets.debug = True
    scss = Bundle('scss/_variables.scss',
    filters='pyscss',
    output='gen/brizzle.min.css')
    assets.register('scss_all', scss)
    pagedown.init_app(app)

    



    from .main import main as main_bp
    from .auth import auth as auth_bp
    from .account import account as account_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(account_bp, url_prefix='/account')

    return app

