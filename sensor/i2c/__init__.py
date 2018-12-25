import threading
import prctl
from common import Constant, utils
from main.logger_helper import L
from main.admin import models
from main import thread_pool
from smbus2 import SMBus
from bmp280 import BMP280


class P:
    initialised = False
    interval = 60
    has_bmp280 = False
    obj_bmp280 = None

    def __init__(self):
        pass


def _read_bmp280():
    temperature = P.obj_bmp280.get_temperature()
    pressure = P.obj_bmp280.get_pressure()
    sensor_address = Constant.HOST_NAME + '_bmp280'
    zone_sensor = models.ZoneSensor.query.filter_by(sensor_address=sensor_address).first()
    if zone_sensor is not None:
        sensor_name = zone_sensor.sensor_name
        current_record = models.Sensor.query.filter_by(address=sensor_address).first()
        if current_record is None:
            sensor_name = zone_sensor.sensor_name
        record = models.Sensor(address=sensor_address, sensor_name=sensor_name)
        record.temperature = round(temperature, 1)
        record.pressure = round(pressure, 1)
        record.save_changed_fields(current_record=current_record, new_record=record,
                                   notify_transport_enabled=True, save_to_graph=True, debug=False)
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
