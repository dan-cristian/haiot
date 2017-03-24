import pylast
from main.admin.model_helper import get_param
from common import Constant
from music import mpd, gmusicproxy
from main.logger_helper import Log
import json

USERNAME = None
_network = None

def init():
    config_file = get_param(Constant.P_LASTFM_CONFIG_FILE)
    with open(config_file, 'r') as f:
        config_list = json.load(f)
    global _network, USERNAME
    API_KEY = config_list['lastfm_api']
    API_SECRET = config_list['lastfm_secret']
    USERNAME = config_list['lastfm_user']
    PASSWORD = config_list['lastfm_pass']
    # In order to perform a write operation you need to authenticate yourself
    password_hash = pylast.md5(PASSWORD)
    _network = pylast.LastFMNetwork(api_key=API_KEY, api_secret=API_SECRET,
                                    username=USERNAME, password_hash=password_hash)


def _multify(text):
    every = 18
    lines = []
    for i in xrange(0, len(text), every):
        lines.append(text[i:i + every])
    return '\n'.join(lines)


def _get_current():
    global _network, USERNAME
    if _network is None:
        init()
    track = _network.get_user(USERNAME).get_now_playing()
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


def get_loved_tracks_to_mpd():
    global _network, USERNAME
    if _network is None:
        init()
    loved_tracks = _network.get_user(USERNAME).get_loved_tracks(limit=None)
    mpd_client = mpd.get_first_active_mpd()
    added = 0
    if mpd_client is not None:
        mpd_client.clear()
        for track in loved_tracks:
            artist = track[0].artist.name
            title = track[0].title
            # print track[0].artist.name, track[0].title
            res = mpd_client.find("any", title)
            if len(res) == 0:
                Log.logger.info("Searching in Google Music for {}".format(title.encode('utf-8')))
                gsong_id = gmusicproxy.get_song_id(artist=artist, title=title)
                if gsong_id is not None:
                    mpd_client.add(gmusicproxy.get_song_url(gsong_id))
                    added += 1
                else:
                    Log.logger.warning("Could not find song {} in Google Music".format(title.encode('utf-8')))
            else:
                mpd_client.add(res[0]['file'])
                added += 1
        mpd_client.close()
        mpd_client.disconnect()
    else:
        Log.logger.warning('No active mpd instance found')
    result = 'Added {} songs'.format(added)
    return '{"result": "' + _multify(result) + '"}'
