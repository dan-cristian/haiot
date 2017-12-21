#from main.logger_helper import Log
#from main import thread_pool
import json
import web
import threading
try:
    from mpu6050 import mpu6050
except Exception, ex:
    print ex

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

_sensor = None
_lastrecord = None
_calibration = None
_sensitivity = 1 # number of decimals


_WEB_PORT=9000 # set to 0 to disable
_urls = ('/', 'index')
_web_thread = None

class AccelRecord:
    def __init__(self, accel, gyro, temp):
        self.accel, self.gyro, self.temp = accel, gyro, temp

    def to_json(self):
        return json.dumps(self)


class index:
    def GET(self):
        return _lastrecord


def calibrate():
    global _calibration
    sensor_all = _sensor.get_all_data()
    _calibration = sensor_all


def _run_web_server():
    app = web.application(_urls, globals())
    web.httpserver.runsimple(app.wsgifunc(), ("0.0.0.0", _WEB_PORT))


def init():
    global _sensor, _web_thread
    _sensor = mpu6050(0x68)
    if _WEB_PORT != 0:
        _web_thread = threading.Thread(target=_run_web_server)
        _web_thread.start()


def thread_run():
    sensor_all = _sensor.get_all_data()
    record = AccelRecord(sensor_all[0], sensor_all[1], sensor_all[2])
    _lastrecord = record
    return 'Processed accel'

if __name__ == "__main__":
    init()
    while True:
        thread_run()

