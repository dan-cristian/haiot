#from main.logger_helper import Log
#from main import thread_pool
import json
import web
import time
import threading
import prctl
from main.logger_helper import L
try:
    from smbus2 import SMBus
    #from mpu6050 import mpu6050
except Exception, ex:
    print ex

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


class P:
    lastrecord = None
    calibration = None
    WEB_PORT = 9000 # set to 0 to disable
    urls = ('/', 'Index')
    web_thread = None
    web_app = None
    stop_app = False


class Raw:
    # Power management registers
    power_mgmt_1 = 0x6b
    power_mgmt_2 = 0x6c
    gyro_scale = 131.0
    accel_scale = 16384.0
    address = 0x69  # This is the default I2C address of ITG-MPU breakout board
    bus = None

    @staticmethod
    def init():
        Raw.bus = SMBus(1)
        # Now wake the 6050 up as it starts in sleep mode
        Raw.bus.write_byte_data(Raw.address, Raw.power_mgmt_1, 0)

    @staticmethod
    def twos_compliment(val):
        if val >= 0x8000:
            return -((65535 - val) + 1)
        else:
            return val

    @staticmethod
    def read_all():
        if Raw.bus is not None:
            raw_gyro_data = Raw.bus.read_i2c_block_data(Raw.address, 0x43, 6)
            raw_accel_data = Raw.bus.read_i2c_block_data(Raw.address, 0x3b, 6)
            raw_temp_data = Raw.bus.read_i2c_block_data(Raw.address, 0x41, 6)
            temp = (Raw.twos_compliment((raw_temp_data[0] << 8) + raw_temp_data[1]) / 340.0) + 36.53
            gyro_scaled_x = Raw.twos_compliment((raw_gyro_data[0] << 8) + raw_gyro_data[1]) / Raw.gyro_scale
            gyro_scaled_y = Raw.twos_compliment((raw_gyro_data[2] << 8) + raw_gyro_data[3]) / Raw.gyro_scale
            gyro_scaled_z = Raw.twos_compliment((raw_gyro_data[4] << 8) + raw_gyro_data[5]) / Raw.gyro_scale
            accel_scaled_x = Raw.twos_compliment((raw_accel_data[0] << 8) + raw_accel_data[1]) / Raw.accel_scale
            accel_scaled_y = Raw.twos_compliment((raw_accel_data[2] << 8) + raw_accel_data[3]) / Raw.accel_scale
            accel_scaled_z = Raw.twos_compliment((raw_accel_data[4] << 8) + raw_accel_data[5]) / Raw.accel_scale
            return gyro_scaled_x, gyro_scaled_y, gyro_scaled_z, accel_scaled_x, accel_scaled_y, accel_scaled_z, temp
        else:
            return None


############


def _represent():
    last = P.lastrecord
    res = None
    try:
        res = json.dumps(last)
        #res = "[{'y': %f, 'x': %f, 'z': %f}, {'y': %f, 'x': %f, 'z': %f}, %f]" % \
        #      (last[0]['y'], last[0]['x'], last[0]['z'],
        #       last[1]['y'], last[1]['x'], last[1]['z'],
        #       last[2])
    except Exception, ex:
        L.l.error("Unable to json accel data, ex={}".format(ex))
    return res


class Index:
    def GET(self):
        L.l.info("Returning accel {}".format(_represent()))
        return _represent()


def _run_web_server():
    try:
        P.web_app = web.application(P.urls, globals())
        web.httpserver.runsimple(P.web_app.wsgifunc(), ("0.0.0.0", P.WEB_PORT))
    except Exception as ex:
        L.l.error("Start accel raw data webserver failed, ex={}".format(ex))


def unload():
    P.stop_app = True
    if P.web_app is not None:
        P.web_app.stop()
    if P.web_thread is not None:
        P.web_thread.join()


def init():
    try:
        Raw.init()
    except Exception as ex:
        L.l.error("Unable to init accel, ex={}".format(ex))

    if P.WEB_PORT != 0:
        P.web_thread = threading.Thread(target=_run_web_server)
        P.web_thread.name = 'WebAccel'
        P.web_thread.start()


def read_sensor():
    if Raw.bus is not None:
        try:
            (gyro_scaled_x, gyro_scaled_y, gyro_scaled_z,
             accel_scaled_x, accel_scaled_y, accel_scaled_z, temp) = Raw.read_all()

            sensor_all = [{'y': accel_scaled_y, 'x': accel_scaled_x, 'z': accel_scaled_z},
                          {'y': gyro_scaled_y, 'x': gyro_scaled_x, 'z': gyro_scaled_z}, temp]
        except Exception as ex:
            L.l.error("Unable to read accel, ex={}".format(ex))
        P.lastrecord = sensor_all
        return sensor_all
    else:
        return None


def thread_run():
    prctl.set_name("accel")
    threading.current_thread().name = "accel"
    read_sensor()
    return 'Processed accel'


if __name__ == "__main__":
    init()
    try:
        while True:
            thread_run()
            time.sleep(0.1)
    finally:
        P.web_app.stop()
        P.web_thread.join()
