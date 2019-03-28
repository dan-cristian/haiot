import subprocess
#from webui.api import api_v1
from main.logger_helper import L
from main.admin import models, model_helper
from common import Constant
from pydispatch import dispatcher
# import mpd
from main.admin.model_helper import get_param


def update_custom_relay(relay_pin_name, power_is_on):
    current_relay = models.ZoneCustomRelay.query.filter_by(relay_pin_name=relay_pin_name).first()
    if current_relay is not None:
        L.l.info("Update relay {} on rule common to {}".format(relay_pin_name, power_is_on))
        current_relay.relay_is_on = power_is_on
        current_relay.commit_record_to_db_notify()
    else:
        L.l.info("Cannot find relay {} on rule common update relay".format(relay_pin_name))


def get_custom_relay(relay_pin_name):
    current_relay = models.ZoneCustomRelay.query.filter_by(relay_pin_name=relay_pin_name).first()
    if current_relay is not None:
        state = current_relay.relay_is_on
    else:
        L.l.info("Cannot find relay {} on rule common get custom relay".format(relay_pin_name))
        state = None
    return state


def update_command_override_relay(relay_pin_name, is_rule, is_gui):
    m = models.ZoneCustomRelay
    relay_row = m().query_filter_first(m.host_name.in_([Constant.HOST_NAME]), m.relay_pin_name.in_([relay_pin_name]))

    m = models.CommandOverrideRelay
    override_row = m().query_filter_first(m.host_name.in_([Constant.HOST_NAME]), m.relay_pin_name.in_([relay_pin_name]))


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
