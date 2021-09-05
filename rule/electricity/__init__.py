from datetime import datetime
from enum import Enum
import collections
import random
import sys
from main.logger_helper import L
from rule import rule_common
import rule
from gpio import pigpio_gpio
from storage.model import m


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
    STATE_CHANGE_INTERVAL = 30  # how often can change state, in seconds
    MAX_OFF_INTERVAL = 600  # seconds, how long can stay off after job has started, if device supports breaks
    MIN_ON_INTERVAL = 60  # how long to run before auto stop, in seconds
    DEVICE_SUPPORTS_BREAKS = False  # can this device be started/stopped several times during the job
    AVG_CONSUMPTION = 1
    JOB_DURATION = 3600 * 4  # max duration if device does not support breaks
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
            L.l.info("Cannot stop already started device {}".format(self.RELAY_NAME))
            valid_power_status = None
        if not power_is_on and not self.can_stop_relay():
            L.l.info("Cannot stop device {} yet".format(self.RELAY_NAME))
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
        return delta >= self.MIN_ON_INTERVAL and (self.DEVICE_SUPPORTS_BREAKS or delta >= self.JOB_DURATION)

    def update_job_finished(self):
        # job is never finished for devices without power metering
        pass

    def set_watts(self, watts):
        self.watts = watts

    # returns power status changes
    def grid_updated(self, grid_watts):
        changed_relay_status = False
        # get relay status to check for user forced start
        power_on = self.is_power_on()
        if grid_watts <= 0:
            # start device if exporting and there is enough surplus
            export_watts = -grid_watts
            # only trigger power on if over treshold
            if export_watts > P.MIN_WATTS_THRESHOLD and self.AVG_CONSUMPTION <= export_watts and not power_on:
                self.set_power_status(power_is_on=True, exported_watts=export_watts)
                L.l.info("Starting relay {} state={} consuming={} surplus={}".format(
                    self.RELAY_NAME, self.state, self.watts, export_watts))
                changed_relay_status = True
            else:
                # L.l.info('No action {} on export watts {} thresh {} avg_cons {} power_on {}'.format(
                #    self.RELAY_NAME, export_watts, P.MIN_WATTS_THRESHOLD, self.AVG_CONSUMPTION, power_on))
                pass
        else:
            # L.l.info("Not exporting, import={}".format(grid_watts))
            import_watts = grid_watts
            if power_on and self.watts is not None:
                current_watts = self.watts
            else:
                # pwm device has no AVG consumption so check for none below
                current_watts = self.AVG_CONSUMPTION
            # only trigger power off if over treshold.
            if current_watts is not None:
                if current_watts > P.IDLE_WATTS:
                    if import_watts > P.MIN_WATTS_THRESHOLD and power_on:
                        L.l.info("Stopping relay {} state={} consuming={} surplus={}".format(
                            self.RELAY_NAME, self.state, current_watts, grid_watts))
                        self.set_power_status(power_is_on=False)
                        changed_relay_status = True
                    else:
                        # L.l.info("Keep device {} consumption {} import power {} power_on={} thresh {}".format(
                        #    self.RELAY_NAME, current_watts, grid_watts, power_on, P.MIN_WATTS_THRESHOLD))
                        pass
                else:
                    L.l.info('No change as watts {} are in idle zone {}'.format(current_watts, P.IDLE_WATTS))
            else:
                L.l.info('Current watts on import is None for device {}'.format(self))
        self.update_job_finished()
        return changed_relay_status

    def __init__(self, relay_name, relay_id, avg_consumption, supports_breaks=False):
        self.AVG_CONSUMPTION = avg_consumption
        self.RELAY_NAME = relay_name
        self.RELAY_ID = relay_id
        self.DEVICE_SUPPORTS_BREAKS = supports_breaks


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

    def __init__(self, relay_name, relay_id, utility_name, avg_consumption):
        self.UTILITY_NAME = utility_name
        self.watts = 0  # must init to avoid stop as relay
        Relaydevice.__init__(self, relay_name, relay_id, avg_consumption)


class LoadPowerDevice(Relaydevice):
    UTILITY_NAME = None
    MAX_WATTS = None

    def __init__(self, relay_name, relay_id, utility_name, max_watts):
        self.UTILITY_NAME = utility_name
        self.MAX_WATTS = max_watts
        Relaydevice.__init__(self, relay_name, relay_id, avg_consumption=None)  # no avg consumption for load devices


class Dishwasher(Powerdevice):
    MIN_WATTS_OFF = 1
    DEVICE_SUPPORTS_BREAKS = True
    MAX_OFF_INTERVAL = 60 * 30  # until water get's cold
    MIN_ON_INTERVAL = 120

    def __init__(self, relay_name, utility_name, avg_consumption):
        relay_id = None
        Powerdevice.__init__(self, relay_name, relay_id, utility_name, avg_consumption)


class Washingmachine(Powerdevice):
    MIN_WATTS_OFF = 2
    DEVICE_SUPPORTS_BREAKS = False
    MAX_OFF_INTERVAL = 60 * 10  # until water get's cold

    def __init__(self, relay_name, utility_name, avg_consumption):
        relay_id = None
        Powerdevice.__init__(self, relay_name, relay_id, utility_name, avg_consumption)


class Upscharger(Powerdevice):
    DEVICE_SUPPORTS_BREAKS = False

    def __init__(self, relay_name, utility_name=None, avg_consumption=None):
        Powerdevice.__init__(self, relay_name, None, utility_name, avg_consumption)


class PwmHeater(LoadPowerDevice):
    DEVICE_SUPPORTS_BREAKS = True
    max_duty = 100  # set actual duty on receiving devices so use percentages here
    frequency = None

    # override
    def set_power_status(self, power_is_on, pwm_watts=None):
        # L.l.info("Setting pwm {} status {} to watts level {}".format(self.RELAY_NAME, power_is_on, pwm_watts))
        if power_is_on:
            adjust = 1
            required_duty = int(adjust * self.max_duty * pwm_watts / self.MAX_WATTS)
            if required_duty > self.max_duty:
                L.l.warning('Capping incorrect duty {} watts={} max_duty={} max_watt={} '.format(
                    required_duty, pwm_watts, self.max_duty, self.MAX_WATTS))
                required_duty = self.max_duty
            pwm_watts = min(pwm_watts, self.MAX_WATTS)
            pwm = pigpio_gpio.P.pwm.set(
                self.RELAY_NAME, duty_cycle=required_duty, frequency=self.frequency, target_watts=pwm_watts)
            self.target_watts = pwm_watts
            L.l.info('Just set power to freq={} duty={} target={}'.format(pwm.frequency, pwm.duty_cycle, pwm_watts))
        else:
            pigpio_gpio.P.pwm.set(self.RELAY_NAME, duty_cycle=0, target_watts=0)
            self.target_watts = 0

    def is_power_on(self):
        if pigpio_gpio.P.pwm is not None:
            frequency, duty_cycle = pigpio_gpio.P.pwm.get(self.RELAY_NAME)
            if duty_cycle is None:
                duty_cycle = 0
            # L.l.info('Pwm frequency={} duty={} is_on={}'.format(frequency, duty_cycle, duty_cycle > 0))
            return duty_cycle > 0
            # not used
        return None

    def grid_updated(self, grid_watts):
        power_on = self.is_power_on()
        if self.target_watts is None:
            current_watts = 0
        else:
            current_watts = self.target_watts

        # if grid_watts > 0:  # for debug only
        #    export = grid_watts  # for debug only
        #    new_target = export  # for debug only

        if grid_watts <= 0:
            export = -grid_watts
            new_target = export + self.target_watts
            L.l.info('Adjusting PWM to delta export={}, total target={}'.format(export, new_target))
            self.set_power_status(power_is_on=True, pwm_watts=new_target)
        else:
            import_watts = grid_watts
            delta = current_watts - import_watts
            if delta < 0:
                # if power_on:
                # L.l.info('Need to stop, importing {} PWM with delta={}'.format(import_watts, delta))
                self.set_power_status(power_is_on=False)
            else:
                new_target = current_watts - delta
                L.l.info('Need to adjust down PWM on import {} to {} with delta={}'.format(
                    import_watts, new_target, delta))
                self.set_power_status(power_is_on=True, pwm_watts=delta)
        return True

    def __init__(self, relay_name, relay_id, utility_name, max_watts, frequency):
        LoadPowerDevice.__init__(self, relay_name, relay_id, utility_name, max_watts)
        self.frequency = frequency
        self.target_watts = 0


class P:
    initialised = False
    grid_watts = None
    grid_importing = None
    grid_exporting = None
    device_list = collections.OrderedDict()  # key is utility name
    utility_list = {}
    MIN_WATTS_THRESHOLD = 70
    IDLE_WATTS = 10
    emulate_export = False # used to test export energy scenarios

    @staticmethod
    # init in order of priority
    def init_dev():
        # pwm = m.Pwm.find_one({m.Pwm.name: "boiler"})
        # freq = pwm.frequency
        if P.emulate_export:
            if False:
                relay = 'boiler2'
                utility = 'power boiler'
                obj = PwmHeater(relay_name=relay, relay_id=4, utility_name='power boiler', max_watts=2400,
                                frequency=freq)
                P.device_list[relay] = obj
                P.utility_list[utility] = obj

            if False:
                relay = 'boiler'
                utility = 'power boiler'
                obj = PwmHeater(relay_name=relay, relay_id=3, utility_name=utility, max_watts=2400, frequency=freq)
                P.device_list[relay] = obj
                P.utility_list[utility] = obj

        relay = 'batterycharger_relay'
        P.device_list[relay] = Relaydevice(relay_name=relay, relay_id=None, avg_consumption=400, supports_breaks=True)
        # P.device_list[relay] = obj
        # P.utility_list[utility] = obj
        #relay = 'plug_1'
        #utility = 'power plug 1'
        # obj = Dishwasher(relay_name=relay, utility_name=utility, avg_consumption=80)
        # P.device_list[relay] = obj
        # P.utility_list[utility] = obj
        #relay = 'big_battery_relay'
        #P.device_list[relay] = Relaydevice(relay_name=relay, relay_id=None, avg_consumption=50, supports_breaks=True)
        #relay = 'beci_upscharge_relay'
        #P.device_list[relay] = Upscharger(relay_name=relay, avg_consumption=200)
        #relay = 'blackwater_pump_relay'
        #P.device_list[relay] = Relaydevice(relay_name=relay, relay_id=None, avg_consumption=50, supports_breaks=True)

        if not P.emulate_export:
            if False:
                relay = 'boiler2'
                utility = 'power boiler'
                obj = PwmHeater(relay_name=relay, relay_id=4, utility_name='power boiler', max_watts=2400,
                                frequency=freq)
                P.device_list[relay] = obj
                P.utility_list[utility] = obj

            # relay = 'boiler'
            #utility = 'power boiler'

            # obj = PwmHeater(relay_name=relay, relay_id=3, utility_name=utility, max_watts=2400, frequency=freq)
            # P.device_list[relay] = obj
            # P.utility_list[utility] = obj

    def __init__(self):
        pass


def _update_devices():
    if P.grid_watts is not None:
        P.grid_importing = (P.grid_watts > P.MIN_WATTS_THRESHOLD)
        P.grid_exporting = (P.grid_watts < -P.MIN_WATTS_THRESHOLD)
        # let all devices know grid status and make power changes
        dev_list = []
        if P.grid_exporting:
            dev_list = P.device_list.values()
        elif P.grid_importing:
            dev_list = reversed(P.device_list.values())
        for device in dev_list:
            changed = device.grid_updated(P.grid_watts)
            if changed:  # exit to allow main meter to update and recheck if more power changes are needed
                # L.l.info('Done change action for device {}'.format(device))
                if P.emulate_export is True:
                    break
                else:
                    break


# energy rule
def rule_energy_export(obj=m.PowerMonitor(), change=None):
    if change is not None and 'power' in change:
        if obj.name == 'main l1':
            if P.emulate_export is True:
                P.grid_watts = random.randint(-800, -300)
            else:
                P.grid_watts = obj.power
            # L.l.info('Got rule main watts {}'.format(P.grid_watts))
            _update_devices()
    else:
        #L.l.info('Got alternate power {} change={}'.format(obj, change))
        pass


def rule_energy_utility(obj=m.Utility(), change=None):
    if change is not None and 'units_2_delta' in change:
        if obj.utility_name != 'power main mono':
            # L.l.info('Got energy utility {}'.format(obj.utility_name))
            if obj.utility_name in P.utility_list:
                inst = P.utility_list[obj.utility_name]
                if isinstance(inst, Relaydevice) and inst.UTILITY_NAME == obj.utility_name:
                    # set consumption for device
                    inst.set_watts(obj.units_2_delta)
                else:
                    L.l.info('Discarding utility {}, not relevant'.format(obj.utility_name))


def init():
    P.emulate_export = False
    P.init_dev()
    current_module = sys.modules[__name__]
    rule.init_sub_rule(thread_run_func=None, rule_module=current_module)
    L.l.info("Initialised solar rules with {} devices".format(len(P.device_list)))
