from datetime import datetime
from enum import Enum
import time
import collections
from main.logger_helper import L
from main.admin import models
from rule import rule_common
from gpio import pigpio_gpio


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
    MIN_ON_INTERVAL = 60  # how long to run before auto stop
    DEVICE_SUPPORTS_BREAKS = False  # can this device be started/stopped several times during the job
    AVG_CONSUMPTION = 1
    watts = None  # current consumption for this device
    last_state_change = datetime.min
    last_state_on = datetime.min
    state = DeviceState.NO_INIT
    power_is_on = None

    def set_power_status(self, power_is_on, exported_watts=None):
        valid_power_status = power_is_on
        if not power_is_on and self.state == DeviceState.USER_FORCED_START:
            # do not stop the relay, as user forced a start
            L.l.info("Not stopping forced start device {}, power={}".format(self.RELAY_NAME, self.is_power_on()))
            valid_power_status = None
        if not power_is_on and self.is_power_on() and not self.can_state_change():
            L.l.info("Cannot stop already started device")
            valid_power_status = None
        if not power_is_on and not self.can_stop_relay():
            L.l.info("Cannot stop device yet")
            valid_power_status = None
        if valid_power_status is not None and self.is_power_on() != valid_power_status:
            rule_common.update_custom_relay(relay_pin_name=self.RELAY_NAME, power_is_on=valid_power_status)
            self.last_state_change = datetime.now()
            if valid_power_status:
                self.last_state_on = datetime.now()

    def is_power_on(self):
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

    def can_stop_relay(self):
        delta = (datetime.now() - self.last_state_on).total_seconds()
        return delta >= self.MIN_ON_INTERVAL and self.DEVICE_SUPPORTS_BREAKS

    def update_job_finished(self):
        # job is never finished for devices without power metering
        pass

    # returns power status changes
    def grid_updated(self, grid_watts):
        changed_relay_status = False
        # get relay status to check for user forced start
        power_on = self.is_power_on()
        if grid_watts <= 0:
            # start device if exporting and there is enough surplus
            export_watts = -grid_watts
            # only trigger power on if over treshold
            if export_watts > P.MIN_WATTS_THRESHOLD and self.AVG_CONSUMPTION <= export_watts and not self.is_power_on():
                self.set_power_status(power_is_on=True, exported_watts=grid_watts)
                L.l.info("Should auto start device {} state={} consuming={} surplus={}".format(
                    self.RELAY_NAME, self.state, self.watts, export_watts))
                changed_relay_status = True
        else:
            # L.l.info("Not exporting, import={}".format(grid_watts))
            import_watts = grid_watts
            if power_on and self.watts is not None:
                current_watts = self.watts
            else:
                current_watts = self.AVG_CONSUMPTION
            # only trigger power off if over treshold
            if current_watts > P.IDLE_WATTS:
                if import_watts > P.MIN_WATTS_THRESHOLD and current_watts < grid_watts and self.is_power_on():
                    L.l.info("Should auto stop device {} state={} consuming={} surplus={}".format(
                        self.RELAY_NAME, self.state, current_watts, grid_watts))
                    self.set_power_status(power_is_on=False)
                    changed_relay_status = True
                else:
                    L.l.debug("Keep device {} consumption {} with import power {} and power_on={}".format(
                        self.RELAY_NAME, current_watts, grid_watts, self.is_power_on()))
        self.update_job_finished()
        return changed_relay_status

    def __init__(self, relay_name, avg_consumption):
        self.AVG_CONSUMPTION = avg_consumption
        self.RELAY_NAME = relay_name


class Powerdevice(Relaydevice):
    MIN_WATTS_OFF = None  # min consumption to be considered OFF / job done
    UTILITY_NAME = None
    JOB_FINISHED_DURATION = 180  # for how long the device stays on min consumption before job is finished
    last_min_watts_read = None

    # check if device has finished job
    def update_job_finished(self):
        if self.state == DeviceState.AUTO_START:
            if self.power_is_on:
                if self.watts <= self.MIN_WATTS_OFF:
                    if self.last_min_watts_read is None:
                        self.last_min_watts_read = datetime.now()
                    else:
                        delta = (datetime.now() - self.last_min_watts_read).total_seconds()
                        L.l.info("Job {} about to stop delta={}".format(self.RELAY_NAME, delta))
                        if delta >= self.JOB_FINISHED_DURATION:
                            L.l.info("Job {} finished delta={}".format(self.RELAY_NAME, delta))
                            self.state = DeviceState.JOB_FINISHED
                            self.last_min_watts_read = None
                else:
                    self.last_min_watts_read = None
            else:
                L.l.info("Warning, relay {} state is {} but power is {}".format(
                    self.RELAY_NAME, self.state, self.power_is_on))

    def set_watts(self, watts):
        self.watts = watts

    def __init__(self, relay_name, utility_name, avg_consumption):
        self.UTILITY_NAME = utility_name
        self.watts = 0  # must init to avoid stop as relay
        Relaydevice.__init__(self, relay_name, avg_consumption)


class LoadPowerDevice(Relaydevice):
    UTILITY_NAME = None
    MAX_WATTS = None

    def __init__(self, relay_name, utility_name, max_watts):
        self.UTILITY_NAME = utility_name
        self.MAX_WATTS = max_watts
        Relaydevice.__init__(self, relay_name, avg_consumption=None)  # no avg consumption for load devices


class Dishwasher(Powerdevice):
    MIN_WATTS_OFF = 1
    DEVICE_SUPPORTS_BREAKS = True
    MAX_OFF_INTERVAL = 60 * 30  # until water get's cold
    MIN_ON_INTERVAL = 120

    def __init__(self, relay_name, utility_name, avg_consumption):
        Powerdevice.__init__(self, relay_name, utility_name, avg_consumption)


class Washingmachine(Powerdevice):
    MIN_WATTS_OFF = 2
    DEVICE_SUPPORTS_BREAKS = False
    MAX_OFF_INTERVAL = 60 * 10  # until water get's cold

    def __init__(self, relay_name, utility_name, avg_consumption):
        Powerdevice.__init__(self, relay_name, utility_name, avg_consumption)


class Upscharger(Powerdevice):
    DEVICE_SUPPORTS_BREAKS = False

    def __init__(self, relay_name, utility_name=None, avg_consumption=None):
        Powerdevice.__init__(self, relay_name, utility_name, avg_consumption)


class PwmHeater(LoadPowerDevice):
    DEVICE_SUPPORTS_BREAKS = True
    max_duty = 1000000

    # override
    def set_power_status(self, power_is_on, exported_watts=None):
        L.l.info("Setting pwm {} status {} to watts level {}".format(self.RELAY_NAME, power_is_on, exported_watts))
        if power_is_on:
            assert exported_watts is not None
            required_duty = (exported_watts / self.MAX_WATTS) * self.max_duty
            pigpio_gpio.P.pwm.set(self.RELAY_NAME, duty_cycle=required_duty)
        else:
            pigpio_gpio.P.pwm.set(self.RELAY_NAME, is_started=False)

    def is_power_on(self):
        is_on, frequency, duty_cycle = pigpio_gpio.P.pwm.get(self.RELAY_NAME)
        return is_on

    def __init__(self, relay_name, utility_name, max_watts):
        LoadPowerDevice.__init__(self, relay_name, utility_name, max_watts)


class P:
    initialised = False
    grid_watts = None
    grid_importing = None
    grid_exporting = None
    device_list = collections.OrderedDict()  # key is utility name
    utility_list = {}
    MIN_WATTS_THRESHOLD = 30
    IDLE_WATTS = 10

    @staticmethod
    # init in order of priority
    def init_dev():
        relay = 'washing_relay'
        utility = 'power washing'
        obj = Washingmachine(relay_name=relay, utility_name=utility, avg_consumption=70)
        P.device_list[relay] = obj
        P.utility_list[utility] = obj
        relay = 'plug_1'
        utility = 'power plug 1'
        obj = Dishwasher(relay_name=relay, utility_name=utility, avg_consumption=80)
        P.device_list[relay] = obj
        P.utility_list[utility] = obj
        relay = 'big_battery_relay'
        P.device_list[relay] = Relaydevice(relay_name=relay, avg_consumption=50)
        relay = 'beci_upscharge_relay'
        P.device_list[relay] = Upscharger(relay_name=relay, avg_consumption=200)
        relay = 'blackwater_pump_relay'
        P.device_list[relay] = Relaydevice(relay_name=relay, avg_consumption=50)
        relay = 'boiler'
        utility = 'power boiler'
        obj = PwmHeater(relay_name=relay, utility_name=utility, max_watts=2400)
        P.device_list[relay] = obj
        P.utility_list[utility] = obj
        relay = 'boiler2'
        utility = 'power boiler'
        obj = PwmHeater(relay_name=relay, utility_name='power boiler', max_watts=2400)
        P.device_list[relay] = obj
        P.utility_list[utility] = obj

    def __init__(self):
        pass


# energy rule
def rule_energy_export(obj=models.Utility(), field_changed_list=None):
    if field_changed_list is not None and 'units_2_delta' in field_changed_list:
        if obj.utility_name == 'power main mono':
            P.grid_watts = obj.units_2_delta
            P.grid_importing = (P.grid_watts > P.MIN_WATTS_THRESHOLD)
            P.grid_exporting = (P.grid_watts < -P.MIN_WATTS_THRESHOLD)
            # let all devices know grid status and make power changes
            dev_list = []
            if P.grid_exporting:
                dev_list = P.device_list.values()
            if P.grid_importing:
                dev_list = reversed(P.device_list.values())
            for device in dev_list:
                changed = device.grid_updated(P.grid_watts)
                if changed:  # exit to allow main meter to update and recheck if more power changes are needed
                    break
        else:
            # set consumption for device
            if obj.utility_name in P.utility_list:
                inst = P.utility_list[obj.utility_name]
                if isinstance(inst, Powerdevice) and inst.UTILITY_NAME == obj.utility_name:
                    inst.set_watts(obj.units_2_delta)
                else:
                    pass


def init():
    P.init_dev()
    L.l.info("Initialised solar rules with {} devices".format(len(P.device_list)))
