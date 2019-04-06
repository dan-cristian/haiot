__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from main import L, thread_pool
from main import thread_pool
from main.admin import models
import random
initialised = False


def test1():
    noerr = True
    i = 0
    while noerr:
        i += 1
        L.l.info("Iteration {}".format(i))
        key = 'boiler2'
        rec = models.Pwm.query.filter_by(name=key).first()
        if rec is None or rec.name != key:
            noerr = False
        duty_cycle = random.randint(100, 100000)
        new_pwm = models.Pwm(id=rec.id)
        new_pwm.name = rec.name
        new_pwm.duty_cycle = duty_cycle
        new_pwm.save_changed_fields(
            current_record=rec, new_record=new_pwm, notify_transport_enabled=True, debug=False)


def unload():
    # ...
    # thread_pool.remove_callable(test_run.thread_run)
    global initialised
    initialised = False


def init():
    L.l.info('TEST module initialising')
    # test1()
    # sensor_address = "ZMNHTDx Smart meter S4 S5 S6:2"
    # current_record = models.Sensor.query.filter_by(address=sensor_address).first()
    # thread_pool.add_interval_callable(test_run.thread_run, run_interval_second=60)
    global initialised
    initialised = True


