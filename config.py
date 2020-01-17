import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet


basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.flaskenv'))
key = Fernet.generate_key()

class Config(object):
    VERSION = '0.0.1'
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'snapekilledumbledore'
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_SUBJECT_PREFIX = os.environ.get('MAIL_SUBJECT_PREFIX')
    ADMIN_EMAIL = os.environ.get('MAIL_SENDER') or 'bryan.bailey@brizzle.dev'
    WTF_CSRF_ENABLED = True
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or  \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    UPLOAD_FOLDER = os.path.join(basedir, 'app/static/uploads')
    STASH_FOLDER = os.path.join(UPLOAD_FOLDER, 'stash')
    POST_FOLDER = os.path.join(UPLOAD_FOLDER, 'blog')
    PROJECT_FOLDER = os.path.join(UPLOAD_FOLDER, 'projects')
    DOWNLOAD_FOLDER = os.path.join(basedir, 'app/static/download')
    CLOUD_PLATFORM = 'aws'
    FERNET_KEY = Fernet(key)
    HEADER_ETAG = os.environ.get('HEADER_ETAG')
    COMIC_API_KEY = os.environ.get('COMIC_API_KEY')
    COMIC_API_FORMAT = os.environ.get('COMIC_API_FORMAT')
    COMIC_API_RESOURCE = os.environ.get('COMIC_API_RESOURCE')
    COMIC_API_FILTERS = os.environ.get('COMIC_API_FILTERS')
    COMIC_API_URI = os.environ.get('COMIC_API_URI')
    TWITCH_API = os.environ.get('TWITCH_API_KEY')
    ENTRIES_PER_PAGE = 10
    DAILY_LIMIT_STD = 5
    DAILY_LIMIT_MOD = 10
    FLASK_CONFIG = os.environ.get('FLASK_CONFIG')
    INSTAGRAM_USER = os.environ.get('INSTAGRAM_USER')
    INSTAGRAM_PASS = os.environ.get('INSTAGRAM_PASS')
    SUMMARY_LIMIT = 129
    GITHUB_ACCESS_TOKEN=os.environ.get('GITHUB_ACCESS_TOKEN')

    @staticmethod
    def init_app(app):
        pass


class DevConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or  \
        'sqlite:///' + os.path.join(basedir, 'dev.db')


class TestConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or  \
        'sqlite:///' + os.path.join(basedir, 'test.db')


config = {
    'development': DevConfig,
    'testing': TestConfig,
    'production': Config,
    'default': DevConfig
}