from urllib import addinfo

import pylast
from main.admin.model_helper import get_param
from common import Constant
from music import mpd, gmusicproxy
from main.logger_helper import L
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
        try:
            if track.get_userloved():
                prefix = '! '
            else:
                prefix = ''
        except Exception, ex:
            prefix = "? "
        return '{"result": "' + _multify(prefix + track.title) + '"}'


def _add_to_playlist(tracks):
    mpd_client = mpd.get_first_active_mpd()
    added = 0
    if mpd_client is not None:
        mpd_client.clear()
        for track in tracks:
            if type(track) == pylast.Track:
                artist = track.artist.name
                title = track.title
            else:
                artist = track[0].artist.name
                title = track[0].title
            # print track[0].artist.name, track[0].title
            L.l.info("Searching for {} - {}".format(artist.encode('utf-8'), title.encode('utf-8')))
            res = mpd_client.search("any", title)
            if len(res) == 0:
                L.l.info("Search again in mpd")
                res = mpd_client.search("file", title)
            if len(res) == 0:
                L.l.info("Searching in Google Music as song not found in mpd")
                gsong_id = gmusicproxy.get_song_id(artist=artist, title=title)
                if gsong_id is not None:
                    # adding stream songs first to encourage first play (these are newer I guess)
                    if added > 1:
                        addindex = 1  # keep first song first
                    else:
                        addindex = 0
                    L.l.info("Added file {}".format(gmusicproxy.get_song_url(gsong_id)))
                    mpd_client.addid(gmusicproxy.get_song_url(gsong_id), addindex)
                    added += 1
                else:
                    L.l.warning("Could not find the song in Google Music")
            else:
                mpd_client.add(res[0]['file'])
                L.l.info("Added file {}".format(res[0]['file']))
                added += 1
            if added == 1:  # fixme: might re-play several times
                mpd_client.play(0)
        mpd_client.close()
        mpd_client.disconnect()
        result = 'Added {} songs'.format(added)
    else:
        result = 'Lastfm: No active mpd instance found'
        L.l.warning(result)
    return result


def get_by_tag(tag):
    global _network, USERNAME
    if _network is None:
        init()
    tracks = _network.get_user(USERNAME).get_tagged_tracks(tag)
    result = _add_to_playlist(tracks)
    return '{"result": "' + _multify(result) + '"}'


def get_loved_tracks_to_mpd():
    global _network, USERNAME
    if _network is None:
        init()
    loved_tracks = _network.get_user(USERNAME).get_loved_tracks(limit=None)
    result = _add_to_playlist(loved_tracks)
    return '{"result": "' + _multify(result) + '"}'
