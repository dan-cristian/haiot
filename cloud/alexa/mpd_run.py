from mpd import MPDClient
from main.logger_helper import L
from main.admin.model_helper import get_param
from common import Constant


def mpd(request):
    if request.json is not None:
        L.l.info('ALEXA request request={}'.format(request.json['request']))
        if 'intent' in request.json['request']:
            intent = request.json['request']['intent']
            if intent is not None:
                cmd = None
                zone = None
                if intent['name'] == 'AMAZON.PauseIntent':
                    cmd = 'pause'
                elif intent['name'] == 'AMAZON.ResumeIntent':
                    cmd = 'resume'
                elif intent['name'] == 'AMAZON.NextIntent':
                    cmd = 'next'
                elif intent['name'] == 'AMAZON.PreviousIntent':
                    cmd = 'previous'
                if 'slots' in intent.keys():
                    slots = intent['slots']
                    for name, value in slots.iteritems():
                        if name == 'Action':
                            if 'value' in value.keys():
                                cmd = value['value']
                        elif name == 'Zone':
                            if 'value' in value.keys():
                                zone = value['value']
                port_config = get_param(Constant.P_MPD_PORT_ZONE).split(',')
                alt_port = None
                client = MPDClient()
                client.timeout = 5
                if zone is None:
                    # get the zone playing, only if one is active
                    port_list_play = []
                    alt_zone = None
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
                if cmd is not None and zone is not None:
                    L.l.info('ALEXA executes {} in {}'.format(cmd, zone))
                    port = None
                    for pair in port_config:
                        if zone in pair:
                            port = int(pair.split('=')[1])
                            break
                    if port is None:
                        port = alt_port
                    if port is not None:
                        client.connect(get_param(Constant.P_MPD_SERVER), port)
                        status = client.status()
                        outcome = 'not available'
                        if cmd == 'next':
                            client.next()
                            outcome = client.currentsong()['title']
                        elif cmd == 'previous':
                            client.previous()
                            outcome = client.currentsong()['title']
                        elif cmd == 'pause' or cmd == 'stop':
                            client.pause(1)
                            outcome = client.status()['state']
                        elif cmd == 'resume' or cmd == 'play':
                            client.pause(0)
                            outcome = client.status()['state']
                        elif cmd == 'volumeup' or cmd == 'louder':
                            client.setvol(int(status['volume']) + 5)
                            outcome = client.status()['volume']
                        elif cmd == 'volumedown' or cmd == 'quiet':
                            client.setvol(int(status['volume']) - 5)
                            outcome = client.status()['volume']
                        client.close()
                        client.disconnect()
                        response = 'Action done, {} in zone {}, result is {}'.format(cmd, zone, outcome)
                    else:
                        response = 'Could not connect to MPD server, port not found'
                else:
                    response = 'Warning, action not done, was {} in zone {}'.format(cmd, zone)
            else:
                response = 'Warning, incomplete action'
        else:
            response = 'Warning, intent not found'
    else:
        response = 'Invalid command'
    return '{ "version": "1.0", "sessionAttributes": {}, ' \
           '"response": { "outputSpeech": {"type": "PlainText", "text": " ' + response + ' "}, ' \
           '"shouldEndSession": true }}'
