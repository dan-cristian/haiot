from datetime import datetime
from enum import Enum
import time
from main.logger_helper import L
from main.admin import models
from rule import rule_common


class DeviceState(Enum):
    NO_INIT = 0
    FIRST_START = 1
    AUTO_START = 2
    AUTO_STOP = 3
    USER_FORCED_START = 4


class Relaydevice:
    RELAY_NAME = None
    STATE_CHANGE_INTERVAL = 300  # how often can change state
    last_state_change = datetime.min
    state = DeviceState.NO_INIT
    DEVICE_SUPPORTS_BREAKS = False  # can this device be started/stopped several times during the job

    def set_power_status(self, power_is_on):
        rule_common.update_custom_relay(relay_pin_name=self.RELAY_NAME, power_is_on=power_is_on)
        self.last_state_change = datetime.now()

    def get_power_status(self):
        power_is_on = rule_common.get_custom_relay(self.RELAY_NAME)
        return power_is_on

    def can_state_change(self):
        return (datetime.now() - self.last_state_change).total_seconds() > self.STATE_CHANGE_INTERVAL

    def __init__(self):
        pass


class Powerdevice(Relaydevice):
    watts = None
    MIN_WATTS_OFF = None  # min consumption to be considered OFF / job done
    UTILITY_NAME = None

    def grid_updated(self, grid_watts):
        pass

    def user_forced_start(self):
        self.state = DeviceState.USER_FORCED_START

    def set_watts(self, watts):
        self.watts = watts

    def __init__(self):
        Relaydevice.__init__(self)


class Dishwasher(Powerdevice):
    MIN_WATTS_OFF = 1
    RELAY_NAME = 'plug_1'
    UTILITY_NAME = 'power plug 1'
    DEVICE_SUPPORTS_BREAKS = True

    def __init__(self):
        Powerdevice.__init__(self)
        # super(Powerdevice, self).__init__()


class Washingmachine(Powerdevice):
    MIN_WATTS_OFF = 2
    RELAY_NAME = 'plug_2'
    UTILITY_NAME = 'power plug 2'
    DEVICE_SUPPORTS_BREAKS = False

    def __init__(self):
        Powerdevice.__init__(self)


class Upscharger(Relaydevice):
    RELAY_NAME = 'ups_charger'
    DEVICE_SUPPORTS_BREAKS = False

    def __init__(self):
        Relaydevice.__init__(self)


class P:
    grid_watts = None
    grid_importing = None
    device_list = {}  # key is utility name
    EXPORT_MIN_WATTS = -50

    # init in order of priority
    def __init__(self):
        self.device_list[Dishwasher.RELAY_NAME] = Dishwasher()
        self.device_list[Washingmachine.RELAY_NAME] = Washingmachine()
        self.device_list[Upscharger.RELAY_NAME] = Upscharger()




# will I have export without this extra load?
def _exporting(extra_load):
    if extra_load is None:
        extra_load = 0
    if P.grid_watts is not None:
        return P.grid_watts - extra_load < P.EXPORT_MIN_WATTS
    else:
        return False


# energy rule
def rule_energy_export(obj=models.Utility(), field_changed_list=None):
    if field_changed_list is not None:
        if 'units_2_delta' in field_changed_list:
            if obj.utility_name == 'power main mono':
                P.grid_watts = obj.units_2_delta
                for device in P.device_list:
                    device.grid_updated(P.grid_watts)
            else:
                if obj.utility_name in P.device_list.keys():
                    P.device_list[obj.utility_name].set_watts(obj.units_2_delta)

    return
    # if exporting
    if P.grid_watts is not None:
        if _exporting(P.plug1_watts):
            if P.grid_importing is True or P.grid_importing is None:
                L.l.info("Exporting power {}w".format(P.grid_watts))
                P.grid_importing = False
            if _can_state_change() and not P.plug1_job_started:
                L.l.info("Starting plug 1 to reduce export, grid={}".format(P.grid_watts))
                rule_common.update_custom_relay(relay_pin_name=P.RELAY_1_NAME, power_is_on=True)
                P.last_state_change = datetime.now()
                # P.plug1_auto_stopped = False
                P.plug1_job_started = True
                return
        else:
            if P.grid_importing is False or P.grid_importing is None:
                L.l.info("Importing power {}w".format(P.grid_watts))
                P.grid_importing = True
            if P.plug1_watts is not None and P.plug1_watts > P.PLUG1_MIN_WATTS_ON and _can_state_change():
                power_is_on = rule_common.get_custom_relay(P.RELAY_1_NAME)
                if P.plug1_auto_stopped is True:
                    if power_is_on:
                        L.l.info("Plug1 started, probably overriden by user, plug {}w, grid {}w".format(
                            P.plug1_watts, P.grid_watts))
                        # to supress above info messages
                        P.last_state_change = datetime.now()
                    else:
                        # all ok, plug is stopped, power is off, saving!
                        pass
                else:
                    L.l.info("Stopping plug1 to cut import, plug {}w, grid {}w".format(
                        P.plug1_watts, P.grid_watts))
                    time.sleep(10)
                    rule_common.update_custom_relay(relay_pin_name=P.RELAY_1_NAME, power_is_on=False)
                    P.plug1_auto_stopped = True
                    P.last_state_change = datetime.now()
            # reset user override when done to enable automatic switch
            # fixme: min watts might go below in the process, check multiple values. enters here after plug start, avoid!
            if P.plug1_job_started and P.plug1_watts is not None and P.plug1_watts <= P.PLUG1_MIN_WATTS_OFF:
                P.plug1_auto_stopped = False
                L.l.info("Plug1 no more consumption, job done, plug {}w, grid {}w".format(P.plug1_watts, P.grid_watts))
                P.plug1_job_started = False
