import argparse
import ssl
import threading
import prctl
from main.logger_helper import L
from main import thread_pool

from apps.tesla.TeslaPy.teslapy import Tesla
#from apps.tesla.TeslaPy import menu

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
                P.voltage = ch['charger_voltage']
                P.is_charging[idx] = ch['charging_state'] == 'Charging'
                if act_amps > 0:
                    if not P.is_charging[idx]:
                        L.l.error("I was expecting vehicle to charge")
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

    email = 'dan.cristian@gmail.com'
    P.tesla = Tesla(email=email, cache_file="../private_config/.credentials/tesla_cache.json")
    P.vehicles = P.tesla.vehicle_list()
    for i, vehicle in enumerate(P.vehicles):
        L.l.info("Tesla {} vin={} state={}".format(vehicle['display_name'], vehicle['vin'], vehicle['state']))
    if len(P.vehicles) > 0:
        P.initialised = True
