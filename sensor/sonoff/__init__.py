import sys
import os
import glob
import errno
import threading
from socket import timeout
from ipaddress import IPv4Address
from urllib.error import HTTPError, URLError
import prctl
from pydispatch import dispatcher
import transport.mqtt_io
from common import Constant, utils, get_json_param
from main.logger_helper import L
from main import thread_pool
from transport import mqtt_io
from storage.model import m
import python_arptable


class P:
    initialised = False
    sonoff_topic = None
    check_period = 60 * 60  # every hour
    mac_list = {}  # key=mac, value=file_name
    TASMOTA_PATH = "../private_config/tasmota/device_config/"
    TASMOTA_CONFIG = TASMOTA_PATH + "tasmota.config"

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
                if 'Today' in energy:
                    today_energy = energy['Today']
                else:
                    today_energy = None
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
                for i in [1, 2, 3, 4, 5, 6, 7, 8]:
                    c = 'C{}'.format(i)
                    if c in counter:
                        cval = int(counter[c])
                        dispatcher.send(Constant.SIGNAL_UTILITY_EX, sensor_name=sensor_name, value=cval, index=i)

            # iot/sonoff/tele/sonoff-basic-3/SENSOR =
            # {"Time":"2018-10-28T08:12:26","BMP280":{"Temperature":24.6,"Pressure":971.0},"TempUnit":"C"}
            # "BME280":{"Temperature":24.1,"Humidity":39.2,"Pressure":980.0},"PressureUnit":"hPa","TempUnit":"C"}
            # {"BME680":{"Temperature":29.0,"Humidity":63.3,"Pressure":981.6,"Gas":24.46},"PressureUnit":"hPa","TempUnit":"C"}
            # "MHZ19B":{"Model":"B","CarbonDioxide":473,"Temperature":26.0},"TempUnit":"C"
            for k, v in obj.items():
                if k.startswith('BME') or k.startswith('BMP') or k.startswith('MHZ19') or k.startswith('DS18B20'):
                    sensor_address = '{}_{}'.format(sensor_name, k.lower())
                    zone_sensor, sensor = _get_air_sensor(sensor_address=sensor_address, sensor_type=k)
                    if 'Temperature' in v:
                        sensor.temperature = v['Temperature']
                    if 'Pressure' in v:
                        sensor.pressure = v['Pressure']
                    if 'Humidity' in v:
                        if 0 < v['Humidity'] < 100:
                            sensor.humidity = v['Humidity']
                    if 'Gas' in v:
                        sensor.gas = v['Gas']
                    if 'CarbonDioxide' in v:
                        sensor.co2 = v['CarbonDioxide']
                    sensor.save_changed_fields(broadcast=True, persist=True)

                if k.startswith('INA219'):
                    ina = v  # obj['INA219']
                    # multiple ina sensors
                    if '-' in k:
                        index = k.split('-')[1]
                        sensor = m.PowerMonitor.find_one(
                            {m.PowerMonitor.host_name: sensor_name, m.PowerMonitor.type: "ina{}".format(index)})
                    else:
                        sensor = m.PowerMonitor.find_one({m.PowerMonitor.host_name: sensor_name})
                    if sensor is None:
                        L.l.warning('Sensor INA on {} not defined in db'.format(sensor_name))
                        sensor = m.PowerMonitor()
                        sensor.id = sensor.id
                    if 'Voltage' in ina:
                        voltage = ina['Voltage']
                        sensor.voltage = voltage
                    if 'Current' in ina:
                        current = ina['Current']
                        sensor.current = current
                    if 'Power' in ina:
                        power = ina['Power']
                        sensor.power = power
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
                sensor_address = '{}_{}'.format(sensor_name, 'pms5003')
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
                if sensor.pm_1 + sensor.pm_2_5 + sensor.pm_10 + sensor.p_0_3 + sensor.p_0_5 + sensor.p_1 \
                        + sensor.p_2_5 + sensor.p_5 + sensor.p_10 != 0:
                    sensor.save_changed_fields(broadcast=True, persist=True)
            if 'RfReceived' in obj:
                rf = obj['RfReceived']
                sensor_id = rf['Data']
                alarm = m.ZoneAlarm.find_one({m.ZoneAlarm.gpio_pin_code: sensor_id})
                if alarm is not None:
                    dispatcher.send(Constant.SIGNAL_GPIO, gpio_pin_code=sensor_id, pin_connected=True)
                    dispatcher.send(Constant.SIGNAL_GPIO, gpio_pin_code=sensor_id, pin_connected=False)
                else:
                    L.l.warning('Unknown Sonoff RF packet received {}'.format(sensor_id))
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


'''Read all mac addresses from config files'''
def _read_mac_files():
    path = P.TASMOTA_PATH + "*"
    files = glob.glob(path)
    for name in files:  # 'file' is a builtin type, 'name' is a less-ambiguous variable name.
        try:
            with open(name) as f:  # No need to specify 'r': this is the default.
                first_line = f.readline().lower()
                if first_line.startswith('#mac address='):
                    mac = first_line.split("=")[1].rstrip('\n')
                    P.mac_list[mac] = name
        except IOError as exc:
            if exc.errno != errno.EISDIR:  # Do not fail if a directory is found, just ignore it.
                raise  # Propagate other kinds of IOError.


def _tasmota_config(config_file, device_name, ip):
    tasmota_url = "http://{}/cm?cmnd={}"
    # init common parameters

    # init specific device parameters
    with open(config_file) as f:
        for line in f:
            line = line.rstrip("\n").rstrip("\r")
            if not line.lower().startswith('#') and line.strip():
                command = line.split(maxsplit=1)[0].lower()
                if "<name>" in line:
                    line = line.replace("<name>", device_name)
                if "<day>" in line:
                    line = line.replace("<day>", str(utils.get_base_location_now_date().day))
                line = utils.encode_url_request(line)
                request = tasmota_url.format(ip, line)
                done = False
                for i in range(0, 5):
                    try:
                        response = utils.get_url_content(url=request, timeout=10)
                        if command in response.lower():
                            L.l.info("Set {}: {}={}".format(device_name, request, response))
                            break
                        elif '{"WARNING":"Enable weblog 2 if response expected"}' in response:
                            L.l.info("Set {}: {}={}".format(device_name, request, response))
                            break
                        else:
                            L.l.warning("Error setting tasmota param {}".format(response))
                    except IOError as eio:
                        L.l.error("Tasmota config IO error {}".format(eio))
                    except (URLError, HTTPError, timeout) as et:
                        L.l.error("Tasmota timeout error {}".format(et))
                    except Exception as ex:
                        L.l.error("Tasmota config exception {}".format(ex))


'''Look for tasmota devices in the network not initialised and init them'''
def _tasmota_discovery():
    # try to connect assuming is a tasmota device
    L.l.info("Begin tasmota network scan")
    net_hosts = utils.get_my_network_ip_list()
    for ip in net_hosts:
        try:
            if ip >= IPv4Address("192.168.0.145"):
                dev_name = utils.parse_http(url="http://{}/cm?cmnd=friendlyname1".format(ip),
                                            start_key='{"FriendlyName1":"', end_key='"}', timeout=3)
                if dev_name is not None:
                    arp = python_arptable.get_arp_table()
                    for entry in arp:
                        if IPv4Address(entry["IP address"]) == ip:
                            mac = entry["HW address"]
                            if mac in P.mac_list:
                                config_file = P.mac_list[mac]
                                file_name = os.path.basename(config_file)
                                # dev_name = utils.parse_http(url="http://{}/cm?cmnd=friendlyname1".format(ip),
                                #                            start_key='{"FriendlyName1":"', end_key='"}')
                                last_update = utils.parse_http(url="http://{}/cm?cmnd=friendlyname2".format(ip),
                                                                start_key='{"FriendlyName2":"', end_key='"}', timeout=3)
                                if dev_name != file_name or last_update != str(utils.get_base_location_now_date().day):
                                    # tasmota device is not configured
                                    L.l.info("Configuring tasmota device {} as {}".format(ip, file_name))
                                    _tasmota_config(config_file=P.TASMOTA_CONFIG, device_name=file_name, ip=ip)
                                    _tasmota_config(config_file=config_file, device_name=file_name, ip=ip)
                            break
                else:
                    L.l.info("Tasmota scan: IP {} not responding".format(ip))
        except Exception as ex:
            L.l.info("Tasmota scan: IP {} failed".format(ip))
            pass

    L.l.info("Finalised tasmota network scan")


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
    #_tasmota_discovery()
    prctl.set_name("idle")
    threading.current_thread().name = "idle"


def unload():
    thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    L.l.info('Sonoff module initialising')
    P.sonoff_topic = str(get_json_param(Constant.P_MQTT_TOPIC_SONOFF_1))
    # mqtt_io.P.mqtt_client.message_callback_add(P.sonoff_topic, mqtt_on_message)
    mqtt_io.add_message_callback(P.sonoff_topic, mqtt_on_message)
    _read_mac_files()
    thread_pool.add_interval_callable(thread_run, P.check_period)
    P.initialised = True
