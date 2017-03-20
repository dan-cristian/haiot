import pylast
from main.admin.model_helper import get_param
from common import Constant
import json

API_KEY = None
API_SECRET = None
USERNAME = None
PASSWORD = None


def init():
    config_file = get_param(Constant.P_LASTFM_CONFIG_FILE)
    with open(config_file, 'r') as f:
        config_list = json.load(f)
    global API_KEY, API_SECRET, USERNAME, PASSWORD
    API_KEY = config_list['lastfm_api']
    API_SECRET = config_list['lastfm_secret']
    USERNAME = config_list['lastfm_user']
    PASSWORD = config_list['lastfm_pass']


def _multify(text):
    every = 22
    lines = []
    for i in xrange(0, len(text), every):
        lines.append(text[i:i + every])
    return '\n'.join(lines)


def _get_current():
    global API_KEY, API_SECRET, USERNAME, PASSWORD
    if API_KEY is None:
        init()
    # In order to perform a write operation you need to authenticate yourself
    password_hash = pylast.md5(PASSWORD)
    network = pylast.LastFMNetwork(api_key=API_KEY, api_secret=API_SECRET,
                                   username=USERNAME, password_hash=password_hash)
    track = network.get_user(USERNAME).get_now_playing()
    return track


def love(request):
    track = _get_current()
    if track is None:
        result = "Not Playing!"
    else:
        track.love()
        if track.get_userloved():
            result = 'LOVED ' + track.title
        else:
            result = 'Failed!'
    return '{"result": "' + _multify(result) + '"}'


def current():
    track = _get_current()
    if track is None:
        return '{"result": "None Playing!"}'
    else:
        if track.get_userloved():
            prefix = '! '
        else:
            prefix = ''
        return '{"result": "' + _multify(prefix + track.title) + '"}'

