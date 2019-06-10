from main.logger_helper import L
import json
from urllib.request import urlopen, Request
import ssl
import os
from main import thread_pool
from pydispatch import dispatcher
from common import Constant, get_json_param
from transport import mqtt_io
import time
from storage.model import m


class P:
    initialised = False
    mqtt_topic_receive = None
    mqtt_topic_receive_prefix = None
    phonetrack_url = None
    phonetrack_token = None
    mqtt_list = []

    def __init__(self):
        pass


# {'_type': 'location', 'acc': 50, 'alt': 416, 'batt': 43, 'conn': 'w', 'inregions': ['home'],
# 'lat': 46.7519617, 'lon': 23.6198686, 't': 'u', 'tid': 'dc', 'tst': 1560181924, 'vac': 2, 'vel': 0}
def mqtt_on_message(client, userdata, msg):
    try:
        device = msg.topic.split(P.mqtt_topic_receive_prefix)[1]
        payload = msg.payload.decode('utf-8').lower()
        L.l.info('Got owncloud mqtt {}={}'.format(msg.topic, payload))
        json_obj = json.loads(payload)
        if json_obj['_type'] == 'location':
            if 'inregions' in json_obj:
                for reg in json_obj['inregions']:
                    pass
            tst = time.time()
            sensor = m.DustSensor.find_one({m.DustSensor.address: device + '_PMS5003'})
            if sensor is not None:
                pm2_5 = sensor.pm_2_5
            else:
                pm2_5 = 0
            sensor = m.Sensor.find_one({m.Sensor.address: device + '_a0'})
            if sensor is not None:
                a0 = sensor.vad
            else:
                a0 = 0
            rec = {'<name>': json_obj['tid'], '<lat>': json_obj['lat'], '<lon>': json_obj['lon'],
                   '<alt>': json_obj['alt'], '<speed>': json_obj['vel'], '<acc>': json_obj['acc'],
                   '<sat>': pm2_5, '<bearing>': a0, '<bat>': json_obj['batt'],
                   '<time>': tst}  # '<time>': json_obj['tst']}
            P.mqtt_list.append(rec)
    except Exception as ex:
        L.l.error('Error owntracks mqtt {} ex={}'.format(msg.payload, ex), exc_info=True)


def thread_run():
    if (not os.environ.get('PYTHONHTTPSVERIFY', '') and
            getattr(ssl, '_create_unverified_context', None)):
        ssl._create_default_https_context = ssl._create_unverified_context
    for mqtt in list(P.mqtt_list):
        url = P.phonetrack_url
        for key in mqtt:
            val = str(mqtt[key])
            url = url.replace(key, val)
        try:
            text = str(urlopen(url).read())
            P.mqtt_list.remove(mqtt)
        except Exception as ex:
            L.l.warning('Unable to post location to phonetrack, err={}, url={}'.format(ex, url))
    ssl._create_default_https_context = ssl.create_default_context


def unload():
    L.l.info('Owntracks module unloading')
    thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    L.l.info('Owntracks module initialising')
    config_file = get_json_param(Constant.P_ALL_CREDENTIAL_FILE)
    with open(config_file, 'r') as f:
        config = json.load(f)
        P.phonetrack_token = config['nextcloud_phonetrack_token']
    P.phonetrack_url = get_json_param(Constant.P_NEXTCLOUD_PHONETRACK_URL).replace('<token>', P.phonetrack_token)
    P.mqtt_topic_receive = get_json_param(Constant.P_MQTT_TOPIC_OWNTRACKS_RECEIVE)
    P.mqtt_topic_receive_prefix = P.mqtt_topic_receive.replace('#', '')
    mqtt_io.P.mqtt_client.message_callback_add(P.mqtt_topic_receive, mqtt_on_message)
    mqtt_io.add_message_callback(P.mqtt_topic_receive, mqtt_on_message)
    thread_pool.add_interval_callable(thread_run, run_interval_second=10)
    P.initialised = True
