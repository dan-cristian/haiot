import subprocess
from main.logger_helper import L
from main import sqlitedb
if sqlitedb:
    from storage.sqalc import models
from common import Constant
from pydispatch import dispatcher
from storage.model import m


def update_custom_relay(relay_pin_name, power_is_on):
    current_relay = m.ZoneCustomRelay.find_one({m.ZoneCustomRelay.relay_pin_name: relay_pin_name})
    if current_relay is not None:
        L.l.info("Update relay {} on rule common to {}, current state={}".format(
            relay_pin_name, power_is_on, current_relay.relay_is_on))
        current_relay.relay_is_on = power_is_on
        current_relay.save_changed_fields(broadcast=True, persist=True)
    else:
        L.l.info("Cannot find relay {} on rule common update relay".format(relay_pin_name))


def get_custom_relay(relay_pin_name):
    current_relay = m.ZoneCustomRelay.find_one({m.ZoneCustomRelay.relay_pin_name: relay_pin_name})
    if current_relay is not None:
        state = current_relay.relay_is_on
    else:
        L.l.info("Cannot find relay {} on rule common get custom relay".format(relay_pin_name))
        state = None
    return state


def play_bell_local(sound_file):
    # client = mpd.MPDClient(use_unicode=True)
    # client.connect(get_param(Constant.P_MPD_SERVER), 6600)
    #result = subprocess.check_output(['aplay', 'scripts/audio/{}'.format(sound_file)], stderr=subprocess.STDOUT)
    try:
        result = subprocess.check_output(['aplay', 'scripts/static/sounds/{}'.format(sound_file)],
                                         stderr=subprocess.STDOUT)
        L.l.info("Play bell returned: {}".format(result))
    except Exception as ex:
        L.l.error('Unable to play local sound {}, er={}'.format(sound_file, ex))


def send_notification(title, message=None, url=None, priority=None, deviceid=None, image_url=None):
    dispatcher.send(Constant.SIGNAL_PUSH_NOTIFICATION, title=title, message=message, url=url, priority=priority,
                    deviceid=deviceid, image_url=image_url)


def send_chat(message=None, notify=False):
    dispatcher.send(Constant.SIGNAL_CHAT_NOTIFICATION, message=message, notify=notify)


def send_email(subject=None, body=None):
    dispatcher.send(Constant.SIGNAL_EMAIL_NOTIFICATION, subject=subject, body=body)


def notify_via_all(title=None, message=None, priority=None):
    send_notification(title=title, message=message, priority=priority)
    send_chat(message=message)
    send_email(subject=title, body=message)


def init():
    pass
