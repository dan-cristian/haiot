import threading
import prctl
from common import Constant
from main.logger_helper import L
from main import sqlitedb
from main import thread_pool
from storage.model import m


class P:
    initialised = False
    interval = 60
    has_bmp280 = False
    obj_bmp280 = None

    def __init__(self):
        pass


try:
    from smbus2 import SMBus
    from bmp280 import BMP280
except ImportError:
    pass


def _read_bmp280():
    temperature = P.obj_bmp280.get_temperature()
    pressure = P.obj_bmp280.get_pressure()
    sensor_address = Constant.HOST_NAME + '_bmp280'
    zone_sensor = m.ZoneSensor.find_one({m.ZoneSensor.sensor_address: sensor_address})
    if zone_sensor is not None:
        sensor_name = zone_sensor.sensor_name
        record = m.Sensor.find_one({m.Sensor.address: sensor_address})
        if record is None:
            record = m.Sensor()
            record.address = sensor_address
            record.sensor_name = sensor_name
            record.type = 'BMP280'
        record.temperature = round(temperature, 1)
        record.pressure = round(pressure, 1)
        record.save_changed_fields(broadcast=True, persist=True)
    else:
        L.l.info("Undefined {} sensor found temp={} and pressure={}".format(sensor_address, temperature, pressure))


def thread_run():
    prctl.set_name("i2c")
    threading.current_thread().name = "i2c"
    if P.has_bmp280:
        _read_bmp280()
    prctl.set_name("idle")
    threading.current_thread().name = "idle"


def _init_bmp280():
    try:
        bus = SMBus(1)
        P.obj_bmp280 = BMP280(i2c_dev=bus)
        temperature = P.obj_bmp280.get_temperature()
        pressure = P.obj_bmp280.get_pressure()
        L.l.info("Found BMP280 sensor, temp={} baro={}".format(temperature, pressure))
        P.has_bmp280 = True
    except Exception as ex:
        pass


def unload():
    thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    L.l.info('i2c sensors module initialising')
    _init_bmp280()
    thread_pool.add_interval_callable(thread_run, run_interval_second=P.interval)
