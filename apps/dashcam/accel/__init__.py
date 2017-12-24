#from main.logger_helper import Log
#from main import thread_pool
import json
import web
import time
import threading
try:
    #import smbus
    from smbus2 import SMBus
    #from mpu6050 import mpu6050
except Exception, ex:
    print ex

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


class Params:
    lastrecord = None
    #sensor = None
    calibration = None
    WEB_PORT = 9000 # set to 0 to disable
    urls = ('/', 'Index')
    web_thread = None
    web_app = None


class Raw:
    # Power management registers
    power_mgmt_1 = 0x6b
    power_mgmt_2 = 0x6c

    gyro_scale = 131.0
    accel_scale = 16384.0

    address = 0x68  # This is the default I2C address of ITG-MPU breakout board
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


############


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
    #Params.calibration = Params.sensor.get_all_data()
    pass

def _run_web_server():
    try:
        Params.web_app = web.application(Params.urls, globals())
        web.httpserver.runsimple(Params.web_app.wsgifunc(), ("0.0.0.0", Params.WEB_PORT))
    except Exception, ex:
        print ex


def unload():
    if Params.web_app is not None:
        Params.web_app.stop()
        Params.web_thread.join()


def init():
    try:
        Raw.init()
    except Exception, ex:
        print ex

    if Params.WEB_PORT != 0:
        Params.web_thread = threading.Thread(target=_run_web_server)
        Params.web_thread.name = 'WebAccel'
        Params.web_thread.start()


def read_sensor():
    try:
        #sensor_all = Params.sensor.get_all_data()
        (gyro_scaled_x, gyro_scaled_y, gyro_scaled_z,
         accel_scaled_x, accel_scaled_y, accel_scaled_z, temp) = Raw.read_all()

        sensor_all = [{'y': accel_scaled_y, 'x': accel_scaled_x, 'z': accel_scaled_z},
                      {'y': gyro_scaled_y, 'x': gyro_scaled_x, 'z': gyro_scaled_z}, temp]
    except Exception, ex:
        print ex
        sensor_all = [{'y': -0.49320554199218747, 'x': -9.528922607421874, 'z': 1.0414777221679687},
                      {'y': -0.8625954198473282, 'x': -3.0839694656488548, 'z': 0.7938931297709924}, 99]
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
            time.sleep(0.1)
    finally:
        Params.web_app.stop()
        Params.web_thread.join()
