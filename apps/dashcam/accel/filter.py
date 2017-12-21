import math
import time

# http://blog.bitify.co.uk/2013/11/using-complementary-filter-to-combine.html

_K = 0.98
_K1 = 1 - _K
_time_diff = 0.01
_last_x = _last_y = _gyro_offset_x = _gyro_offset_y = _gyro_total_x = _gyro_total_y = None



def twos_compliment(val):
    if (val >= 0x8000):
        return -((65535 - val) + 1)
    else:
        return val


def dist(a, b):
    return math.sqrt((a * a) + (b * b))


def get_y_rotation(x, y, z):
    radians = math.atan2(x, dist(y, z))
    return -math.degrees(radians)


def get_x_rotation(x, y, z):
    radians = math.atan2(y, dist(x, z))
    return math.degrees(radians)



def filter_init(gyro_scaled_x, gyro_scaled_y, gyro_scaled_z, accel_scaled_x, accel_scaled_y, accel_scaled_z):
    global _last_x, _last_y, _gyro_offset_x, _gyro_offset_y, _gyro_total_x, _gyro_total_y
    #now = time.time()
    #(gyro_scaled_x, gyro_scaled_y, gyro_scaled_z, accel_scaled_x, accel_scaled_y, accel_scaled_z) = read_all()

    _last_x = get_x_rotation(accel_scaled_x, accel_scaled_y, accel_scaled_z)
    _last_y = get_y_rotation(accel_scaled_x, accel_scaled_y, accel_scaled_z)

    _gyro_offset_x = gyro_scaled_x
    _gyro_offset_y = gyro_scaled_y

    _gyro_total_x = (_last_x) - _gyro_offset_x
    _gyro_total_y = (_last_y) - _gyro_offset_y

    #print "{0:.4f} {1:.2f} {2:.2f} {3:.2f} {4:.2f} {5:.2f} {6:.2f}".format(time.time() - now, (last_x), gyro_total_x,
    #                                                                       (last_x), (last_y), gyro_total_y, (last_y))


def filter_clean(gyro_scaled_x, gyro_scaled_y, gyro_scaled_z, accel_scaled_x, accel_scaled_y, accel_scaled_z):
    global _last_x, _last_y, _gyro_offset_x, _gyro_offset_y, _gyro_total_x, _gyro_total_y
    #for i in range(0, int(3.0 / _time_diff)):
    time.sleep(_time_diff - 0.005)

    #(gyro_scaled_x, gyro_scaled_y, gyro_scaled_z, accel_scaled_x, accel_scaled_y, accel_scaled_z) = read_all()

    gyro_scaled_x -= _gyro_offset_x
    gyro_scaled_y -= _gyro_offset_y

    gyro_x_delta = (gyro_scaled_x * _time_diff)
    gyro_y_delta = (gyro_scaled_y * _time_diff)

    _gyro_total_x += gyro_x_delta
    _gyro_total_y += gyro_y_delta

    rotation_x = get_x_rotation(accel_scaled_x, accel_scaled_y, accel_scaled_z)
    rotation_y = get_y_rotation(accel_scaled_x, accel_scaled_y, accel_scaled_z)

    _last_x = _K * (_last_x + gyro_x_delta) + (_K1 * rotation_x)
    _last_y = _K * (_last_y + gyro_y_delta) + (_K1 * rotation_y)

    #print "{0:.4f} {1:.2f} {2:.2f} {3:.2f} {4:.2f} {5:.2f} {6:.2f}".format(time.time() - now, (rotation_x),
    #                                                                       (gyro_total_x), (last_x), (rotation_y),
    #                                                                       (gyro_total_y), (last_y))
    return _last_x, _last_y