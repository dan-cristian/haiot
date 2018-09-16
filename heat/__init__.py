__author__ = 'dcristian'

from pydispatch import dispatcher

import heat_loop
from main.logger_helper import L
from main import thread_pool
from main.admin import models
from common import Constant, utils
from main.admin.model_helper import commit
import gpio

initialised=False


# execute when heat status change is signaled. changes gpio pin status if pin is local
def record_update(obj_dict=None):
    if not obj_dict:
        obj_dict = {}
    try:
        source_host_name = utils.get_object_field_value(obj_dict, Constant.JSON_PUBLISH_SOURCE_HOST)
        zone_id = utils.get_object_field_value(obj_dict, utils.get_model_field_name(models.ZoneHeatRelay.zone_id))
        pin_name = utils.get_object_field_value(
            obj_dict, utils.get_model_field_name(models.ZoneHeatRelay.heat_pin_name))
        is_on = utils.get_object_field_value(obj_dict,utils.get_model_field_name(models.ZoneHeatRelay.heat_is_on))
        # fixme: remove hard reference to object field
        sent_on = utils.get_object_field_value(obj_dict, "event_sent_datetime")
        L.l.debug('Received heat relay update from {} zoneid={} pin={} is_on={} sent={}'.format(
            source_host_name, zone_id, pin_name, is_on, sent_on))
        zone_heat_relay = models.ZoneHeatRelay.query.filter_by(zone_id=zone_id).first()
        if zone_heat_relay:
            gpio_host_name = zone_heat_relay.gpio_host_name
            cmd_heat_is_on = utils.get_object_field_value(obj_dict,
                                                          utils.get_model_field_name(models.ZoneHeatRelay.heat_is_on))
            L.l.debug('Local heat state zone_id {} must be changed to {} on pin {}'.format(
                zone_id, cmd_heat_is_on, zone_heat_relay.gpio_pin_code))
            if cmd_heat_is_on:
                pin_value = 1
            else:
                pin_value = 0
            # set pin only on pins owned by this host
            if zone_heat_relay and gpio_host_name == Constant.HOST_NAME:
                pin_state = gpio.relay_update(gpio_pin_code=zone_heat_relay.gpio_pin_code, pin_value=pin_value)
            else:
                pin_state = pin_value
            if pin_state == pin_value:
                pin_state = (pin_state == 1)
                zone_heat_relay.heat_is_on = pin_state
                zone_heat_relay.notify_transport_enabled = False
                commit()
            else:
                L.l.warning(
                    'Heat state zone_id {} unexpected val={} after setval={}'.format(zone_id, pin_state, pin_value))
        else:
            L.l.warning('No heat relay defined for zone {}, db data issue?'.format(zone_id))
    except Exception as ex:
        L.l.warning('Error updating heat relay state, err {}'.format(ex))


def handle_event_heat(zone='', heat_is_on=''):
    assert isinstance(zone, models.Zone)
    pass


def unload():
    L.l.info('Heat module unloading')
    global initialised
    initialised = False
    thread_pool.remove_callable(heat_loop.thread_run)
    dispatcher.disconnect(handle_event_heat, signal=Constant.SIGNAL_HEAT, sender=dispatcher.Any)


def init():
    L.l.info('Heat module initialising')
    dispatcher.connect(handle_event_heat, signal=Constant.SIGNAL_HEAT, sender=dispatcher.Any)
    thread_pool.add_interval_callable(heat_loop.thread_run, 60)
    global initialised
    initialised = True
