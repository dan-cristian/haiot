import datetime
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
    total_energy_day_update = {}  # sensor list with day dates when last energy update is recorded
    total_energy_returned_day_update = {}

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
# http://192.168.0.31/settings?mqtt_update_period=2
def _process_message(msg):
    # L.l.info("Topic={} payload={}".format(msg.topic, msg.payload))
    atoms = msg.topic.split('/')
    if "adc" in msg.topic:
        if len(atoms) > 2:
            if atoms[2] == "adc":
                sensor = m.PowerMonitor.find_one({m.PowerMonitor.host_name: atoms[1],
                                                  m.PowerMonitor.type: "shelly",
                                                  m.PowerMonitor.sensor_index: int(atoms[3])})
                if sensor is not None:
                    sensor.voltage = float(msg.payload)
                    sensor.save_changed_fields(broadcast=False, persist=True)
                else:
                    L.l.warning("Shelly sensor {} not defined in PowerMonitor config, adc={}".format(
                        atoms[1], msg.payload))
    if "ext_temperature" in msg.topic:
        if len(atoms) > 2:
            if atoms[2] == "ext_temperature":
                airsensor = m.AirSensor.find_one({m.AirSensor.address: atoms[1]})
                if airsensor is not None:
                    airsensor.temperature = float(msg.payload)
                    airsensor.save_changed_fields(broadcast=False, persist=True)
                else:
                    L.l.warning("Shelly sensor {} not defined in AirSensor config, temp={}".format(
                        atoms[1], msg.payload))
    if "relay" in msg.topic:
        if len(msg.topic) > 2:
            if atoms[2] == "relay":
                relay = m.ZoneCustomRelay.find_one({m.ZoneCustomRelay.gpio_pin_code: atoms[1]})
                if relay is not None:
                    state_on = "{}".format(msg.payload) == "on"
                    relay.relay_is_on = state_on
                    relay.save_changed_fields(broadcast=False, persist=True)
                else:
                    #L.l.warning("Shelly sensor {} not defined in Relay config, state={}".format(
                    #    atoms[1], msg.payload))
                    pass
    if "emeter" in msg.topic:
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
                    elif atoms[4] == 'energy':
                        sensor.energy = float(val)
                    elif atoms[4] == "total":
                        sensor.total_energy = float(val)
                        if sensor.total_energy_day_start is None:
                            sensor.total_energy_day_start = sensor.total_energy
                        if sensor.name not in P.total_energy_day_update.keys():
                            P.total_energy_day_update[sensor.name] = datetime.datetime.now().day
                        sensor.total_energy_daily = sensor.total_energy - sensor.total_energy_day_start
                        if P.total_energy_day_update[sensor.name] != datetime.datetime.now().day:  #
                            sensor.total_energy_day_end = sensor.total_energy - sensor.total_energy_day_start
                            sensor.total_energy_day_start = sensor.total_energy
                            P.total_energy_day_update[sensor.name] = datetime.datetime.now().day  #
                        if sensor.total_energy_last is not None:
                            sensor.total_energy_now = max(0, sensor.total_energy - sensor.total_energy_last)
                        sensor.total_energy_last = sensor.total_energy
                    elif atoms[4] == "returned_energy":
                        sensor.energy_export = float(val)
                    elif atoms[4] == "total_returned":
                        sensor.total_energy_returned = float(val)
                        if sensor.total_energy_returned_day_start is None:
                            sensor.total_energy_returned_day_start = sensor.total_energy_returned
                        if sensor.name not in P.total_energy_returned_day_update.keys():
                            P.total_energy_returned_day_update[sensor.name] = datetime.datetime.now().day
                        sensor.total_energy_returned_daily = \
                            sensor.total_energy_returned - sensor.total_energy_returned_day_start
                        if P.total_energy_returned_day_update[sensor.name] != datetime.datetime.now().day:
                            sensor.total_energy_returned_day_end = sensor.total_energy_returned - \
                                                                   sensor.total_energy_returned_day_start
                            sensor.total_energy_returned_day_start = sensor.total_energy_returned
                            P.total_energy_returned_day_update[sensor.name] = datetime.datetime.now().day
                        if sensor.total_energy_returned_last is not None:
                            sensor.total_energy_returned_now = \
                                max(0, sensor.total_energy_returned - sensor.total_energy_returned_last)
                        sensor.total_energy_returned_last = sensor.total_energy_returned
                    elif atoms[4] == "reactive_power":
                        sensor.reactive_power = float(val)
                    else:
                        L.l.warning("Unprocessed shelly value {}".format(atoms[4]))
                    # L.l.info("Shelly {} {}={}".format(sensor.name, atoms[4], val))
                    sensor.save_changed_fields(broadcast=False, persist=True)
                else:
                    L.l.warning("No shelly sensor {} index={} in config file".format(atoms[1], atoms[3]))
            else:
                L.l.warning("Invalid sensor topic {}".format(msg.topic))
    # shelly 2PM Plus
    if "switch:" in msg.topic:
        if len(atoms) == 4:
            index = int(atoms[3].split("switch:")[1])
            sensor = m.PowerMonitor.find_one({m.PowerMonitor.host_name: atoms[1],
                                              m.PowerMonitor.type: "shelly",
                                              m.PowerMonitor.sensor_index: index})
            if sensor is not None:
                # b'{"id":0, "source":"init", "output":true, "apower":-474.1, "voltage":222.4,
                # "current":2.164, "pf":-0.97, "aenergy":{"total":495.858},"temperature":{"tC":62.9, "tF":145.2}}'
                payload = str(msg.payload)
                if sensor.reversed_direction:
                    sign = -1
                else:
                    sign = 1
                if "apower" in payload:
                    sensor.power = sign * float(payload.split('"apower":')[1].split(",")[0])
                if "current" in payload:
                    sensor.current = float(payload.split('"current":')[1].split(",")[0])
                if "voltage" in payload:
                    sensor.voltage = float(payload.split('"voltage":')[1].split(",")[0])
                if "aenergy" in payload:
                    prev_energy = sensor.total_energy_last
                    en_text = payload.split('aenergy":{"total":')[1].split(",")[0]
                    en_text = en_text.replace("{", "")
                    sensor.total_energy_last = float(en_text)
                    if prev_energy is None:
                        prev_energy = sensor.total_energy_last
                    # might be a  bug, negative value returned after power loss
                    sensor.total_energy_now = max(0, sensor.total_energy_last - prev_energy)
                sensor.save_changed_fields(persist=True)


def mqtt_on_message(client, userdata, msg):
    try:
        prctl.set_name("mqtt_shelly")
        threading.current_thread().name = "mqtt_shelly"
        _process_message(msg)
    except Exception as ex:
        L.l.error("Error processing shelly mqtt {}, err={}, msg={}".format(msg.topic, ex, msg), exc_info=True)
    finally:
        prctl.set_name("idle_mqtt_shelly")
        threading.current_thread().name = "idle_mqtt_shelly"


def set_relay_state(relay_name, relay_is_on, relay_index):
    # shellies/shellyuni-<deviceid>/relay/<i>/command accepts on, off or toggle
    if relay_is_on:
        payload = "on"
    else:
        payload = "off"
    topic = "{}/{}/relay/{}/command".format(P.shelly_topic, relay_name, relay_index)
    transport.send_message_topic(topic=topic, json=payload)
    L.l.info("Set shelly relay {}:{} to on={}".format(relay_name, relay_index, relay_is_on))
    return None


def _get_relay_status(relay_name, relay_index):
    # payload = "off"
    # topic = "{}/{}/relay/{}".format(P.shelly_topic, relay_name, relay_index)
    # transport.send_message_topic(payload, topic)
    pass

def post_init():
    if P.initialised:
        # force sonoff sensors to send their status
        relays = m.ZoneCustomRelay.find({m.ZoneCustomRelay.relay_type: Constant.GPIO_PIN_TYPE_SHELLY})
        # m.ZoneCustomRelay.gpio_host_name: Constant.HOST_NAME,
        for relay in relays:
            L.l.info('Reading shelly sensor {}'.format(relay.gpio_pin_code))
            if relay.relay_pin_name == "chargerfan_1":
                set_relay_state(relay.gpio_pin_code, True, relay.relay_index)
            else:
                set_relay_state(relay.gpio_pin_code, False, relay.relay_index)


def thread_run():
    prctl.set_name("shelly")
    threading.current_thread().name = "shelly"
    # not used
    prctl.set_name("idle_shelly")
    threading.current_thread().name = "idle_shelly"


def unload():
    # thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    L.l.info('Shelly module initialising')
    P.shelly_topic = str(get_json_param(Constant.P_MQTT_TOPIC_SHELLY))
    mqtt_io.add_message_callback(P.shelly_topic + "/#", mqtt_on_message)
    # thread_pool.add_interval_callable(thread_run, P.check_period)
    P.initialised = True
