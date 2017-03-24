from mpd import MPDClient
from main.logger_helper import Log
from main.admin.model_helper import get_param
from common import Constant


def get_first_active_mpd():
    port_config = get_param(Constant.P_MPD_PORT_ZONE).split(',')

    alt_port = None
    alt_zone = None

    client = MPDClient()
    client.timeout = 5
    # get the zone playing, only if one is active
    port_list_play = []
    for pair in port_config:
        port_val = int(pair.split('=')[1])
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
        return None


def next():
    client = get_first_active_mpd()
    if client is not None:
        client.next()


def toggle():
    client = get_first_active_mpd()
    if client is not None:
        if client.status()['state'] == 'play':
            client.pause(1)
        else:
            client.pause(0)
