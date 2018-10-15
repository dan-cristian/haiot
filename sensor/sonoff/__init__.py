import threading
import prctl
from pydispatch import dispatcher
from common import Constant, utils
from main.logger_helper import L
from main.admin import model_helper, models
from main import thread_pool
from transport import mqtt_io


class P:
    initialised = False
    sonoff_topic = None
    check_period = 5

    def __init__(self):
        pass


# '{"Time":"2018-10-14T21:57:33","ENERGY":{"Total":0.006,"Yesterday":0.000,"Today":0.006,"Power":5,"Factor":0.10,"Voltage":214,"Current":0.241}}'
# 'iot/sonoff/tele/sonoff-pow-2/SENSOR'
# Tasmota MQTT - put /iot/sonoff prefix in MQTT settings
def mqtt_on_message(client, userdata, msg):
    # L.l.info("Topic={} payload={}".format(msg.topic, msg.payload))
    if '/SENSOR' in msg.topic or '/RESULT' in msg.topic:
        topic_clean = P.sonoff_topic.replace('#', '')
        if topic_clean in msg.topic:
            sensor_name = msg.topic.split(topic_clean)[1].split('/')[1]
            obj = utils.json2obj(msg.payload)
            if 'ENERGY' in obj:
                energy = obj['ENERGY']
                power = energy['Power']
                voltage = energy['Voltage']
                factor = energy['Factor']
                current = energy['Current']
                # unit should match Utility unit name in models definition
                dispatcher.send(Constant.SIGNAL_UTILITY_EX, sensor_name=sensor_name, value=power, unit='watt')
                dispatcher.send(Constant.SIGNAL_UTILITY_EX, sensor_name=sensor_name, value=current, unit='kWh')
            elif 'POWER' in obj:
                power_is_on = obj['POWER'] == 'ON'
                current_relay = models.ZoneCustomRelay.query.filter_by(gpio_pin_code=sensor_name,
                                                                       gpio_host_name=Constant.HOST_NAME).first()
                if current_relay is not None:
                    L.l.info("Got relay {} state={}".format(sensor_name, power_is_on))
                    new_relay = models.ZoneCustomRelay(gpio_pin_code=sensor_name, gpio_host_name=Constant.HOST_NAME)
                    new_relay.relay_is_on = power_is_on
                    models.ZoneCustomRelay().save_changed_fields(
                        current_record=current_relay, new_record=new_relay, notify_transport_enabled=True,
                        save_to_graph=True)
                else:
                    L.l.error("ZoneCustomRelay with code {} does not exist in database".format(sensor_name))
            else:
                L.l.warning("Energy payload missing from topic {}".format(msg.topic))
        else:
            L.l.warning("Invalid sensor topic {}".format(msg.topic))


def thread_run():
    prctl.set_name("sonoff")
    threading.current_thread().name = "sonoff"

    prctl.set_name("idle")
    threading.current_thread().name = "idle"


def unload():
    thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    L.l.info('Sonoff module initialising')
    P.sonoff_topic = str(model_helper.get_param(Constant.P_MQTT_TOPIC_SONOFF_1))
    mqtt_io.P.mqtt_client.message_callback_add(P.sonoff_topic, mqtt_on_message)
    thread_pool.add_interval_callable(thread_run, P.check_period)
