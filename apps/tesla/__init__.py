import threading
import prctl
from main.logger_helper import L
from main import thread_pool
from storage.model import m
from apps.tesla.TeslaPy.teslapy import Tesla
from common import Constant, get_secure_general


__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


class P:
    initialised = False
    tesla = None
    vehicles = None
    voltage = 220  # default one
    max_amps = 16
    is_charging = dict()

    def __init__(self):
        pass


def vehicle_valid(idx):
    if P.vehicles is None or len(P.vehicles) <= idx:
        L.l.error("Vehicle id not on list or list is empty")
        return False
    else:
        return True


def set_charging_amps(amps, idx=0):
    if vehicle_valid(idx):
        P.vehicles[idx].command('CHARGING_AMPS', charging_amps=amps)


def get_actual_charging_amps(idx=0):
    if vehicle_valid(idx):
        vehicle = P.vehicles[idx]
        try:
            if vehicle['state'] == 'asleep':
                vehicle.sync_wake_up()
            if vehicle['state'] == 'online':
                vehicle_data = vehicle.get_vehicle_data()
                ch = vehicle_data['charge_state']
                act_amps = ch['charger_actual_current']
                act_voltage = ch['charger_voltage']
                if act_voltage is not None:
                    P.voltage = act_voltage
                P.is_charging[idx] = ch['charging_state'] == 'Charging'
                if act_amps > 0:
                    if not P.is_charging[idx]:
                        L.l.error("I was expecting vehicle to charge")
                car = m.ElectricCar.find_one({m.ElectricCar.id: idx})
                if car is not None:
                    car.charger_current = act_amps
                    if act_voltage is not None:
                        car.actual_voltage = act_voltage
                    car.is_charging = P.is_charging[idx]
                    car.save_changed_fields(broadcast=False, persist=True)
                return act_amps
            else:
                L.l.error("Vehicle not online, state={}".format(vehicle['state']))
        except Exception as ex:
            L.l.error("Unable to get vehicle charging data, er={}".format(ex))
    return None


def get_voltage():
    return P.voltage


def is_charging(idx):
    if idx in P.is_charging.keys():
        return P.is_charging[idx]
    else:
        return None


def stop_charge(idx=0):
    if vehicle_valid(idx):
        L.l.info("Stopping tesla charging")
        P.vehicles[idx].command('STOP_CHARGE')


def start_charge(idx=0):
    if vehicle_valid(idx):
        L.l.info("Starting tesla charging")
        P.vehicles[idx].command('START_CHARGE')


def thread_run():
    prctl.set_name("")
    threading.current_thread().name = "tesla"
    #
    prctl.set_name("idle_tesla")
    threading.current_thread().name = "idle_tesla"
    return 'Processed tesla'


def unload():
    L.l.info('Tesla module unloading')
    thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    L.l.info('Tesla module initialising')
    thread_pool.add_interval_callable(thread_run, run_interval_second=60)
    email = get_secure_general("tesla_account_email")
    P.tesla = Tesla(email=email, cache_file="../private_config/.credentials/tesla_cache.json")
    P.vehicles = P.tesla.vehicle_list()
    for i, vehicle in enumerate(P.vehicles):
        name = vehicle['display_name']
        vin = vehicle['vin']
        state = vehicle['state']
        car = m.ElectricCar.find_one({m.ElectricCar.name: name})
        if car is not None:
            car.vin = vin
            car.state = state
            car.save_changed_fields(broadcast=False, persist=True)
        else:
            L.l.warning("Cannot find electric car = {} in config file".format(name))
        L.l.info("Electric car {} vin={} state={}".format(name, vin, state))
    if len(P.vehicles) > 0:
        P.initialised = True
