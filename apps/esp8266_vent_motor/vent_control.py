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
    closed = 1
    last_action = utime.time()
    rtc = None


def save_rtc():
    P.rtc.memory("{}".format(P.closed))


def read_rtc():
    mem = P.rtc.memory()
    print("Reading rtc memory={}".format(mem))
    if mem is not None and len(mem) > 0:
        P.closed = int(mem)
        print("Read rtc memory={}".format(P.closed))
    else:
        print("Read rtc memory is None")


def init_motor():
    """
    IN1 -->  D5
    IN2 -->  D6
    IN3 -->  D1
    IN4 -->  D2
    """
    P.motor = uln2003.create(Pin(14, Pin.OUT), Pin(12, Pin.OUT), Pin(5, Pin.OUT), Pin(4, Pin.OUT), delay=2)
    P.rtc = machine.RTC()


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
    if P.closed == 0:
        P.motor.angle(P.close_angle, direction)
        P.closed = 1
        P.last_action = utime.time()
    else:
        print("Already closed, ignoring")
    save_rtc()


def open_full_vent(direction):
    if P.closed == 1:
        P.motor.angle(P.open_angle, direction)
        P.closed = 0
        P.last_action = utime.time()
    else:
        print("Already opened, ignoring")
    save_rtc()


def vent_move(angle):
    direction = int(angle >= 0)  # 1 or 0
    P.motor.angle(abs(angle), direction)
    print("Vent moved angle {} direction {}".format(angle, direction))


def timer_actions():
    delta = utime.time() - P.last_action
    if delta > 60:
        vcc = machine.ADC(1).read()
        # send current state to mqtt
        mqtt.publish('{{"vcc": {},"closed": {}}}'.format(vcc, P.closed))
        mqtt.disconnect()
        # put the device to sleep
        common.init_deep_sleep(sleep_sec=60)
