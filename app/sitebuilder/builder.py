from markdown2 import markdown
from jinja2 import Environment, FileSystemLoader
from json import load
from abc import ABCMeta, abstractmethod
import os
from flask import redirect, url_for


# template_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'templates')
template_env = Environment(loader=FileSystemLoader(searchpath='./'))
template = template_env.get_template('app/sitebuilder/layout.html')

# load options from json config
try:
    with open('app/sitebuilder/config.json') as cfg:
        config = load(cfg)
except Exception as msg:
    print('[\033[1;31mError\33[0m] Unable to load configuration file. Exiting with the following error: \n{}'.format(msg))
    return redirect('auth.shutdown')

# 
templates = Environment(loader=FileSystemLoader(searchpath=config['template_dir']))
index = templates.get_template('index.html')
page = templates.get_template('page.html')
blog = templates.get_template('blog.html')
post = templates.get_template('post.html')

# read template markdown
def generate_markdown(template):
    with open('app/sitebuilder/{}.md'.format(template)) as markdown_file:
        content = markdown(
            markdown_file.read(),
            extras=['fenced-code-blocks', 'code-friendly']
        )

# write updated contents of layout.html to index.html
def generate_layout(template):
    with open('app/sitebuilder/{}.html'.format(template), 'w') as out_file:
        out_file.write(
            template.render(
                title=config['title'],
                description=config['description'],
                author=config['author'],
                code_link=config['code_link'],
                identifier=config['identifier'],
                url=config['url'],
                article=article
            )
        )

# render the layout class from the name
def render_layout(layout):
    website = eval(layout)()
    return website

def write_template(template):
    content = ""
    for section in template.sections:
        print('writing section -- {}'.format(section))
        content += section.content()
        try:
            with open('{}.html'.format(type(template).__name__), 'w') as page:
                page.write(content)
        except Exception as msg:
            print('[\033[1;31mFail\033[0m] Unable to write page {}'.format(type(template).__name__))
        

def build_site(template):
    try:
        layout = eval(template)()
        print('[\033[1;32mBuild\033[0m] Creating {} website'.format(type(template).__name__))
        print('The following components will be generated: {}'.format(template.get_sections()))
        print('[\033[1;32mBuild\033[0m] Successfully created {}'.format(type(template).__name__))
        return layout
    except Exception as msg:
        print('[\033[1;31mFail\033[0m] Unable to build site layout\n{}'.format(msg))