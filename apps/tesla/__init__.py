import threading
import prctl
from datetime import datetime
from main.logger_helper import L
from main import thread_pool
from storage.model import m
from apps.tesla.TeslaPy.teslapy import Tesla
from common import Constant, get_secure_general, utils, get_json_param
from transport import mqtt_io

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


class P:
    initialised = False
    tesla = None
    vehicles = None
    voltage = 220  # default one
    max_amps = 16
    api_requests = 0
    refresh_request_pause = 30  # seconds between each status update request
    stop_charge_interval = 60  # seconds interval with amps set to 0 after which charging is stopped
    last_refresh_request = datetime.min
    user_charging_mode = False  # True is user started the charging, so don't run automatic charging setup
    home_latitude = None
    home_longitude = None
    can_charge_at_home = False  # True if car is at home, so automatic charging can happen
    teslamate_topic = None
    teslamate_can_charge = False  # do not trigger automatic charging, car maybe not be at home etc
    teslamate_charging_amp = dict()
    teslamate_last_charging_update = datetime.min
    teslamate_voltage = dict()
    # save car params
    is_charging = dict()
    charging_amp = dict()
    car_latitude = dict()
    car_longitude = dict()
    car_state = dict()
    last_charging_stopped = dict()  # timestamps when car charging was stopped

    def __init__(self):
        pass


def can_refresh():
    return (datetime.now() - P.last_refresh_request).total_seconds() >= P.refresh_request_pause


def can_auto_charge():
    return (not P.user_charging_mode) and P.can_charge_at_home


def vehicle_valid(car_id):
    if P.vehicles is None or len(P.vehicles) <= (car_id - 1):  # first id can be 1
        L.l.error("Vehicle id not on list or list is empty")
        return False
    else:
        return True


def should_stop_charge(car_id):
    if car_id not in P.last_charging_stopped.keys() or P.last_charging_stopped[car_id] is None \
            or not is_charging(car_id):
        return False
    else:
        return (datetime.now() - P.last_charging_stopped[car_id]).total_seconds() > P.stop_charge_interval


def set_charging_amps(amps, car_id=1):
    if vehicle_valid(car_id):
        P.vehicles[car_id - 1].command('CHARGING_AMPS', charging_amps=amps)
        P.charging_amp[car_id] = amps
        P.api_requests += 1
        if amps == 0:
            if P.last_charging_stopped[car_id] is None:  # only update if previously was charging
                P.last_charging_stopped[car_id] = datetime.now()
        else:
            P.last_charging_stopped[car_id] = None  # reset timestamp


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
        return None

    P.last_charging_stopped[car_id] = None
    vehicle = P.vehicles[car_id - 1]
    try:
        P.car_state[car_id] = vehicle['state']
        if vehicle['state'] in ['asleep', 'offline']:
            vehicle.sync_wake_up()
            P.api_requests += 1
        if vehicle['state'] == 'online':
            vehicle_data = vehicle.get_vehicle_data()
            P.api_requests += 1
            P.last_refresh_request = datetime.now()
            ch = vehicle_data['charge_state']
            charging_mode = ch['scheduled_charging_mode']
            P.user_charging_mode = ch['user_charge_enable_request']
            L.l.info('User charging request={}, mode={}'.format(P.user_charging_mode, charging_mode))
            if P.user_charging_mode:
                L.l.info("Manual override detected, car will not stop charging")
            act_amps = ch['charger_actual_current']
            P.charging_amp[car_id] = act_amps
            act_voltage = ch['charger_voltage']
            if act_voltage > 0:
                P.voltage = act_voltage
            P.is_charging[car_id] = (ch['charging_state'] == 'Charging')

            L.l.info("Car charging status = {}".format(ch['charging_state']))
            L.l.info("Car charging amp = {}".format(act_amps))
            if act_amps > 0:
                if not P.is_charging[car_id]:
                    L.l.error("I was expecting vehicle to charge")
            car = m.ElectricCar.find_one({m.ElectricCar.id: car_id})
            if car is not None:
                car.charger_current = act_amps
                if act_voltage is not None:
                    car.actual_voltage = act_voltage
                car.is_charging = P.is_charging[car_id]
                car.save_changed_fields(broadcast=False, persist=True)
            ds = vehicle_data['drive_state']
            if ds is not None:
                P.car_latitude[car_id] = ds['latitude']
                P.car_longitude[car_id] = ds['longitude']
                if (abs(P.home_latitude - P.car_latitude[1]) < 0.0002) \
                        and (abs(P.home_longitude - P.car_longitude[1]) < 0.0002):
                    P.can_charge_at_home = True
                else:
                    P.can_charge_at_home = False
            return act_amps
        else:
            L.l.error("Vehicle not online, state={}".format(vehicle['state']))
    except Exception as ex:
        L.l.error("Unable to get vehicle charging data, #API{}, er={}".format(P.api_requests, ex))
        P.last_refresh_request = datetime.now()
        P.vehicles = P.tesla.vehicle_list()


def get_nonzero_voltage():
    return P.voltage


def get_voltage(car_id=1):
    if car_id in P.teslamate_voltage.keys():
        return P.teslamate_voltage[car_id]
    else:
        return None


def is_charging(car_id=1):
    voltage = get_voltage(car_id)
    if voltage is not None:
        return P.teslamate_voltage[car_id] > 0
    else:
        return None

    # if car_id in P.is_charging.keys():
    #    return P.is_charging[car_id]
    # else:
    #    L.l.warning("Cannot find charging flag for id {}".format(car_id))
    #    return None


def stop_charge(car_id=1):
    if vehicle_valid(car_id):
        L.l.info("Stopping tesla charging")
        P.vehicles[car_id - 1].command('STOP_CHARGE')
        P.is_charging[car_id] = False
        P.last_charging_stopped[car_id] = None
        P.api_requests += 1


def start_charge(car_id=1):
    if vehicle_valid(car_id):
        L.l.info("Starting tesla charging")
        P.vehicles[car_id - 1].command('START_CHARGE')
        P.api_requests += 1


# https://docs.teslamate.org/docs/integrations/mqtt/
def _process_message(msg):
    car_id = int(msg.topic.split("teslamate/cars/")[1][:2].replace("/", ""))
    if "plugged_in" in msg.topic:
        value = msg.payload
    if "charger_actual_current" in msg.topic:
        value = int(msg.payload)
        P.teslamate_charging_amp[car_id] = value
        P.teslamate_last_charging_update = datetime.now()
    if "charger_power" in msg.topic:
        value = int(msg.payload)
        P.is_charging[car_id] = (value == 1)
    if "charger_voltage" in msg.topic:
        value = int(msg.payload)
        P.teslamate_voltage[car_id] = value
        if value > 0:
            P.voltage = value
    if "state" in msg.topic:
        value = "{}".format(msg.payload).replace("b", "").replace("\\", "").replace("'", "")
        P.car_state[car_id] == value
        # online, asleep, charging
    if "geofence" in msg.topic:
        value = "{}".format(msg.payload).replace("b", "").replace("\\", "").replace("'", "")
        P.teslamate_can_charge = (value.lower() == "home")
    if "battery_level" in msg.topic:
        value = int(msg.payload)



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
        L.l.info("Electric car {} vin={} state={}".format(name, vin, state))


def read_all_vehicles():
    L.l.info("Updating all Tesla vehicles")
    for i, vehicle in enumerate(P.vehicles):
        name = vehicle['display_name']
        car = m.ElectricCar.find_one({m.ElectricCar.name: name})
        if car is not None:
            vehicle_update(car.id)
        else:
            L.l.warning("Cannot find car = {} in config file".format(name))


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
    L.l.info('Tesla module initialising')
    thread_pool.add_interval_callable(thread_run, run_interval_second=300)
    email = get_secure_general("tesla_account_email")
    P.home_latitude = get_secure_general("home_latitude")
    P.home_longitude = get_secure_general("home_longitude")
    P.tesla = Tesla(email=email, cache_file="../private_config/.credentials/tesla_cache.json", timeout=30)
    P.vehicles = P.tesla.vehicle_list()
    P.api_requests += 1
    first_read_all_vehicles()
    if len(P.vehicles) > 0:
        P.initialised = True
