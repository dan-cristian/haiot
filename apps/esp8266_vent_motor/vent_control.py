import uln2003
import machine
from machine import Pin
import utime
import ujson
import mqtt
import common


class P:
    motor = None
    max_angle = 90  # prevent vent stop from flipping over
    last_action = utime.time()


def init_motor():
    """
    IN1 -->  D5 wemos
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


def vent_move(angle):
    new_angle = common.rtc_storage.angle + angle
    if 0 <= new_angle <= P.max_angle:
        if angle > 0:
            direction = 1
        else:
            direction = -1
        P.motor.angle(abs(angle), direction)
        common.rtc_storage.angle = new_angle
        print("Vent moved angle {} direction {}, new angle={}".format(angle, direction, new_angle))
        common.save_rtc()
    else:
        print("Invalid angle request {}, outside range 0 - {}. Angle is {}".format(angle, P.max_angle,
                                                                                   common.rtc_storage.angle))


def timer_actions():
    delta = utime.time() - P.last_action
    if delta > 60:
        common.publish_state()
        P.last_action = utime.time()
        # common.init_deep_sleep(sleep_sec=300)
