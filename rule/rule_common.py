import subprocess
from webui.api import api_v1
from main.logger_helper import L
from main.admin import models, model_helper
from common import Constant
from pydispatch import dispatcher
from transport.mqtt_io import sender
# import mpd
from main.admin.model_helper import get_param


class P:
    openhab_topic = None


def update_custom_relay(relay_pin_name, power_is_on):
    msg = api_v1.generic_db_update(model_name="ZoneCustomRelay", filter_name="relay_pin_name",
                                   field_name="relay_is_on", filter_value=relay_pin_name, field_value=power_is_on)
    """carefull with API fields order to match app.route definition """
    # with app.test_client() as c:

    #    msg = c.get('/apiv1/db_update/model_name=ZoneCustomRelay&'
    #                'filter_name=relay_pin_name&field_name=relay_is_on&filter_value={}&field_value={}'.
    #                format(relay_pin_name, power_is_on)).data
    L.l.info(msg)


def update_command_override_relay(relay_pin_name, is_rule, is_gui):
    m = models.ZoneCustomRelay
    relay_row = m().query_filter_first(m.host_name.in_([Constant.HOST_NAME]), m.relay_pin_name.in_([relay_pin_name]))

    m = models.CommandOverrideRelay
    override_row = m().query_filter_first(m.host_name.in_([Constant.HOST_NAME]), m.relay_pin_name.in_([relay_pin_name]))


def play_bell_local(sound_file):
    # client = mpd.MPDClient(use_unicode=True)
    # client.connect(get_param(Constant.P_MPD_SERVER), 6600)
    #result = subprocess.check_output(['aplay', 'scripts/audio/{}'.format(sound_file)], stderr=subprocess.STDOUT)
    result = subprocess.check_output(['aplay', 'scripts/static/sounds/{}'.format(sound_file)], stderr=subprocess.STDOUT)
    L.l.info("Play bell returned: {}".format(result))


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
    P.openhab_topic = str(model_helper.get_param(Constant.P_MQTT_TOPIC_OPENHAB))


def send_mqtt_openhab(subtopic, payload):
    sender.send_message(payload, P.openhab_topic + "/" + subtopic)