from datetime import datetime
from enum import Enum
import collections
import random
import sys
import apps.tesla
from main.logger_helper import L
from rule import rule_common
import rule
from gpio import pigpio_gpio
from storage.model import m
import math


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
    STATE_CHANGE_INTERVAL = 1  # how often can change state, in seconds
    MAX_OFF_INTERVAL = 600  # seconds, how long can stay off after job has started, if device supports breaks
    MIN_ON_INTERVAL = 1  # how long to run before auto stop, in seconds
    DEVICE_SUPPORTS_BREAKS = False  # can this device be started/stopped several times during the job
    AVG_CONSUMPTION = 1
    JOB_DURATION = 3600 * 4  # max duration if device does not support breaks
    watts = None  # current consumption for this device
    last_state_change = datetime.min
    last_state_on = datetime.min
    state = DeviceState.NO_INIT
    power_is_on = None

    def power_status_changed(self):
        P.system_wait_time = self.STATE_CHANGE_INTERVAL  # signal to wider system that it needs to wait
        P.last_state_change = datetime.now()

    def set_power_status(self, power_is_on, exported_watts=None):
        valid_power_status = power_is_on
        if not power_is_on and self.state == DeviceState.USER_FORCED_START:
            # do not stop the relay, as user forced a start
            L.l.info("Not stopping forced start device {}, power={}".format(self.RELAY_NAME, self.is_power_on()))
            valid_power_status = None
        if not power_is_on and self.is_power_on() and not self.can_state_change():
            L.l.info("Cannot stop already started device {}, breaks={}".format(
                self.RELAY_NAME, self.DEVICE_SUPPORTS_BREAKS))
            valid_power_status = None
        if not power_is_on and not self.can_stop_relay():
            L.l.info("Cannot stop device {} yet, breaks={}".format(self.RELAY_NAME, self.DEVICE_SUPPORTS_BREAKS))
            valid_power_status = None
        if valid_power_status is not None and self.is_power_on() != valid_power_status:
            rule_common.update_custom_relay(relay_pin_name=self.RELAY_NAME, power_is_on=valid_power_status)
            self.last_state_change = datetime.now()
            self.power_status_changed()
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
        # job is never finished for devices without power meteringtrue
        pass

    def set_watts(self, watts):
        self.watts = watts

    # returns power status changes
    def grid_updated(self, grid_watts):
        changed_relay_status = False
        # get relay status to check for user forced start
        power_on = self.is_power_on()
        if power_on is None:
            # assume charger is on fixme read real status
            power_on = False
        if grid_watts <= 0:
            # start device if exporting and there is enough surplus
            export_watts = -grid_watts
            # only trigger power on if over treshold
            if export_watts > P.MIN_WATTS_THRESHOLD \
                    and self.AVG_CONSUMPTION <= (export_watts + P.MIN_WATTS_THRESHOLD) and not power_on:
                L.l.info("Starting relay {} state={} consuming={} surplus={}".format(
                    self.RELAY_NAME, self.state, self.watts, export_watts))
                self.set_power_status(power_is_on=True, exported_watts=export_watts)
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
                        L.l.info("Stopping relay {} state={} consuming={} surplus={} import={} min_w={}".format(
                            self.RELAY_NAME, self.state, current_watts, grid_watts, import_watts,
                            P.MIN_WATTS_THRESHOLD))
                        self.set_power_status(power_is_on=False)
                        changed_relay_status = True
                    else:
                        # L.l.info("Keep device {} consumption {} import power {} power_on={} thresh {}".format(
                        #    self.RELAY_NAME, current_watts, grid_watts, power_on, P.MIN_WATTS_THRESHOLD))
                        pass
                else:
                    # L.l.info('No change as watts {} are in idle zone {}'.format(current_watts, P.IDLE_WATTS))
                    pass
            else:
                L.l.info('Current watts on import is None for device {}'.format(self))
        self.update_job_finished()
        return changed_relay_status

    def __init__(self, relay_name, avg_consumption, relay_id=None, supports_breaks=False, min_on_interval=1,
                 state_change_interval=1):
        self.AVG_CONSUMPTION = avg_consumption
        self.RELAY_NAME = relay_name
        self.RELAY_ID = relay_id
        self.DEVICE_SUPPORTS_BREAKS = supports_breaks
        self.MIN_ON_INTERVAL = min_on_interval
        self.STATE_CHANGE_INTERVAL = state_change_interval


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


class InverterRelay(Relaydevice):
    pass


class BatteryCharger(Relaydevice):
    voltage_sensor_name = None
    voltage_max_limit = None
    voltage_max_floor = None
    voltage_max_peak_reached = False

    def __init__(self, relay_name, avg_consumption, supports_breaks, min_on_interval, state_change_interval,
                 voltage_sensor_name, voltage_max_limit, voltage_max_floor):
        Relaydevice.__init__(self, relay_name=relay_name, supports_breaks=supports_breaks,
                             min_on_interval=min_on_interval,
                             state_change_interval=state_change_interval, avg_consumption=avg_consumption)
        self.voltage_max_limit = voltage_max_limit
        self.voltage_sensor_name = voltage_sensor_name
        self.voltage_max_floor = voltage_max_floor

    def grid_updated(self, grid_watts):
        voltage_sensor = m.PowerMonitor.find_one({m.PowerMonitor.name: self.voltage_sensor_name})
        if voltage_sensor is None:
            L.l.warning("Could not find voltage sensor {} for battery charger {}".format(
                self.voltage_sensor_name, self.RELAY_NAME))
        if voltage_sensor is not None and voltage_sensor.voltage is not None:
            if voltage_sensor.voltage > self.voltage_max_limit:
                L.l.info("Reached max voltage {} for battery charger {}, stop charge".format(
                    voltage_sensor.voltage, self.RELAY_NAME))
                self.voltage_max_peak_reached = True
                super().set_power_status(power_is_on=False)
                # stop battery charging, peak reached. allow for resting
                # allow turn off for other devices
                return False
            elif voltage_sensor.voltage <= self.voltage_max_floor:
                # battery discharged under resting floor, can restart charging
                # L.l.info("Battery charger {} discharged under max, continue".format(self.RELAY_NAME))
                self.voltage_max_peak_reached = False
                # skip any actions if the charger is currently charging a critical cell (otherwise it will stop charge)
                if P.bms_cell_critical_charge_recovery_started and self.RELAY_NAME == P.critical_charger_name:
                    # skip charger actions
                    L.l.info("Keeping charger on as cell level is still critical, voltage={}".format(
                        voltage_sensor.voltage))
                    return False
                else:
                    return super().grid_updated(grid_watts)
            else:
                # not fully charged but over max floor
                if not self.voltage_max_peak_reached:
                    L.l.info("Battery charger {} full not reached, continue".format(self.RELAY_NAME))
                    return super().grid_updated(grid_watts)
                else:
                    # peak voltage was reached
                    # battery is resting, don't do anything
                    L.l.info("Battery charger {} is resting, nothing to do".format(self.RELAY_NAME))
                    return False
        else:
            # not enough voltage data, assume needs charging
            return super().grid_updated(grid_watts)


class TeslaCharger(Relaydevice):
    vehicle_id = None
    DEBUG = True

    def __init__(self, relay_name, vehicle_id, state_change_interval):
        self.vehicle_id = vehicle_id
        Relaydevice.__init__(self, relay_name=relay_name, avg_consumption=220,
                             state_change_interval=state_change_interval)

    def grid_updated(self, grid_watts):
        P.thread_pool_status = "Tesla grid_updated start"
        act_amps = apps.tesla.get_last_charging_amps(self.vehicle_id)
        if act_amps is None:
            act_amps = 0
        tesla_charging_watts = act_amps * apps.tesla.get_nonzero_voltage()

        if not apps.tesla.can_auto_charge(self.vehicle_id) or apps.tesla.is_battery_full():
            if act_amps > 0:
                L.l.info("Exit Tesla charge control, can_auto_charge={}, full={}".format(
                    apps.tesla.can_auto_charge(self.vehicle_id), apps.tesla.is_battery_full()))
            return False

        if grid_watts > 0:
            # consuming from grid
            P.thread_pool_status = "Tesla grid_updated we have grid consumption"
            if act_amps > 0:
                # reduce tesla charging to reduce grid energy usage
                target_watts = max(tesla_charging_watts - grid_watts, 0)
                # using floor rounding to always export
                target_amps = math.floor(target_watts / apps.tesla.get_nonzero_voltage())
                if target_amps != act_amps:
                    # fixme: detect when user started charging from app and don't stop charging
                    L.l.info("Reducing Tesla charging from {} to {} Amps".format(act_amps, target_amps))
                    P.thread_pool_status = 'tesla.set_charging_amps 1'
                    if apps.tesla.set_charging_amps(target_amps):
                        self.power_status_changed()
                        return True
                else:
                    if TeslaCharger.DEBUG:
                        L.l.info("Tesla target-1 amp={}, act_amp={}".format(target_amps, act_amps))
            else:
                # nothing to do to reduce grid power consumption. stop charging after staying for too long on 0 charge
                if apps.tesla.should_stop_charge(self.vehicle_id):
                    P.thread_pool_status = 'tesla.stop_charge'
                    apps.tesla.stop_charge(self.vehicle_id)
                # is_charging = apps.tesla.is_charging(self.vehicle_id)
                # if is_charging:
                #    L.l.info("Car is charging, stopping")
                #    apps.tesla.stop_charge(self.vehicle_id)
                #pass
        else:
            # exporting to grid, need to increase charging amps
            P.thread_pool_status = "Tesla grid_updated grid export"
            # check if charging is started before changing amps
            if not apps.tesla.is_charging(self.vehicle_id):
                #fixme do not start charging if car is disconnected from plug
                P.thread_pool_status = 'tesla.start_charge 3'
                res = apps.tesla.start_charge(self.vehicle_id)
                if not res:
                    if TeslaCharger.DEBUG:
                        L.l.info("Tesla cannot start charging")
                    return False

            if act_amps == apps.tesla.P.MAX_AMP:
                L.l.info("Tesla already charging at max amps {}, battery_full={}".format(act_amps,
                                                                                         apps.tesla.is_battery_full()))
                # force charge start
                P.thread_pool_status = 'tesla.start_charge 1'
                apps.tesla.start_charge(self.vehicle_id)
                return False
            else:
                target_watts = tesla_charging_watts - grid_watts
                # using floor round down
                target_amps = math.floor(target_watts / apps.tesla.get_nonzero_voltage())
                if act_amps == 0:
                    if not apps.tesla.is_charging(self.vehicle_id):
                        P.thread_pool_status = 'tesla.start_charge 2'
                        res = apps.tesla.start_charge(self.vehicle_id)
                        L.l.info("Tesla start charging={}".format(res))
                    else:
                        L.l.info("Tesla is already charging, no need to start charge")
                if target_amps != act_amps:
                    L.l.info("Increasing Tesla charging from {} to {} Amps".format(act_amps, target_amps))
                    P.thread_pool_status = 'tesla.set_charging_amps 2'
                    if apps.tesla.set_charging_amps(min(target_amps, apps.tesla.P.MAX_AMP)):
                        self.power_status_changed()
                        return True
                    else:
                        if TeslaCharger.DEBUG:
                            L.l.info("Tesla set charging amp did not returned True")
                else:
                    if TeslaCharger.DEBUG:
                        L.l.info("Tesla target-2 amp={}, act_amp={}".format(target_amps, act_amps))
        return False




class P:
    initialised = False
    grid_watts = None
    grid_amps = None
    inverter_watts = 0  # power produced by inverter, to be subtracted from house power
    inverter_amps = 0
    grid_watts_last_update = datetime.min  # used to detect if main meter is down, to switch to secondary
    grid_importing = None
    grid_exporting = None
    device_list = collections.OrderedDict()  # key is utility name
    utility_list = {}
    MIN_WATTS_THRESHOLD = 200  # variation allowed for import/export
    IDLE_WATTS = 200  # use high value, as the inverter compensates from batteries. without inverter keep low, at 70.
    emulate_export = False  # used to test export energy scenarios
    last_state_change = datetime.min
    system_wait_time = 0  # seconds to wait until any device can change state (some relays have latency)
    bms_min_cell_voltage_list = {}  # dict with all min cell voltages
    bms_min_cell_voltage = None  # minimum cell voltage in all bms'es

    bms_cell_min_voltage_critical = 2.7  # charger is started here to increase cell voltage
    bms_cell_critical_charge_recovery_started = False  # cell was charged from low voltage to recovery voltage
    bms_cell_voltage_critical_recovery = 2.9  # charger is stopped here as cell has recovered
    critical_charger_name = "batterycharge_4"  # charger used to recover cells

    bms_cell_min_inverter_voltage_protection = 3  # inverter is stopped when a cell reaches this limit
    bms_cell_inverter_topup_voltage = 3.3
    bms_cell_charge_topup_reached = False  # cell was charged from low voltage to a safety level, inverter can start
    inverter_relay_name = "invertermain_relay"

    thread_pool_status = None

    @staticmethod
    def can_state_change():
        return (datetime.now() - P.last_state_change).total_seconds() >= P.system_wait_time

    @staticmethod
    # init in order of priority
    def init_dev():
        # pwm = m.Pwm.find_one({m.Pwm.name: "boiler"})
        # freq = pwm.frequency
        if P.emulate_export:
            pass



        # keep energy producing devices first in the list
        # order energy consumption with highest consumption first

        #relay = 'inverterpw'
        #P.device_list[relay] = InverterRelay(relay_name=relay, avg_consumption=-500,
        #                                   supports_breaks=True, min_on_interval=60, state_change_interval=120)


        relay = 'batterycharge_1'  # index 1, right, stable
        P.device_list[relay] = BatteryCharger(relay_name=relay, avg_consumption=700,  # 730
                                              supports_breaks=True, min_on_interval=6, state_change_interval=3,
                                              voltage_sensor_name="house battery",
                                              voltage_max_limit=28.6, voltage_max_floor=27.2)
        relay = 'batterycharge_2'  # index 3, right, stable
        P.device_list[relay] = BatteryCharger(relay_name=relay, avg_consumption=750,  # 735
                                              supports_breaks=True, min_on_interval=6, state_change_interval=3,
                                              voltage_sensor_name="house battery",
                                              voltage_max_limit=28.6, voltage_max_floor=27.2)
        relay = 'batterycharge_3'  # index 4, left, somewhat stable
        P.device_list[relay] = BatteryCharger(relay_name=relay, avg_consumption=750,  # 730
                                              supports_breaks=True, min_on_interval=6, state_change_interval=3,
                                              voltage_sensor_name="house battery",
                                              voltage_max_limit=28.6, voltage_max_floor=27.2)
        relay = 'batterycharge_4'  # index 2, flaky
        P.device_list[relay] = BatteryCharger(relay_name=relay, avg_consumption=750,  # 725
                                              supports_breaks=True, min_on_interval=6, state_change_interval=3,
                                              voltage_sensor_name="house battery",
                                              voltage_max_limit=28.6, voltage_max_floor=27.2)
        if apps.tesla.P.initialised:
            relay = 'tesla_charger'
            P.device_list[relay] = TeslaCharger(relay_name=relay, vehicle_id=1, state_change_interval=15)

        relay = 'waterheater_relay'
        P.device_list[relay] = Relaydevice(relay_name=relay, avg_consumption=2900,
                                           supports_breaks=True, min_on_interval=1, state_change_interval=3)

        if not P.emulate_export:
            pass

    def __init__(self):
        pass


def _update_devices():
    if P.grid_watts is not None and P.can_state_change():
        P.grid_importing = (P.grid_watts > P.MIN_WATTS_THRESHOLD)
        P.grid_exporting = (P.grid_watts < -P.MIN_WATTS_THRESHOLD)
        # let all devices know grid status and make power changes
        dev_list = []
        if P.grid_exporting:
            dev_list = P.device_list.values()
        elif P.grid_importing:
            dev_list = reversed(P.device_list.values())
        for device in dev_list:
            P.thread_pool_status = 'update {}'.format(device.RELAY_NAME)
            changed = device.grid_updated(P.grid_watts)
            if changed:  # exit to allow main meter to update and recheck if more power changes are needed
                # L.l.info('Done change action for device {}'.format(device))
                if P.emulate_export is True:
                    break
                else:
                    break


# energy rule
def rule_energy_export(obj=m.PowerMonitor(), change=None):
    if change is not None and 'current' in change or 'power' in change:
        if obj.name == 'invertermain':
            P.inverter_watts = max(0, obj.power)  # keep only positive values
        # L.l.info('Got power {} change={}'.format(obj.name, change))
        if obj.name == 'main l1':
            if P.emulate_export is True:
                P.grid_watts = random.randint(-900, -800)
            else:
                P.grid_watts = obj.power + P.inverter_watts
                P.grid_amps = obj.current
                P.grid_watts_last_update = datetime.now()
            # L.l.info('Got rule main watts {}'.format(P.grid_watts))
            _update_devices()
    if change is not None and 'voltage' in change:
        if obj.name == 'batterycharge monitor 1':
            # start inverter if battery has enough voltage
            #if obj.voltage is not None:
            #    relay = m.ZoneCustomRelay.find_one({"relay_pin_name": P.inverter_relay_name})
            #    if relay is not None:
            #        relay.relay_is_on = obj.voltage > 24.4
            #        relay.save_changed_fields()
            pass  # replaced with cell voltage monitoring


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
        else:
            main_sensor_lapsed = (datetime.now() - P.grid_watts_last_update).total_seconds()
            if main_sensor_lapsed > 120:
                P.grid_watts = obj.units_2_delta
                L.l.info('Using backup sensor for rule main watts={}'.format(P.grid_watts))
                _update_devices()


# energy rule
def rule_energy_bms_cell(obj=m.Bms(), change=None):
    if change is not None and change[0].startswith('v0'):
        min_volt = min(value for value in [obj.v01, obj.v02, obj.v03, obj.v04, obj.v05, obj.v06, obj.v07, obj.v08]
                       if value is not None)
        P.bms_min_cell_voltage_list[obj.name] = min_volt
        for min_val in P.bms_min_cell_voltage_list.values():
            min_volt = min(min_volt, min_val)

        if min_volt != P.bms_min_cell_voltage:
            P.bms_min_cell_voltage = min_volt
            L.l.info("Minimum bms cell voltage is {}".format(P.bms_min_cell_voltage))
            # start or stop the inverter
            inverter_relay = m.ZoneCustomRelay.find_one({"relay_pin_name": P.inverter_relay_name})
            if inverter_relay is not None:
                if P.bms_min_cell_voltage <= P.bms_cell_min_inverter_voltage_protection:
                    P.bms_cell_charge_topup_reached = False
                    inverter_relay.relay_is_on = False
                    inverter_relay.save_changed_fields()
                    L.l.info("Inverter off, min cell voltage<{}".format(P.bms_cell_min_inverter_voltage_protection))
                if P.bms_min_cell_voltage >= P.bms_cell_inverter_topup_voltage:
                    P.bms_cell_charge_topup_reached = True
                    inverter_relay.relay_is_on = True
                    inverter_relay.save_changed_fields()
                    L.l.info("Inverter on, cell voltage reached top-up {}".format(P.bms_cell_inverter_topup_voltage))

            # start or stop the charger to maintain cells above safe level
            if P.bms_min_cell_voltage <= P.bms_cell_min_voltage_critical:
                L.l.info("Cell voltage {} reached minimum critical level {}".format(P.bms_min_cell_voltage,
                                                                                    P.bms_cell_min_voltage_critical))
                P.bms_cell_critical_charge_recovery_started = True
                charge_relay = m.ZoneCustomRelay.find_one({"relay_pin_name": P.critical_charger_name})
                if charge_relay is not None:
                    charge_relay.relay_is_on = True
                    charge_relay.save_changed_fields()
                    L.l.info("Charge relay {} set to on to recover cell".format(charge_relay.pin_name))
            elif (P.bms_cell_critical_charge_recovery_started
                  and P.bms_min_cell_voltage >= P.bms_cell_voltage_critical_recovery):
                # stop charge once cell is over recovery level
                charge_relay = m.ZoneCustomRelay.find_one({"relay_pin_name": P.critical_charger_name})
                charge_relay.relay_is_on = False
                charge_relay.save_changed_fields()
                P.bms_cell_critical_charge_recovery_started = False
                L.l.info("Charge relay {} set to off as recovery cell done".format(charge_relay.relay_pin_name))


def init():
    P.emulate_export = False
    P.init_dev()
    current_module = sys.modules[__name__]
    rule.init_sub_rule(thread_run_func=None, rule_module=current_module)
    L.l.info("Initialised solar rules with {} devices".format(len(P.device_list)))

