import os
from datetime import datetime
from flask import render_template, session, redirect, url_for, flash, request
from app import create_app, db
from flask_migrate import Migrate
from app.account.models import User, Role, Invitation, Post, PostCategory, Tag, Banned, Contact, Media, Project
import click
from subprocess import check_call, CalledProcessError, check_output
import ssh_agent_setup
from core import aws_deploy
from github import Github


app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app, db)


@app.shell_context_processor
def make_shell_context():
    return dict(
        db=db,
        User=User,
        Role=Role,
        Invitation=Invitation,
        Post=Post, 
        PostCategory=PostCategory, 
        Tag=Tag, 
        Banned=Banned, 
        Contact=Contact, 
        Media=Media, 
        Project=Project
    )


@app.cli.command()
@click.option('--platform', type=click.Choice(['aws', 'heroku', 'digitalocean', 'google']))
@click.option('-p', type=click.Choice(['aws', 'heroku', 'digitalocean', 'google']))
def deploy(platform, p):
    ''' Deploy Web Application to prefered cloud service '''

    if app.config['FLASK_CONFIG'] != "production" or "testing" or None:
        print("Deployment is not available for this configuration. Please change to [production] or [testing]")
        return

    print('Deploying to {}'.format(app.config['FLASK_CONFIG']))

    if platform or p == 'aws':
        try:
            aws_deploy(os.getenv('APP_DOMAIN'), os.getenv('APP_NAME'))
        except Exception as msg:
            print('[\033[1;31mFail\033[0m] Unable to deploy to AWS EC2 Instance.\n{}'.format(msg))


@app.cli.command()
@click.option('--db/--no-db')
def update(db):
    print('''=======================================================
[\033[1;32mRunning\033[0m] Brizzle.dev Site Maintenance
=======================================================''')
    ssh_dir = os.getenv('SSH_FOLDER')
    app_dir = os.getenv('APP_FOLDER')

    try:
        print('''==========================
Configuring ssh-agent
==========================''')
        ssh_agent_setup.setup()
        ssh_agent_setup.addKey('/home/ubuntu/.ssh/brizzle')
        print('[\033[1;32mSuccess\033[0m] .ssh Configured')
    except Exception as msg:
        print('[\033[1;31mFail\033[0m] Unable to configure Github .ssh access')

    try:
        print('''==========================
Pulling From GitHub Repository
==========================''')
        check_output(['git', 'pull'], cwd=app_dir)
        print('[\033[1;32mSuccess\033[0m] application downloaded from Repository')
    except CalledProcessError as msg:
        print('[\033[1;31mFail\033[0m] Unable to pull from GitHub Repository.')

    if (db):
        print('''==========================
Performing Database Maintenance
==========================''')
        try:
            check_output(['flask', 'db', 'migrate', '-m', 'Brizzle.dev Database maintenance: {}'.format(datetime.utcnow)], cwd=app_dir)
            check_output(['flask', 'db', 'upgrade'], cwd=app_dir)
            print("[\033[1;32mSuccess\033[0m] Database Maintenance completed!")
        except Exception as msg:
            print("[\033[1;31mFail\33[0m] Unable to upgrade database:\n{}".format(msg))

    # if all goes well, restart the service
    try:
        print('''==========================
Restarting System Service
==========================''')
        check_output(['sudo', 'systemctl', 'restart', 'brizzle.service'])
        print('[\033[1;32mSuccess\033[0m] Application maintenance completed')
    except Exception as msg:
        print('[\033[1;31mFail\33[0m] System Restart failed with the following error\n{}'.format(msg))

        

    




if __name__ == "__main__":
    app.run(host='0.0.0.0')