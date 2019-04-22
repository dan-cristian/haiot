from main.logger_helper import L
from pydispatch import dispatcher
from main import thread_pool, sqlitedb
if sqlitedb:
    from main.admin import models
from common import Constant, utils
from presence import presence_bt
from presence import presence_wifi
from main.tinydb_model import ZoneAlarm, Zone, Presence

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'
initialised = False


def not_used_record_update(json=''):
    # Log.logger.info('Got presence update')
    if sqlitedb:
        models.Presence().json_to_record_query(json_obj=json)
    else:
        # fixme
        pass


def handle_event_presence_io(gpio_pin_code='', direction='', pin_value='', pin_connected=None):
    try:
        # Log.logger.info('Presence got event pin {} connected={}'.format(gpio_pin_code, pin_connected))
        # skip too many updates, only capture when contact is not connected (for PIR sensors this is alarm)

        #if not pin_connected:
        if sqlitedb:
            zonealarm = models.ZoneAlarm().query_filter_first(
                models.ZoneAlarm.gpio_host_name.in_([Constant.HOST_NAME]),
                models.ZoneAlarm.gpio_pin_code.in_([gpio_pin_code]))
        else:
            zonealarm = ZoneAlarm.find_one({ZoneAlarm.gpio_host_name: Constant.HOST_NAME,
                                            ZoneAlarm.gpio_pin_code: gpio_pin_code})
        # zone_id = None
        # fixme: for now zonealarm holds gpio to zone mapping, should be made more generic
        if zonealarm is not None:
            zone_id = zonealarm.zone_id
            if zone_id is not None:
                if sqlitedb:
                    zone = models.Zone().query_filter_first(models.Zone.id == zone_id)
                else:
                    zone = Zone.find_one({Zone.id: zone_id})
                if zone is not None:
                    zone_name = zone.name
                else:
                    L.l.warning("Zone not found for presence zoneid={}".format(zone_id))
                    zone_name = "zone_name not found"
                if sqlitedb:
                    current_record = models.Presence().query_filter_first(models.Presence.zone_id == zone_id)
                    record = models.Presence()
                else:
                    current_record = Presence.find_one({Presence.zone_id: zone_id})
                    record = Presence()
                record.event_type = zonealarm.sensor_type
                record.zone_id = zone_id
                record.zone_name = zone_name
                # record.event_io_date = utils.get_base_location_now_date()
                record.sensor_name = zonealarm.alarm_pin_name
                record.is_connected = pin_connected
                # Log.logger.info('Presence saving sensor {}'.format(record.sensor_name))
                record.save_changed_fields(current_record=current_record, new_record=record,
                                           notify_transport_enabled=True, save_to_graph=True,
                                           save_all_fields=True)
            else:
                L.l.warning('Unable to find presence zone for pin {} in Alarm table'.format(gpio_pin_code))
    except Exception as ex:
        L.l.critical("Unable to save presence, er={}".format(ex), exc_info=True)


def handle_event_presence_cam(zone_name, cam_name, has_move):
    L.l.debug("Got cam event zone {} cam {} move={}".format(zone_name, cam_name, has_move))
    if sqlitedb:
        zone = models.Zone().query_filter_first(models.Zone.name == zone_name)
    else:
        zone = Zone.find_one({Zone.name: zone_name})
    if zone is not None:
        if sqlitedb:
            current_record = models.Presence().query_filter_first(models.Presence.zone_id == zone.id)
            record = models.Presence()
        else:
            current_record = Presence().find_one({Presence.zone_id: zone.id})
            record = Presence()
        record.event_type = Constant.PRESENCE_TYPE_CAM
        record.zone_id = zone.id
        record.zone_name = zone_name
        # record.event_camera_date = utils.get_base_location_now_date()
        record.sensor_name = cam_name
        record.is_connected = bool(int(has_move))
        L.l.debug("Saving cam event zone {} sensor {} is_conn={} record={}".format(
            record.zone_name, record.sensor_name, record.is_connected, record))
        record.save_changed_fields(current_record=current_record, new_record=record,
                                   notify_transport_enabled=True, save_to_graph=True,
                                   save_all_fields=True)
    else:
        L.l.warning('Unable to find presence zone for camera zone {}'.format(zone_name))


def unload():
    L.l.info('Presence module unloading')
    # ...
    thread_pool.remove_callable(presence_bt.thread_run)
    global initialised
    initialised = False


def init():
    L.l.debug('Presence module initialising')
    thread_pool.add_interval_callable(presence_wifi.thread_run, run_interval_second=20)
    dispatcher.connect(handle_event_presence_io, signal=Constant.SIGNAL_GPIO, sender=dispatcher.Any)
    dispatcher.connect(handle_event_presence_cam, signal=Constant.SIGNAL_CAMERA, sender=dispatcher.Any)
    global initialised
    initialised = True

