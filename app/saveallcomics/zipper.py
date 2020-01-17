import os
import shutil
import zipfile

basedir = os.path.dirname(__file__)

def create_comic_archive(title, folder):
    print('Creating comic archive: {}.cbr'.format(title))

    output = shutil.make_archive(title, 'zip', folder)
    os.rename(output, os.path.join(folder, title +'.cbr'))
    print('Performing folder cleanup...')
    ignore = ('.cbr', '000.jpg')
    for img in os.listdir(folder):
        if not img.endswith(ignore):
            os.remove(os.path.join(folder, img))