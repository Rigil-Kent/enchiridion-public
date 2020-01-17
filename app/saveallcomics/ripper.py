import os
import urllib.request
from bs4 import BeautifulSoup


def get_soup_obj(url, headers):
    req = urllib.request.Request(url, headers=headers)
    raw = urllib.request.urlopen(req)

    return BeautifulSoup(raw, 'html.parser')


def get_title(soup):
    ''' Grab the title element string from a Beautiful Soup object
    removing the last 45 garbage characters'''
    comic_title = soup.title.string.replace('Read All Comics Online For Free', '').replace('…', '').replace('|', '').replace(' ...', '')
    return comic_title.strip()


def get_img_links(soup):
    images = []
    for link in soup.findAll('a'):
        if not link.has_attr('href') and link.string != 'More results...':
            print(link.string)
            img = link.img['src']
            images.append(img)

    return images

def download_img_links(links, soup, folder, title=None):
    # test to see if the folder exists
    if title is None:
        print('No title specified\ncreating from reqest')
        title = get_title(soup)
    # if it doesn't, create it
    if not os.path.exists(os.path.join(folder, title)):
        os.makedirs(os.path.join(folder, title), mode=0o777)
        print('Folder {} created...'.format(os.path.join(folder, title)))
    # retrieve files from server
    for link in links:
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-agent', 'Mozilla/5.0')]
        urllib.request.install_opener(opener)
        print('Downloading file {} from {}'.format((link[-6:] if link[-11:-4] != '%2Bcopy' else (link[-13:-11] + link[-4:]) ), title))
        urllib.request.urlretrieve(link, filename=os.path.join(folder + '/' + title, title + ' 0' + (link[-6:] if link[-11:-4] != '%2Bcopy' else (link[-13:-11] + link[-4:]) )))

    print("Download Complete!")
    
