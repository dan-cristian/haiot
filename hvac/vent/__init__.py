import threading
import prctl
from main.logger_helper import L
from main import thread_pool
from storage.model import m
from devices import vent_atrea

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


class P:
    initialised = False

    last_vent_mode = None
    last_power_level = None
    central_vent_sensor_name = "vent-air-w_pms5003"
    co2_ok_value = 550
    co2_warn_value = 1000

    def __init__(self):
        pass


def adjust():
    dust_sensor = m.DustSensor.find_one({m.DustSensor.address: P.central_vent_sensor_name})
    vent = m.Ventilation.find_one({m.Ventilation.id: 0})
    if vent is None:
        L.l.error("Ventilation system not defined in conf, exit")
        return
    # shutoff vent system on high pm25
    if dust_sensor is not None:
        pm25 = dust_sensor.pm_2_5
        # assumes vent system has id 0 in conf file

        if vent.mode != vent_atrea.P.mode_off:
            P.last_vent_mode = vent.mode
        if pm25 > 50:  # max pm level to shutdown
            vent.mode = vent_atrea.P.mode_off
        else:
            if P.last_vent_mode is not None:
                vent.mode = P.last_vent_mode
        vent.save_changed_fields()

    if P.last_power_level is None:
        P.last_power_level = vent.power_level

    # adjust vent system power based on CO2 levels
    if vent.mode != vent_atrea.P.mode_off:
        co2_vals = []
        co2_ids = []
        air_list = m.AirSensor.find()
        for sensor in air_list:
            if sensor.co2 is not None and sensor.co2 > 400:  # add all co2 sensors with valid values
                co2_vals.append(sensor.co2)
                co2_ids.append(sensor.address)
        if len(co2_vals) > 0:
            max_co2 = max(co2_vals)
            if max_co2 < P.co2_ok_value:  # reduce power level, no need
                L.l.info("CO2 levels are low, {}, reducing system speed to minimum".format(max_co2))
                P.last_power_level = vent.power_level
                vent_atrea.set_power_level(vent_atrea.P.power_level_min)
                vent.power_level = vent_atrea.P.power_level_min
                vent.save_changed_fields()
            else:  # resume initial power level
                if vent.power_level != P.last_power_level:
                    L.l.info("CO2 levels are increased, resuming system speed to {}".format(P.last_power_level))
                    vent_atrea.set_power_level(P.last_power_level)
                    vent.power_level = P.last_power_level
                    vent.save_changed_fields()


def thread_run():
    prctl.set_name("hvac vent")
    threading.current_thread().name = "hvac vent"
    adjust()
    prctl.set_name("idle")
    threading.current_thread().name = "idle"
    return 'Processed hvac vent'


def unload():
    L.l.info('Hvac vent module unloading')
    thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    L.l.info('Hvac vent module initialising')
    thread_pool.add_interval_callable(thread_run, run_interval_second=60)
    P.initialised = True
    # dispatcher.connect(_init_recovery, signal=Constant.SIGNAL_USB_DEVICE_CHANGE, sender=dispatcher.Any)
    # dispatcher.send(Constant.SIGNAL_USB_DEVICE_CHANGE)
