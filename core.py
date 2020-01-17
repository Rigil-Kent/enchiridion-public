import os
import string
import time
import hashlib
import urllib.request
import boto3
import sys
import pandas
from threading import Thread
from os.path import splitext, exists
from datetime import datetime, timedelta
from flask import request, redirect, flash, Markup, render_template, make_response, url_for, current_app
from werkzeug.utils import secure_filename
from flask_mail import Message
from app import mail
from bs4 import BeautifulSoup
from subprocess import check_output


accepted_methods = ["GET", "POST"]
translate = str.maketrans('', '', string.punctuation)
images = ['.jpg', '.png', '.gif', '.svg']
video = ['.mp4', '.mkv', '.ogv', '.flv']
audio = ['.mp3', '.wav', '.ogg', '.aac', '.mid']
spread = ['.xlsx', '.csv']
etc = ['.pdf', '.cbr']
valid_ext = images + video + audio + spread + etc
clear = lambda platform: os.system('cls') if platform == 'win32' else os.system('clear')

def stop_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        print('[Error] Not currently running the Werkzeug server')
        return redirect(url_for('main.blog'))
    func()

def update_server():
    try:
        check_output(['sudo', 'apt', 'update'])
        check_output(['sudo', 'apt', 'install', 'python3-pip', 'python3-dev', 'build-essential', 'libssl-dev', 'libffi-dev', 'python3-setuptools'])
        check_output(['sudo', 'apt', 'install' 'python3-venv'])
        print('[\033[1;32mSuccess\033[0m] Server updated')
    except Exception as msg:
        print('[\033[1;31mFail\033[0m] Unable to update system.\n{}'.format(msg))

def create_project_repo(git, name, set_private=None):
    if set_private:
        try:
            git.get_user().create_repo(
                name.translate(translate).replace(' ', '-').replace('.', '').lower(), 
                private=True)
            print('[Created] {} project repository'.format(name))
        except Exception as msg:
            print(msg)
    else:
        try:
            git.get_user().create_repo(
                name.translate(translate).replace(' ', '-').replace('.', '').lower())
        except Exception as msg:
            print(msg)

    
def create_project(name):
    try:
        os.mkdir(name)
        os.chdir(os.path.join('/home/ubuntu', name))
        check_output(['python3.6', '-m', 'venv', 'env'])
        print('[\033[1;32mSuccess\033[0m] Project {} created'.format(name))
    except Exception as msg:
        print('[\033[1;31mFail\033[0m] Unable to create project.\n{}'.format(msg))
    finally:
        check_output(['source', os.path.join(name, '/bin/activate')])

def install_packages():
    required = ['wheel', 'uwsgi', 'flask']
    try:
        for item in required:
            check_output(['pip', 'install', item])

        check_output(['pip', 'install', '-r', 'requirements.txt'])
        check_output(['deactivate'])
        print('[\033[1;32mSuccess\033[0m] Require packages installed')
    except Exception as msg:
        print('[\033[1;31mFail\033[0m] Unable to install required packages.\n{}'.format(msg))

def create_project_ini(name):
    ini_template='''[uwsgi]
    module = main:app

    master = true
    processes = 5

    socket = {}.sock
    vacuum = true

    die-on-term = true'''.format(name)

    try:
        with open(os.path.join('home', 'ubuntu', name, name +'.ini')) as cfg:
            cfg.write(ini_template)
        print('[\033[1;32mSuccess\033[0m] Project ini initialized')
    except Exception as msg:
        print('[\033[1;31mFail\033[0m] Unable to generate {}.ini.\n{}'.format(name, msg))

def create_system_service(name):
    service_template = '''[Unit]
    Description={} web application instance
    After=network.target
    
    [Service]
    User=ubuntu
    Group=www-data
    WorkingDirectory=/home/ubuntu/{}
    Environment="PATH=/home/ubuntu/{}/env/bin"
    ExecStart=/home/ubuntu/{}/env/bin/uwsgi --ini {}.ini
    
    [Install]
    WantedBy=multi-user.target'''.format(name)
    try:
        with open(os.path.join('etc', 'systemd', 'system', '{}.service'.format(name))) as serv:
            serv.write(service_template)
        print('[\033[1;32mSuccess\033[0m] System service \033[1;32m{}\033[0m] created'.format())
    except Exception as msg:
        print('[\033[1;31mFail\033[0m] Unable to create {}.service.\n{}'.format(name, msg))

def start_system_service(name):
    try:
        check_output(['sudo', 'systemctl', 'start', name])
        check_output(['sudo', 'systemctl', 'enable', name])
    except Exception as msg:
        print('[\033[1;31mFail\033[0m] Unable to start {}.service.\n{}'.format(name, msg))

def service_is_active(name):
    try:
        status = check_output['sudo', 'systemctl', 'status', name]
        if "(running)" in status.split():
            return True
        else:
            return False
    except Exception as msg:
        print('[\033[1;31mFail\033[0m] Unable to check system status.\n{}'.format(msg))

def configure_nginx_proxy(domain, name):
    nginx_template = '''server {
        listen 80;
        server_name {} www.{};

        location / {
            include uwsgi_params;
            uwsgi_pass unix:/home/ubuntu/{}/{}.sock;
        }
    }'''.format(domain, domain, name, name)

    try:
        with open(os.path.join('etc', 'nginx', 'sites-available', name)) as nginx:
            nginx.write(nginx_template)
    except Exception as msg:
        print('[\033[1;31mFail\033[0m] Unable to configure nginx.\n{}'.format(msg))

def enable_nginx_config(name):
    try:
        check_output(['sudo', 'ln', '-s', os.path.join('etc', 'nginx', 'sites-available', name), os.path.join('etc', 'nginx', 'sites-enabled')])
    except Exception as msg:
        print('[\033[1;31mFail\033[0m] Unable to enable server block configuration.\n{}'.format(msg))
    finally:
        success = check_output(['sudo', 'nginx', '-t'])
        if (success.endswith('successful')):
            return True
        else:
            return False

def restart_nginx():
    try:
        check_output(['sudo', 'systemctl', 'restart', 'nginx'])
        check_output(['sudo', 'ufw', 'allow', "'Nginx Full'"])
    except Exception as msg:
        print('[\033[1;31mFail\033[0m] Unable to restart nginx.\n{}'.format(msg))

def aws_deploy(domain, name):
    update_server()
    create_project(name)
    install_packages()
    create_project_ini(name)
    create_system_service(name)
    start_system_service(name)
    if service_is_active(name):
        configure_nginx_proxy(domain, name)
        if enable_nginx_config(name):
            restart_nginx()

def doc_textract():
    client = boto3.client('textract', region_name=current_app.config['S3_REGION'], aws_access_key_id=current_app.config['S3_ACCESS_KEY'], aws_secret_access_key=current_app.config['S3_SECRET_KEY'])
    s3 = boto3.resource('s3', aws_access_key_id=current_app.config['S3_ACCESS_KEY'], aws_secret_access_key=current_app.config['S3_SECRET_KEY'])
    bucket = s3.Bucket(current_app.config['S3_BUCKET'])
    extracted_data = []

    for s3_file in bucket.objects.all():
        response = client.detect_document_text(Document={'S3Object': {'Bucket': bucket, 'Name': s3_file.key}})
        blocks = response['Blocks']

        for block in blocks:
            if block['BlockType'] != 'PAGE':
                print('Detected: ' + block['Text'])
                print('Confidence: ' + "{:2f}".format(block['Confidence']) + '%')

def summarize(text):
    slices = text.split()
    return " ".join(slices[:current_app.config["SUMMARY_LIMIT"]])
    
def encrypt_email(key, email):
    import base64
    encoded_chars = []
    for i in range(len(email)):
        key_c = key[i % len(key)]
        encoded_c = chr(ord(email[i]) + ord(key_c) % 256)
        encoded_chars.append(encoded_c)
    encoded_string = "".join(encoded_c)
    return base64.urlsafe_b64encode(encoded_string)

def generate_invite_code(email_address):
    email_hash = hashlib.md5(email_address.encode())
    return email_hash.hexdigest()

def check_invite_code(field, code):
    email_hash = hashlib.md5(field.encode())

    if code == email_hash.hexdigest():
        return True
    else:
        return False

def env_from_dict(env):
    data = ""
    for key,value in env.items():
        if env[key] != "":
            data += "{}={}\n".format(key.upper(),value)

    return data

def generate_env(data, envfile, testing=False):
    if (exists(envfile)):
        clear(os.sys.platform)
        print('[\033[1;31mWarning\033[0m]] existing {} file detected.'.format(envfile))
        confirmed = input('Continue? (this will overwrite the existing file) [y/n] ')
        if (confirmed.lower() == 'n'):
            os.sys.exit('{} was not created'.format(envfile))

    if not testing:
        clear(os.sys.platform)
        print('Creating {} file'.format(envfile))

        try:
            with open(envfile, 'w') as file:
                file.write(data)
        except Exception as err:
            print(err)

def aws_deploy():
    print('Targeting: Amazon Web Services (AWS)')

def heroku_deploy():
    print('Targeting: Heroku')

def digital_ocean_deploy():
    print('Targeting: Digital Ocean')

def check_extension(extension):
    extension = extension.lower()
    images = ['.jpg', '.png', '.gif', '.svg']
    video = ['.mp4', '.mkv', '.ogv', '.flv']
    audio = ['.mp3', '.wav', '.ogg', '.aac', '.mid']
    spread = ['.xlsx', '.csv']


    if extension in images:
        return "image"
    elif extension in video:
        return "video"
    elif extension in audio:
        return "audio"
    elif extension in spread:
        return "spreadsheet"
    elif extension is "pdf":
        return "pdf"
    elif extension is "cbr":
        return "cbr"
    else:
        return "application"

def upload_file(filerequest, filetype=None):
    if request.method == "POST":
        if filerequest not in request.files:
            return False

        file = request.files[filerequest]

        if file.filename == '':
            return False

        filename = secure_filename(file.filename)
        name,ext = splitext(filename)

        if ext.lower() not in valid_ext:
            print("I'm sorry. I can't allow you to do that, Dave...")
            msg = Markup('<div class="alert alert-light alert-dismissible mb-4 py-3 border-left-danger">Invalid file type<button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>')
            flash(msg)
            return False

        try:
            if filetype == "cbr":
                file.save(os.path.join(current_app.config['STASH_FOLDER'], filename))
            elif filetype == "post":
                file.save(os.path.join(current_app.config['POST_FOLDER'], filename))
            elif filetype == "project":
                file.save(os.path.join(current_app.config['PROJECT_FOLDER'], filename))
            else:
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

            msg = Markup('<div class="alert alert-light alert-dismissible mb-4 py-3 border-left-success">Upload successful<button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>')

            flash(msg)
            return filename
        except Exception as err:
            msg = Markup('<div class="alert alert-light alert-dismissible mb-4 py-3 border-left-danger" role="alert">Upload failed: {} No File!<button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>'.format(err))
            flash(msg)
            return False

def send_async_email(msg):
    with current_app.app_context():
        mail.send(msg)

def send_email(subject, sender, to, template, **kwargs):
    msg = Message(subject, sender=sender, recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_async_email, args=[msg])
    thr.start()
    return thr

def send_mail(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=[recipients])
    msg.body = text_body
    msg.html = html_body
    mail.send(msg)
