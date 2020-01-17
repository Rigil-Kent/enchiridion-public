from flask import Markup
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField, IntegerField, FileField
from wtforms.validators import DataRequired, EqualTo, Length, Email, Regexp, NumberRange
from wtforms import ValidationError
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from .models import User, Role, Banned, Contact, Post, PostCategory, Page, Media, Menu, Tag, Comic
from core import check_invite_code

def enabled_roles():
    return Role.query

def enabled_pages():
    return Page.query

def enabled_posts():
    return Post.query

def enabled_tags():
    return Tag.query

def enabled_categories():
    return PostCategory.query

def enabled_menus():
    return Menu.query

def enabled_users():
    return User.query


class SetupForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(1, 64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(1, 64)])
    email = StringField('Email', validators=[DataRequired(), Length(1, 64), Email()])
    username = StringField('Username', validators=[
        DataRequired(),
        Length(1, 64),
        Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0, 'Usernames must contain only letters, numbers and underscores')])
    password = PasswordField('Password', validators=[DataRequired(), EqualTo('password2', message='Passwords must match')])
    password2 = PasswordField('Repeat Password', validators=[DataRequired()])
    avatar = FileField('Avatar')
    show_display_name = BooleanField('Show Display Name')
    website = StringField('Website URL')
    bio = TextAreaField('Bio')
    submit = SubmitField('Launch')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('An account using this email address has already been registered.')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username is already in use.')

class UpdateForm(FlaskForm):
    first_name = StringField('First Name')
    last_name = StringField('Last Name')
    email = StringField('Email')
    avatar = FileField('Avatar')
    show_display_name = BooleanField('Show Display Name')
    website = StringField('Website URL')
    bio = TextAreaField('Bio')
    role = QuerySelectField('Role', query_factory=enabled_roles, get_label='name', allow_blank=True)
    submit = SubmitField("Update")

class InviteForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(1, 64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(1, 64)])
    email = StringField('Email', validators=[DataRequired(), Length(1, 64), Email()])
    username = StringField('Username', validators=[
        DataRequired(),
        Length(1, 64),
        Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0, 'Usernames must contain only letters, numbers and underscores')])
    password = PasswordField('Password', validators=[DataRequired(), EqualTo('password2', message='Passwords must match')])
    password2 = PasswordField('Repeat Password', validators=[DataRequired()])
    avatar = FileField('Avatar')
    show_display_name = BooleanField('Show Display Name')
    website = StringField('Website URL')
    bio = TextAreaField('Bio')
    submit = SubmitField('Create Account')


    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('An account using this email address has already been registered.')

        if Banned.query.filter_by(email=field.data).first():
            raise ValidationError('This email address has been banned.')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username is already in use.')

    def validate_code(self, field):
        if (not check_invite_code(field)):
            raise ValidationError('Email address does not match the invitation code.')

class SendInviteForm(FlaskForm):
    first_name = StringField('First Name')
    last_name = StringField('Last Name')
    email = StringField('Email address', validators=[DataRequired(), Email()])
    send = SubmitField('Invite')

    def validate_email(self, field):
        if Banned.query.filter_by(email=field.data).first():
            raise ValidationError('This email address has been banned.')

class RequestInviteForm(SendInviteForm):
    submit_val = Markup('<i class="fa fa-paper-plane" title="Submit"></i>')
    request = SubmitField(submit_val)

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(1, 64)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class TagForm(FlaskForm):
    name = StringField('Tag Name', validators=[DataRequired(), Length(1, 64)])
    description = StringField('Tag Description')
    submit = SubmitField('Add')

class CatForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(1, 64)])
    description = StringField('Category Description')
    submit = SubmitField('Add')

class PostForm(FlaskForm):
    title = StringField('Post Title', validators=[DataRequired(), Length(1, 128)])
    permalink = StringField('Permalink')
    visibility = SelectField('Visibility', choices=[('published', 'Published'), ('draft', 'Draft'), ('trash', 'Trash')])
    featured_image = FileField('Featured Image')
    summary = TextAreaField('Post Summary')
    content = TextAreaField('Post Body')
    allow_comments = BooleanField('Allow Comments')
    allow_pingbacks = BooleanField('Allow Pingbacks')
    is_sticky = BooleanField('Sticky Post')
    submit = SubmitField('Publish')

class ProjectForm(FlaskForm):
    name = StringField('Post Title', validators=[DataRequired(), Length(1, 128)])
    featured_image = FileField('Featured Image')
    content = TextAreaField('Post Body')
    submit = SubmitField('Publish')

class PageForm(FlaskForm):
    name = StringField('Page Title', validators=[DataRequired(), Length(1, 64)])
    slug = StringField('Permalink')
    subtitle = StringField('Page Sub Title', validators=[DataRequired(), Length(1, 128)])
    content = TextAreaField('Page Content')
    enable_social_links = BooleanField('Enable Social Links')
    submit = SubmitField('Publish')

class MediaForm(FlaskForm):
    title = StringField('User-Friendly File Name', validators=[DataRequired(), Length(1, 64)])
    filename = FileField('File')
    caption = StringField('File Caption')
    description = StringField('File Description (Optional)')
    submit = SubmitField('Upload')

class ContactForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    subject = StringField('Subject', validators=[DataRequired()])
    message = TextAreaField('Message', validators=[DataRequired()])
    contact = SubmitField("Send Message")