from pydispatch import dispatcher
from main.logger_helper import L
from common import Constant, utils
from storage.model import m
from gpio import io_common
__author__ = 'dcristian'

initialised = False


def handle_event_alarm(gpio_pin_code='', direction='', pin_value='', pin_connected=None):
    zonealarm = m.ZoneAlarm.find_one(
        {m.ZoneAlarm.gpio_pin_code: gpio_pin_code, m.ZoneAlarm.gpio_host_name: Constant.HOST_NAME})
    if zonealarm is not None:
        zonearea = m.ZoneArea.find_one({m.ZoneArea.zone_id: zonealarm.zone_id})
        if zonearea is not None:
            area = m.Area.find_one({m.Area.id: zonearea.area_id})
            if area is not None:
                zonealarm.start_alarm = area.is_armed
                zone = m.Zone.find_one({m.Zone.id: zonealarm.zone_id})
                if zone is not None:
                    dispatcher.send(signal=Constant.SIGNAL_ALARM, zone_name=zone.name,
                                    alarm_pin_name=zonealarm.alarm_pin_name, pin_connected=pin_connected)
                    dispatcher.send(Constant.SIGNAL_PRESENCE, zone_name=zone.name, zone_id=zone.id)
                else:
                    L.l.error(
                        "Could not find zone for gpio pin {}, trigger actions could be missed".format(gpio_pin_code))
                # L.l.info('Alarm event in {} pin {} connect={}'.format(
                #    zone.name, zonealarm.alarm_pin_name, pin_connected))
                zonealarm.alarm_pin_triggered = not pin_connected
                zonealarm.updated_on = utils.get_base_location_now_date()
                zonealarm.save_changed_fields(broadcast=True, persist=True)
            else:
                L.l.warning('Zone {} is mapped to missing area' % zonealarm.zone_id)
        else:
            L.l.warning('Zone {} not mapped to an area, pin={}'.format(zonealarm.zone_id, gpio_pin_code))
    else:
        L.l.info('Missing zone alarm for gpio code {} host {}'.format(gpio_pin_code, Constant.HOST_NAME))


def unload():
    L.l.info('Alarm module unloading')
    global initialised
    # dispatcher.disconnect(dispatcher.connect(handle_event_alarm, signal=Constant.SIGNAL_GPIO, sender=dispatcher.Any))
    # thread_pool.remove_callable(alarm_loop.thread_run)
    initialised = False


def init():
    L.l.info('Alarm module initialising')
    dispatcher.connect(handle_event_alarm, signal=Constant.SIGNAL_GPIO, sender=dispatcher.Any)
    # get list of input gpio ports and communicate them to gpio modules for proper port setup as "IN"
    port_list = []
    local_alarms = m.ZoneAlarm.find({m.ZoneAlarm.gpio_host_name: Constant.HOST_NAME})
    for alarm in local_alarms:
        gpio_pin = m.GpioPin()
        gpio_pin.host_name = Constant.HOST_NAME
        gpio_pin.contact_type = alarm.sensor_type
        if alarm.relay_type == Constant.GPIO_PIN_TYPE_PI_FACE_SPI:
            gpio_pin.board_index, gpio_pin.pin_direction, gpio_pin.pin_index_bcm = io_common.decode_piface_pin(
                alarm.gpio_pin_code)
        elif alarm.relay_type == Constant.GPIO_PIN_TYPE_PI_STDGPIO:
            gpio_pin.pin_index_bcm = int(alarm.gpio_pin_code)
        else:
            # for sonoff RF alarms I don't need a pin setup
            pass
        gpio_pin.pin_type = alarm.relay_type
        gpio_pin.pin_code = alarm.gpio_pin_code
        port_list.append(gpio_pin)
    dispatcher.send(signal=Constant.SIGNAL_GPIO_INPUT_PORT_LIST, gpio_pin_list=port_list)
    # just for test on netbook
    # import gpio.rpi_gpio
    # gpio.rpi_gpio.setup_in_ports(port_list)
    global initialised
    initialised = True
