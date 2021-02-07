import unicodedata
from main.logger_helper import L
from common import Constant, get_json_param
from main import sqlitedb
from cloud import lastfm
from storage.model import m

from common import fix_module
while True:
    try:
        from mpd import MPDClient
        break
    except ImportError as iex:
        if not fix_module(iex):
            break


class P:
    zone_port = {}
    unique_ports = {}
    thread_pool_status = ''

    def __init__(self):
        pass


def _multify(text):
    every = 18
    lines = []
    for i in range(0, len(text), every):
        lines.append(text[i:i + every])
    return '\n'.join(lines)


def _get_port(zone_name):
    if zone_name in P.zone_port.keys():
        return P.zone_port[zone_name]
    else:
        return None


def _get_client(port=None):
    client = MPDClient()
    client.timeout = 5
    if port is not None:
        client.connect(get_json_param(Constant.P_MPD_SERVER), port)
    return client


def _close_client(client):
    client.close()
    client.disconnect()


def get_first_active_mpd():
    port_config = get_json_param(Constant.P_MPD_PORT_ZONE).split(',')
    first_port = None
    alt_port = None
    alt_zone = None

    client = _get_client()
    # get the zone playing, only if one is active
    port_list_play = []
    for pair in port_config:
        port_val = int(pair.split('=')[1])
        if first_port is None:
            first_port = port_val
        zone_val = pair.split('=')[0]
        client.connect(get_json_param(Constant.P_MPD_SERVER), port_val)
        if client.status()['state'] == 'play':
            port_list_play.append(port_val)
            alt_zone = zone_val
        client.close()
        client.disconnect()
    if len(port_list_play) == 1:
        alt_port = port_list_play[0]
        zone = alt_zone
    if alt_port is not None:
        client.connect(get_json_param(Constant.P_MPD_SERVER), alt_port)
        return client
    else:
        client.connect(get_json_param(Constant.P_MPD_SERVER), first_port)
        return client


def next():
    client = get_first_active_mpd()
    if client is not None:
        client.next()
    result = client.currentsong()['title']
    return '{"result": "' + _multify(result) + '"}'


def next_song(zone_name):
    client = _get_client(_get_port(zone_name))
    if client is not None:
        client.next()
        # force state change
        client.pause(1)
        client.pause(0)


def previous_song(zone_name):
    client = _get_client(_get_port(zone_name))
    if client is not None:
        client.previous()


def toggle():
    client = get_first_active_mpd()
    if client is not None:
        if client.status()['state'] == 'play':
            client.pause(1)
        else:
            client.pause(0)
    result = client.status()['state']
    return '{"result": "' + _multify(result) + '"}'


def toggle_state(zone_name):
    client = _get_client(_get_port(zone_name))
    if client is not None:
        if client.status()['state'] == 'play':
            client.pause(1)
        else:
            if client.status()['state'] == 'stop':
                client.play()
            else:
                client.pause(0)


def is_playing(client):
    return client.status()['state'] == 'play'


def play(zone_name, default_dir=None):
    client = _get_client(_get_port(zone_name))
    if client is not None:
        client.play()
        if client.status()['state'] != 'play':
            populate(zone_name, default_dir)
            client.play()
        return client.status()['state'] == 'play'
    else:
        return False


def pause(zone_name):
    client = _get_client(port=_get_port(zone_name))
    if client is not None:
        client.pause(1)
        return client.status()['state'] == 'stop'
    else:
        return False


def set_volume(zone_name, volume):
    client = _get_client(_get_port(zone_name))
    if client is not None:
        client.setvol(volume)
        L.l.info('Set volume for {} vol={}'.format(zone_name, volume))


def set_position(zone_name, position_percent):
    client = _get_client(_get_port(zone_name))
    if client is not None and is_playing(client):
        song = client.currentsong()
        if 'time' in song:
            client.seekcur(float(song['time']) * position_percent / 100)
    else:
        L.l.info('Cannot set position as client is none or not playing')


# http://pythonhosted.org/python-mpd2/topics/commands.html#the-music-database
def populate(zone_name, default_dir=None):
    client = _get_client(port=_get_port(zone_name))
    if client is not None:
        # fixme: populate playlist
        client.clear()
        if default_dir is None:
            client.add('/')
        else:
            client.add(default_dir)
        client.random(1)
        return len(client.playlist())
    else:
        return False


def _read_port_config():
    port_config = get_json_param(Constant.P_MPD_PORT_ZONE).split(',')
    for pair in port_config:
        split = pair.split('=')
        names = split[0]
        port = split[1]
        if ':' in names:
            name_list = names.split(':')
            for name in name_list:
                P.zone_port[name] = int(port)
                P.unique_ports[int(port)] = name
        else:
            P.zone_port[names] = int(port)
            P.unique_ports[int(port)] = names


def _normalise(uni):
    # if isinstance(uni, str):
    # uni = uni.decode('utf-8')
    return uni
    #return unicodedata.normalize('NFKD', uni).encode('ascii', 'ignore')


# {'songid': '100', 'playlistlength': '32', 'playlist': '8', 'repeat': '0', 'consume': '0', 'mixrampdb': '0.000000',
# 'random': '0', 'state': 'play', 'elapsed': '116.831', 'volume': '26', 'single': '0', 'nextsong': '4',
# 'time': '117:262', 'song': '3', 'audio': '44100:24:2', 'bitrate': '320', 'nextsongid': '101'}
#
# {'album': 'A State of Trance 888 (2018-11-01) [IYPP] (SBD)', 'title': 'Destiny', 'track': '20',
# 'artist': 'Soul Lifters', 'pos': '19', 'last-modified': '2018-11-02T18:44:57Z',
# 'file': '_New/recent/asot888/20. Soul Lifters - Destiny.mp3', 'time': '287', 'id': '116'}
def _save_status(zone, status_json, song):
    rec = m.Music.find_one({m.Music.zone_name: zone})
    if rec is None:
        rec = m.Music()
        rec.zone_name = zone
    rec.state = status_json['state']
    if rec.state == 'stop':
        rec.title = ''
        rec.artist = ''
        rec.album = ''
        rec.song = ''
    else:
        if 'title' in song:
            rec.title = _normalise(song['title'])
        if 'artist' in song:
            rec.artist = _normalise(song['artist'])
        if 'album' in song:
            rec.album = _normalise(song['album'])
        if rec.title and rec.artist:
            rec.song = "{} - {}".format(rec.artist, rec.title)
        if 'volume' in status_json:
            rec.volume = int(status_json['volume'])
    if 'elapsed' in status_json and 'time' in song:
        rec.position = int(100 * (float(status_json['elapsed']) / float(song['time'])))
    rec.save_changed_fields(broadcast=True)


def save_lastfm():
    P.thread_pool_status = 'Saving lastfm'
    lastfmloved = lastfm.iscurrent_loved()
    lastfmsong = lastfm.get_current_song()
    if lastfmsong is not None:
        recs = m.MusicLoved.find()
        if len(recs) > 0:
            rec = recs[0]
        else:
            rec = m.MusicLoved()
        rec.lastfmsong = lastfmsong
        if lastfmloved is None:
            lastfmloved = False
        rec.lastfmloved = lastfmloved
        rec.lastfmsong = lastfmsong
        # notify all as loved state might not change
        rec.save_changed_fields(broadcast=True, persist=True)


def update_state(zone_name):
    if zone_name is not None:
        client = _get_client(_get_port(zone_name=zone_name))
        if client is not None:
            status = client.status()
            song = client.currentsong()
            _save_status(zone=zone_name, status_json=status, song=song)
    else:
        update_state_all()


def update_state_all():
    try:
        for port in P.unique_ports.keys():
            P.thread_pool_status = 'MPD port {}'.format(port)
            client = _get_client(port)
            if client is not None:
                zone_name = P.unique_ports[port]
                status = client.status()
                song = client.currentsong()
                _save_status(zone=zone_name, status_json=status, song=song)
    except Exception as ex:
        L.l.error('Error in mpd run, ex={}'.format(ex), exc_info=True)


# https://github.com/Mic92/python-mpd2/blob/master/doc/topics/commands.rst
def thread_run():
    update_state_all()
    save_lastfm()


def init():
    _read_port_config()
