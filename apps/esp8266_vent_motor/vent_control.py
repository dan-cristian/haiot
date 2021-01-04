import uln2003
import machine
from machine import Pin
import utime
import ujson
import mqtt
import common


class P:
    close_angle = 90
    open_angle = 90
    motor = None
    last_action = utime.time()


def init_motor():
    """
    IN1 -->  D5
    IN2 -->  D6
    IN3 -->  D1
    IN4 -->  D2
    """
    P.motor = uln2003.create(Pin(14, Pin.OUT), Pin(12, Pin.OUT), Pin(5, Pin.OUT), Pin(4, Pin.OUT), delay=2)


def test_motor():
    # P.motor.step(100)
    # P.motor.step(100, -1)
    P.motor.angle(10)
    # P.motor.angle(360, -1)
    P.motor.angle(10, -1)


def calibrate_close():
    pass


def calibrate_open():
    pass


def close_full_vent(direction):
    if common.rtc_storage.closed == 0:
        P.motor.angle(P.close_angle, direction)
        common.rtc_storage.closed = 1
        P.last_action = utime.time()
        print("Closed vent")
    else:
        print("Already closed, ignoring")
    common.save_rtc()


def open_full_vent(direction):
    if common.rtc_storage.closed == 1:
        P.motor.angle(P.open_angle, direction)
        common.rtc_storage.closed = 0
        P.last_action = utime.time()
        print("Opened vent")
    else:
        print("Already opened, ignoring")
    common.save_rtc()


def vent_move(angle):
    if angle > 0:
        direction = 1
    else:
        direction = -1
    P.motor.angle(abs(angle), direction)
    print("Vent moved angle {} direction {}".format(angle, direction))


def timer_actions():
    delta = utime.time() - P.last_action
    if delta > 60:
        common.publish_state()
        common.init_deep_sleep(sleep_sec=300)
