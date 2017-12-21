#from main.logger_helper import Log
#from main import thread_pool
import json
import web
import time
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
_web_app = None


class AccelRecord:
    def __init__(self, accel, gyro, temp):
        self.accel, self.gyro, self.temp = accel, gyro, temp

    def __repr__(self):
        try:
            res = "[{'y': %f, 'x': %f, 'z': %f}, {'y': %f, 'x': %f, 'z': %f}, {%f}]" % \
                  (self.accel['y'] , self.accel['x'], self.accel['z'], self.gyro['y'], self.gyro['x'], self.gyro['z'],
                   self.temp)
        except Exception, ex:
            pass
        return res


    def to_json(self):
        return json.dumps(self)


class index:
    def GET(self):
        record = read_sensor()
        print "returning {}".format(record)
        return record


def calibrate():
    global _calibration
    sensor_all = _sensor.get_all_data()
    _calibration = sensor_all


def _run_web_server():
    global _web_app
    try:
        _web_app = web.application(_urls, globals())
        web.httpserver.runsimple(_web_app.wsgifunc(), ("0.0.0.0", _WEB_PORT))
    except Exception, ex:
        print ex

def init():
    global _sensor, _web_thread
    try:
        _sensor = mpu6050(0x68)
    except Exception, ex:
        print ex

    if _WEB_PORT != 0:
        _web_thread = threading.Thread(target=_run_web_server)
        _web_thread.start()


def read_sensor():
    global _lastrecord
    try:
        sensor_all = _sensor.get_all_data()
    except Exception, ex:
        print ex
        sensor_all = [{'y': -0.49320554199218747, 'x': -9.528922607421874, 'z': 1.0414777221679687}, {'y': -0.8625954198473282, 'x': -3.0839694656488548, 'z': 0.7938931297709924}, 28.577058823529413]
    record = AccelRecord(sensor_all[0], sensor_all[1], sensor_all[2])
    _lastrecord = record
    return record

def thread_run():
    read_sensor()
    return 'Processed accel'


if __name__ == "__main__":
    init()
    try:
        while True:
            thread_run()
            time.sleep(0.2)
    finally:
        _web_app.stop()
        _web_thread.join()
