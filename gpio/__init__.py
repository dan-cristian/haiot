import gpio.io_common

__author__ = 'dcristian'
from main import sqlitedb
from datetime import datetime, timedelta
from main.logger_helper import L
from common import Constant
from common import utils
if sqlitedb:
    from storage.sqalc import models
# from storage.tiny.tinydb_model import GpioPin
from main import thread_pool
from sensor import sonoff
from gpio import io_common
# from gpio import std_gpio
from gpio import pcf8574_gpio
import threading
import prctl
from gpio import rpi_gpio
from gpio import pigpio_gpio
from storage.model import m


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


# update hardware pin state and record real pin value in local DB only
def relay_update(gpio_pin_code=None, pin_value=None, from_web=False):
    result = None
    # return pin value after state set
    try:
        L.l.debug('Received relay state update pin {}'.format(gpio_pin_code))
        if sqlitedb:
            gpiopin_list = models.GpioPin.query.filter_by(pin_code=gpio_pin_code, host_name=Constant.HOST_NAME).all()
        else:
            # gpiopin_list = GpioPin.find(filter={GpioPin.pin_code: gpio_pin_code, GpioPin.host_name: Constant.HOST_NAME})
            pass
        if gpiopin_list is not None:
            lenpin = len(gpiopin_list)
            if lenpin > 1:
                L.l.warning("Multiple records with same pin code {} len {}".format(gpio_pin_code, lenpin))
            for gpiopin in gpiopin_list:
                # L.l.info("Update relay {} value={}".format(gpiopin, pin_value))
                pin_value = relay_set(gpio_pin_index_bcm=gpiopin.pin_index_bcm, gpio_pin_type=gpiopin.pin_type,
                                      gpio_board_index=gpiopin.board_index, value=pin_value, from_web=from_web)
                result = pin_value
                gpiopin.pin_value = pin_value
                gpiopin.notify_transport_enabled = False
                gpiopin.commit_record_to_db()
        else:
            L.l.warning('Pin {} does not exists locally, is db data correct?'.format(gpio_pin_code))
    except Exception as ex:
        L.l.error('Error updating relay state err={}'.format(ex), exc_info=True)
    return result


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


#  save relay io state to db, except for current node
#  carefull not to trigger infinite recursion updates
def not_used_gpio_record_update(json_object):
    try:
        host_name = utils.get_object_field_value(json_object, 'name')
        # L.l.info('Received gpio state update from {} json={}'.format(host_name, json_object))
        if host_name != Constant.HOST_NAME:
            if sqlitedb:
                models.GpioPin().save_changed_fields_from_json_object(debug=False,
                                                                      json_object=json_object, notify_transport_enabled=False, save_to_graph=False)
            else:
                # fixme: add
                pass
    except Exception as ex:
        L.l.warning('Error on gpio state update, err {}'.format(ex))


def zone_custom_relay_record_update(json_object):
    # save relay state to db, except for current node
    # carefull not to trigger infinite recursion updates
    try:
        target_host_name = utils.get_object_field_value(json_object, 'gpio_host_name')
        source_host = utils.get_object_field_value(json_object, 'source_host_')
        is_event_external = utils.get_object_field_value(json_object, 'is_event_external')
        # L.l.info('Received custom relay state update for host {}'.format(host_name))
        if target_host_name == Constant.HOST_NAME:
            # execute local pin change related actions like turn on/off a relay
            if P.initialised:
                gpio_pin_code = utils.get_object_field_value(json_object, 'gpio_pin_code')
                relay_type = utils.get_object_field_value(json_object, 'relay_type')
                relay_is_on = utils.get_object_field_value(json_object, 'relay_is_on')
                expire = utils.get_object_field_value(json_object, 'expire')
                if P.has_zwave and relay_type == Constant.GPIO_PIN_TYPE_ZWAVE:
                    if source_host == Constant.HOST_NAME:
                        if is_event_external:
                            # event received from outside, so no need to set relay state again
                            pass
                        else:
                            # event received from user db change, so act it
                            vals = gpio_pin_code.split('_')
                            if len(vals) == 2:
                                node_id = int(vals[1])
                                L.l.info('Received relay state update host {}, obj={}'.format(
                                    target_host_name, json_object))
                                # zwave switch name is not needed, identify device only by node_id
                                zwave.set_switch_state(node_id=node_id, state=relay_is_on)
                                if expire is not None:
                                    # revert back to initial state
                                    expire_time = datetime.now() + timedelta(seconds=expire)
                                    init_val = not (bool(relay_is_on))
                                    func = (zwave.set_switch_state, node_id, init_val)
                                    if expire_time not in P.expire_func_list.keys():
                                        P.expire_func_list[expire_time] = func
                                        func_update = (io_common.update_custom_relay, gpio_pin_code, init_val, True)
                                        P.expire_func_list[expire_time + timedelta(microseconds=1)] = func_update
                                    else:
                                        L.l.error("Duplicate zwave key in list")
                                        exit(999)
                            else:
                                L.l.error("Incorrect zwave switch format {}, must be <name>_<node_id>".format(
                                    gpio_pin_code))
                elif relay_type == Constant.GPIO_PIN_TYPE_SONOFF:
                    if source_host == Constant.HOST_NAME:
                        if is_event_external:
                            # event received from outside, so no need to set relay state again
                            pass
                        else:
                            # event received from user db change, so act it
                            sonoff.set_relay_state(relay_name=gpio_pin_code, relay_is_on=relay_is_on)
                    else:
                        # fixme: what to do here?
                        L.l.info("Warning - what should I do, event from other host?")
                elif relay_type == Constant.GPIO_PIN_TYPE_PI_PCF8574:
                    if source_host == Constant.HOST_NAME:
                        if is_event_external:
                            # event received from outside, so no need to set relay state again
                            pass
                        else:
                            # event received from user db change, so act it
                            pcf8574_gpio.set_pin_value(pin_index=gpio_pin_code, pin_value=not relay_is_on)
                    else:
                        # fixme: what to do here?
                        L.l.info("Warning - pcf what should I do, event from other host?")
                else:
                    if sqlitedb:
                        gpio_record = models.GpioPin.query.filter_by(pin_code=gpio_pin_code,
                                                                     host_name=Constant.HOST_NAME).first()
                    else:
                        # gpio_record = GpioPin.find_one({GpioPin.pin_code: gpio_pin_code, GpioPin.host_name: Constant.HOST_NAME})
                        pass
                    if gpio_record is not None:
                        # if source_host != Constant.HOST_NAME:
                        #    L.l.info('Event received from other host, event={}'.format(json_object))
                        if source_host == Constant.HOST_NAME and is_event_external:
                            L.l.info('Event received from outside from same host, so no need to set relay state again')
                        else:
                            # L.l.info('Event received from user db change, so act it')
                            value = 1 if relay_is_on else 0

                            pin_code = gpio_record.pin_index_bcm
                            pin_type = gpio_record.pin_type
                            board = gpio_record.board_index
                            relay_set(gpio_pin_index_bcm=pin_code, gpio_pin_type=pin_type, gpio_board_index=board,
                                      value=value, from_web=False)
                            if expire is not None and relay_is_on:
                                # revert back to off state in x seconds
                                expire_time = datetime.now() + timedelta(seconds=expire)
                                init_val = not (bool(relay_is_on))
                                func = (relay_set, pin_code, pin_type, board, init_val, False)
                                # set notify to true to inform openhab on state change
                                if pin_type == Constant.GPIO_PIN_TYPE_PI_FACE_SPI:
                                    pin_code_ok = gpio.io_common.format_piface_pin_code(
                                        board_index=board, pin_direction=Constant.GPIO_PIN_DIRECTION_OUT,
                                        pin_index=pin_code)
                                else:
                                    pin_code_ok = pin_code
                                func_update = (io_common.update_custom_relay, pin_code_ok, init_val, True)
                                if expire_time not in P.expire_func_list.keys():
                                    P.expire_func_list[expire_time] = func
                                    P.expire_func_list[expire_time + timedelta(microseconds=1)] = func_update
                                else:
                                    L.l.error("Duplicate key in gpio list")
                                    exit(999)

                    else:
                        L.l.warning('Could not find gpio record for custom relay pin code={}'.format(gpio_pin_code))
        # todo: check if for zwave we get multiple redundant db saves
        if sqlitedb:
            models.ZoneCustomRelay().save_changed_fields_from_json_object(
                json_object=json_object, notify_transport_enabled=False, save_to_graph=False)
        else:
            # fixme: ?
            pass
    except Exception as ex:
        L.l.error('Error on zone custom relay update, err={}'.format(ex), exc_info=True)


def set_relay_state(pin_code, relay_is_on, relay_type):
    if relay_type == Constant.GPIO_PIN_TYPE_SONOFF:
        res = sonoff.set_relay_state(relay_name=pin_code, relay_is_on=relay_is_on)
    elif relay_type == Constant.GPIO_PIN_TYPE_PI_PCF8574:
        res = pcf8574_gpio.set_pin_value(pin_index=pin_code, pin_value=not relay_is_on)
    elif P.has_zwave and relay_type == Constant.GPIO_PIN_TYPE_ZWAVE:
        node_id = zwave.get_node_id_from_txt(pin_code)
        res = zwave.set_switch_state(node_id=node_id, state=relay_is_on)
    elif relay_type == Constant.GPIO_PIN_TYPE_PI_FACE_SPI:
        value = 1 if relay_is_on else 0
        res = piface.set_pin_code_value(pin_code=pin_code, pin_value=value)
    elif relay_type == Constant.GPIO_PIN_TYPE_PI_STDGPIO:
            bcm_id = int(pin_code)
            value = 1 if relay_is_on else 0
            res = rpi_gpio.set_pin_bcm(bcm_id=bcm_id, pin_value=value)
    else:
        L.l.error('Unexpected relay type {}'.format(relay_type))
        res = None
    return res


def zone_custom_relay_upsert_listener(record, changed_fields):
    assert isinstance(record, m.ZoneCustomRelay)
    if record.gpio_host_name != Constant.HOST_NAME:
        return
    L.l.info('Upsert listener {} pin {}'.format(record.relay_type, record.gpio_pin_code))
    set_relay_state(record.gpio_pin_code, record.relay_is_on, record.relay_type)
    if record.expire is not None:
        pin_code = record.gpio_pin_code
        if record.relay_type == Constant.GPIO_PIN_TYPE_SONOFF:
            expired_relay_is_on = not record.relay_is_on
            expire_func = (sonoff.set_relay_state, record.gpio_pin_code, expired_relay_is_on)
        elif record.relay_type == Constant.GPIO_PIN_TYPE_PI_PCF8574:
            # pcf on state is reversed!
            expired_relay_is_on = record.relay_is_on
            expire_func = (pcf8574_gpio.set_pin_value, record.gpio_pin_code, expired_relay_is_on)
        elif P.has_zwave and record.relay_type == Constant.GPIO_PIN_TYPE_ZWAVE:
            node_id = zwave.get_node_id_from_txt(pin_code)
            expired_relay_is_on = not record.relay_is_on
            zwave.set_switch_state(node_id=node_id, state=record.relay_is_on)
            expire_func = (zwave.set_switch_state, node_id, expired_relay_is_on)
        elif record.relay_type in [Constant.GPIO_PIN_TYPE_PI_STDGPIO, Constant.GPIO_PIN_TYPE_PI_FACE_SPI]:
            value = 1 if record.relay_is_on else 0
            expired_relay_is_on = not record.relay_is_on
            if record.relay_type == Constant.GPIO_PIN_TYPE_PI_FACE_SPI:
                expire_func = (piface.set_pin_code_value, record.gpio_pin_code, value)
            else:
                bcm_id = int(record.gpio_pin_code)
                expire_func = (rpi_gpio.set_pin_bcm, bcm_id, value)
        else:
            L.l.warning('Unknown relay type {}'.format(record.relay_type))
            expire_func = None
            pin_code = None
            expired_relay_is_on = None
        # setup revert back to initial state
        expire_time = datetime.now() + timedelta(seconds=record.expire)
        if expire_time not in P.expire_func_list.keys():
            P.expire_func_list[expire_time] = expire_func
            func_update = (io_common.update_custom_relay, pin_code, expired_relay_is_on, True)
            P.expire_func_list[expire_time + timedelta(microseconds=1)] = func_update
        else:
            L.l.error("Duplicate expire key in list")


# https://stackoverflow.com/questions/26881396/how-to-add-a-function-call-to-a-list
def _process_expire():
    for func_time in dict(P.expire_func_list).keys():
        if datetime.now() >= func_time:
            func = P.expire_func_list[func_time]
            L.l.info("Function expired, executing relay action func={}".format(func))
            func[0](*func[1:])
            del P.expire_func_list[func_time]
            L.l.info("Function deleted, list={}".format(len(P.expire_func_list)))


def thread_run():
    prctl.set_name("gpio")
    threading.current_thread().name = "gpio"
    _process_expire()
    prctl.set_name("idle")
    threading.current_thread().name = "idle"


def unload():
    try:
        L.l.info('Unloading gpio pins')
        # std_gpio.unload()
        # bbb_io.unload()
        piface.unload()
        rpi_gpio.unload()
        pigpio_gpio.unload()
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
            if relay_value is not None or Constant.HOST_NAME=='netbook':
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
                alarm.alarm_pin_triggered = not pin_connected
                alarm.save_changed_fields(broadcast=True, persist=True, listeners=False)

    # piface.post_init()
    # rpi_gpio.post_init()
    # pcf8574_gpio.post_init()


def init():
    L.l.debug("GPIO initialising")
    if Constant.IS_MACHINE_RASPBERRYPI or Constant.IS_MACHINE_ODROID:
        pcf8574_gpio.init()
        piface.init()
        rpi_gpio.init()
        pigpio_gpio.init()
    # if Constant.IS_MACHINE_BEAGLEBONE:
        # bbb_io.init()
        # std_gpio.init()
    if Constant.is_os_windows():
        pigpio_gpio.init()
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
