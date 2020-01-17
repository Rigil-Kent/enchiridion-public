import os
import requests
import json
import threading
import time
from shutil import copyfile
from fake_useragent import UserAgent
from datetime import datetime, timedelta
from github import Github
from flask import render_template, session, redirect, url_for, flash, request, current_app, Markup, make_response
from . import main
from .forms import Ripper, RepoForm
from .. import db
from flask_login import current_user, login_required
from ..saveallcomics import ripper, zipper
from ..account.forms import InviteForm, SetupForm, LoginForm, RequestInviteForm, ContactForm
from ..account.models import Invitation, User, Role, Contact,Comic, Page, Post, PostCategory, Tag, Project
from core import generate_invite_code, check_invite_code, send_mail, upload_file, send_email, translate, create_project_repo


accepted_methods = ['GET', 'POST']
agent = UserAgent()

headers = {
    'User-Agent': agent.random,
    'ETag': 'W/"7dc470913f1fe9bb6c7355b50a0737bc"'
     }
resource = 'search'


class DownloaderThread(threading.Thread):
    def __init__(self):
        self.progress = 0
        super().__init__()

    def run(self):
        for _ in range(10):
            time.sleep(1)
            self.progress += 10

def get_comic_info(url, title):
    # remove extra spacing and characters from title, replacing them with +
    search_term = title[:-11].replace(' –', '+').replace(' ', '+').lower()

    # parse the issue number out of the title
    issue_number = title[-8] if title[-9] == '0' else title[-9:-7]

    # generate search query
    comicevine_url = url=url.format(current_app.config['COMIC_API_RESOURCE'], current_app.config['COMIC_API_KEY'], search_term, current_app.config['COMIC_API_FORMAT'])

    # get the request object
    req = requests.get(comicevine_url, headers=headers)

    # convert object to json
    comic = req.json()

    # grab the results
    comic = comic['results']
    try:
    # the api limits results to the first 10 items; since there is a high probability
    # that the query could turn up results without an "issue_number" key
    # this will return None and the paragraph will not be rendered
        for i in range(10):
            if (comic[i]['issue_number'] == issue_number):
                return comic[i]['description']
    except KeyError:
        return None

def download_comic_files(soup):
    # create list for comic file links
    comic_files = []

    # set the image_folder name to the title of the comic
    image_folder = os.path.join(current_app.config['DOWNLOAD_FOLDER'], ripper.get_title(soup))

    # append each comic link found in the bs4 response to the comic file list
    for link in ripper.get_img_links(soup):
        comic_files.append(link)

    # download the completed comic list
    ripper.download_img_links(comic_files, soup, current_app.config['DOWNLOAD_FOLDER'])

    # create a comic archive from all images in image_folder
    zipper.create_comic_archive(ripper.get_title(soup), image_folder)

    # copy comic to stash
    filename = ripper.get_title(soup) + '.cbr'
    src = str(os.path.join(image_folder, filename))
    dest = str(os.path.join(current_app.config['STASH_FOLDER'], filename))
    copyfile(src, dest)

@main.route('/', methods=accepted_methods)
def index():
    posts = Post.query.order_by(Post.timestamp.desc()).limit(3)
    req = RequestInviteForm()

    if req.validate_on_submit():
        subject = "Invitation Code Request by {}<{}>".format(req.first_name.data, req.email.data)
        
        send_mail(subject, current_app.config['ADMIN_EMAIL'], current_app.config['ADMIN_EMAIL'], text_body=render_template('email/invite_req.txt', name=req.first_name.data, email=req.email.data), html_body=render_template('email/invite_req.html', name=req.first_name.data, email=req.email.data))
        send_mail("Thank you for your interest in Saves-All-Comics", current_app.config['ADMIN_EMAIL'], req.email.data, text_body=render_template('email/thankyou_req.txt', name=req.first_name.data), html_body=render_template('email/thankyou_req.html', name=req.first_name.data))
        time.sleep(2)
        msg = Markup('<div class="alert alert-info alert-dismissible mb-4 py-3 text-center" role="alert"><h4>Thank You</h4><p><i class="fa fa-check-circle-o"></i> Moderators were alerted to your request. An email was sent to {} for confirmation.</p> <hr> <p class="text-danger"><small>Please keep in mind that this tool is not intended for use by the general public and no guarantees are made that access will be granted.</small></p><button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>'.format(req.email.data))
        flash(msg, category='public')
        return redirect(url_for('main.blog'))

    return render_template('brizzledev3/index.html', posts=posts, req=req)

@main.route('/contact', methods=accepted_methods)
def contact():
    form = ContactForm()
    req = RequestInviteForm()
    posts = Post.query.all()

    if req.request.data and req.validate_on_submit():
        subject = "Invitation Code Request by {}<{}>".format(req.first_name.data, req.email.data)
        
        send_mail(subject, current_app.config['ADMIN_EMAIL'], current_app.config['ADMIN_EMAIL'], text_body=render_template('email/invite_req.txt', name=req.first_name.data, email=req.email.data), html_body=render_template('email/invite_req.html', name=req.first_name.data, email=req.email.data))
        send_mail("Thank you for your interest in Saves-All-Comics", current_app.config['ADMIN_EMAIL'], req.email.data, text_body=render_template('email/thankyou_req.txt', name=req.first_name.data), html_body=render_template('email/thankyou_req.html', name=req.first_name.data))
        time.sleep(2)
        msg = Markup('<div class="alert alert-info alert-dismissible mb-4 py-3 text-center" role="alert"><h4>Thank You</h4><p><i class="fa fa-check-circle-o"></i> Moderators were alerted to your request. An email was sent to {} for confirmation.</p> <hr> <p class="text-danger"><small>Please keep in mind that this tool is not intended for use by the general public and no guarantees are made that access will be granted.</small></p><button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>'.format(req.email.data))
        flash(msg, category='public')
        return redirect(url_for('main.blog'))

    if form.contact.data and form.validate_on_submit():
        contact = Contact()
        contact.name = form.name.data
        contact.email = form.email.data
        contact.subject = form.subject.data
        contact.message = form.message.data

        subject = "Development Inquiry from {}<{}>".format(contact.name, contact.email)

        send_mail(subject, current_app.config['ADMIN_EMAIL'], current_app.config['ADMIN_EMAIL'], text_body=render_template('email/contact_send.txt', name=contact.name, email=contact.email, msg=contact.message), html_body=render_template('email/contact_send.html', name=contact.name, email=contact.email, msg=contact.message))
        send_mail("Thank you for your interest in Saves-All-Comics", current_app.config['ADMIN_EMAIL'], contact.email, text_body=render_template('email/contact_req.txt', name=contact.name), html_body=render_template('email/contact_req.html', name=contact.name))
        time.sleep(2)

        db.session.add(contact)
        db.session.commit()
        msg = Markup('Email sent! Someone will reach out within 24 hours.')
        flash(msg, category='public')
        return redirect(url_for('main.index'))

    return render_template('brizzledev3/contact.html', form=form, req=req, posts=posts)

@main.route('/register/invalid')
def invalid():
    return render_template('admin/invalid.html')

@main.route('/register/<code>', methods=accepted_methods)
def register(code):
    invitation = Invitation.query.filter_by(invitation_code=code).first()
    if invitation is None:
        return redirect(url_for('main.invalid'))
    invite = InviteForm()

    if invite.validate_on_submit():
        referer = User.query.filter_by(username=invitation.invited_by.username).first()
        user = User()
        user.username = invite.username.data
        user.email = invite.email.data
        if not (check_invite_code(invite.email.data, code)):
            return redirect(url_for('main.invalid'))
        user.first_name = invite.first_name.data
        user.last_name = invite.last_name.data
        user.password = invite.password.data

        the_file = upload_file('avatar')

        if the_file:
            post.featured_image = the_file

        send_mail("Thank you for registering with Save All Comics", current_app.config['ADMIN_EMAIL'], invitation.email, text_body=render_template('email/thankyou_req.txt', invitation=invitation), html_body=render_template('email/thankyou_req.html', invitation=invitation))
        msg = "Email Confirmation Sent! Please login."

        db.session.add(user)
        db.session.delete(invitation)
        db.session.commit()

        user = User.query.filter_by(username=invite.username.data).first()
        # user.referer = referer

        db.session.add(user)
        db.session.commit()
        flash(msg, category='public')
        return redirect(url_for('main.savecomic'))
    return render_template('admin/register.html', invite=invite, invitation=invitation)
    
@main.route('/saveallcomics', methods=accepted_methods)
def savecomic():
    form = Ripper()

    if form.validate_on_submit():
        if current_user.is_anonymous:
            return redirect(url_for('auth.login'))

        if current_user.daily_counter < 1:
            msg = Markup('<div class="card mb-4 py-3 border-left-warning"><div class="card-body">You have reached your daily download limit. Check back tomorrow!</div></div>')
            flash(msg, category=current_user.username)
            return redirect(request.url)

        soup = ripper.get_soup_obj(form.search.data, headers)
        title = ripper.get_title(soup)
        filename = title + '.cbr'
        if not Comic.query.filter_by(title=title).first():
            if not os.path.exists(os.path.join(current_app.config['DOWNLOAD_FOLDER'], title, filename)):
                download_comic_files(soup)
            comic = Comic()
            comic.title = title
            comic.user_id = current_user.id
            comic.filename = filename
            db.session.add(comic)
            db.session.commit()
        else:
            current_user.comics.append(Comic.query.filter_by(title=title).first())
            db.session.add(current_user)
            db.session.commit()
        cover = title + ' 000.jpg'
        current_user.daily_counter -= 1
        db.session.add(current_user)
        db.session.commit()
        description = get_comic_info(current_app.config['COMIC_API_URI'], title)
        return render_template('success.html', title=title, cover=cover, description=description)

    return render_template('index.html', form=form)

@main.route('/sitebuilder', methods=accepted_methods)
def builder():
    git = Github(current_app.config['GITHUB_ACCESS_TOKEN'])
    
    repos = git.get_user().get_repos()
    req = RequestInviteForm()
    form = RepoForm()

    if form.validate_on_submit():
        create_project_repo(git, form.name.data, set_private=True)

        return redirect(request.url)

    return render_template('main/sitebuilder.html', repos=repos, form=form, req=req)

@main.route('/projects', methods=accepted_methods)
def projects():
    projects = Project.query.order_by(Project.timestamp.desc()).limit(5)
    latest_posts = Post.query.order_by(Post.timestamp.desc()).limit(4)
    req = RequestInviteForm()

    if req.validate_on_submit():
        subject = "Invitation Code Request by {}<{}>".format(req.first_name.data, req.email.data)
        
        send_mail(subject, current_app.config['ADMIN_EMAIL'], current_app.config['ADMIN_EMAIL'], text_body=render_template('email/invite_req.txt', name=req.first_name.data, email=req.email.data), html_body=render_template('email/invite_req.html', name=req.first_name.data, email=req.email.data))
        send_mail("Thank you for your interest in Saves-All-Comics", current_app.config['ADMIN_EMAIL'], req.email.data, text_body=render_template('email/thankyou_req.txt', name=req.first_name.data), html_body=render_template('email/thankyou_req.html', name=req.first_name.data))
        time.sleep(2)
        msg = Markup('<div class="alert alert-info alert-dismissible mb-4 py-3 text-center" role="alert"><h4>Thank You</h4><p><i class="fa fa-check-circle-o"></i> Moderators were alerted to your request. An email was sent to {} for confirmation.</p> <hr> <p class="text-danger"><small>Please keep in mind that this tool is not intended for use by the general public and no guarantees are made that access will be granted.</small></p><button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>'.format(req.email.data))
        flash(msg, category='public')
        return redirect(url_for('main.blog'))
    return render_template('brizzledev3/projects.html', req=req, projects=projects, latest_posts=latest_posts)

@main.route('/project/<slug>', methods=accepted_methods)
def project(slug):
    project = Project.query.filter_by(slug=slug).first_or_404()
    req = RequestInviteForm()
    prev_id = project.id - 1
    next_id = project.id + 1
    if prev_id > 0:
        prev = Project.query.filter_by(id=(prev_id)).first()
    else:
        prev = None

    if next_id > 0:
        _next = Project.query.filter_by(id=next_id).first()
    else:
        _next = None

    tags = Tag.query.order_by(Tag.timestamp.desc()).limit(10)
    categories = PostCategory.query.order_by(PostCategory.timestamp.desc()).limit(10)
    latest_posts = Post.query.order_by(Post.timestamp.desc()).limit(4)

    if req.validate_on_submit():
        subject = "Invitation Code Request by {}<{}>".format(req.first_name.data, req.email.data)
        
        send_mail(subject, current_app.config['ADMIN_EMAIL'], current_app.config['ADMIN_EMAIL'], text_body=render_template('email/invite_req.txt', name=req.first_name.data, email=req.email.data), html_body=render_template('email/invite_req.html', name=req.first_name.data, email=req.email.data))
        send_mail("Thank you for your interest in Saves-All-Comics", current_app.config['ADMIN_EMAIL'], req.email.data, text_body=render_template('email/thankyou_req.txt', name=req.first_name.data), html_body=render_template('email/thankyou_req.html', name=req.first_name.data))
        time.sleep(2)
        msg = Markup('<div class="alert alert-info alert-dismissible mb-4 py-3 text-center" role="alert"><h4>Thank You</h4><p><i class="fa fa-check-circle-o"></i> Moderators were alerted to your request. An email was sent to {} for confirmation.</p> <hr> <p class="text-danger"><small>Please keep in mind that this tool is not intended for use by the general public and no guarantees are made that access will be granted.</small></p><button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>'.format(req.email.data))
        flash(msg, category='public')
        return redirect(url_for('main.blog'))
    return render_template('brizzledev3/single-project.html', project=project, prev=prev, _next=_next, req=req, categories=categories, tags=tags, latest_posts=latest_posts)

@main.route('/<slug>', methods=accepted_methods)
def page(slug):
    page = Page.query.filter_by(slug=slug).first_or_404()
    return render_template('index.html', page=page)

@main.route('/blog', methods=accepted_methods)
def blog():
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['ENTRIES_PER_PAGE'], error_out=False
    )
    posts = pagination.items
    tags = Tag.query.order_by(Tag.timestamp.desc()).limit(10)
    categories = PostCategory.query.order_by(PostCategory.timestamp.desc()).limit(10)
    latest_posts = Post.query.order_by(Post.timestamp.desc()).limit(4)
    req = RequestInviteForm()

    if req.validate_on_submit():
        subject = "Invitation Code Request by {}<{}>".format(req.first_name.data, req.email.data)
        
        send_mail(subject, current_app.config['ADMIN_EMAIL'], current_app.config['ADMIN_EMAIL'], text_body=render_template('email/invite_req.txt', name=req.first_name.data, email=req.email.data), html_body=render_template('email/invite_req.html', name=req.first_name.data, email=req.email.data))
        send_mail("Thank you for your interest in Saves-All-Comics", current_app.config['ADMIN_EMAIL'], req.email.data, text_body=render_template('email/thankyou_req.txt', name=req.first_name.data), html_body=render_template('email/thankyou_req.html', name=req.first_name.data))
        time.sleep(2)
        msg = Markup('<div class="alert alert-info alert-dismissible mb-4 py-3 text-center" role="alert"><h4>Thank You</h4><p><i class="fa fa-check-circle-o"></i> Moderators were alerted to your request. An email was sent to {} for confirmation.</p> <hr> <p class="text-danger"><small>Please keep in mind that this tool is not intended for use by the general public and no guarantees are made that access will be granted.</small></p><button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>'.format(req.email.data))
        flash(msg, category='public')
        return redirect(url_for('main.blog'))

    return render_template('brizzledev3/blog.html', req=req, posts=posts, pagination=pagination, page=page, categories=categories, tags=tags, latest_posts=latest_posts)


@main.route('/post/<permalink>', methods=accepted_methods)
def post(permalink):
    post = Post.query.filter_by(permalink=permalink).first_or_404()
    posts = Post.query.all()
    req = RequestInviteForm()
    tags = Tag.query.order_by(Tag.timestamp.desc()).limit(10)
    categories = PostCategory.query.order_by(PostCategory.timestamp.desc()).limit(10)
    tags = Tag.query.order_by(Tag.timestamp.desc()).limit(10)
    categories = PostCategory.query.order_by(PostCategory.timestamp.desc()).limit(10)
    latest_posts = Post.query.order_by(Post.timestamp.desc()).limit(4)
    prev_id = post.id - 1
    next_id = post.id + 1
    if prev_id > 0:
        prev = Post.query.filter_by(id=(prev_id)).first()
    else:
        prev = None

    if next_id > 0:
        _next = Post.query.filter_by(id=next_id).first()
    else:
        _next = None

    if req.validate_on_submit():
        subject = "Invitation Code Request by {}<{}>".format(req.first_name.data, req.email.data)
        
        send_mail(subject, current_app.config['ADMIN_EMAIL'], current_app.config['ADMIN_EMAIL'], text_body=render_template('email/invite_req.txt', name=req.first_name.data, email=req.email.data), html_body=render_template('email/invite_req.html', name=req.first_name.data, email=req.email.data))
        send_mail("Thank you for your interest in Saves-All-Comics", current_app.config['ADMIN_EMAIL'], req.email.data, text_body=render_template('email/thankyou_req.txt', name=req.first_name.data), html_body=render_template('email/thankyou_req.html', name=req.first_name.data))
        time.sleep(2)
        msg = Markup('<div class="alert alert-info alert-dismissible mb-4 py-3 text-center" role="alert"><h4>Thank You</h4><p><i class="fa fa-check-circle-o"></i> Moderators were alerted to your request. An email was sent to {} for confirmation.</p> <hr> <p class="text-danger"><small>Please keep in mind that this tool is not intended for use by the general public and no guarantees are made that access will be granted.</small></p><button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>'.format(req.email.data))
        flash(msg, category='public')
        return redirect(url_for('main.blog'))

    return render_template('brizzledev3/single-blog.html', post=post, posts=posts, req=req, categories=categories, tags=tags, prev=prev, _next=_next, latest_posts=latest_posts)

@main.route('/blog/category/<name>', methods=accepted_methods)
def category(name):
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.filter(Post.categories.any(PostCategory.name == name)).order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['ENTRIES_PER_PAGE'], error_out=False
    )
    posts = pagination.items
    tags = Tag.query.order_by(Tag.timestamp.desc()).limit(10)
    categories = PostCategory.query.order_by(PostCategory.timestamp.desc()).limit(10)
    latest_posts = Post.query.order_by(Post.timestamp.desc()).limit(4)
    req = RequestInviteForm()
    if req.validate_on_submit():
        subject = "Invitation Code Request by {}<{}>".format(req.first_name.data, req.email.data)
        
        send_mail(subject, current_app.config['ADMIN_EMAIL'], current_app.config['ADMIN_EMAIL'], text_body=render_template('email/invite_req.txt', name=req.first_name.data, email=req.email.data), html_body=render_template('email/invite_req.html', name=req.first_name.data, email=req.email.data))
        send_mail("Thank you for your interest in Saves-All-Comics", current_app.config['ADMIN_EMAIL'], req.email.data, text_body=render_template('email/thankyou_req.txt', name=req.first_name.data), html_body=render_template('email/thankyou_req.html', name=req.first_name.data))
        time.sleep(2)
        msg = Markup('<div class="alert alert-info alert-dismissible mb-4 py-3 text-center" role="alert"><h4>Thank You</h4><p><i class="fa fa-check-circle-o"></i> Moderators were alerted to your request. An email was sent to {} for confirmation.</p> <hr> <p class="text-danger"><small>Please keep in mind that this tool is not intended for use by the general public and no guarantees are made that access will be granted.</small></p><button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>'.format(req.email.data))
        flash(msg, category='public')
        return redirect(url_for('main.blog'))
    return render_template('brizzledev3/cat.html', posts=posts, pagination=pagination, page=page, name=name, req=req, tags=tags, categories=categories, latest_posts=latest_posts)

@main.route('/blog/tag/<name>', methods=accepted_methods)
def tag(name):
    tag = Tag.query.filter_by(name=name).first_or_404()
    tags = Tag.query.order_by(Tag.timestamp.desc()).limit(10)
    categories = PostCategory.query.order_by(PostCategory.timestamp.desc()).limit(10)
    latest_posts = Post.query.order_by(Post.timestamp.desc()).limit(4)
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.filter(Post.tags.any(Tag.name == tag.name)).order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['ENTRIES_PER_PAGE'], error_out=False
    )
    req = RequestInviteForm()
    posts = pagination.items

    if req.validate_on_submit():
        subject = "Invitation Code Request by {}<{}>".format(req.first_name.data, req.email.data)
        
        send_mail(subject, current_app.config['ADMIN_EMAIL'], current_app.config['ADMIN_EMAIL'], text_body=render_template('email/invite_req.txt', name=req.first_name.data, email=req.email.data), html_body=render_template('email/invite_req.html', name=req.first_name.data, email=req.email.data))
        send_mail("Thank you for your interest in Saves-All-Comics", current_app.config['ADMIN_EMAIL'], req.email.data, text_body=render_template('email/thankyou_req.txt', name=req.first_name.data), html_body=render_template('email/thankyou_req.html', name=req.first_name.data))
        time.sleep(2)
        msg = Markup('<div class="alert alert-info alert-dismissible mb-4 py-3 text-center" role="alert"><h4>Thank You</h4><p><i class="fa fa-check-circle-o"></i> Moderators were alerted to your request. An email was sent to {} for confirmation.</p> <hr> <p class="text-danger"><small>Please keep in mind that this tool is not intended for use by the general public and no guarantees are made that access will be granted.</small></p><button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>'.format(req.email.data))
        flash(msg, category='public')
        return redirect(url_for('main.blog'))
    return render_template('brizzledev3/tag.html', posts=posts, pagination=pagination, page=page, name=tag.name, req=req, tags=tags, categories=categories, latest_posts=latest_posts)

@main.route('/services', methods=accepted_methods)
def services():
    req = RequestInviteForm()
    return render_template('brizzledev3/service.html', req=req)

@main.route('/sitemap.xml', methods=['GET'])
def sitemap():
    pages = []
    ten_days_ago = datetime.now() - timedelta(days=10)

    for rule in current_app.url_map.iter_rules():
        if 'GET' in rule.methods and len(rule.arguments) == 0 and not rule.rule.startswith('/account') and not rule.rule.startswith('/auth') and not rule.rule.startswith('/register') and not rule.rule.startswith('/sitebuilder'):
            pages.append([url_for('main.index', _external=True) + rule.rule.replace('/', ''), ten_days_ago.date().isoformat()])

    posts = Post.query.order_by(Post.timestamp).all()

    for post in posts:
        url = url_for('main.post', permalink=post.permalink, _external=True)
        modified_time = post.timestamp.date().isoformat()
        pages.append([url, modified_time])

    projects = Project.query.order_by(Project.timestamp).all()

    for project in projects:
        url = url_for('main.project', slug=project.slug, _external=True)
        modified_time = project.timestamp.date().isoformat()
        pages.append([url, modified_time])

    sitemap_template = render_template('brizzledev3/sitemap_template.xml', pages=pages)
    response = make_response(sitemap_template)
    response.headers["Content-Type"] = "application/xml"
    return response

@main.route('/robots.txt')
def robots():
    robots_txt = render_template('brizzledev3/robots.txt')
    response = make_response(robots_txt)
    response.headers['Content-Type'] = 'text/plain'
    return response