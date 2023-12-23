import gpio.io_common
import time
from main import sqlitedb
from datetime import datetime, timedelta
from main.logger_helper import L
from common import Constant
from common import utils
from pydispatch import dispatcher
from main import thread_pool
from sensor import sonoff, shelly
from gpio import io_common
# from gpio import std_gpio
from gpio import pcf8574_gpio
import threading
import prctl
from gpio import rpi_gpio
#from gpio import pigpio_gpio
from storage.model import m


__author__ = 'dcristian'


class P:
    initialised = False
    expire_func_list = {}
    has_zwave = False
    has_piface = False

    def __init__(self):
        pass


try:
    from sensor import zwave
    P.has_zwave = True
except ImportError:
    pass

try:
    from gpio import piface
    P.has_piface = True
except ImportError:
    pass


# parameter is GpioPin model, not the pin index!
def relay_get(gpio_pin_obj=None, from_web=False):
    pin_value = None
    message = 'Get relay state for pin {}'.format(gpio_pin_obj)
    # if Constant.HOST_MACHINE_TYPE in [Constant.MACHINE_TYPE_RASPBERRY, Constant.MACHINE_TYPE_BEAGLEBONE,
    #                                  Constant.MACHINE_TYPE_ODROID]:
    if gpio_pin_obj.pin_type in [Constant.GPIO_PIN_TYPE_PI_STDGPIO, Constant.GPIO_PIN_TYPE_BBB]:
        if rpi_gpio.P.initialised:
            pin_value = rpi_gpio.get_pin_bcm(bcm_id=int(gpio_pin_obj.pin_index_bcm))
        # else:
        #    pin_value = std_gpio.get_pin_bcm(bcm_id=gpio_pin_obj.pin_index_bcm)
    elif gpio_pin_obj.pin_type == Constant.GPIO_PIN_TYPE_PI_FACE_SPI:
        # todo: check if pin index is bcm type indeed for piface
        if P.has_piface:
            pin_value = piface.get_out_pin_value(
                pin_index=gpio_pin_obj.pin_index_bcm, board_index=gpio_pin_obj.board_index)
        else:
            L.l.error('Piface not initialised so cannot get relay pin')
    elif gpio_pin_obj.pin_type == Constant.GPIO_PIN_TYPE_PI_PCF8574:
        pin_value = pcf8574_gpio.get_pin(pin_index=int(gpio_pin_obj.pin_index_bcm))
    else:
        L.l.warning('Cannot select gpio method for pin={}'.format(gpio_pin_obj))
    # else:
    #    message += ' error not running on gpio enabled devices'
    #    pin_value = None
    #    L.l.warning(message)

    # if from_web:
    #    return return_web_message(pin_value=pin_value, ok_message=message, err_message=message)
    # else:
    return pin_value


# set gpio pin without updating DB, so make sure it's used only after DB update trigger
def relay_set(gpio_pin_index_bcm=None, gpio_pin_type=None, gpio_board_index=None, value=None, from_web=False):
    pin_value = None
    value = int(value)
    message = 'Set relay state [{}] for pin [{}] from web=[{}]'.format(value, gpio_pin_index_bcm, from_web)
    # L.l.info(message)
    # if Constant.HOST_MACHINE_TYPE in [Constant.MACHINE_TYPE_RASPBERRY, Constant.MACHINE_TYPE_BEAGLEBONE,
    #     #                             Constant.MACHINE_TYPE_ODROID]:
    if gpio_pin_type in [Constant.GPIO_PIN_TYPE_PI_STDGPIO, Constant.GPIO_PIN_TYPE_BBB]:
        if rpi_gpio.P.initialised:
            pin_value = rpi_gpio.set_pin_bcm(bcm_id=int(gpio_pin_index_bcm), pin_value=int(value))
        # else:
        #    pin_value = std_gpio.set_pin_bcm(gpio_pin_index_bcm, value)
    elif gpio_pin_type == Constant.GPIO_PIN_TYPE_PI_FACE_SPI:
        if P.has_piface:
            pin_value = piface.set_pin_value(pin_index=int(gpio_pin_index_bcm), pin_value=int(value),
                                             board_index=int(gpio_board_index))
        else:
            L.l.error('Piface not initialised so cannot set relay pin')
    elif gpio_pin_type == Constant.GPIO_PIN_TYPE_PI_PCF8574:
        pin_value = pcf8574_gpio.set_pin_value(pin_index=int(gpio_pin_index_bcm), pin_value=value)
    else:
        L.l.warning("Unknown pin type {}".format(gpio_pin_type))
    # else:
    #    message += ' error not running on gpio enabled devices'
    #    L.l.warning(message)

    # if from_web:
    #    return return_web_message(pin_value=pin_value, ok_message=message, err_message=message)
    # else:
    return pin_value


def set_relay_state(pin_code, relay_is_on, relay_type, relay_index):
    if relay_type == Constant.GPIO_PIN_TYPE_SONOFF and sonoff.P.initialised:
        res = sonoff.set_relay_state(relay_name=pin_code, relay_is_on=relay_is_on, relay_index=relay_index)
    elif relay_type == Constant.GPIO_PIN_TYPE_SHELLY and shelly.P.initialised:
        res = shelly.set_relay_state(relay_name=pin_code, relay_is_on=relay_is_on, relay_index=relay_index)
    elif relay_type == Constant.GPIO_PIN_TYPE_PI_PCF8574 and pcf8574_gpio.P.initialised:
        res = pcf8574_gpio.set_pin_value(pin_index=int(pin_code), pin_value=not relay_is_on)
    elif P.has_zwave and relay_type == Constant.GPIO_PIN_TYPE_ZWAVE and zwave.P.initialised:
        node_id = zwave.get_node_id_from_txt(pin_code)
        res = zwave.set_switch_state(node_id=node_id, state=relay_is_on)
    elif relay_type == Constant.GPIO_PIN_TYPE_PI_FACE_SPI and piface.P.initialised:
        value = 1 if relay_is_on else 0
        res = piface.set_pin_code_value(pin_code=pin_code, pin_value=value)
    elif relay_type == Constant.GPIO_PIN_TYPE_PI_STDGPIO and rpi_gpio.P.initialised:
        bcm_id = int(pin_code)
        # value = 1 if relay_is_on else 0
        value = 0 if relay_is_on else 1
        res = rpi_gpio.set_pin_bcm(bcm_id=bcm_id, pin_value=value)
    else:
        res = None
    return res


def zone_custom_relay_upsert_listener(record, changed_fields):
    assert isinstance(record, m.ZoneCustomRelay)
    if record.gpio_host_name not in [Constant.HOST_NAME, '', None] \
            or m.ZoneCustomRelay.relay_is_on not in changed_fields:
        return
    L.l.info('Upsert listener {} pin {} value {}'.format(record.relay_type, record.gpio_pin_code, record.relay_is_on))
    set_relay_state(record.gpio_pin_code, record.relay_is_on, record.relay_type, record.relay_index)
    # L.l.info('Upsert after pin {} value {}'.format(record.gpio_pin_code, record.relay_is_on))
    expire_func = None
    # apply expire action only for relay ON events
    if record.expire is not None and record.relay_is_on is True:
        pin_code = record.gpio_pin_code
        expired_relay_is_on = False
        if record.relay_type == Constant.GPIO_PIN_TYPE_SONOFF and sonoff.P.initialised:
            expire_func = (sonoff.set_relay_state, record.gpio_pin_code, expired_relay_is_on)
        elif record.relay_type == Constant.GPIO_PIN_TYPE_PI_PCF8574 and pcf8574_gpio.P.initialised:
            # pcf on state is reversed!
            expire_func = (pcf8574_gpio.set_pin_value, record.gpio_pin_code, not expired_relay_is_on)
        elif P.has_zwave and record.relay_type == Constant.GPIO_PIN_TYPE_ZWAVE and zwave.P.initialised:
            node_id = zwave.get_node_id_from_txt(pin_code)
            zwave.set_switch_state(node_id=node_id, state=record.relay_is_on)
            expire_func = (zwave.set_switch_state, node_id, expired_relay_is_on)
        elif record.relay_type == Constant.GPIO_PIN_TYPE_PI_STDGPIO and rpi_gpio.P.initialised:
            # value = 1 if expired_relay_is_on else 0
            value = 0 if expired_relay_is_on else 1
            bcm_id = int(record.gpio_pin_code)
            expire_func = (rpi_gpio.set_pin_bcm, bcm_id, value)
        elif record.relay_type == Constant.GPIO_PIN_TYPE_PI_FACE_SPI and piface.P.initialised:
            value = 1 if expired_relay_is_on else 0
            expire_func = (piface.set_pin_code_value, record.gpio_pin_code, value)
        else:
            expire_func = None
            pin_code = None
        if expire_func is not None:
            # setup revert to off
            expire_time = datetime.now() + timedelta(seconds=record.expire)
            if expire_time not in P.expire_func_list.keys():
                if expire_func in P.expire_func_list.values():
                    L.l.warning('Expire function already in list, ignoring, func={}'.format(expire_func))
                else:
                    P.expire_func_list[expire_time] = expire_func
                    func_update = (io_common.update_listener_custom_relay, record, expired_relay_is_on)
                    P.expire_func_list[expire_time + timedelta(microseconds=1)] = func_update
            else:
                L.l.error("Duplicate expire key in list")


# https://stackoverflow.com/questions/26881396/how-to-add-a-function-call-to-a-list
def _process_expire():
    if len(P.expire_func_list) > 0:
        for func_time in sorted(P.expire_func_list.keys()):
            if datetime.now() >= func_time:
                func = P.expire_func_list[func_time]
                L.l.info("Function expired, executing relay action func={}".format(func))
                func[0](*func[1:])
                P.expire_func_list.pop(func_time, None)
                # del P.expire_func_list[func_time]
                L.l.info("Function deleted, list={}".format(len(P.expire_func_list)))


def thread_run():
    prctl.set_name("gpio")
    threading.current_thread().name = "gpio"
    _process_expire()
    prctl.set_name("idle_gpio")
    threading.current_thread().name = "idle_gpio"


def unload():
    try:
        L.l.info('Unloading gpio pins')
        # std_gpio.unload()
        # bbb_io.unload()
        piface.unload()
        rpi_gpio.unload()
        #pigpio_gpio.unload()
        pcf8574_gpio.unload()
    except Exception as ex:
        L.l.error('Error unloading gpio, ex={}'.format(ex), exc_info=True)
    P.initialised = False


def post_init():
    # if Constant.is_os_windows():
        # not supported
    #    return

    # init relay (out) pins
    relays = m.ZoneCustomRelay.find({m.ZoneCustomRelay.gpio_host_name: Constant.HOST_NAME})
    for relay in relays:
        gpio_pin_code = relay.gpio_pin_code
        relay_type = relay.relay_type
        if relay_type == Constant.GPIO_PIN_TYPE_PI_FACE_SPI:
            func = piface.post_init_relay_value
        elif relay_type == Constant.GPIO_PIN_TYPE_PI_PCF8574:
            func = pcf8574_gpio.post_init_relay_value
        elif relay_type == Constant.GPIO_PIN_TYPE_SONOFF:
            # handled in sonoff module
            func = None
        elif relay_type == Constant.GPIO_PIN_TYPE_ZWAVE:
            # handled in zwave module
            func = None
        else:
            func = rpi_gpio.post_init_relay_value
        if func is not None:
            relay_value = func(gpio_pin_code=gpio_pin_code)
            L.l.info('Init relay {} pin {}, value read is {}'.format(relay.relay_pin_name, gpio_pin_code, relay_value))
            if relay_value is not None or Constant.HOST_NAME == 'netbook':
                relay.relay_is_on = relay_value
                # skip listeners to avoid relay triggering?
                relay.save_changed_fields(broadcast=True, persist=True, listeners=False)

    # init pir/contact (in) pins
    alarms = m.ZoneAlarm.find({m.ZoneAlarm.gpio_host_name: Constant.HOST_NAME})
    for alarm in alarms:
        gpio_pin_code = alarm.gpio_pin_code
        relay_type = alarm.relay_type
        if relay_type == Constant.GPIO_PIN_TYPE_PI_FACE_SPI:
            func = piface.post_init_alarm_value
        elif relay_type == Constant.GPIO_PIN_TYPE_PI_PCF8574:
            func = pcf8574_gpio.post_init_alarm_value
        elif relay_type == Constant.GPIO_PIN_TYPE_SONOFF:
            # handled in sonoff module
            func = None
        elif relay_type == Constant.GPIO_PIN_TYPE_ZWAVE:
            # handled in zwave module
            func = None
        else:
            func = rpi_gpio.post_init_alarm_value
        if func is not None:
            pin_connected = func(gpio_pin_code=gpio_pin_code)
            if pin_connected is not None:
                if alarm.sensor_type == Constant.CONTACT_TYPE_NO:
                    alarm.alarm_pin_triggered = pin_connected
                else:
                    alarm.alarm_pin_triggered = not pin_connected
                L.l.info('Init alarm {} pin {}, value read is {} type {}'.format(
                    alarm.alarm_pin_name, gpio_pin_code, pin_connected, alarm.sensor_type))
                alarm.save_changed_fields(broadcast=True, persist=True, listeners=False)

    # init PWM
    # pwm_list = m.Pwm.find({m.Pwm.host_name: Constant.HOST_NAME})
    # for pwm in pwm_list:
    #    pwm.frequency, pwm.duty = pigpio_gpio.P.pwm.get(pwm.name)
    #    pwm.save_changed_fields(broadcast=True, persist=True)

    piface.post_init()
    # rpi_gpio.post_init()
    # pcf8574_gpio.post_init()


def _handle_io_event(gpio_pin_code='', direction='', pin_value='', pin_connected=None):
    sensor = m.IOSensor.find_one({m.IOSensor.io_code: gpio_pin_code, m.IOSensor.host_name: Constant.HOST_NAME})
    if sensor is not None:
        if sensor.purpose == Constant.IO_SENSOR_PURPOSE:
            if pin_connected:
                dispatcher.send(Constant.SIGNAL_UTILITY, sensor_name=sensor.sensor_name, units_delta_a=1)
    else:
        pass
        # L.l.info('Cannot find IOSensor {}'.format(gpio_pin_code))


def _init_io():
    dispatcher.connect(_handle_io_event, signal=Constant.SIGNAL_GPIO, sender=dispatcher.Any)
    # get list of input gpio ports and communicate them to gpio modules for proper port setup as "IN"
    port_list = []
    local_sensors = m.IOSensor.find({m.IOSensor.host_name: Constant.HOST_NAME})
    for sensor in local_sensors:
        gpio_pin = m.GpioPin()
        gpio_pin.host_name = Constant.HOST_NAME
        gpio_pin.contact_type = sensor.sensor_type
        if sensor.relay_type == Constant.GPIO_PIN_TYPE_PI_FACE_SPI:
            gpio_pin.board_index, gpio_pin.pin_direction, gpio_pin.pin_index_bcm = io_common.decode_piface_pin(
                sensor.io_code)
        else:
            gpio_pin.pin_index_bcm = int(sensor.io_code)
        gpio_pin.pin_type = sensor.relay_type
        gpio_pin.pin_code = sensor.io_code
        port_list.append(gpio_pin)
    L.l.info('Init {} IO sensor input ports'.format(len(port_list)))
    dispatcher.send(signal=Constant.SIGNAL_GPIO_INPUT_PORT_LIST, gpio_pin_list=port_list)


def init():
    L.l.debug("GPIO initialising")
    if Constant.IS_MACHINE_RASPBERRYPI or Constant.IS_MACHINE_ODROID:
        pcf8574_gpio.init()
        # piface.init()
        rpi_gpio.init()

    #pigpio_gpio.init()

    # if Constant.IS_MACHINE_BEAGLEBONE:
        # bbb_io.init()
        # std_gpio.init()
    #if Constant.is_os_windows():
    #    pigpio_gpio.init()
    # init last after RPI
    piface.init()
    # init IO Sensors
    _init_io()
    m.ZoneCustomRelay.add_upsert_listener(zone_custom_relay_upsert_listener)
    thread_pool.add_interval_callable(thread_run, run_interval_second=1)
    P.initialised = True

    if False:  # L.DEBUG_REMOTE:
        try:
            import ptvsd
            ptvsd.enable_attach(address=('0.0.0.0', 5678), redirect_output=True)
            print('Enabled remote debugging, waiting 15 seconds for client to attach')
            ptvsd.wait_for_attach(timeout=15)
        except Exception as ex:
            print("Error in remote debug: {}".format(ex))
