import os
import threading
import prctl
from datetime import datetime
from apps.tesla.TeslaPy.teslapy import VehicleError
from main.logger_helper import L
from main import thread_pool
from storage.model import m
from common import Constant, get_secure_general, get_json_param
from transport import mqtt_io
from apps.tesla.TeslaPy.teslapy import Tesla

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


class P:
    initialised = False
    tesla = None
    vehicles = None
    email = None
    DEFAULT_VOLTAGE = 220
    MIN_VOLTAGE = 120
    voltage = 220  # default one
    MAX_AMP = 22  # maximum charging amps for tesla. # todo: can auto detect this, but depends on house breakers too
    api_requests = 0
    refresh_request_pause = 30  # seconds between each status update request
    stop_charge_interval = 300  # seconds interval with amps set to 0 after which charging is stopped
    last_too_many_requests_date = datetime.min
    too_many_request_pause_interval = 60  # wait until making next API req
    last_refresh_request = datetime.min
    scheduled_charging_mode = None
    user_charging_mode = False  # True is user started the charging, so don't run automatic charging setup
    charging_state = None
    charge_limit_soc = None
    battery_level = None
    home_latitude = None
    home_longitude = None
    can_charge_at_home = None  # True if car is at home, so automatic charging can happen
    teslamate_topic = None
    teslamate_geo_home = None  # do not trigger automatic charging, car maybe not be at home etc
    teslamate_charging_amp = dict()
    teslamate_last_charging_update = datetime.min
    charging_stopped = None  # update charging state when sending charge start/stop commands
    charging_status_date = datetime.min
    teslamate_voltage = dict()
    teslamate_plugged_in = dict()
    teslamate_time_to_full_charge = None
    teslamate_soc = None
    teslamate_battery_level = None
    battery_full = None
    # save car params
    is_charging = dict()
    is_preconditioning = dict()
    is_climate_on = dict()
    charging_amp = dict()
    car_latitude = dict()
    car_longitude = dict()
    car_state = dict()
    last_charging_stopped = dict()  # timestamps when car charging was stopped
    DEBUG = True
    last_debug = datetime.now()
    DEBUG_DELTA = 60  # sec

    def __init__(self):
        pass


def can_refresh():
    return (datetime.now() - P.last_refresh_request).total_seconds() >= P.refresh_request_pause


def can_print_debug():
    res = P.DEBUG and (datetime.now() - P.last_debug).total_seconds() > P.DEBUG_DELTA
    if res:
        P.last_debug = datetime.now()
    return res

# allow variable charging when car is at home and scheduling is not enabled
# when scheduling is enabled the car charging parameters will not change - allows manual user adjustments only
def can_auto_charge(vehicle_id=1):
    if vehicle_id in P.teslamate_plugged_in.keys():
        plugged_in = P.teslamate_plugged_in[vehicle_id]
    else:
        plugged_in = P.charging_state != 'Disconnected'
    if vehicle_id in P.is_preconditioning.keys():
        is_preconditioning = P.is_preconditioning[vehicle_id]
    else:
        is_preconditioning = False
    if vehicle_id in P.is_climate_on.keys():
        is_climate_on = P.is_climate_on[vehicle_id]
    else:
        is_climate_on = False
    res = (P.can_charge_at_home or P.teslamate_geo_home) and not P.scheduled_charging_mode \
          and plugged_in # and (is_preconditioning is False) and (is_climate_on is False)
    if res is False and P.can_charge_at_home is None and P.teslamate_geo_home is None and plugged_in:
        L.l.info("Forcing Tesla auto charge as I miss data, assume I can charge")
        res = True
    if res is None and plugged_in:
        # force a charge to trigger charge status
        res = True
    if can_print_debug() and (res is False or res is None):
        L.l.info("Tesla debug auto_charge: home={} geo={} sched={} plugged={} time_full={} precond={} clim={}".format(
            P.can_charge_at_home, P.teslamate_geo_home, P.scheduled_charging_mode, plugged_in,
            P.teslamate_time_to_full_charge, is_preconditioning, is_climate_on
        ))
    return res


def is_battery_full():
    if P.charge_limit_soc is not None:
        soc_full = (P.battery_level is not None and P.charge_limit_soc is not None) and \
                   (P.battery_level >= P.charge_limit_soc) or \
                   (P.teslamate_battery_level is not None and P.teslamate_soc is not None) and \
                   (P.teslamate_battery_level >= P.teslamate_soc)
        res = soc_full
    else:
        res = P.battery_full
    if P.battery_full is None and res:
        L.l.info("Tesla battery state conflicting, force start charge")
        res = False
    # (P.teslamate_time_to_full_charge is not None and P.teslamate_time_to_full_charge == 0)
    if res is True and P.DEBUG:
        L.l.info("Tesla battery seems full P.full={}, limit={} level={} mate_level={}".format(
            P.battery_full, P.charge_limit_soc, P.battery_level, P.teslamate_battery_level))
    return res


def vehicle_valid(car_id):
    if P.vehicles is None or len(P.vehicles) <= (car_id - 1):  # first id can be 1
        L.l.error("Tesla id not on list or list is empty")
        return False
    else:
        return True


def should_stop_charge(car_id):
    if car_id not in P.last_charging_stopped.keys() or P.last_charging_stopped[car_id] is None \
            or not is_charging(car_id):
        return False
    else:
        return (datetime.now() - P.last_charging_stopped[car_id]).total_seconds() > P.stop_charge_interval


def try_connection_recovery(car_id):
    L.l.info("Trying to recover Tesla cloud connection")
    try:
        P.tesla.close()
        P.tesla = Tesla(email=P.email, cache_file="../private_config/.credentials/tesla_cache.json", timeout=120)
        P.vehicles = P.tesla.vehicle_list()
        vehicle = P.vehicles[car_id - 1]
        P.car_state[car_id] = vehicle['state']
        state = vehicle['state']
        if state in ['asleep', 'offline']:
            L.l.info("Tesla is {}, trying to wake it ...".format(state))
            vehicle.sync_wake_up()
        else:
            L.l.info("Tesla is {}, nothing to do on recovery".format(state))
    except Exception as ex:
        L.l.error("Unable to recover Tesla connection, er={}".format(ex))
        if "Too Many Requests" in "{}".format(ex):
            P.last_too_many_requests_date = datetime.now()


def set_charging_amps(amps, car_id=1):
    if vehicle_valid(car_id):
        if amps <= P.MAX_AMP:
            try:
                if can_run_api_cmd():
                    P.vehicles[car_id - 1].command('CHARGING_AMPS', charging_amps=amps)
                    P.charging_amp[car_id] = amps
                    P.api_requests += 1
                    if amps == 0:
                        if P.last_charging_stopped[car_id] is None:  # only update if previously was charging
                            P.last_charging_stopped[car_id] = datetime.now()
                    else:
                        P.last_charging_stopped[car_id] = None  # reset timestamp
                    return True
                else:
                    L.l.warning("Skipping set Tesla charging amps due to too many requests")
            except VehicleError as vex:
                L.l.error("VehicleError, cannot set Tesla charging amps: {}".format(vex))
                P.last_too_many_requests_date = datetime.now()
            except Exception as ex:
                L.l.error("Unable to set Tesla charging amps: {}".format(ex))
                try_connection_recovery(car_id)
        else:
            L.l.warning("Set Tesla amperage too high, {} A".format(amps))
    return False


def get_last_charging_amps(car_id=1):
    # return first teslamate values
    if car_id in P.teslamate_charging_amp.keys():
        return P.teslamate_charging_amp[car_id]
    else:
        # if teslamate is not updated, return last known from direct read
        if car_id in P.charging_amp.keys():
            return P.charging_amp[car_id]
        else:
            return None


# https://github.com/tdorssers/TeslaPy
def vehicle_update(car_id=1):
    if (not vehicle_valid(car_id)) or (not can_refresh()):
        L.l.info("Not updating Tesla vehicle, valid={}, can_refresh={}".format(vehicle_valid(car_id), can_refresh()))
        return None

    vehicle = P.vehicles[car_id - 1]
    try:
        P.car_state[car_id] = vehicle['state']
        if vehicle['state'] in ['asleep', 'offline']:
            # fixme: do no wake the car
            # vehicle.sync_wake_up()
            P.api_requests += 1
        if vehicle['state'] == 'online':
            vehicle_data = vehicle.get_vehicle_data()
            P.api_requests += 1
            P.last_refresh_request = datetime.now()
            ch = vehicle_data['charge_state']
            P.scheduled_charging_mode = (ch['scheduled_charging_mode'] != "Off")
            P.user_charging_mode = ch['user_charge_enable_request']
            P.charging_state = ch['charging_state']
            P.charge_limit_soc = ch['charge_limit_soc']
            P.battery_level = ch['battery_level']
            L.l.info('Tesla user charging request={}, schedule mode={}'.format(P.user_charging_mode,
                                                                               P.scheduled_charging_mode))
            if P.user_charging_mode:
                L.l.info("Tesla manual user charging detected")
            act_amps = ch['charger_actual_current']
            if act_amps is None:
                act_amps = 0
            P.charging_amp[car_id] = act_amps
            if car_id not in P.last_charging_stopped.keys():
                if act_amps == 0:
                    P.last_charging_stopped[car_id] = datetime.now()
                else:
                    P.last_charging_stopped[car_id] = None
            act_voltage = ch['charger_voltage']
            if act_voltage is None:
                act_voltage = 0
            if act_voltage > 0:
                P.voltage = act_voltage
                P.teslamate_voltage[car_id] = act_voltage
            P.is_charging[car_id] = (ch['charging_state'] == 'Charging')
            if P.is_charging[car_id]:
                P.charging_stopped = False
            P.charging_status_date = datetime.now()
            L.l.info("Tesla charging status = {}".format(ch['charging_state']))
            L.l.info("Tesla charging amp = {}".format(act_amps))
            if act_amps > 0:
                if not P.is_charging[car_id]:
                    L.l.error("I was expecting Tesla vehicle to charge")
            car = m.ElectricCar.find_one({m.ElectricCar.id: car_id})
            if car is not None:
                car.charger_current = act_amps
                if act_voltage is not None:
                    car.actual_voltage = act_voltage
                car.is_charging = P.is_charging[car_id]
                car.save_changed_fields(broadcast=False, persist=True)
            ds = vehicle_data['drive_state']
            if ds is not None:
                if 'latitude' in ds and 'longitude' in ds:
                    P.car_latitude[car_id] = ds['latitude']
                    P.car_longitude[car_id] = ds['longitude']
                    if (abs(P.home_latitude - P.car_latitude[1]) < 0.0002) \
                            and (abs(P.home_longitude - P.car_longitude[1]) < 0.0002):
                        P.can_charge_at_home = True
                    else:
                        P.can_charge_at_home = False
                else:
                    L.l.warning("Cannot find latitude/longitude in Tesla response, got this:{}".format(ds))
            return act_amps
        else:
            L.l.error("Tesla not online, state={}".format(vehicle['state']))
    except Exception as ex:
        L.l.error("Unable to get Tesla charging data, #API{}, er={}".format(P.api_requests, ex))
        P.last_refresh_request = datetime.now()
        summary = vehicle.get_vehicle_summary()
        P.vehicles = P.tesla.vehicle_list()


def get_nonzero_voltage():
    if P.voltage < P.MIN_VOLTAGE:
        return P.DEFAULT_VOLTAGE
    else:
        return P.voltage


def get_voltage(car_id=1):
    if car_id in P.teslamate_voltage.keys():
        return P.teslamate_voltage[car_id]
    else:
        return None


def is_charging(car_id=1):
    voltage = get_voltage(car_id)
    if voltage is not None:
        # sometimes voltage is higher than 0 when not charging
        voltage_charge = P.teslamate_voltage[car_id] > P.MIN_VOLTAGE
    else:
        voltage_charge = False

    if voltage_charge:
        # dbl check if really charging
        last_delta = (datetime.now() - P.charging_status_date).total_seconds()
        L.l.info("Tesla on charge check charge_stopped={}, last update={}s".format(P.charging_stopped, last_delta))
        return True
    else:
        return False

    # if car_id in P.is_charging.keys():
    #    return P.is_charging[car_id]
    # else:
    #    L.l.warning("Cannot find charging flag for id {}".format(car_id))
    #    return None


def stop_charge(car_id=1):
    if vehicle_valid(car_id):
        L.l.info("Stopping Tesla charging")
        try:
            run_api_cmd(P.vehicles[car_id - 1], 'STOP_CHARGE')
            # P.vehicles[car_id - 1].command('STOP_CHARGE')
            P.is_charging[car_id] = False
            P.last_charging_stopped[car_id] = None
            P.api_requests += 1
            P.charging_stopped = True
            P.charging_status_date = datetime.now()
            return True
        except VehicleError as vex:
            L.l.warning("Tesla error, cannot stop charging, er={}".format(vex))
            if "{}".format(vex) == "not_charging":
                P.charging_stopped = True
                P.charging_status_date = datetime.now()
                return True
        except Exception as ex:
            L.l.warning("Tesla exception, cannot stop charging, er={}".format(ex))
        return False


def can_run_api_cmd():
    return (datetime.now() - P.last_too_many_requests_date).total_seconds() > P.too_many_request_pause_interval


def run_api_cmd(vehicle, command):
    if can_run_api_cmd():
        vehicle.command(command)
    else:
        L.l.warning("Skipping Tesla API call, waiting due to many requests error")
        raise Exception("Not making Tesla API call")


def start_charge(car_id=1):
    if vehicle_valid(car_id):
        L.l.info("Starting Tesla charging")
        vehicle = P.vehicles[car_id - 1]
        try:
            run_api_cmd(vehicle, 'START_CHARGE')
            # vehicle.command('START_CHARGE')
            P.api_requests += 1
            P.charging_stopped = False
            P.charging_status_date = datetime.now()
            return True
        except VehicleError as vex:
            if "{}".format(vex) == "disconnected":
                L.l.warning("Tesla is disconnected, cannot start charging")
                P.charging_stopped = True
                P.charging_status_date = datetime.now()
            if "{}".format(vex) == "complete":
                L.l.info("Tesla charge is already complete, cannot start charging")
                P.battery_full = True
                P.charging_stopped = True
                P.charging_status_date = datetime.now()
                return False
            if "{}".format(vex) == "is_charging":
                P.charging_stopped = False
                P.charging_status_date = datetime.now()
                return True
        except Exception as ex:
            if "vehicle unavailable" in "{}".format(ex):
                L.l.warning("Tesla unavailable on start charge, trying to wake")
                vehicle.sync_wake_up()
            if "Too Many Requests" in "{}".format(ex):
                L.l.warning("Tesla API error, too many requests: {}".format(ex))
                P.last_too_many_requests_date = datetime.now()
            L.l.error("Got error when trying to start Tesla charging, err={}".format(ex))
        return False


# https://docs.teslamate.org/docs/integrations/mqtt/
def _process_message(msg):
    car_id = int(msg.topic.split("teslamate/cars/")[1][:2].replace("/", ""))
    if "inside_temp" in msg.topic:
        value = "{}".format(msg.payload).replace("b", "").replace("\\", "").replace("'", "")
    if "plugged_in" in msg.topic:
        value = msg.payload
        P.teslamate_plugged_in[car_id] = (value == b'true')
        L.l.info("Tesla is plugged in={}".format(P.teslamate_plugged_in[car_id]))
    if "charger_actual_current" in msg.topic:
        if msg.payload != b'':
            value = int(msg.payload)
            P.teslamate_charging_amp[car_id] = value
            P.teslamate_last_charging_update = datetime.now()
        L.l.info("Tesla charger actual current = {}".format(msg.payload))
    if "charger_power" in msg.topic:
        value = int(msg.payload)
        if value == 0:
            P.is_charging[car_id] = False
            L.l.info("Tesla stopped charging")
        elif value == 1:
            P.is_charging[car_id] = True
            L.l.info("Tesla started charging")
        else:
            L.l.info("Tesla charging power={}, unknown state".format(value))
    if "charger_voltage" in msg.topic:
        value = int(msg.payload)
        P.teslamate_voltage[car_id] = value
        if value > 0:
            P.voltage = value
    if "charge_limit_soc" in msg.topic:
        value = int(msg.payload)
        P.teslamate_soc = value
        L.l.info("Tesla charge limit soc={}".format(value))
    # time to full charge does not get reported all time, stays at 0.0. not reliable.
    if "time_to_full_charge" in msg.topic:
        P.teslamate_time_to_full_charge = float(msg.payload)
        L.l.info("Tesla time to full charge={}".format(P.teslamate_time_to_full_charge))
        if P.teslamate_time_to_full_charge == 0.0:
            L.l.info("Tesla might need charging, mate soc={}, soc={}, bat mate level={}, level={} full={}".format(
                P.teslamate_soc, P.charge_limit_soc, P.teslamate_battery_level, P.battery_level, P.battery_full))
            if P.battery_level is not None and P.teslamate_soc is not None and P.battery_level < P.teslamate_soc:
                P.battery_full = False
                L.l.info("Set Tesla battery as not full")
        if P.teslamate_time_to_full_charge > 0:
            L.l.info("Set tesla battery level to None to force charge")
            P.battery_full = False
            P.battery_level = None
            P.teslamate_battery_level = None
    if "state" in msg.topic:
        value = "{}".format(msg.payload).replace("b", "").replace("\\", "").replace("'", "")
        P.car_state[car_id] == value
        # online, asleep, charging, suspended
        L.l.info("Tesla_mate state={}".format(value))
    if "geofence" in msg.topic:
        value = "{}".format(msg.payload).replace("b", "").replace("\\", "").replace("'", "")
        P.teslamate_geo_home = (value.lower() == "home")
        L.l.info("Tesla geo={}".format(value))
    if "battery_level" in msg.topic:
        value = int(msg.payload)
        P.teslamate_battery_level = value
        # P.battery_full = None
        L.l.info("Tesla battery level={}".format(value))
    if "power" in msg.topic:
        value = int(msg.payload)
        L.l.info("Tesla battery power={}".format(value))
        if value == -1:  # charging started
            # refresh vehicle state to detect if user started the charging
            # temporarily set user charging to true to avoid automatic stop
            P.user_charging_mode = True
            vehicle_update(car_id)
        L.l.info("Tesla_mate power={}".format(value))
    if "is_climate_on" in msg.topic:
        value = bool(msg.payload)
        L.l.info("Tesla climate on={}".format(value))
        P.is_climate_on[car_id] = value
    if "is_preconditioning" in msg.topic:
        value = bool(msg.payload)
        L.l.info("Tesla is preconditioning={}".format(value))
        P.is_preconditioning[car_id] = value
    if "user_charge_enable_request" in msg.topic:  # not working
        value = "{}".format(msg.payload).replace("b", "").replace("\\", "").replace("'", "")
        P.user_charging_mode = value == "True"
    if "scheduled_charging_start_time" in msg.topic:
        value = "{}".format(msg.payload).replace("b", "").replace("\\", "").replace("'", "")
        L.l.info("Detected Tesla start charge as schedule changed={}".format(value))
        P.scheduled_charging_mode = (value != "")
    if P.DEBUG:
        L.l.info("Teslamate: {}={}".format(msg.topic, msg.payload))


def mqtt_on_message(client, userdata, msg):
    try:
        prctl.set_name("mqtt_teslamate")
        threading.current_thread().name = "mqtt_teslamate"
        _process_message(msg)
    except Exception as ex:
        L.l.error("Error processing teslamate mqtt {}, err={}, msg={}".format(msg.topic, ex, msg), exc_info=True)
    finally:
        prctl.set_name("idle_mqtt_teslamate")
        threading.current_thread().name = "idle_mqtt_teslamate"


def first_read_all_vehicles():
    for i, vehicle in enumerate(P.vehicles):
        name = vehicle['display_name']
        vin = vehicle['vin']
        state = vehicle['state']
        car = m.ElectricCar.find_one({m.ElectricCar.name: name})
        if car is not None:
            car.vin = vin
            car.state = state
            car.save_changed_fields(broadcast=False, persist=True)
            P.teslamate_topic = str(get_json_param(Constant.P_MQTT_TOPIC_TESLAMATE)).replace("<car_id>", str(car.id))
            P.teslamate_topic += "#"
            mqtt_io.add_message_callback(P.teslamate_topic, mqtt_on_message)
            L.l.info("Teslamate connected to mqtt topic: {}".format(P.teslamate_topic))
            vehicle_update(car.id)
        else:
            L.l.warning("Cannot find electric car = {} in config file".format(name))
        L.l.info("Tesla car {} vin={} state={}".format(name, vin, state))


def read_all_vehicles():
    L.l.info("Updating all Tesla vehicles")
    for i, vehicle in enumerate(P.vehicles):
        name = vehicle['display_name']
        car = m.ElectricCar.find_one({m.ElectricCar.name: name})
        if car is not None:
            vehicle_update(car.id)
        else:
            L.l.warning("Cannot find Tesla = {} in config file".format(name))


def thread_run():
    prctl.set_name("")
    threading.current_thread().name = "tesla"

    if P.user_charging_mode:
        read_all_vehicles()

    prctl.set_name("idle_tesla")
    threading.current_thread().name = "idle_tesla"
    return 'Processed tesla'


def unload():
    L.l.info('Tesla module unloading')
    thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    L.l.info('Tesla module initialising, current dir={}'.format(os.getcwd()))
    thread_pool.add_interval_callable(thread_run, run_interval_second=300)
    P.email = get_secure_general("tesla_account_email")
    P.home_latitude = get_secure_general("home_latitude")
    P.home_longitude = get_secure_general("home_longitude")
    P.tesla = Tesla(email=P.email, cache_file="../private_config/.credentials/tesla_cache.json", timeout=180)
    P.vehicles = P.tesla.vehicle_list()
    P.api_requests += 1
    first_read_all_vehicles()
    if len(P.vehicles) > 0:
        P.initialised = True
