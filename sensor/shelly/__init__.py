import threading
import prctl
from pydispatch import dispatcher
import transport.mqtt_io
from common import Constant, utils, get_json_param
from main.logger_helper import L
from main import thread_pool
from transport import mqtt_io
from storage.model import m


class P:
    initialised = False
    shelly_topic = None
    check_period = 60 * 60  # every hour

    def __init__(self):
        pass


def _get_zone_sensor(sensor_address, sensor_type):
    zone_sensor = m.ZoneSensor.find_one({m.ZoneSensor.sensor_address: sensor_address})
    if zone_sensor is None:
        # use tasmota sensor name if not define in config
        actual_sensor_name = '{}'.format(sensor_address)
    else:
        actual_sensor_name = zone_sensor.sensor_name
    return zone_sensor, actual_sensor_name


def _get_sensor(sensor_address, sensor_type):
    zone_sensor, actual_sensor_name = _get_zone_sensor(sensor_address, sensor_type)
    sensor = m.Sensor.find_one({m.Sensor.address: sensor_address})
    if sensor is None:
        sensor = m.Sensor()
        sensor.address = sensor_address
        sensor.sensor_name = actual_sensor_name
    return zone_sensor, sensor


def _get_dust_sensor(sensor_address, sensor_type):
    zone_sensor, actual_sensor_name = _get_zone_sensor(sensor_address, sensor_type)
    sensor = m.DustSensor.find_one({m.DustSensor.address: sensor_address})
    if sensor is None:
        sensor = m.DustSensor()
        sensor.address = sensor_address
    return zone_sensor, sensor


def _get_air_sensor(sensor_address, sensor_type):
    zone_sensor, actual_sensor_name = _get_zone_sensor(sensor_address, sensor_type)
    sensor = m.AirSensor.find_one({m.AirSensor.address: sensor_address})
    if sensor is None:
        sensor = m.AirSensor()
        sensor.address = sensor_address
    return zone_sensor, sensor


# 'shellies/shellyem3-ECFABCC7F0F4/emeter/0/power'
# 'shellies/shellyem3-ECFABCC7F0F4/emeter/0/pf'
# 'shellies/shellyem3-ECFABCC7F0F4/emeter/0/current'
# 'shellies/shellyem3-ECFABCC7F0F4/emeter/0/voltage'
# 'shellies/shellyem3-ECFABCC7F0F4/emeter/0/total'

# Tasmota MQTT - put iot/sonoff/%prefix%/%topic%/ in MQTT settings
def _process_message(msg):
    # L.l.info("Topic={} payload={}".format(msg.topic, msg.payload))
    atoms = msg.topic.split('/')
    if len(atoms) == 5:
        if atoms[2] == "emeter":
            val = "{}".format(msg.payload).replace("b", "").replace("\\", "").replace("'", "")
            sensor = m.PowerMonitor.find_one({m.PowerMonitor.host_name: atoms[1],
                                              m.PowerMonitor.type: "shelly",
                                              m.PowerMonitor.sensor_index: int(atoms[3])})
            if sensor is not None:
                if atoms[4] == "power":
                    sensor.power = float(val)
                elif atoms[4] == "voltage":
                    sensor.voltage = float(val)
                elif atoms[4] == "pf":
                    sensor.power_factor = float(val)
                elif atoms[4] == 'current':
                    sensor.current = float(val)
                elif atoms[4] == "total":
                    sensor.total_energy = float(val)
                elif atoms[4] == "total_returned":
                    sensor.total_energy_export = float(val)
                else:
                    L.l.warning("Unprocessed shelly value {}".format(atoms[4]))
                sensor.save_changed_fields(broadcast=True, persist=True)
            else:
                L.l.warning("No shelly sensor {} in config file".format(atoms[1]))
        else:
            L.l.warning("Invalid sensor topic {}".format(msg.topic))


def mqtt_on_message(client, userdata, msg):
    try:
        prctl.set_name("mqtt_shelly")
        threading.current_thread().name = "mqtt_shelly"
        _process_message(msg)
    except Exception as ex:
        L.l.error("Error processing shelly mqtt {}, err={}, msg={}".format(msg.topic, ex, msg), exc_info=True)
    finally:
        prctl.set_name("idle")
        threading.current_thread().name = "idle"


def set_relay_state(relay_name, relay_is_on):
    return None


def _get_relay_status(relay_name):
    # topic = P.shelly_topic.replace('#', '')
    # transport.send_message_topic('', topic + 'cmnd/' + relay_name + '/Power1')
    pass


def post_init():
    pass


def thread_run():
    prctl.set_name("shelly")
    threading.current_thread().name = "shelly"
    prctl.set_name("idle")
    threading.current_thread().name = "idle"


def unload():
    thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    L.l.info('Shelly module initialising')
    P.shelly_topic = str(get_json_param(Constant.P_MQTT_TOPIC_SHELLY)) + "/#"
    mqtt_io.add_message_callback(P.shelly_topic, mqtt_on_message)
    thread_pool.add_interval_callable(thread_run, P.check_period)
    P.initialised = True
