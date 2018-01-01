from pydispatch import dispatcher
from main.logger_helper import L
from main.admin import models
from main import thread_pool
from common import Constant, utils
from main.admin.model_helper import commit

__author__ = 'dcristian'

initialised = False


def handle_event_alarm(gpio_pin_code='', direction='', pin_value='', pin_connected=None):
    zonealarm = models.ZoneAlarm.query.filter_by(gpio_pin_code=gpio_pin_code).first()
    if zonealarm is not None:
        zonearea = models.ZoneArea().query_filter_first(models.ZoneArea.zone_id == zonealarm.zone_id)
        if zonearea is not None:
            area = models.Area().query_filter_first(models.Area.id == zonearea.area_id)
            if area is not None:
                zonealarm.start_alarm = area.is_armed
            else:
                L.l.warning('Zone {} is mapped to missing area' % zonealarm.zone_id)
        else:
            L.l.warning('Zone %s not mapped to an area' % zonealarm.zone_id)
        zone = models.Zone.query.filter_by(id=zonealarm.zone_id).first()
        dispatcher.send(signal=Constant.SIGNAL_ALARM, zone_name=zone.name, pin_connected=pin_connected)
        L.l.debug('Got alarm event in {} zoneid={} pin_connected={} pin_value={}'.format(
            zone.name, zonealarm.zone_id, pin_connected, pin_value))
        zonealarm.alarm_pin_triggered = pin_value
        zonealarm.updated_on = utils.get_base_location_now_date()
        zonealarm.notify_transport_enabled = True
        commit()
    else:
        L.l.warning('Unexpected mising zone alarm for gpio code {}'.format(gpio_pin_code))


def unload():
    L.l.info('Alarm module unloading')
    global initialised
    # dispatcher.disconnect(dispatcher.connect(handle_event_alarm, signal=Constant.SIGNAL_GPIO, sender=dispatcher.Any))
    # thread_pool.remove_callable(alarm_loop.thread_run)
    initialised = False


def init():
    L.l.info('Alarm module initialising')
    # alarm_loop.init()
    # thread_pool.add_interval_callable(alarm_loop.thread_run)
    dispatcher.connect(handle_event_alarm, signal=Constant.SIGNAL_GPIO, sender=dispatcher.Any)
    # get list of input gpio ports and communicate them to gpio modules for proper port setup as "IN"
    port_list = []
    local_alarms = models.ZoneAlarm().query_filter_all(models.ZoneAlarm.gpio_host_name.in_([Constant.HOST_NAME]))
    for alarm in local_alarms:
        L.l.info("Processing zone alarm {} for host {}".format(alarm, Constant.HOST_NAME))
        gpio_pin = models.GpioPin().query_filter_first(models.GpioPin.pin_code.in_([alarm.gpio_pin_code]),
                                                       models.GpioPin.host_name.in_([Constant.HOST_NAME]))
        if gpio_pin is not None:
            # Log.logger.info('Schedule setup alarm port pin={} type={}'.format(gpio_pin.pin_code, gpio_pin.pin_type))
            port_list.append(gpio_pin)
        else:
            L.l.warning('Unexpected empty gpio pin response for alarm setup {}'.format(alarm))
    dispatcher.send(signal=Constant.SIGNAL_GPIO_INPUT_PORT_LIST, gpio_pin_list=port_list)
    # just for test on netbook
    # import gpio.rpi_gpio
    # gpio.rpi_gpio.setup_in_ports(port_list)
    global initialised
    initialised = True
