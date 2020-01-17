from app import db, login_manager
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, current_user
from flask import url_for, current_app


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Permission:
    FOLLOW = 1
    COMMENT = 2
    WRITE = 4
    MODERATE = 8
    ADMIN = 16


class Role(db.Model):
    __tablename__ = 'role'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    name = db.Column(db.String(64), unique=True, index=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    def __repr__(self):
        return "<Role {}>".format(self.name)

    def add_permission(self, permission):
        if self.has_permission(permission):
            self.permissions += permission

    def remove_permission(self, permission):
        if self.has_permission(permission):
            self.permissions -= permission

    def reset_permissions(self):
        self.permissions = 0

    def has_permission(self, permission):
        return self.permissions & permission == permission

    @staticmethod
    def insert_roles():
        roles = {
            'User': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE],
            'Moderator': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE, Permission.MODERATE],
            'Administrator': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE, Permission.MODERATE, Permission.ADMIN]
        }

        default_role = 'User'

        for r in roles:
            role = Role.query.filter_by(name=r).first()
            
            if role is None:
                role = Role(name=r)

            role.reset_permissions()

            for permission in roles[r]:
                role.add_permission(permission)

            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    username = db.Column(db.String(64), unique=True)
    password_hash = db.Column(db.String(128))
    first_name = db.Column(db.String(64), index=True)
    last_name = db.Column(db.String(64), index=True)
    display_name = db.Column(db.String(64), unique=True, index=True)
    show_display_name = db.Column(db.Boolean, default=False)
    email = db.Column(db.String(128), unique=True, index=True)
    website = db.Column(db.String(128), index=True)
    bio = db.Column(db.Text)
    avatar = db.Column(db.String(256))
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    media = db.relationship('Media', backref='uploader', lazy='dynamic')
    invitations = db.relationship('Invitation', backref='invites', lazy='dynamic')
    referer = db.relationship('Invitation', backref='invited_by', lazy='dynamic')
    comics = db.relationship('Comic', backref='library', lazy='dynamic')
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    last_download = db.Column(db.DateTime(), default=datetime.utcnow)
    daily_counter = db.Column(db.Integer, default=5)
    is_banned = db.Column(db.Boolean, default=False)
    invite_limit = db.Column(db.Integer, default=3)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            self.role = Role.query.filter_by(default=True).first()

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def ping(self):
        self.last_seen = datetime.utcnow
        db.session.add(self)
        db.session.commit()

    def increase_limit(self):
        self.invite_limit += 1
        db.session.add(self)
        db.session.commit()

    @staticmethod
    def counter():
        if current_user.last_download is None or current_user.last_download.date() < datetime.now().date():
            current_user.last_download = datetime.now()
            current_user.daily_counter = current_app.config['DAILY_LIMIT_STD'] if current_user.role.name == 'Moderator' else current_app.config['DAILY_LIMIT_MOD']
            db.session.add(current_user)
            db.session.commit()

    def give_credits(self, user, number):
        if self.role.name == "Administrator" or self.role.name == "Moderator":
            user.daily_counter = number
            db.session.add(user)
            db.session.commit()

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    name = db.Column(db.String)
    email = db.Column(db.String)
    subject = db.Column(db.String(256))
    message = db.Column(db.Text)

class Invitation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    referer_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    email = db.Column(db.String(128), index=True)
    invitation_code = db.Column(db.String(512), index=True)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))

class Comic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    title = db.Column(db.String(256), index=True)
    filename = db.Column(db.String(256), index=True)

class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    title = db.Column(db.String(256), index=True)
    filename = db.Column(db.String(256))
    filetype = db.Column(db.String(64), index=True)
    caption = db.Column(db.String(256))
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)

    @classmethod
    def as_dict(self):
        return [
            {
                'title': image.title,
                'value': url_for('static', filename='uploads/' + image.filename)
            } for image in Media.query.filter_by(filetype='image').all()
        ]

post_categories = db.Table('post_categories', db.Model.metadata, db.Column('post_id', db.Integer, db.ForeignKey('post.id')), db.Column('post_category_id', db.Integer, db.ForeignKey('post_category.id')))
post_tags = db.Table('post_tags', db.Model.metadata, db.Column('post_id', db.Integer, db.ForeignKey('post.id')), db.Column('tag_id', db.Integer, db.ForeignKey('tag.id')))
project_tags = db.Table('project_tags', db.Model.metadata, db.Column('project_id', db.Integer, db.ForeignKey('project.id')), db.Column('tag_id', db.Integer, db.ForeignKey('tag.id')))

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    title = db.Column(db.String(128), index=True, unique=True)
    permalink = db.Column(db.String(256))
    visibility = db.Column(db.String(64), index=True)
    featured_image = db.Column(db.String(256))
    allow_comments = db.Column(db.Boolean, default=True, index=True)
    allow_pingbacks = db.Column(db.Boolean, default=True, index=True)
    is_sticky = db.Column(db.Boolean, default=False, index=True)
    summary = db.Column(db.Text)
    content = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    categories = db.relationship('PostCategory', secondary=post_categories, backref=db.backref('posts', lazy='dynamic'))
    tags = db.relationship('Tag', secondary=post_tags, backref=db.backref('posts', lazy='dynamic'))

    @classmethod
    def as_dict(self):
        return [{
            'timestamp': post.timestamp,
            'title': post.title,
            'permalink': post.permalink,
            'visibility': post.visibility,
            'featured_image': post.featured_image,
            'allow_comments': post.allow_comments,
            'allow_pingbacks': post.allow_pingbacks,
            'is_sticky': post.is_sticky,
            'summary': post.summary,
            'author': post.author.username,
            'categories': [cat.name for cat in post.categories],
            'tags': [tag.name for tag in post.tags],
            'content': post.content
        } for post in Post.query.all()]


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    name = db.Column(db.String(64), index=True, unique=True)
    slug = db.Column(db.String(64), index=True, unique=True)
    description = db.Column(db.Text)

    @classmethod
    def as_dict(self):
        return [{
            "timestamp":tag.timestamp, 
            "name": tag.name
            } for tag in Tag.query.all()]
    
    @staticmethod
    def insert():
        tags = ['default']

        for t in tags:
            tag = Tag.query.filter_by(name=t).first()

            if tag is None:
                tag = Tag(name=t)

            db.session.add(tag)
        db.session.commit()


class PostCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    name = db.Column(db.String(64), index=True, unique=True)
    slug = db.Column(db.String(64), index=True, unique=True)
    description = db.Column(db.Text)
    default = db.Column(db.Boolean, default=False, index=True)

    @classmethod
    def as_dict(self):
        return [{"timestamp": category.timestamp, "name": category.name} for category in PostCategory.query.all()]

    @staticmethod
    def insert():
        categories = ['uncategorized']

        default_category = 'uncategorized'

        for c in categories:
            category = PostCategory.query.filter_by(name=c).first()
            
            if category is None:
                category = PostCategory(name=c)

            category.default = (category.name == default_category)
            db.session.add(category)
        db.session.commit()

menu_pages = db.Table('menu_pages', db.Model.metadata, db.Column('page_id', db.Integer, db.ForeignKey('page.id')), db.Column('menu_id', db.Integer, db.ForeignKey('menu.id')))

class Menu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True, unique=True)
    name = db.Column(db.String(64), index=True)
    pages = db.relationship('Page', secondary=menu_pages, backref=db.backref('menus', lazy='dynamic'))
    auto_add = db.Column(db.Boolean, default=False)
    primary = db.Column(db.Boolean, default=False)
    is_footer = db.Column(db.Boolean, default=False)
    is_social = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<Menu {}>'.format(self.name)

    @classmethod
    def as_dict(self):
        return [{
            "timestamp": menu.timestamp,
            "name": menu.name,
            "pages": [page.name for page in menu.pages],
            "auto_add": menu.auto_add,
            "primary": menu.primary,
            "is_footer": menu.is_footer,
            "is_social": menu.is_social
        } for menu in Menu.query.all()]

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    name = db.Column(db.String(128), index=True, unique=True)
    slug = db.Column(db.String(256))
    content = db.Column(db.Text)
    featured_image = db.Column(db.String(256))
    tags = db.relationship('Tag', secondary=project_tags, backref=db.backref('projects', lazy='dynamic'))
    client = db.Column(db.String(256))
    website = db.Column(db.String(512))
    completed = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    summary = db.Column(db.Text)

    @classmethod
    def as_dict(self):
        return [{
            "timestamp": project.timestamp,
            "name": project.name,
            "slug": project.slug,
            "content": project.content,
        } for project in Project.query.all()]

class Page(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    name = db.Column(db.String(128), index=True, unique=True)
    slug = db.Column(db.String(256))
    content = db.Column(db.Text)
    subtitle = db.Column(db.String(512))
    enable_social_links = db.Column(db.Boolean, default=True)
    enable_services = db.Column(db.Boolean, default=False)

    @classmethod
    def as_dict(self):
        return [{
            "timestamp": page.timestamp,
            "name": page.name,
            "slug": page.slug,
            "content": page.content,
            "subtitle": page.subtitle,
            "enable_social_links": page.enable_social_links,
            "enable_services": page.enable_services
        } for page in Page.query.all()]

    @staticmethod
    def insert():
        pages = ['contact', 'privacy', 'terms']

        for p in pages:
            page = Page.query.filter_by(name=p).first()

            if page is None:
                page = Page(name=p)

            db.session.add(page)
        db.session.commit()


class Banned(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    email = db.Column(db.String(512), index=True, unique=True)
