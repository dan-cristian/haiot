from mpd import MPDClient
from main.logger_helper import L
from main.admin.model_helper import get_param
from common import Constant


def _multify(text):
    every = 18
    lines = []
    for i in xrange(0, len(text), every):
        lines.append(text[i:i + every])
    return '\n'.join(lines)


def _get_port(zone_name):
    port_config = get_param(Constant.P_MPD_PORT_ZONE).split(',')
    for pair in port_config:
        split = pair.split('=')
        if split[0] == zone_name:
            return int(split[1])
    return None


def _get_client(port=None):
    client = MPDClient()
    client.timeout = 5
    if port is not None:
        client.connect(get_param(Constant.P_MPD_SERVER), port)
    return client


def _close_client(client):
    client.close()
    client.disconnect()


def get_first_active_mpd():
    port_config = get_param(Constant.P_MPD_PORT_ZONE).split(',')
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
        client.connect(get_param(Constant.P_MPD_SERVER), port_val)
        if client.status()['state'] == 'play':
            port_list_play.append(port_val)
            alt_zone = zone_val
        client.close()
        client.disconnect()
    if len(port_list_play) == 1:
        alt_port = port_list_play[0]
        zone = alt_zone
    if alt_port is not None:
        client.connect(get_param(Constant.P_MPD_SERVER), alt_port)
        return client
    else:
        client.connect(get_param(Constant.P_MPD_SERVER), first_port)
        return client


def next():
    client = get_first_active_mpd()
    if client is not None:
        client.next()
    result = client.currentsong()['title']
    return '{"result": "' + _multify(result) + '"}'


def toggle():
    client = get_first_active_mpd()
    if client is not None:
        if client.status()['state'] == 'play':
            client.pause(1)
        else:
            client.pause(0)
    result = client.status()['state']
    return '{"result": "' + _multify(result) + '"}'


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
