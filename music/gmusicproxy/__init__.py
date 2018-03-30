from main.logger_helper import L
from main.admin.model_helper import get_param
from common import Constant
import requests
import urllib


# http://gmusicproxy.net/

def get_song_id(artist, title):
    url = get_param(Constant.P_GMUSICPROXY_URL)
    title = urllib.quote(title.encode('utf-8'), safe='')
    artist = urllib.quote(artist.encode('utf-8'), safe='')
    param = '/search_id?type=song&title={}&artist={}&exact=yes'.format(title, artist)
    try:
        result = requests.get('{}{}'.format(url, param), timeout=7).text
        if result == '':
            return None
        else:
            return result
    except Exception, ex:
        L.l.critical("Error on get song from google proxy: {}".format(ex))
        return None

def get_song_url(song_id):
    url = get_param(Constant.P_GMUSICPROXY_URL)
    param = '/get_song?id={}'.format(song_id)
    return '{}{}'.format(url, param)
