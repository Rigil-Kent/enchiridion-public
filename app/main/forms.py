from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
import wtforms.validators
from wtforms.validators import Length, MacAddress, IPAddress, DataRequired, EqualTo


class Ripper(FlaskForm):
    search = StringField('Search')
    submit = SubmitField('Download')

class RepoForm(FlaskForm):
    name = StringField('Project Name')
    submit = SubmitField('Create')