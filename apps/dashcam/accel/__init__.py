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


class Params:
    lastrecord = None
    sensor = None
    calibration = None
    sensitivity = 1 # number of decimals
    WEB_PORT = 9000 # set to 0 to disable
    urls = ('/', 'Index')
    web_thread = None
    web_app = None


def _represent():
    last = Params.lastrecord
    res = None
    try:
        res = json.dumps(last)
        #res = "[{'y': %f, 'x': %f, 'z': %f}, {'y': %f, 'x': %f, 'z': %f}, %f]" % \
        #      (last[0]['y'], last[0]['x'], last[0]['z'],
        #       last[1]['y'], last[1]['x'], last[1]['z'],
        #       last[2])
    except Exception, ex:
        print ex
    return res


def _to_json():
    return _represent()


class Index:
    def GET(self):
        #print "returning {}".format(_represent())
        return _represent()


def calibrate():
    Params.calibration = Params.sensor.get_all_data()


def _run_web_server():
    try:
        Params.web_app = web.application(Params.urls, globals())
        web.httpserver.runsimple(Params.web_app.wsgifunc(), ("0.0.0.0", Params.WEB_PORT))
    except Exception, ex:
        print ex


def init():
    try:
        Params.sensor = mpu6050(0x68)
    except Exception, ex:
        print ex

    if Params.WEB_PORT != 0:
        Params.web_thread = threading.Thread(target=_run_web_server)
        Params.web_thread.name = 'WebAccel'
        Params.web_thread.start()


def read_sensor():
    try:
        sensor_all = Params.sensor.get_all_data()
    except Exception, ex:
        print ex
        sensor_all = [{'y': -0.49320554199218747, 'x': -9.528922607421874, 'z': 1.0414777221679687}, {'y': -0.8625954198473282, 'x': -3.0839694656488548, 'z': 0.7938931297709924}, 28.577058823529413]
    Params.lastrecord = sensor_all
    return sensor_all


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
        Params.web_app.stop()
        Params.web_thread.join()
