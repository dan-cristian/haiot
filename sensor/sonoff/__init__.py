import threading
import prctl
from pydispatch import dispatcher
import transport.mqtt_io
from common import Constant, utils, get_json_param
from main.logger_helper import L
from main import sqlitedb
if sqlitedb:
    from main.admin import models
from main import thread_pool
from transport import mqtt_io
from storage.model import m


class P:
    initialised = False
    sonoff_topic = None
    check_period = 5

    def __init__(self):
        pass


def _get_zone_sensor(sensor_address, sensor_type):
    if sqlitedb:
        zone_sensor = models.ZoneSensor.query.filter_by(sensor_address=sensor_address).first()
    else:
        zone_sensor = m.ZoneSensor.find_one({m.ZoneSensor.sensor_address: sensor_address})
    if zone_sensor is None:
        actual_sensor_name = 'N/A {} {}'.format(sensor_address, sensor_type)
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


# '{"Time":"2018-10-14T21:57:33","ENERGY":{"Total":0.006,"Yesterday":0.000,"Today":0.006,"Power":5,"Factor":0.10,"Voltage":214,"Current":0.241}}'
# 'iot/sonoff/tele/sonoff-pow-2/SENSOR'
# {"Time":"2018-11-01T23:42:54","ENERGY":{"TotalStartTime":"2018-10-31T20:05:27","Total":0.000,"Yesterday":0.000,"Today":0.000,"Period":0,
# "Power":0,"ApparentPower":0,"ReactivePower":0,"Factor":0.00,"Voltage":220,"Current":0.000}}
#
# Tasmota MQTT - put iot/sonoff/%prefix%/%topic%/ in MQTT settings
def _process_message(msg):
    # L.l.info("Topic={} payload={}".format(msg.topic, msg.payload))
    if '/SENSOR' in msg.topic or '/RESULT' in msg.topic:
        topic_clean = P.sonoff_topic.replace('#', '')
        if topic_clean in msg.topic:
            sensor_name = msg.topic.split(topic_clean)[1].split('/')[1]
            obj = utils.json2obj(transport.mqtt_io.payload2json(msg.payload))
            if 'ENERGY' in obj:
                energy = obj['ENERGY']
                power = float(energy['Power'])
                if 'Voltage' in energy:
                    voltage = int(energy['Voltage'])
                else:
                    voltage = None
                if 'Factor' in energy:
                    factor = energy['Factor']
                else:
                    factor = None
                if 'Current' in energy:
                    current = float(energy['Current'])
                else:
                    current = None
                # unit should match Utility unit name in models definition
                dispatcher.send(Constant.SIGNAL_UTILITY_EX, sensor_name=sensor_name, value=power, unit='watt')
                # todo: save total energy utility
                if voltage or factor or current:
                    zone_sensor = m.ZoneSensor.find_one({m.ZoneSensor.sensor_address: sensor_name})
                    if zone_sensor is not None:
                        record = m.Sensor.find_one({m.Sensor.address: sensor_name})
                        if record is None:
                            record = m.Sensor()
                            record.address = sensor_name
                            record.sensor_name = zone_sensor.sensor_name
                        record.vad = None
                        record.iad = None
                        record.vdd = None
                        if voltage is not None:
                            record.vad = round(voltage, 0)
                        if current is not None:
                            record.iad = round(current, 1)
                        if factor is not None:
                            record.vdd = round(factor, 1)
                        if voltage is not None or current is not None or factor is not None:
                            record.save_changed_fields(broadcast=True, persist=True)
                # dispatcher.send(Constant.SIGNAL_UTILITY_EX, sensor_name=sensor_name, value=current, unit='kWh')
            if 'POWER' in obj:
                power_is_on = obj['POWER'] == 'ON'
                # relay = m.ZoneCustomRelay.find_one({m.ZoneCustomRelay.gpio_pin_code: sensor_name,
                #                                    m.ZoneCustomRelay.gpio_host_name: Constant.HOST_NAME})
                relay = m.ZoneCustomRelay.find_one({m.ZoneCustomRelay.gpio_pin_code: sensor_name})
                if relay is not None:
                    L.l.info("Got relay {} state={}".format(sensor_name, power_is_on))
                    relay.relay_is_on = power_is_on
                    relay.save_changed_fields(broadcast=True, persist=True)
                else:
                    L.l.warning("ZoneCustomRelay {} not defined in db".format(sensor_name))
            if 'COUNTER' in obj:
                # TelePeriod 60
                counter = obj['COUNTER']
                for i in [1, 2, 3, 4]:
                    c = 'C{}'.format(i)
                    if c in counter:
                        cval = int(counter[c])
                        dispatcher.send(Constant.SIGNAL_UTILITY_EX, sensor_name=sensor_name, value=cval, index=i)
            if 'BMP280' in obj:
                # iot/sonoff/tele/sonoff-basic-3/SENSOR =
                # {"Time":"2018-10-28T08:12:26","BMP280":{"Temperature":24.6,"Pressure":971.0},"TempUnit":"C"}
                bmp = obj['BMP280']
                temp = bmp['Temperature']
                press = bmp['Pressure']
                sensor_address = '{}_{}'.format(sensor_name, 'bmp280')
                zone_sensor, sensor = _get_sensor(sensor_address=sensor_address, sensor_type='BMP280')
                sensor.temperature = temp
                sensor.pressure = press
                sensor.save_changed_fields(broadcast=True, persist=True)
            if 'BME280' in obj:
                # "BME280":{"Temperature":24.1,"Humidity":39.2,"Pressure":980.0},"PressureUnit":"hPa","TempUnit":"C"}
                bmp = obj['BME280']
                sensor_address = '{}_{}'.format(sensor_name, 'bme280')
                zone_sensor, sensor = _get_sensor(sensor_address=sensor_address, sensor_type='BME280')
                sensor.temperature = bmp['Temperature']
                sensor.pressure = bmp['Pressure']
                if 0 < bmp['Humidity'] < 100:
                    sensor.humidity = bmp['Humidity']
                sensor.save_changed_fields(broadcast=True, persist=True)
            if 'INA219' in obj:
                ina = obj['INA219']
                voltage = ina['Voltage']
                current = ina['Current']
                power = ina['Power']
                sensor = m.PowerMonitor.find_one({m.PowerMonitor.host_name: sensor_name})
                if sensor is None:
                    L.l.warning('Sensor INA on {} not defined in db'.format(sensor_name))
                    sensor = m.PowerMonitor()
                    sensor.id = sensor.id
                sensor.voltage = voltage
                sensor.save_changed_fields(broadcast=True, persist=True)
            if 'ANALOG' in obj:
                # "ANALOG":{"A0":7}
                an = obj['ANALOG']
                a0 = an['A0']
                sensor_address = '{}_{}'.format(sensor_name, 'a0')
                zone_sensor, sensor = _get_sensor(sensor_address=sensor_address, sensor_type='ANALOG')
                sensor.vad = a0
                sensor.save_changed_fields(broadcast=True, persist=True)
            if 'PMS5003' in obj:
                # "PMS5003":{"CF1":0,"CF2.5":1,"CF10":3,"PM1":0,"PM2.5":1,"PM10":3,"PB0.3":444,"PB0.5":120,"PB1":12,
                # "PB2.5":6,"PB5":2,"PB10":2}
                pms = obj['PMS5003']
                sensor_address = '{}_{}'.format(sensor_name, 'PMS5003')
                zone_sensor, sensor = _get_dust_sensor(sensor_address=sensor_address, sensor_type='PMS5003')
                sensor.pm_1 = pms['PM1']
                sensor.pm_2_5 = pms['PM2.5']
                sensor.pm_10 = pms['PM10']

                sensor.p_0_3 = pms['PB0.3']
                sensor.p_0_5 = pms['PB0.5']
                sensor.p_1 = pms['PB1']

                sensor.p_2_5 = pms['PB2.5']
                sensor.p_5 = pms['PB5']
                sensor.p_10 = pms['PB10']
                # sometimes first read after power on returns invalid 0 values
                if sensor.pm_1 + sensor.pm_2_5 +  sensor.pm_10 + sensor.p_0_3+ sensor.p_0_5 + sensor.p_1 \
                        + sensor.p_2_5 + sensor.p_5 + sensor.p_10 != 0:
                    sensor.save_changed_fields(broadcast=True, persist=True)
        else:
            L.l.warning("Invalid sensor topic {}".format(msg.topic))


def mqtt_on_message(client, userdata, msg):
    try:
        prctl.set_name("mqtt_sonoff")
        threading.current_thread().name = "mqtt_sonoff"
        _process_message(msg)
    except Exception as ex:
        L.l.error("Error processing sonoff mqtt {}, err={}, msg={}".format(msg.topic, ex, msg), exc_info=True)
    finally:
        prctl.set_name("idle")
        threading.current_thread().name = "idle"


# iot/sonoff/stat/sonoff-basic-5/POWER = ON/OFF
def set_relay_state(relay_name, relay_is_on):
    if not P.initialised:
        return None
    if relay_is_on:
        payload = 'ON'
    else:
        payload = 'OFF'
    topic = P.sonoff_topic.replace('#', '')
    L.l.info('Set sonoff relay {} to {}'.format(relay_name, relay_is_on))
    transport.send_message_topic(payload, topic + 'cmnd/' + relay_name + '/POWER')
    return relay_is_on


def _get_relay_status(relay_name):
    topic = P.sonoff_topic.replace('#', '')
    transport.send_message_topic('', topic + 'cmnd/' + relay_name + '/Power1')


def post_init():
    if P.initialised:
        # force sonoff sensors to send their status
        relays = m.ZoneCustomRelay.find({m.ZoneCustomRelay.relay_type: Constant.GPIO_PIN_TYPE_SONOFF})
        # m.ZoneCustomRelay.gpio_host_name: Constant.HOST_NAME,
        for relay in relays:
            L.l.info('Reading sonoff sensor {}'.format(relay.gpio_pin_code))
            _get_relay_status(relay.gpio_pin_code)


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
    P.sonoff_topic = str(get_json_param(Constant.P_MQTT_TOPIC_SONOFF_1))
    mqtt_io.P.mqtt_client.message_callback_add(P.sonoff_topic, mqtt_on_message)
    thread_pool.add_interval_callable(thread_run, P.check_period)
    P.initialised = True
