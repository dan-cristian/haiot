import threading
import prctl
from main.logger_helper import L
from main import thread_pool
from storage.model import m
from devices import vent_atrea
from sensor import radoneye
import datetime

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


class P:
    initialised = False
    last_vent_mode = None
    central_vent_sensor_name = "vent-air-w_pms5003"
    co2_ok_value = 650
    co2_warn_value = 1000
    radon_ok_value = 70
    radon_warn_value = 100
    # https://www.engineeringtoolbox.com/co2-comfort-level-d_1024.html
    central_mode_is_min = False
    max_outdoor_pm25 = 50
    last_power_increase = datetime.datetime.now()
    increase_delta_minutes = 5

    def __init__(self):
        pass


def adjust():
    dust_sensor = m.DustSensor.find_one({m.DustSensor.address: P.central_vent_sensor_name})
    # assumes vent system has id 0 in conf file
    vent = m.Ventilation.find_one({m.Ventilation.id: 0})
    if vent is None:
        L.l.error("Ventilation system not defined in conf, exit")
        return

    radon_sensor = m.AirSensor.find_one({m.AirSensor.id: radoneye.P.radoneye_id})
    radon_is_high = (radon_sensor is not None) and (radon_sensor.radon is not None) and \
                    (radon_sensor.radon > P.radon_ok_value)
    radon_is_warn = (radon_sensor is not None) and (radon_sensor.radon is not None) and \
                    (radon_sensor.radon > P.radon_warn_value)

    # shutoff vent system on high pm25
    if dust_sensor is not None:
        pm25 = dust_sensor.pm_2_5
        if vent.mode != vent_atrea.P.mode_off:
            P.last_vent_mode = vent.mode
        if pm25 > P.max_outdoor_pm25 and not radon_is_warn:  # max pm level to shutdown
            vent.mode = vent_atrea.P.mode_off
        else:
            if P.last_vent_mode is not None:
                vent.mode = P.last_vent_mode
            else:
                vent.mode = vent_atrea.P.mode_default
        vent.save_changed_fields()
        if vent.mode == vent_atrea.P.mode_off:
            # no point in doing other vent adjustments
            return

    # adjust vent system power based on CO2 levels
    if vent.mode != vent_atrea.P.mode_off:
        co2_vals = []
        co2_ids = []
        co2_sensors = {}
        air_list = m.AirSensor.find()
        max_co2_count = 0
        for sensor in air_list:
            if sensor.co2 is not None and sensor.co2 >= 400:  # add all co2 sensors with valid values
                # check if this is a house sensor (indoor)
                zone = m.Zone.find_one({m.Zone.id: sensor.zone_id})
                if zone is not None and zone.is_indoor:
                    # check if there is an adjustable vent
                    check_vent = m.Vent.find_one({m.Vent.zone_id: sensor.zone_id})
                    if check_vent is not None:
                        co2_vals.append(sensor.co2)
                        co2_ids.append(sensor.address)
                        co2_sensors[sensor.address] = sensor
                        if sensor.co2 > P.co2_ok_value:
                            max_co2_count += 1

        new_power_level = None
        if len(co2_vals) > 0:
            max_co2 = max(co2_vals)
            max_address = co2_ids[co2_vals.index(max_co2)]
            max_co2_sensor = co2_sensors[max_address]
            if max_co2 <= P.co2_ok_value and not radon_is_high:  # reduce power level to minimum, no need
                L.l.info("CO2/radon levels are low: {}, reducing system speed to minimum".format(max_co2))
                new_power_level = vent_atrea.P.power_level_min
                P.central_mode_is_min = True
            else:  # resume initial power level
                if P.central_mode_is_min:
                    L.l.info("CO2/radon levels are increased, resuming system speed")
                    new_power_level = vent_atrea.P.power_level_default
                    P.central_mode_is_min = False
                else:
                    # adjust vent system power if needed to remove co2 faster
                    trend = max_co2_sensor.get_trend("co2", max_address)
                    L.l.info("CO2 max trend for {} is {}".format(max_address, trend))
                    delta_power_increase = (datetime.datetime.now() - P.last_power_increase).total_seconds() / 60
                    if trend == 1 and delta_power_increase >= P.increase_delta_minutes:
                        # co2 increasing, faster if there are multiple rooms above max co2
                        new_power_level = vent.power_level + max_co2_count
                        P.last_power_increase = datetime.datetime.now()
            # adjust vent openings based on co2 room levels
            adjust_vents(co2_sensors, max_co2_sensor, radon_sensor, radon_is_high)
            if new_power_level is not None:
                vent_atrea.set_power_level(new_power_level)


def adjust_vents(co2_sensors, max_co2_sensor, radon_sensor, radon_is_high):
    # adjust vents based on co2 room level or radon. CO2 takes priority.
    # open vent/s in one room
    if max_co2_sensor.co2 <= P.co2_ok_value and radon_is_high:
        # open zone vent with radon high and co2 ok
        zone_id_open = radon_sensor.zone_id
    else:
        # open if co2 is high
        zone_id_open = max_co2_sensor.zone_id
    vents = m.Vent.find({m.Vent.zone_id: zone_id_open})
    for vent in vents:
        vent.angle = 90
        vent.save_changed_fields(broadcast=True)

    # close the rest
    vents = m.Vent.find()
    for vent in vents:
        if vent.zone_id != zone_id_open:
            vent.angle = -90  # close if not in a room with max co2 or radon
        vent.save_changed_fields(broadcast=True)  # this also sends mqtt command to vent


def vent_upsert_listener(record, changed_fields):
    # L.l.info("Ignoring vent upsert {} changed={}".format(record, changed_fields))
    assert isinstance(record, m.Vent)
    # if "angle" in changed_fields and record.angle is not None:
    #    set_angle(record.host_name, record.angle)


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
    m.Vent.add_upsert_listener(vent_upsert_listener)
    # dispatcher.connect(_init_recovery, signal=Constant.SIGNAL_USB_DEVICE_CHANGE, sender=dispatcher.Any)
    # dispatcher.send(Constant.SIGNAL_USB_DEVICE_CHANGE)
