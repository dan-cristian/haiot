# from urllib import addinfo


# from main.admin.model_helper import get_param
import os
from common import Constant, get_json_param
import music.mpd
from music import gmusicproxy
from main.logger_helper import L
import json
from difflib import get_close_matches
import pylast
import re


class P:
    USERNAME = None
    network = None

    def __init__(self):
        pass


def _multify(text):
    every = 18
    lines = []
    for i in range(0, len(text), every):
        lines.append(text[i:i + every])
    return '\n'.join(lines)



def _get_current():
    track = None
    if P.network is None:
        init()
    if P.network is not None:
        try:
            track = P.network.get_user(P.USERNAME).get_now_playing()
        except Exception as ex:
            L.l.warning("Unable to get current lastfm play, err={}".format(ex))
    else:
        L.l.warning("Unable to init lastfm network")
    return track


def love(request):
    track = _get_current()
    if track is None:
        result = "Not Playing!"
    else:
        track.love()
        for i in range(1, 4):
            if track.get_userloved():
                result = 'LOVED ' + track.title
                break
            else:
                result = 'Failed-{}!'.format(i)
    return '{"result": "' + _multify(result) + '"}'


# used for garmin
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
        except Exception as ex:
            prefix = "? "
        return '{"result": "' + _multify(prefix + track.title) + '"}'


def get_current_song():
    track = _get_current()
    if track is not None:
        return track.title
    else:
        return None


def iscurrent_loved():
    track = _get_current()
    res = None
    if track is not None:
        try:
            res = track.get_userloved()
        except Exception as ex:
            L.l.warning('Cannot get track love status, ex={}'.format(ex))
    return res


def set_current_loved(loved):
    track = _get_current()
    res = None
    if track is not None:
        try:
            if loved:
                res = track.love()
            else:
                res = track.unlove()
        except Exception as ex:
            L.l.warning('Cannot set track love status, ex={}'.format(ex))
    return res


def _complex_search(artist, title, mpd_client):
    #artist = 'PLAYROOM - STANDERWICK'.lower()
    #title = 'Apricus (ASOT 1002) [Progressive Pick]'.lower()
    #item = 'Trance/asot/asot1002/Armin van Buuren - A State Of Trance 1002 (04.02.2021) SBD Split Track/08. STANDERWICK - Apricus [PROGRESSIVE PICK].mp3'.lower()
    #song_list = ['AC_DC/Back In Black/00 Freebird.mp3'.lower(), item]
    #match = get_close_matches(title, song_list, n=2, cutoff=0.2)
    #if len(match) == 0:
    #    match = get_close_matches(artist, song_list, n=2, cutoff=0.2)
    #return match
    res = []
    clean_title = re.sub(re.compile(r'[^a-zA-Z ]+'), '', title).lower().strip()
    clean_artist = re.sub(re.compile(r'[^a-zA-Z ]+'), '', artist).lower().strip()
    splits = clean_title.split()
    for prev, curr in zip(splits, splits[1:]):
        res = mpd_client.search("title", prev)
        if len(res) == 1:
            return res
        elif len(res) > 1:
            res = mpd_client.search("title", '{} {}'.format(prev, curr))
            if len(res) == 1:
                return res
            else:
                for song in res:
                    if ('title' in song and title in song['title'].lower()) \
                            or ('artist' in song and artist in song['artist'].lower()) \
                            or ('artist' in song and clean_artist in song['artist'].lower()) \
                            or ('albumartist' in song and artist in song['albumartist'].lower())\
                            or ('albumartist' in song and clean_artist in song['albumartist'].lower()):
                        return [song]

    splits = clean_artist.split()
    for prev, curr in zip(splits, splits[1:]):
        res = mpd_client.search("artist", prev)
        if len(res) == 1:
            return res
        elif len(res) > 1:
            res = mpd_client.search("artist", '{} {}'.format(prev, curr))
            if len(res) == 1:
                return res
    return []


def _add_to_playlist(tracks):
    mpd_client = music.mpd.get_first_active_mpd()
    all_songs = None
    song_list = []
    added = 0
    missed = 0
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
                # L.l.info("Search again in mpd")
                res = mpd_client.search("file", title)
                if len(res) == 0:
                    if all_songs is None:
                        all_songs = mpd_client.listall('/')
                        for song in all_songs:
                            if 'file' in song:
                                song_list.append(song['file'].lower())
                    res = _complex_search(artist, title, mpd_client)
            if len(res) > 0:
                mpd_client.add(res[0]['file'])
                L.l.info("Added file {}".format(res[0]['file']))
                added += 1
            else:
                L.l.warning("Could not find music track {}".format(title))
                missed += 1
            if False:  # len(res) == 0:
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

            if added == 1:  # fixme: might re-play several times
                mpd_client.play(0)
        mpd_client.close()
        mpd_client.disconnect()
        result = 'Added {}, missed {} songs'.format(added, missed)
    else:
        result = 'Lastfm: No active mpd instance found'
        L.l.warning(result)
    return result


def get_by_tag(tag):
    if P.network is None:
        init()
    if P.network is not None:
        tracks = P.network.get_user(P.USERNAME).get_tagged_tracks(tag)
        result = _add_to_playlist(tracks)
    else:
        result = 'not init'
    return '{"result": "' + _multify(result) + '"}'


def get_loved_tracks_to_mpd():
    if P.network is None:
        init()
    if P.network is not None:
        loved_tracks = P.network.get_user(P.USERNAME).get_loved_tracks(limit=None)
        result = _add_to_playlist(loved_tracks)
    else:
        result = 'not init'
    return '{"result": "' + _multify(result) + '"}'


def init():
    config_file = get_json_param(Constant.P_LASTFM_CONFIG_FILE)
    if os.path.isfile(config_file):
        with open(config_file, 'r') as f:
            config_list = json.load(f)
        API_KEY = config_list['lastfm_api']
        API_SECRET = config_list['lastfm_secret']
        P.USERNAME = config_list['lastfm_user']
        PASSWORD = config_list['lastfm_pass']
        # In order to perform a write operation you need to authenticate yourself
        password_hash = pylast.md5(PASSWORD)
        try:
            P.network = pylast.LastFMNetwork(
                api_key=API_KEY, api_secret=API_SECRET, username=P.USERNAME, password_hash=password_hash)
        except Exception as ex:
            L.l.error("Cannot init lastfm, ex={}".format(ex))
    else:
        L.l.info('Missing config file for lastfm')
