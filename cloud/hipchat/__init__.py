#!/usr/bin/env python

import requests
import json
from main.logger_helper import L
from common import Constant
from main.admin import model_helper
from pydispatch import dispatcher

_token = None
_room = None
initialised = False


def hipchat_notify(message, color='yellow', notify=False, format='html', host='api.hipchat.com'):
    """Send notification to a HipChat room via API version 2

    Parameters
    ----------
    token : str
        HipChat API version 2 compatible token (room or user token)
    room: str
        Name or API ID of the room to notify
    message: str
        Message to send to room
    color: str, optional
        Background color for message, defaults to yellow
        Valid values: yellow, green, red, purple, gray, random
    notify: bool, optional
        Whether message should trigger a user notification, defaults to False
    format: str, optional
        Format of message, defaults to text
        Valid values: text, html
    host: str, optional
        Host to connect to, defaults to api.hipchat.com
    """
    global _token, _room
    message += ' [%s]' % Constant.HOST_NAME
    if len(message) > 10000:
        raise ValueError('Message too long')
    if format not in ['text', 'html']:
        raise ValueError("Invalid message format '{0}'".format(format))
    if color not in ['yellow', 'green', 'red', 'purple', 'gray', 'random']:
        raise ValueError("Invalid color {0}".format(color))
    if not isinstance(notify, bool):
        raise TypeError("Notify must be boolean")

    url = "https://{0}/v2/room/{1}/notification".format(host, _room)
    headers = {'Content-type': 'application/json'}
    headers['Authorization'] = "Bearer " + _token
    payload = {
        'message': message,
        'notify': notify,
        'message_format': format,
        'color': color
    }
    r = requests.post(url, data=json.dumps(payload), headers=headers)
    r.raise_for_status()


def unload():
    L.l.info('Hipchat module unloading')
    #dispatcher.disconnect(dispatcher.connect(hipchat_notify, signal=Constant.SIGNAL_PUSH_NOTIFICATION,
    #                                         sender=dispatcher.Any))
    global initialised
    initialised = False


def init():
    L.l.debug('Hipchat module initialising')
    dispatcher.connect(hipchat_notify, signal=Constant.SIGNAL_CHAT_NOTIFICATION, sender=dispatcher.Any)
    global _token, _room
    _token = model_helper.get_param(Constant.P_HIPCHAT_TOKEN)
    _room = model_helper.get_param(Constant.P_HIPCHAT_ROOM_API_ID)
    try:
        pass
        # hipchat_notify(message='Module initialising', notify=True, color='red')
        # send_message(title="Initialised", message="Module initialised")
        # send_message(title="Initialised 2", message="Module initialised 2")
    except Exception, ex:
        L.l.error("Unable tp init hipchat %s" % ex)
    # thread_pool.add_interval_callable(_send_queue, run_interval_second=60)
    global initialised
    initialised = True
