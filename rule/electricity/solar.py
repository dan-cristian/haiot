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
    USER_FORCED_STOP = 5
    JOB_FINISHED = 6


class Relaydevice:
    RELAY_NAME = None
    STATE_CHANGE_INTERVAL = 30  # how often can change state
    MAX_OFF_INTERVAL = 600  # seconds, how long can stay off after job has started, if device supports breaks
    DEVICE_SUPPORTS_BREAKS = False  # can this device be started/stopped several times during the job
    AVG_CONSUMPTION = 1
    watts = None
    last_state_change = datetime.min
    state = DeviceState.NO_INIT
    power_is_on = None

    def set_power_status(self, power_is_on):
        if (self.state == DeviceState.USER_FORCED_STOP or not self.DEVICE_SUPPORTS_BREAKS) and power_is_on is False:
            # do not start the relay, as user forced a stop
            L.l.info("Not starting relay {}, state={}".format(self.RELAY_NAME, self.state))
            pass
        elif self.state == DeviceState.USER_FORCED_START and power_is_on is False:
            # do not stop the relay, as user forced a start
            L.l.info("Not stopping relay {}, state={}".format(self.RELAY_NAME, self.state))
        else:
            if self.can_state_change():
                if self.get_power_status() != power_is_on:
                    rule_common.update_custom_relay(relay_pin_name=self.RELAY_NAME, power_is_on=power_is_on)
                    self.last_state_change = datetime.now()
                else:
                    L.l.info("Relay {} state already {}, power={}".format(self.RELAY_NAME, self.state,
                                                                          self.power_is_on))
                    pass
                if power_is_on:
                    if self.state == DeviceState.NO_INIT or self.state == DeviceState.JOB_FINISHED:
                        if power_is_on:
                            self.state = DeviceState.FIRST_START
                            L.l.info("Was first relay start {}, state={}".format(self.RELAY_NAME, self.state))
                        else:
                            self.state = DeviceState.AUTO_STOP
                            L.l.info("Was auto stop relay {}, state={}".format(self.RELAY_NAME, self.state))
                    elif self.state == DeviceState.FIRST_START:
                        self.state = DeviceState.AUTO_START
                        L.l.info("Now is auto start relay {}, state={}".format(self.RELAY_NAME, self.state))
                    elif self.state == DeviceState.AUTO_STOP:
                        self.state = DeviceState.AUTO_START
                        L.l.info("Was auto start relay {}, state={}".format(self.RELAY_NAME, self.state))
                    elif self.state == DeviceState.AUTO_START:
                        # already on
                        L.l.info("Keep relay on {}, state={}".format(self.RELAY_NAME, self.state))
                        pass
                else:
                    if self.state == DeviceState.AUTO_START:
                        self.state = DeviceState.AUTO_STOP
                        L.l.info("Auto stop relay {}, state={}".format(self.RELAY_NAME, self.state))
                    else:
                        L.l.info("Unexpected state relay {}, state={}".format(self.RELAY_NAME, self.state))
            else:
                L.l.info("Not changing relay {}, state={}".format(self.RELAY_NAME, self.state))

    def get_power_status(self):
        self.power_is_on = rule_common.get_custom_relay(self.RELAY_NAME)
        if self.state == DeviceState.AUTO_STOP and self.power_is_on:
            # if user forced the device start
            self.state = DeviceState.USER_FORCED_START
        if self.state == DeviceState.AUTO_START and not self.power_is_on:
            # if user forced the device stop
            self.state = DeviceState.USER_FORCED_STOP
        return self.power_is_on

    def can_state_change(self):
        return (datetime.now() - self.last_state_change).total_seconds() >= self.STATE_CHANGE_INTERVAL

    def update_job_finished(self):
        # job is never finished for devices without power metering
        pass

    def grid_updated(self, grid_watts):
        # get relay status to check for user forced start
        power_on = self.get_power_status()
        if power_on and self.watts is not None:
            current_watts = self.watts
        else:
            current_watts = self.AVG_CONSUMPTION
        if grid_watts <= 0:
            # start device if exporting and there is enough surplus
            export = -grid_watts
            if current_watts <= export:
                self.set_power_status(power_is_on=True)
                L.l.info("Should auto start device {}, state={} surplus={}".format(self.RELAY_NAME, self.state, export))
            else:
                self.set_power_status(power_is_on=False)
                L.l.info("Should auto stop device {}, state={} surplus={}".format(self.RELAY_NAME, self.state, export))
        else:
            L.l.info("Not exporting, import={}".format(grid_watts))
            pass
        self.update_job_finished()

    def __init__(self):
        pass


class Powerdevice(Relaydevice):
    MIN_WATTS_OFF = None  # min consumption to be considered OFF / job done
    UTILITY_NAME = None
    JOB_FINISHED_DURATION = 180  # for how long the device stays on min consumption before job is finished
    last_min_watts_read = None

    # check if device has finished job
    def update_job_finished(self):
        if self.state == DeviceState.AUTO_START:
            if self.watts <= self.MIN_WATTS_OFF:
                if self.last_min_watts_read is None:
                    self.last_min_watts_read = datetime.now()
                else:
                    delta = (datetime.now() - self.last_min_watts_read).total_seconds()
                    if delta >= self.JOB_FINISHED_DURATION:
                        self.state = DeviceState.JOB_FINISHED
                        self.last_min_watts_read = None
            else:
                self.last_min_watts_read = None

    def set_watts(self, watts):
        self.watts = watts

    def __init__(self):
        Relaydevice.__init__(self)


class Dishwasher(Powerdevice):
    AVG_CONSUMPTION = 80
    MIN_WATTS_OFF = 1
    RELAY_NAME = 'plug_1'
    UTILITY_NAME = 'power plug 1'
    DEVICE_SUPPORTS_BREAKS = True
    MAX_OFF_INTERVAL = 60 * 30  # until water get's cold

    def __init__(self):
        Powerdevice.__init__(self)
        # super(Powerdevice, self).__init__()


class Washingmachine(Powerdevice):
    AVG_CONSUMPTION = 80
    MIN_WATTS_OFF = 2
    RELAY_NAME = 'plug_2'
    UTILITY_NAME = 'power plug 2'
    DEVICE_SUPPORTS_BREAKS = False
    MAX_OFF_INTERVAL = 60 * 10  # until water get's cold

    def __init__(self):
        Powerdevice.__init__(self)


class Upscharger(Relaydevice):
    AVG_CONSUMPTION = 200
    RELAY_NAME = 'beci_upscharge_relay'
    DEVICE_SUPPORTS_BREAKS = False

    def __init__(self):
        Relaydevice.__init__(self)


class P:
    grid_watts = None
    grid_importing = None
    device_list = {}  # key is utility name
    EXPORT_MIN_WATTS = -50

    @staticmethod
    # init in order of priority
    def init_dev():
        P.device_list[Dishwasher.RELAY_NAME] = Dishwasher()
        P.device_list[Washingmachine.RELAY_NAME] = Washingmachine()
        P.device_list[Upscharger.RELAY_NAME] = Upscharger()

    def __init__(self):
        pass


# energy rule
def rule_energy_export(obj=models.Utility(), field_changed_list=None):
    if field_changed_list is not None and 'units_2_delta' in field_changed_list:
        if obj.utility_name == 'power main mono':
            P.grid_watts = obj.units_2_delta
            # let all devices know grid status
            for device in P.device_list.values():
                device.grid_updated(P.grid_watts)
        else:
            # set consumption for device
            if obj.utility_name in P.device_list.keys():
                P.device_list[obj.utility_name].set_watts(obj.units_2_delta)


def init():
    P.init_dev()
