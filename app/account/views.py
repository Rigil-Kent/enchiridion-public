import os
import errno
import hashlib
import shutil
from random import randint
from os.path import splitext
from shutil import copyfile
from flask import render_template, session, redirect, url_for, flash, request, current_app, Markup, json
from . import account
from .forms import SetupForm, SendInviteForm, TagForm, CatForm, PostForm, ProjectForm, PageForm, MediaForm, UpdateForm
from .models import User, Role, Banned, Contact, Page, Project, Media, Menu, Post, PostCategory, Tag, Invitation, Comic
from .. import db, config
from core import encrypt_email, accepted_methods, generate_invite_code, check_extension, translate, upload_file, send_email, send_mail, summarize
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

@account.before_request
def limit_update():
    if current_user.is_authenticated:
        current_user.counter()

@account.route('/dashboard', methods=accepted_methods)
@login_required
def index():
    comic_count = Comic.query.count()
    user_count = User.query.count()
    # pending = len(current_user.invites)
    pending = Invitation.query.filter(User.invitations.any()).all()
    return render_template('admin/index.html', comic_count=comic_count, user_count=user_count, pending=pending)

@account.route('/comics/invite', methods=accepted_methods)
@login_required
def invite():
    form = SendInviteForm()

    page = request.args.get('page', 1, type=int)

    pagination = Invitation.query.order_by(Invitation.timestamp.desc()).paginate(
        page, per_page=current_app.config['ENTRIES_PER_PAGE'], error_out=False
    )
    invitations = pagination.items

    if form.validate_on_submit():
        comic = Comic.query.get(randint(1, Comic.query.count()))
        invitation = Invitation()
        invitation.first_name = form.first_name.data
        invitation.last_name = form.last_name.data
        invitation.email = form.email.data
        invitation.referer_id = current_user.id
        invitation.invitation_code = generate_invite_code(form.email.data)
        subject = "{} {} has invited you to Save All Comics".format(current_user.first_name, current_user.last_name)
        send_mail(subject, 'bryan.bailey@brizzle.dev', invitation.email, text_body=render_template('email/invitation.txt', invitation=invitation, comic=comic), html_body=render_template('email/invitation.html', invitation=invitation, comic=comic))
        if current_user.role.name != "Administrator":
            current_user.invite_limit -= 1
        db.session.add(current_user)
        db.session.add(invitation)
        db.session.commit()
        msg = Markup('<div class="alert alert-light alert-dismissible mb-4 py-3 border-left-success">Invitation was sent to {}<button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>')
        flash(msg.format(invitation.email))
        return redirect(url_for('account.invite'))
    return render_template('admin/invite.html', form=form, invitations=invitations, pagination=pagination)

@account.route('/comics/invite/<id>/delete')
@login_required
def invite_delete(id):
    invitation = Invitation.query.filter_by(id=id).first_or_404()
    msg = Markup('<div class="alert alert-light alert-dismissible mb-4 py-3 border-left-success">An invitation sent to {} was used.<button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>')
    flash(msg.format(invitation.email), current_user.username)
    db.session.delete(invitation)
    db.session.commit()
    return redirect(url_for('account.invite'))

@account.route('/mycomics', methods=accepted_methods)
@login_required
def mycomics():
    page = request.args.get('page', 1, type=int)

    pagination = current_user.comics.order_by(Comic.timestamp.desc()).paginate(
        page, per_page=current_app.config['ENTRIES_PER_PAGE'], error_out=False
    )
    comics = pagination.items
    return render_template('admin/comics.html', comics=comics, pagination=pagination)

@account.route('/comic/<title>/delete')
@login_required
def comic_delete(title):
    comic = Comic.query.filter_by(title=title).first_or_404()

    if current_user.role.name == 'Administrator':
        print("Removing comic from comic databse. This is a destructive process")
        if os.path.exists(os.path.join(current_app.config['DOWNLOAD_FOLDER'], comic.title, comic.filename)):
            shutil.rmtree(os.path.join(current_app.config['DOWNLOAD_FOLDER'], comic.title))

        msg = Markup('<div class="alert alert-light alert-dismissible mb-4 py-3 border-left-success">Comic {} deleted from global library<button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>')
        flash(msg.format(comic.title))

        db.session.delete(comic)
        db.session.commit()
    else:
        print("Removing comic from user database")
        msg = Markup('<div class="alert alert-light alert-dismissible mb-4 py-3 border-left-success">Comic {} deleted from your library<button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>')
        flash(msg.format(comic.title))
        current_user.comics.remove(comic)
        db.session.add(current_user)
        db.session.commit()
    return redirect(url_for('account.mycomics'))

@account.route('/users', methods=accepted_methods)
@login_required
def users():
    page = request.args.get('page', 1, type=int)

    pagination = User.query.order_by(User.timestamp.desc()).paginate(
        page, per_page=current_app.config['ENTRIES_PER_PAGE'], error_out=False
    )
    users = pagination.items
    invitations = Invitation.query.all()
    return render_template('admin/users.html', users=users, user_count=len(users), pagination=pagination, invitations=invitations)

@account.route('/banlist', methods=accepted_methods)
def banned():
    page = request.args.get('page', 1, type=int)
    pagination = Banned.query.order_by(Banned.timestamp.desc()).paginate(
        page, per_page=current_app.config['ENTRIES_PER_PAGE'], error_out=False
    )
    users = pagination.items
    return render_template('admin/banned.html', users=users, page=page)

@account.route('/user/<username>', methods=accepted_methods)
@login_required
def user(username):
    return render_template('admin/index.html')

@account.route('/user/<username>/edit', methods=accepted_methods)
@login_required
def user_edit(username):
    user = User.query.filter_by(username=username).first()
    latest_downloads = user.comics.order_by(Comic.timestamp.desc()).limit(8)
    form = UpdateForm()

    if request.method == "GET":
        if user is not None:
            form.email.data = user.email
            form.website.data = user.website
            form.first_name.data = user.first_name
            form.last_name.data = user.last_name
            form.website.data = user.website
            form.bio.data = user.bio
            form.show_display_name.data = user.show_display_name
            form.role.data = user.role

    if form.validate_on_submit():
        if user is None:
            user = User()

        user.website = form.website.data
        user.bio = form.bio.data
        if form.email.data != user.email:
            user.email = form.email.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data

        if form.role.data.id != user.role_id:
            user.role_id = form.role.data.id

        the_file = upload_file('avatar')

        if the_file:
            user.avatar = the_file


        db.session.add(user)
        db.session.commit()

        msg = Markup('<div class="alert alert-light alert-dismissible mb-4 py-3 border-left-success">Profile updated!<button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>')
        flash(msg)

        return redirect(url_for('account.user_edit', username=user.username))
    return render_template('admin/user.edit.html', form=form, user=user, latest_downloads=latest_downloads)

@account.route('/user/<id>/delete')
@login_required
def user_delete(id):
    user = User.query.filter_by(id=id).first_or_404()
    msg = Markup('<div class="alert alert-light alert-dismissible mb-4 py-3 border-left-success">User {} deleted<button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>')
    flash(msg.format(user.username))
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('account.users'))

@account.route('/user/<id>/ban')
@login_required
def user_ban(id):
    user = User.query.filter_by(id=id).first_or_404()
    msg = Markup('<div class="alert alert-light alert-dismissible mb-4 py-3 border-left-success">User {} deleted &amp; Banned<button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>')
    banned = Banned()
    banned.email = user.email
    db.session.add(banned)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('account.users'))

@account.route('/pages', methods=accepted_methods)
@login_required
def pages():
    pages = Page.query.all()
    return render_template('admin/pages.html', pages=pages, page_count=len(pages))

@account.route('/page/new', methods=accepted_methods)
@login_required
def page_create():
    form = PageForm()

    if form.validate_on_submit():
        page = Page()
        page.name = form.name.data
        page.slug = form.name.data.translate(translate).replace(' ', '-').replace('.', '').lower()
        page.subtitle = form.subtitle.data
        page.content = form.content.data
        page.enable_social_links = form.enable_social_links.data

        db.session.add(page)
        db.session.commit()

        session['name'] = page.name
        msg = Markup('<div class="alert alert-light alert-dismissible mb-4 py-3 border-left-success">Page {} created<button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>')
        flash(msg.format(page.name))

        return redirect(url_for('account.page_edit', name=page.name))
    return render_template('admin/page.edit.html', form=form)

@account.route('/page/<name>/edit', methods=accepted_methods)
@login_required
def page_edit(name):
    form = PageForm()
    page = Page.query.filter_by(name=name).first_or_404()

    if request.method == 'GET':
        form.name.data = page.name
        form.slug.data = page.slug
        form.subtitle.data = page.subtitle
        form.content.data = page.content
        form.enable_social_links.data = page.enable_social_links

    if form.validate_on_submit():
        page = Page()
        page.name = form.name.data
        page.slug = form.name.data.translate(translate).replace(' ', '-').replace('.', '').lower()
        page.subtitle = form.subtitle.data
        page.content = form.content.data
        page.enable_social_links = form.enable_social_links.data

        db.session.add(page)
        db.session.commit()
        msg = Markup('<div class="alert alert-light alert-dismissible mb-4 py-3 border-left-success">Page {} edited<button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>')
        flash(msg.format(page.name))
        return redirect(url_for('account.page_edit', name=name, form=form))

    return render_template('admin/page.edit.html', form=form)

@account.route('/page/<name>/delete', methods=accepted_methods)
@login_required
def page_delete(name):
    return render_template('admin/index.html')

@account.route('/menus', methods=accepted_methods)
@login_required
def menus():
    return render_template('admin/index.html')

@account.route('/menu/<name>', methods=accepted_methods)
@login_required
def menu(name):
    return render_template('admin/index.html')

@account.route('/projects', methods=accepted_methods)
@login_required
def projects():
    page = request.args.get('page', 1, type=int)
    pagination = Project.query.order_by(Project.timestamp.desc()).paginate(
        page, per_page=current_app.config['ENTRIES_PER_PAGE'], error_out=False
    )
    projects = pagination.items
    return render_template('admin/projects.html', projects=projects, pagination=pagination, page=page)

@account.route('/project/<name>/delete')
def project_delete(name):
    project = Project.query.filter_by(name=name).first_or_404()
    msg = Markup('<div class="alert alert-light alert-dismissible mb-4 py-3 border-left-success">Project deleted<button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>')
    flash(msg)
    db.session.delete(project)
    db.session.commit()
    return redirect(url_for('account.projects'))

@account.route('/post/<name>/edit', methods=accepted_methods)
@login_required
def project_edit(name):
    form = ProjectForm()
    project = Project.query.filter_by(name=name).first_or_404()
    categories = PostCategory.query.all()
    tags = Tag.query.all()

    if request.method == 'GET':
        form.name.data = project.name
        form.content.data = project.content


    if form.validate_on_submit():
        project.name = form.name.data 
        project.slug = form.name.data.translate(translate).replace(' ', '-').replace('.', '').lower()
        project.content = form.content.data
        project.summary = summarize(form.content.data)

        featured_image = upload_file('featured_image', filetype='project')

        if featured_image:
            project.featured_image = featured_image

        db.session.add(project)
        db.session.commit()
        msg = Markup('<div class="alert alert-light alert-dismissible mb-4 py-3 border-left-success">Project {} edited<button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>')
        flash(msg.format(project.name))
        return redirect(url_for('account.project_edit', name=project.name, form=form, categories=categories, tags=tags))
    return render_template('admin/project.edit.html', form=form, project=project, categories=categories, tags=tags)

@account.route('/project/new', methods=accepted_methods)
@login_required
def project_create():
    form = ProjectForm()

    if form.validate_on_submit():
        project = Project()
        project.name = form.name.data
        project.slug = form.name.data.translate(translate).replace(' ', '-').replace('.', '').lower()
        project.content = form.content.data

        featured_image = upload_file('featured_image', filetype='project')

        if featured_image:
            project.featured_image = featured_image

        session['name'] = project.name

        db.session.add(project)
        db.session.commit()
        return redirect(url_for('account.project_edit', name=project.name))
    return render_template('admin/project.edit.html', form=form)

@account.route('/posts', methods=accepted_methods)
@login_required
def posts():
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['ENTRIES_PER_PAGE'], error_out=False
    )
    posts = pagination.items
    return render_template('admin/posts.html', posts=posts, pagination=pagination, page=page)

@account.route('/post/<title>/delete')
def post_delete(title):
    post = Post.query.filter_by(title=title).first_or_404()
    msg = Markup('<div class="alert alert-light alert-dismissible mb-4 py-3 border-left-success">Post deleted<button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>')
    flash(msg)
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for('account.posts'))

@account.route('/post/edit/<title>', methods=accepted_methods)
@login_required
def post_edit(title):
    form = PostForm()
    post = Post.query.filter_by(title=title).first_or_404()
    categories = PostCategory.query.all()
    tags = Tag.query.all()

    if request.method == 'GET':
        form.title.data = post.title
        form.permalink.data = post.permalink
        form.visibility.data = post.visibility
        form.summary.data = post.summary
        form.content.data = post.content
        form.allow_comments.data = post.allow_comments
        form.allow_pingbacks.data = post.allow_pingbacks
        form.is_sticky.data = post.is_sticky

    if form.validate_on_submit():
        post.title = form.title.data 
        post.permalink = form.title.data.translate(translate).replace(' ', '-').replace('.', '').lower()
        post.visibility = form.visibility.data
        post.user_id = current_user.id
        post.summary = form.summary.data
        post.content = form.content.data

        featured_image = upload_file('featured_image', filetype='post')

        if featured_image:
            post.featured_image = featured_image

        db.session.add(post)
        db.session.commit()
        msg = Markup('<div class="alert alert-light alert-dismissible mb-4 py-3 border-left-success">Post {} edited<button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>')
        flash(msg.format(post.title))
        return redirect(url_for('account.post_edit', title=post.title, form=form, categories=categories, tags=tags))
    return render_template('admin/post.edit.html', form=form, post=post, categories=categories, tags=tags)

@account.route('/post/new', methods=accepted_methods)
@login_required
def post_create():
    form = PostForm()

    if form.validate_on_submit():
        post = Post()
        post.title = form.title.data
        post.permalink = form.title.data.translate(translate).replace(' ', '-').replace('.', '').lower()
        post.visibility = form.visibility.data
        post.user_id = current_user.id
        post.summary = form.summary.data
        post.content = form.content.data

        featured_image = upload_file('featured_image', filetype='post')

        if featured_image:
            post.featured_image = featured_image

        session['title'] = post.title

        db.session.add(post)
        db.session.commit()
        return redirect(url_for('account.post_edit', title=post.title))
    return render_template('admin/post.edit.html', form=form)

@account.route('/posts/tags', methods=accepted_methods)
@login_required
def post_tags():
    page = request.args.get('page', 1, type=int)

    pagination = Tag.query.order_by(Tag.timestamp.desc()).paginate(
        page, per_page=current_app.config['ENTRIES_PER_PAGE'], error_out=False
    )
    tags = pagination.items
    form = TagForm()

    if form.validate_on_submit():
        tag = Tag()
        tag.name = form.name.data.lower()

        db.session.add(tag)
        db.session.commit()
        msg = Markup('<div class="alert alert-light alert-dismissible mb-4 py-3 border-left-success">Tag added<button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>')
        flash(msg)

        return redirect(request.url)
    return render_template('admin/tags.html', tags=tags, tag_count=len(tags), form=form, pagination=pagination)

@account.route('/posts/tag/<name>/delete')
@login_required
def tag_delete(name):
    tag = Tag.query.filter_by(name=name).first_or_404()
    msg = Markup('<div class="alert alert-light alert-dismissible mb-4 py-3 border-left-success">Tag deleted<button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>')
    flash(msg)
    db.session.delete(tag)
    db.session.commit()
    return redirect(url_for('account.post_tags'))

@account.route('/post/tag/<name>/add/<postid>')
@login_required
def tag_add(name, postid):
    post = Post.query.filter_by(id=postid).first_or_404()
    tag = Tag.query.filter_by(name=name).first_or_404()
    post.tags.append(tag)
    db.session.add(post)
    db.session.commit()
    msg = Markup('<div class="alert alert-light alert-dismissible mb-4 py-3 border-left-success">Tag added<button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>')
    flash(msg)
    return redirect(url_for('account.post_edit', title=post.title))

@account.route('/project/tag/<name>/<projectid>')
@login_required
def tag_project(name, projectid):
    project = Project.query.filter_by(id=projectid).first_or_404()
    tag = Tag.query.filter_by(name=name).first_or_404()
    project.tags.append(tag)
    db.session.add(project)
    db.session.commit()
    msg = Markup('<div class="alert alert-light alert-dismissible mb-4 py-3 border-left-success">Tag added<button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>')
    flash(msg)
    return redirect(url_for('account.project_edit', name=project.name))

@account.route('/posts/category/<name>/delete')
@login_required
def cat_delete(name):
    cat = PostCategory.query.filter_by(name=name).first_or_404()
    msg = Markup('<div class="alert alert-light alert-dismissible mb-4 py-3 border-left-success">Category deleted<button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>')
    flash(msg)
    db.session.delete(cat)
    db.session.commit()
    return redirect(url_for('account.post_cats'))

@account.route('/post/category/<name>/add/<postid>')
@login_required
def cat_add(name, postid):
    post = Post.query.filter_by(id=postid).first_or_404()
    cat = PostCategory.query.filter_by(name=name).first_or_404()
    post.categories.append(cat)
    db.session.add(post)
    db.session.commit()
    msg = Markup('<div class="alert alert-light alert-dismissible mb-4 py-3 border-left-success">Category added<button role="button" class="close" data-dismiss="alert" type="button">&times;</button></div>')
    flash(msg)
    return redirect(url_for('account.post_edit', title=post.title))

@account.route('/posts/categories', methods=accepted_methods)
@login_required
def post_cats():
    page = request.args.get('page', 1, type=int)

    pagination = PostCategory.query.order_by(PostCategory.timestamp.desc()).paginate(
        page, per_page=current_app.config['ENTRIES_PER_PAGE'], error_out=False
    )
    categories = pagination.items

    form = CatForm()

    if form.validate_on_submit():
        category = PostCategory()
        category.name = form.name.data
        category.slug = form.name.data.translate(translate).replace(' ', '-').lower()

        db.session.add(category)
        db.session.commit()

        return redirect(url_for('account.post_cats'))
    return render_template('admin/categories.html', categories=categories, category_count=len(categories), form=form, pagination=pagination)

@account.route('/media', methods=accepted_methods)
@login_required
def media():
    page = request.args.get('page', 1, type=int)

    pagination = Media.query.order_by(Media.timestamp.desc()).paginate(
        page, per_page=current_app.config['ENTRIES_PER_PAGE'], error_out=False
    )
    media = pagination.items
    return render_template('admin/media.html', media=media, media_count=len(media), pagination=pagination)

@account.route('/media/upload', methods=accepted_methods)
def media_upload():
    form = MediaForm()
    if form.validate_on_submit():
        media = Media()
        the_file = upload_file('filename')

        if not the_file:
            return redirect(request.url)

        filename,extension = splitext(the_file)

        media.title = form.title.data or the_file.split('.')
        media.caption = form.caption.data
        media.filename = the_file
        media.filetype = check_extension(extension)
        media.description = form.description.data
        media.user_id = current_user.id

        db.session.add(media)
        db.session.commit()
        return redirect(url_for('account.media_upload', title=media.title))
    return render_template('admin/media.edit.html', form=form)

@account.route('/media/<id>/delete')
def media_delete(id):
    return render_template(url_for('account.media'))

@account.route('/res/media')
def get_media():
    return json.jsonify(Media.as_dict())

@account.route('/settings', methods=accepted_methods)
@login_required
def settings():
    return render_template('admin/settings.html')

@account.route('/setup', methods=accepted_methods)
def setup():
    form = SetupForm()
    Role.insert_roles()
    PostCategory.insert()
    Tag.insert()

    if form.validate_on_submit():
        admin = Role.query.filter_by(name='Administrator').first()
        print("Creating user")
        user = User()
        user.username = form.username.data
        user.email = form.email.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.password = form.password.data
        print("Adding user role Administrator")
        user.role = admin
        print(user.role.name)
        print("Success")

        db.session.add(user)
        db.session.commit()
        return render_template('admin/setup.success.html', user=user)
    return render_template('admin/setup.html', form=form)
