from datetime import datetime
import traceback
import sys
from copy import deepcopy
from main.logger_helper import L
from main import db
from common import Constant
import graphs
from common import utils, performance
from pydispatch import dispatcher
from main.admin.model_helper import commit


# TODO: read this
# http://lucumr.pocoo.org/2011/7/19/sqlachemy-and-you/


# inherit this to use performance tracked queries
class DbBase:
    def __init__(self):
        pass
    # to fix a bug, https://stackoverflow.com/questions/27812250/sqlalchemy-inheritance-not-working
    __table_args__ = {'extend_existing': True}

    record_uuid = None
    save_to_history = False  # if true this record will be saved to master node database for reporting

    def __check_for_long_query(self, result, start_time, function):
        query_details = function.im_self
        elapsed = performance.add_query(start_time, query_details=query_details)
        if elapsed > 5000:  # with sqlite a long query will throw an error
            L.l.critical("Long running DB query, seconds elapsed={}, result={}".format(elapsed, query_details))
            # db.session.rollback()
            # Log.logger.info("Session was rolled back")
        return result

    def __get_result(self, function):
        start_time = utils.get_base_location_now_date()
        result = function()
        return self.__check_for_long_query(result, start_time, function)

    def query_all(self):
        function = self.query.all
        return self.__get_result(function)

    def query_all_count(self):
        function = self.query.count
        return self.__get_result(function)

    def query_all_limit(self, limit):
        function = self.query.limit(limit).all
        return self.__get_result(function)

    # example with one filter
    # http://docs.sqlalchemy.org/en/latest/orm/tutorial.html
    # models.Rule().query_filter_all(filter=models.Rule.host_name.in_([Constant.HOST_NAME, ""]))
    #
    # def query_filter_all(self, filter):
    #    function = self.query.filter(filter).all
    #    return self.__get_result(function)

    def query_filter_all(self, *query_filter):
        function = self.query.filter(*query_filter).all
        return self.__get_result(function)

    def query_filter_limit(self, limit, *query_filter):
        function = self.query.filter(*query_filter).limit(limit).all
        return self.__get_result(function)

    # simple ex
    #pd = models.PeopleDevice
    #peopledev = pd().query_filter_first(pd.device_id == dev.id)

    # example with multiple filters
    # m = models.Table
    # m().query_filter_first(m.host_name.in_([Constant.HOST_NAME]), m.name.in_([mod.name]))
    def query_filter_first(self, *query_filter):
        func = self.query.filter(*query_filter).first
        #return res
        return self.__get_result(func)

    #    def query_filters_first(self, *filter):
    #        function = self.query.filter(*filter).first
    #        return self.__get_result(function)

    def query_count(self, *query_filter):
        function = self.query.filter(*query_filter).count
        return self.__get_result(function)

    def delete(self):
        function = self.query.delete
        commit()
        return self.__get_result(function)

    def add_commit_record_to_db(self):
        db.session.add(self)
        return commit()

    def add_record_to_session(self):
        db.session.add(self)

    def commit_record_to_db(self):
        return commit()

    # copies fields from a json object to an existing or new db record
    def save_changed_fields_from_json_object(self, json_object=None, unique_key_name=None,
                                             notify_transport_enabled=False, save_to_graph=False,
                                             ignore_only_updated_on_change=True, debug=False, graph_save_frequency=0):
        try:
            new_record = utils.json_to_record(self, json_object)
            # let flask assign an id in case unique key name is different, to avoid key integrity error
            if not unique_key_name:
                unique_key_name = 'id'
            else:
                new_record.id = None
            if hasattr(new_record, unique_key_name):
                unique_key_value = getattr(new_record, unique_key_name)
                kwargs = {unique_key_name: unique_key_value}
                new_record.updated_on = utils.get_base_location_now_date()
                current_record = self.query.filter_by(**kwargs).first()
                self.save_changed_fields(current_record=current_record, new_record=new_record,
                                         notify_transport_enabled=False, save_to_graph=False)
                db.session.commit()
            else:
                L.l.warning('Unique key not found in json record, save aborted')
        except Exception, ex:
            L.l.error('Exception save json to db {}'.format(ex))

    # graph_save_frequency in seconds
    def save_changed_fields(self, current_record='', new_record='', notify_transport_enabled=False, save_to_graph=False,
                            ignore_only_updated_on_change=True, debug=False, graph_save_frequency=0, query_filter=None,
                            save_all_fields=False):
        try:
            # inherit BaseGraph to enable persistence
            if hasattr(self, 'save_to_graph'):  # not all models inherit graph, used for periodic save
                if current_record:
                    # if a record in db already exists
                    if not current_record.last_save_to_graph:
                        current_record.last_save_to_graph = datetime.min
                    save_to_graph_elapsed = (utils.get_base_location_now_date() -
                                             current_record.last_save_to_graph).total_seconds()
                    if save_to_graph_elapsed > graph_save_frequency:
                        L.l.debug('Saving to graph record {}'.format(new_record))
                        current_record.save_to_graph = save_to_graph
                        current_record.save_to_history = save_to_graph
                    else:
                        current_record.save_to_graph = False
                        current_record.save_to_history = False
                else:
                    # this is a new record
                    new_record.save_to_graph = save_to_graph
            # ensure is set for both new and existing records
            new_record.save_to_history = save_to_graph
            if current_record is not None:
                # ensure is set for both new and existing records
                current_record.save_to_history = save_to_graph
                current_record.last_commit_field_changed_list = []
                current_record.notify_transport_enabled = notify_transport_enabled
                for column in new_record.query.statement._columns._all_columns:
                    column_name = str(column)
                    new_value = getattr(new_record, column_name)
                    old_value = getattr(current_record, column_name)
                    if debug:
                        L.l.info('DEBUG process Col={} New={} Old={} Saveall={}'.format(
                            column_name, new_value, old_value, save_all_fields))
                    # todo: comparison not working for float, because str appends .0
                    if ((new_value is not None) and (str(old_value) != str(new_value))) \
                            or (save_all_fields and (new_value is not None)):
                        if column_name != Constant.DB_FIELD_UPDATE:
                            try:
                                obj_type = str(type(self)).split('\'')[1]
                                obj_type_words = obj_type.split('.')
                                obj_type = obj_type_words[len(obj_type_words) - 1]
                            except Exception, ex:
                                obj_type = str(type(self))
                        else:
                            pass
                        if column_name != "id":  # do not change primary key with None
                            setattr(current_record, column_name, new_value)
                            current_record.last_commit_field_changed_list.append(column_name)
                            if debug:
                                L.l.info('DEBUG CHANGE COL={} to VAL={}'.format(column_name, new_value))
                    else:
                        if debug:
                            L.l.info('DEBUG NOT change col={}'.format(column_name))
                if len(current_record.last_commit_field_changed_list) == 0:
                    current_record.notify_transport_enabled = False
                # fixme: remove hardcoded field name
                elif len(current_record.last_commit_field_changed_list) == 1 and ignore_only_updated_on_change and \
                                Constant.DB_FIELD_UPDATE in current_record.last_commit_field_changed_list:
                    current_record.notify_transport_enabled = False
            else:
                new_record.notify_transport_enabled = notify_transport_enabled
                for column in new_record.query.statement._columns._all_columns:
                    column_name = str(column)
                    new_value = getattr(new_record, column_name)
                    if new_value:
                        new_record.last_commit_field_changed_list.append(column_name)
                if debug:
                    L.l.info('DEBUG new record={}'.format(new_record))
                db.session.add(new_record)
            # fixme: remove hardcoded field name
            if hasattr(new_record, 'last_save_to_graph'):
                if current_record is not None:
                    current_record.last_save_to_graph = utils.get_base_location_now_date()
                new_record.last_save_to_graph = utils.get_base_location_now_date()
            # signal other modules we have a new record to process (i.e. upload to cloud)
            if save_to_graph:
                dispatcher.send(signal=Constant.SIGNAL_STORABLE_RECORD,
                                new_record=new_record, current_record=current_record)
            commit()
        except Exception, ex:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            ex_trace = traceback.format_exception(exc_type, exc_value, exc_traceback)
            L.l.error('Error when saving db changes [{}], err={}, trace=\n{}'.format(new_record, ex, ex_trace),
                      exc_info=True)
            if len(db.session.dirty) > 0:
                L.l.info('Session dirty records={}, rolling back'.format(len(db.session.dirty)))
                db.session.rollback()
            else:
                L.l.info('No session dirty records to rollback for error {}'.format(ex))
            raise ex
            # else:
            #    Log.logger.warning('Incorrect parameters received on save changed fields to db')

    # save json to a new or existing record
    def json_to_record_query(self, json_obj):
        record_id = utils.get_object_field_value(json_obj, 'id')
        current_record = self.query_filter_first(self._sa_class_manager["id"] == record_id)
        #if current_record is None:
        #    current_record = self()
        utils.json_to_record(self, json_obj)
        #commit()
        self.save_changed_fields(
            current_record=current_record, new_record=self, notify_transport_enabled=False, save_to_graph=False)


# inherit this to enable easy record changes save and publish
class DbEvent:
    def __init__(self):
        pass

    notified_on_db_commit = False
    notify_transport_enabled = False
    event_sent_datetime = None

    operation_type = None
    last_commit_field_changed_list = []

    def get_deepcopy(self):
        return deepcopy(self)

    # def json_to_record(self, json_object):
    #    return utils.json_to_record(self, json_object)


class DbHistory():
    record_uuid = db.Column(db.String(36))
    source_host_ = db.Column(db.String(50))


class Module(db.Model, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    host_name = db.Column(db.String(50))
    name = db.Column(db.String(50))
    active = db.Column(db.Integer)  # does not work well as Boolean due to all values by default are True
    start_order = db.Column(db.Integer)

    def __init__(self, id='', host_name='', name='', active=0, start_order='999'):
        super(Module, self).__init__()
        if id:
            self.id = id
        self.host_name = host_name
        self.name = name
        self.active = active
        self.start_order = start_order

    def __repr__(self):
        return 'Module {} [{}] {} {}'.format(self.id, self.host_name, self.name[:50], self.active)


class Zone(db.Model, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    active_heat_schedule_pattern_id = db.Column(db.Integer)
    heat_is_on = db.Column(db.Boolean, default=False)
    last_heat_status_update = db.Column(db.DateTime(), default=None)
    heat_target_temperature = db.Column(db.Integer)
    is_indoor_heated = db.Column(db.Boolean)
    is_indoor = db.Column(db.Boolean)
    is_outdoor = db.Column(db.Boolean)

    def __init__(self, id='', name=''):
        super(Zone, self).__init__()
        if id:
            self.id = id
        self.name = name

    def __repr__(self):
        return 'Zone id {} {}'.format(self.id, self.name[:20])


class Area(db.Model, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    is_armed = db.Column(db.Boolean, default=False)

    def __init__(self, id='', name=''):
        super(Area, self).__init__()
        if id:
            self.id = id
        self.name = name

    def __repr__(self):
        return 'Area id {} {} armed={}'.format(self.id, self.name[:20], self.is_armed)


class ZoneArea(db.Model, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    area_id = db.Column(db.Integer, db.ForeignKey('area.id'), nullable=False)
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'), nullable=False)

    def __init__(self, id=''):
        super(ZoneArea, self).__init__()
        if id:
            self.id = id

    def __repr__(self):
        return 'ZoneArea id {} zone={} area={}'.format(self.id, self.zone_id, self.area_id)


class ZoneMusic(db.Model, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'), nullable=False)
    server_ip = db.Column(db.String(15))
    server_port = db.Column(db.Integer)

    def __init__(self, id=''):
        super(ZoneMusic, self).__init__()
        if id:
            self.id = id

    def __repr__(self):
        return 'ZoneMusic id {} zone={} port={}'.format(self.id, self.zone_id, self.area_id)


class Presence(db.Model, DbBase, DbEvent):
    id = db.Column(db.Integer, primary_key=True)
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'), nullable=False)
    zone_name = db.Column(db.String(50))
    sensor_name = db.Column(db.String(50))
    event_type = db.Column(db.String(25)) # cam, pir, contact, wifi, bt
    event_camera_date = db.Column(db.DateTime(), default=None)
    event_alarm_date = db.Column(db.DateTime(), default=None)
    event_io_date = db.Column(db.DateTime(), default=None)
    event_wifi_date = db.Column(db.DateTime(), default=None)
    event_bt_date = db.Column(db.DateTime(), default=None)
    is_connected = db.Column(db.Boolean, default=False)  # pin connected? true on unarmed sensors, false on alarm/move
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now)

    def __init__(self, zone_id=None):
        super(Presence, self).__init__()

    def __repr__(self):
        return 'Presence id {} zone_id {} sensor {} connected {}'.format(self.id, self.zone_id, self.sensor_name, self.is_connected)


class SchedulePattern(db.Model, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    pattern = db.Column(db.String(24))
    auto_activate_on_move = db.Column(db.Boolean, default=False)
    auto_deactivate_on_away = db.Column(db.Boolean, default=False)
    keep_warm = db.Column(db.Boolean, default=False)  # keep the zone warm, used for cold floors
    keep_warm_pattern = db.Column(db.String(20))  # pattern, 5 minutes increments of on/off: 10000100010000111000


    def __init__(self, id=None, name='', pattern=''):
        super(SchedulePattern, self).__init__()
        if id:
            self.id = id
        self.name = name
        self.pattern = pattern

    def __repr__(self):
        return self.name[:len('1234-5678-9012-3456-7890-1234')]


class TemperatureTarget(db.Model, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(1))
    target = db.Column(db.Float)

    def __init__(self, id=None, code='', target=''):
        super(TemperatureTarget, self).__init__()
        if id:
            self.id = id
        self.code = code
        self.target = target

    def __repr__(self):
        return '{} code {}={}'.format(self.id, self.code, self.target)


class HeatSchedule(db.Model, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'), nullable=False)
    # zone = db.relationship('Zone', backref=db.backref('heat schedule zone', lazy='dynamic'))
    pattern_week_id = db.Column(db.Integer, db.ForeignKey('schedule_pattern.id'), nullable=False)
    pattern_weekend_id = db.Column(db.Integer, db.ForeignKey('schedule_pattern.id'), nullable=False)
    ''' temp minimum target if there is move in a zone, to ensure there is heat if someone is at home unplanned'''
    temp_target_code_min_presence = db.Column(db.String(1), db.ForeignKey('temperature_target.code'), nullable=False)
    ''' temp max target if there is no move, to preserve energy'''
    temp_target_code_max_no_presence = db.Column(db.String(1), db.ForeignKey('temperature_target.code'), nullable=False)
    # pattern_week = db.relationship('SchedulePattern', foreign_keys='[HeatSchedule.pattern_week_id]',
    #                               backref=db.backref('schedule_pattern_week', lazy='dynamic'))
    # pattern_weekend = db.relationship('SchedulePattern', foreign_keys='[HeatSchedule.pattern_weekend_id]',
    #                                backref=db.backref('schedule_pattern_weekend', lazy='dynamic'))
    active = db.Column(db.Boolean, default=True)

    def __init__(self, id=None, zone_id=None, pattern_week_id=None, pattern_weekend_id=None,
                 temp_target_code_min_presence=None, temp_target_code_max_no_presence=None):
        super(HeatSchedule, self).__init__()
        if id:
            self.id = id
        self.zone_id = zone_id
        self.pattern_week_id = pattern_week_id
        self.pattern_weekend_id = pattern_weekend_id
        self.temp_target_code_min_presence = temp_target_code_min_presence
        self.temp_target_code_max_no_presence = temp_target_code_max_no_presence

    def __repr__(self):
        return 'Zone {}, Active {}, Week {}, Weekend {}'.format(self.zone_id, self.active,
                                                                self.pattern_week_id, self.pattern_weekend_id)


class Sensor(db.Model, graphs.SensorGraph, DbEvent, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(50), unique=True)
    type = db.Column(db.String(50))
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    counters_a = db.Column(db.BigInteger)
    counters_b = db.Column(db.BigInteger)
    delta_counters_a = db.Column(db.BigInteger)
    delta_counters_b = db.Column(db.BigInteger)
    iad = db.Column(db.Float)
    vdd = db.Column(db.Float)
    vad = db.Column(db.Float)
    pio_a = db.Column(db.Integer)
    pio_b = db.Column(db.Integer)
    sensed_a = db.Column(db.Integer)
    sensed_b = db.Column(db.Integer)
    battery_level = db.Column(db.Integer)  # RFXCOM specific, sensor battery
    rssi = db.Column(db.Integer)  # RFXCOM specific, rssi - distance
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now)
    added_on = db.Column(db.DateTime(), default=datetime.now)
    # FIXME: now filled manually, try relations
    # zone_name = db.Column(db.String(50))
    sensor_name = db.Column(db.String(50))
    alt_address = db.Column(db.String(50)) # alternate address format, use for 1-wire, better readability

    def __init__(self, address=''):
        super(Sensor, self).__init__()
        self.address = address

    def __repr__(self):
        return '{}, {}, {}, {}'.format(self.type, self.sensor_name, self.address, self.temperature)


class SensorError(db.Model, DbBase, DbEvent):
    id = db.Column(db.Integer, primary_key=True)
    sensor_name = db.Column(db.String(50), index=True)
    sensor_address = db.Column(db.String(50))
    error_type = db.Column(db.Integer)  # 0=not found, 1=other err
    error_count = db.Column(db.Integer)
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now, index=True)

    def __repr__(self):
        return '{} {} errors={}'.format(self.id, self.sensor_name, self.error_count)


class Parameter(db.Model, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    value = db.Column(db.String(255))
    description = db.Column(db.String(255))

    def __init__(self, id=None, name='default', value='default'):
        super(Parameter, self).__init__()
        if id:
            self.id = id
        self.name = name
        self.value = value

    def __repr__(self):
        return '{}, {}'.format(self.name, self.value)


class ZoneSensor(db.Model, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    sensor_name = db.Column(db.String(50))
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'))
    # zone = db.relationship('Zone', backref=db.backref('ZoneSensor(zone)', lazy='dynamic'))
    sensor_address = db.Column(db.String(50), db.ForeignKey('sensor.address'))
    target_material = db.Column(db.String(50))  # what material is being measured, water, air, etc
    # sensor = db.relationship('Sensor', backref=db.backref('ZoneSensor(sensor)', lazy='dynamic'))

    def __init__(self, zone_id='', sensor_address='', sensor_name=''):
        super(ZoneSensor, self).__init__()
        self.sensor_address = sensor_address
        self.zone_id = zone_id
        self.sensor_name = sensor_name

    def __repr__(self):
        return 'ZoneSensor zone {} sensor {}'.format(self.zone_id, self.sensor_name)


class Node(db.Model, DbEvent, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    ip = db.Column(db.String(15))
    mac = db.Column(db.String(17))
    os_type = db.Column(db.String(50))
    machine_type = db.Column(db.String(50))
    app_start_time = db.Column(db.DateTime())
    is_master_overall = db.Column(db.Boolean(), default=False)
    is_master_db_archive = db.Column(db.Boolean(), default=False)
    is_master_graph = db.Column(db.Boolean(), default=False)
    is_master_rule = db.Column(db.Boolean(), default=False)
    is_master_logging = db.Column(db.Boolean(), default=False)
    priority = db.Column(db.Integer)  # used to decide who becomes main master in case several hosts are active
    master_overall_cycles = db.Column(db.Integer)  # count of update cycles while node was master
    run_overall_cycles = db.Column(db.Integer)  # count of total update cycles
    execute_command = db.Column(db.String(50))
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now)

    def __init__(self, id=None, name=None, ip=None, priority=None, mac=None, is_master_logging=False):
        super(Node, self).__init__()
        if id:
            self.id = id
        self.name = name
        self.ip = ip
        self.priority = priority
        self.mac = mac
        self.is_master_logging = is_master_logging
        self.run_overall_cycles = 0
        self.master_overall_cycles = 0

    def __repr__(self):
        return 'Node {} ip {}'.format(self.name, self.ip)


class SystemMonitor(db.Model, graphs.SystemMonitorGraph, DbEvent, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    cpu_usage_percent = db.Column(db.Float)
    cpu_temperature = db.Column(db.Float)
    memory_available_percent = db.Column(db.Float)
    uptime_days = db.Column(db.Integer)
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return '{} {} {}'.format(self.id, self.name, self.updated_on)


class Ups(db.Model, graphs.UpsGraph, DbEvent, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    system_name = db.Column(db.String(50))
    port = db.Column(db.String(50))
    input_voltage = db.Column(db.Float)
    remaining_minutes = db.Column(db.Float)
    output_voltage = db.Column(db.Float)
    load_percent = db.Column(db.Float)
    power_frequency = db.Column(db.Float)
    battery_voltage = db.Column(db.Float)
    temperature = db.Column(db.Float)
    power_failed = db.Column(db.Boolean(), default=False)
    beeper_on = db.Column(db.Boolean(), default=False)
    test_in_progress = db.Column(db.Boolean(), default=False)
    other_status = db.Column(db.String(50))
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return '{} {} {}'.format(self.id, self.name, self.updated_on)


class PowerMonitor(db.Model, graphs.UpsGraph, DbEvent, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    type = db.Column(db.String(50))  # INA, etc
    host_name = db.Column(db.String(50))
    voltage = db.Column(db.Float)  # volts
    current = db.Column(db.Float)  # miliamps
    power = db.Column(db.Float)
    max_voltage = db.Column(db.Float)
    warn_voltage = db.Column(db.Float)
    critical_voltage = db.Column(db.Float)
    min_voltage = db.Column(db.Float)
    warn_current = db.Column(db.Integer)
    critical_current = db.Column(db.Integer)
    i2c_addr = db.Column(db.String(50))
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return '{} {} {}'.format(self.id, self.name, self.updated_on)


class SystemDisk(db.Model, graphs.SystemDiskGraph, DbEvent, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    serial = db.Column(db.String(50), unique=True)
    system_name = db.Column(db.String(50))
    hdd_name = db.Column(db.String(50))  # netbook /dev/sda
    hdd_device = db.Column(db.String(50))  # usually empty?
    hdd_disk_dev = db.Column(db.String(50))  # /dev/sda
    temperature = db.Column(db.Float)
    sector_error_count = db.Column(db.Integer)
    smart_status = db.Column(db.String(50))
    power_status = db.Column(db.Integer)
    load_cycle_count = db.Column(db.Integer)
    start_stop_count = db.Column(db.Integer)
    last_reads_completed_count = db.Column(db.Float)
    last_reads_datetime = db.Column(db.DateTime())
    last_writes_completed_count = db.Column(db.Float)
    last_writes_datetime = db.Column(db.DateTime())
    last_reads_elapsed = db.Column(db.Float)
    last_writes_elapsed = db.Column(db.Float)
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now)

    def __init__(self):
        super(SystemDisk, self).__init__()
        self.hdd_disk_dev = ''

    def __repr__(self):
        return '{} {} {} {} {}'.format(self.id, self.serial, self.system_name, self.hdd_name, self.hdd_disk_dev)


class GpioPin(db.Model, DbEvent, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    host_name = db.Column(db.String(50))
    pin_type = db.Column(db.String(50))  # bbb, pi, piface
    pin_code = db.Column(db.String(50))  # friendly format, unique for host, Beagle = P9_11, PI = pin_index
    pin_index_bcm = db.Column(db.String(50))  # bcm format, 0 to n
    pin_value = db.Column(db.Integer)  # 0, 1 or None
    pin_direction = db.Column(db.String(4))  # in, out, None
    board_index = db.Column(db.Integer)  # 0 to n (max 3 for piface)
    description = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=False)  # if pin was setup(exported) through this app. will be unexported when app exit

    def __init__(self):
        super(GpioPin, self).__init__()

    def __repr__(self):
        return 'host={} code={} index={} type={} value={}'.format(self.host_name, self.pin_code, self.pin_index_bcm,
                                                                  self.pin_type, self.pin_value)


class ZoneAlarm(db.Model, DbEvent, DbBase):
    """not all gpios are alarm events, some are contacts, some are movement sensors"""
    # fixme: should be more generic, i.e. ZoneContact (with types = sensor, contact)
    id = db.Column(db.Integer, primary_key=True)
    # friendly display name for pin mapping
    alarm_pin_name = db.Column(db.String(50))
    zone_id = db.Column(db.Integer)  # , db.ForeignKey('zone.id'))
    # zone = db.relationship('Zone', backref=db.backref('ZoneAlarm(zone)', lazy='dynamic'))
    # gpio_pin_code = db.Column(db.String(50), db.ForeignKey('gpio_pin.pin_code'))
    gpio_pin_code = db.Column(db.String(50))
    gpio_host_name = db.Column(db.String(50))
    sensor_type = db.Column(db.String(25))
    # gpio_pin = db.relationship('GpioPin', backref=db.backref('ZoneAlarm(gpiopincode)', lazy='dynamic'))
    alarm_pin_triggered = db.Column(db.Boolean, default=False)  # True if alarm sensor is connected (move detected)
    is_false_alarm_prone = db.Column(db.Boolean, default=False)  # True if sensor can easily trigger false alarms (gate move by wind)
    start_alarm = db.Column(db.Boolean, default=False)  # True if alarm must start (because area/zone is armed)
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now)

    def __init__(self, zone_id='', gpio_pin_code='', host_name=''):
        super(ZoneAlarm, self).__init__()
        self.zone_id = zone_id
        self.gpio_pin_code = gpio_pin_code
        self.gpio_host_name = host_name

    def __repr__(self):
        return 'host:{} pin_name:{} host:{} pin:{} triggered:{}'.format(self.gpio_host_name, self.alarm_pin_name,
                                                                        self.gpio_host_name, self.gpio_pin_code,
                                                                        self.alarm_pin_triggered)


class ZoneHeatRelay(db.Model, DbEvent, DbBase, graphs.BaseGraph):
    id = db.Column(db.Integer, primary_key=True)
    # friendly display name for pin mapping
    heat_pin_name = db.Column(db.String(50))
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'))
    gpio_pin_code = db.Column(db.String(50))  # user friendly format, e.g. P8_11
    gpio_host_name = db.Column(db.String(50))
    heat_is_on = db.Column(db.Boolean, default=False)
    is_main_heat_source = db.Column(db.Boolean, default=False)
    is_alternate_source_switch = db.Column(db.Boolean, default=False)  # switch to alternate source
    is_alternate_heat_source = db.Column(db.Boolean, default=False)  # used for low cost/eco main heat sources

    temp_sensor_name = db.Column(db.String(50))  # temperature sensor name for heat sources to check for heat limit
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now)

    def __init__(self, zone_id=None, gpio_pin_code='', host_name=''):
        super(ZoneHeatRelay, self).__init__()
        self.zone_id = zone_id
        self.gpio_pin_code = gpio_pin_code
        self.gpio_host_name = host_name

    def __repr__(self):
        return 'host {} {} {} {}'.format(self.gpio_host_name, self.gpio_pin_code, self.heat_pin_name, self.heat_is_on)


class ZoneCustomRelay(db.Model, DbEvent, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    # friendly display name for pin mapping
    relay_pin_name = db.Column(db.String(50))
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'))
    gpio_pin_code = db.Column(db.String(50))  # user friendly format, e.g. P8_11
    gpio_host_name = db.Column(db.String(50))
    relay_is_on = db.Column(db.Boolean, default=False)
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now)

    def __init__(self, id=None, zone_id='', gpio_pin_code='', host_name='', relay_pin_name=''):
        super(ZoneCustomRelay, self).__init__()
        if id:
            self.id = id
        self.zone_id = zone_id
        self.gpio_pin_code = gpio_pin_code
        self.gpio_host_name = host_name
        self.relay_pin_name = relay_pin_name

    def __repr__(self):
        return 'host {} {} {} {}'.format(self.gpio_host_name, self.gpio_pin_code, self.relay_pin_name, self.relay_is_on)


class CommandOverrideRelay(db.Model, DbEvent, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    host_name = db.Column(db.String(50))
    is_gui_source = db.Column(db.Boolean, default=False)  # gui has priority over rule
    is_rule_source = db.Column(db.Boolean, default=False)
    relay_pin_name = db.Column(db.String(50))
    start_date = db.Column(db.DateTime(), default=datetime.now)
    end_date = db.Column(db.DateTime(), default=datetime.now)
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now)


class Rule(db.Model, DbEvent, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    host_name = db.Column(db.String(50))
    name = db.Column(db.String(50), unique=True)
    command = db.Column(db.String(50))
    hour = db.Column(db.String(20))
    minute = db.Column(db.String(2))
    second = db.Column(db.String(20))
    day_of_week = db.Column(db.String(20))
    week = db.Column(db.String(20))
    day = db.Column(db.String(20))
    month = db.Column(db.String(20))
    year = db.Column(db.String(20))
    start_date = db.Column(db.DateTime())
    execute_now = db.Column(db.Boolean, default=False)
    is_async = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '{} {}:{}'.format(self.is_active, self.name, self.command)

    def __init__(self, id='', host_name=''):
        # keep host name default to '' rather than None (which does not work on filter in)
        super(Rule, self).__init__()
        if id:
            self.id = id
        self.host_name = host_name


class PlotlyCache(db.Model, DbEvent, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    grid_name = db.Column(db.String(50), unique=True)
    grid_url = db.Column(db.String(250))
    column_name_list = db.Column(db.String(250))
    created_by_node_name = db.Column(db.String(50))
    announced_on = db.Column(db.DateTime())

    def __repr__(self):
        return '{} {}'.format(self.grid_name, self.grid_url)

    def __init__(self, id='', grid_name=''):
        # keep host name default to '' rather than None (which does not work on filter in)
        super(PlotlyCache, self).__init__()
        if id:
            self.id = id
        self.grid_name = grid_name


class Utility(db.Model, graphs.BaseGraph, DbEvent, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    utility_name = db.Column(db.String(50))  # unique name, can be different than sensor name for dual counter
    sensor_name = db.Column(db.String(50), db.ForeignKey('sensor.sensor_name'))
    sensor_index = db.Column(db.Integer)  # 0 for counter_a, 1 for counter_b
    units_total = db.Column(db.Float)  # total number of units measured
    units_delta = db.Column(db.Float)  # total number of units measured since last measurement
    units_2_delta = db.Column(db.Float)  # total number of units measured since last measurement
    ticks_delta = db.Column(db.BigInteger)
    ticks_per_unit = db.Column(db.Float, default=1)  # number of counter ticks in a unit (e.g. 10 for a watt)
    unit_name = db.Column(db.String(50))  # kwh, liter etc.
    unit_2_name = db.Column(db.String(50))  # 2nd unit type, optional, i.e. watts
    unit_cost = db.Column(db.Float)
    cost = db.Column(db.Float)
    utility_type = db.Column(db.String(50))  # water, electricity, gas
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now)

    def __init__(self, sensor_name=''):
        super(Utility, self).__init__()
        self.sensor_name = sensor_name

    def __repr__(self):
        return '{} {} {}'.format(self.id, self.utility_name, self.updated_on)


class State(db.Model, DbEvent, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    entry_name = db.Column(db.String(50))  # unique name
    entry_value = db.Column(db.String(50))
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now)

    def __init__(self, entry_name=''):
        super(State, self).__init__()
        self.entry_name = entry_name

    def __repr__(self):
        return '{} {} {}'.format(self.id, self.entry_name, self.entry_value)


class Device(db.Model, DbEvent, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))  # unique name
    type = db.Column(db.String(50))
    bt_address = db.Column(db.String(50))
    wifi_address = db.Column(db.String(50))
    bt_signal = db.Column(db.Integer)
    wifi_signal = db.Column(db.Integer)
    last_bt_active = db.Column(db.DateTime())
    last_wifi_active = db.Column(db.DateTime())
    last_active = db.Column(db.DateTime())
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now)

    def __init__(self, name=''):
        super(Device, self).__init__()
        self.name = name

    def __repr__(self):
        return '{} {}'.format(self.id, self.name)


class People(db.Model, DbEvent, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))  # unique name
    email = db.Column(db.String(50))
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now)

    def __init__(self, name=''):
        super(People, self).__init__()
        self.name = name

    def __repr__(self):
        return '{} {}'.format(self.id, self.name)


class PeopleDevice(db.Model, DbEvent, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    people_id = db.Column(db.Integer)
    device_id = db.Column(db.Integer)
    give_presence = db.Column(db.Boolean, default=False)
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now)


class Position(db.Model, DbEvent, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer)
    latitude = db.Column(db.String(20))
    longitude = db.Column(db.String(20))
    altitude = db.Column(db.Float)
    hspeed = db.Column(db.Float)
    vspeed = db.Column(db.Float)
    hprecision = db.Column(db.Integer)
    vprecision = db.Column(db.Integer)
    battery = db.Column(db.Integer)
    satellite = db.Column(db.Integer)
    satellite_valid = db.Column(db.Integer)
    updated_on = db.Column(db.DateTime())

'''
tables used to store historical data
column names must match the source model names as save is done automatically
'''


class NodeHistory(db.Model, DbBase):
    __bind_key__ = 'reporting'
    __tablename__ = 'node_history'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    master_overall_cycles = db.Column(db.Integer)  # count of update cycles while node was master
    run_overall_cycles = db.Column(db.Integer)  # count of total update cycles
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now, index=True)
    source_host_ = db.Column(db.String(50))

    def __repr__(self):
        return '{} {}'.format(self.id, self.name)


class SensorHistory(db.Model, DbBase):
    __bind_key__ = 'reporting'
    __tablename__ = 'sensor_history'
    id = db.Column(db.Integer, primary_key=True)
    sensor_name = db.Column(db.String(50), index=True)
    address = db.Column(db.String(50))
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    counters_a = db.Column(db.BigInteger)
    counters_b = db.Column(db.BigInteger)
    delta_counters_a = db.Column(db.BigInteger)
    delta_counters_b = db.Column(db.BigInteger)
    iad = db.Column(db.Float)
    vdd = db.Column(db.Float)
    vad = db.Column(db.Float)
    pio_a = db.Column(db.Integer)
    pio_b = db.Column(db.Integer)
    sensed_a = db.Column(db.Integer)
    sensed_b = db.Column(db.Integer)
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now, index=True)
    added_on = db.Column(db.DateTime(), default=datetime.now)
    source_host_ = db.Column(db.String(50))

    def __repr__(self):
        return '{} {} adr={} t={} ca={} cb={}'.format(self.id, self.sensor_name, self.address, self.temperature,
                                                      self.counters_a, self.counters_b)


class SensorErrorHistory(db.Model, DbBase):
    __bind_key__ = 'reporting'
    __tablename__ = 'sensor_error_history'
    id = db.Column(db.Integer, primary_key=True)
    sensor_name = db.Column(db.String(50), index=True)
    error_type = db.Column(db.Integer)  # 0=not found, 1=other err
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now, index=True)

    def __repr__(self):
        return '{} {}'.format(self.id, self.sensor_name)


class SystemMonitorHistory(db.Model, DbBase):
    __bind_key__ = 'reporting'
    __tablename__ = 'systemmonitor_history'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), index=True)
    cpu_usage_percent = db.Column(db.Float)
    cpu_temperature = db.Column(db.Float)
    memory_available_percent = db.Column(db.Float)
    uptime_days = db.Column(db.Integer)
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now, index=True)
    source_host_ = db.Column(db.String(50))

    def __repr__(self):
        return '{} {} {}'.format(self.id, self.name, self.updated_on)


class UpsHistory(db.Model, DbBase):
    __bind_key__ = 'reporting'
    __tablename__ = 'ups_history'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    system_name = db.Column(db.String(50))
    port = db.Column(db.String(50))
    input_voltage = db.Column(db.Float)
    remaining_minutes = db.Column(db.Float)
    output_voltage = db.Column(db.Float)
    load_percent = db.Column(db.Float)
    power_frequency = db.Column(db.Float)
    battery_voltage = db.Column(db.Float)
    temperature = db.Column(db.Float)
    power_failed = db.Column(db.Boolean(), default=False)
    beeper_on = db.Column(db.Boolean(), default=False)
    test_in_progress = db.Column(db.Boolean(), default=False)
    other_status = db.Column(db.String(50))
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now, index=True)
    source_host_ = db.Column(db.String(50))

    def __repr__(self):
        return '{} {} {}'.format(self.id, self.name, self.updated_on)


class SystemDiskHistory(db.Model, DbBase):
    __bind_key__ = 'reporting'
    __tablename__ = 'systemdisk_history'  # convention: append '_history' -> 'History' to source table name
    id = db.Column(db.Integer, primary_key=True)
    serial = db.Column(db.String(50))
    system_name = db.Column(db.String(50))
    hdd_name = db.Column(db.String(50))  # netbook /dev/sda
    hdd_device = db.Column(db.String(50))  # usually empty?
    hdd_disk_dev = db.Column(db.String(50))  # /dev/sda
    temperature = db.Column(db.Float)
    sector_error_count = db.Column(db.Integer)
    smart_status = db.Column(db.String(50))
    power_status = db.Column(db.Integer)
    load_cycle_count = db.Column(db.Integer)
    start_stop_count = db.Column(db.Integer)
    last_reads_completed_count = db.Column(db.Float)
    last_reads_datetime = db.Column(db.DateTime())
    last_writes_completed_count = db.Column(db.Float)
    last_writes_datetime = db.Column(db.DateTime())
    last_reads_elapsed = db.Column(db.Float)
    last_writes_elapsed = db.Column(db.Float)
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now, index=True)
    source_host_ = db.Column(db.String(50))

    def __init__(self):
        super(SystemDiskHistory, self).__init__()
        self.hdd_disk_dev = ''

    def __repr__(self):
        return '{} {} {} {} {}'.format(self.id, self.serial, self.system_name, self.hdd_name, self.hdd_disk_dev)


class PresenceHistory(db.Model, DbBase):
    __bind_key__ = 'reporting'
    __tablename__ = 'presence_history'  # convention: append '_history' -> 'History' to source table name
    id = db.Column(db.Integer, primary_key=True)
    zone_name = db.Column(db.String(50))
    sensor_name = db.Column(db.String(50))
    event_type = db.Column(db.String(25)) # cam, pir, contact, wifi, bt
    event_camera_date = db.Column(db.DateTime(), default=None)
    event_alarm_date = db.Column(db.DateTime(), default=None)
    event_io_date = db.Column(db.DateTime(), default=None)
    # event_wifi_date = db.Column(db.DateTime(), default=None)
    # event_bt_date = db.Column(db.DateTime(), default=None)
    is_connected = db.Column(db.Boolean, default=False)  # pin connected? true on unarmed sensors, false on alarm/move
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now, index=True)
    source_host_ = db.Column(db.String(50))

    def __repr__(self):
        return 'PresenceHistory zone {} sensor {} connected {} type {}'.format(
            self.zone_name, self.sensor_name, self.is_connected, self.event_type)


class UtilityHistory(db.Model, DbBase):
    __bind_key__ = 'reporting'
    __tablename__ = 'utility_history'  # convention: append '_history' -> 'History' to source table name
    id = db.Column(db.Integer, primary_key=True)
    utility_name = db.Column(db.String(50), index=True)
    sensor_name = db.Column(db.String(50), index=True)
    units_total = db.Column(db.Float)  # total number of units measured
    units_delta = db.Column(db.Float)  # total number of units measured since last measurement
    units_2_delta = db.Column(db.Float)  # total number of units measured since last measurement
    ticks_delta = db.Column(db.BigInteger)
    cost = db.Column(db.Float)
    unit_name = db.Column(db.String(50))  # kwh, liter etc.
    unit_2_name = db.Column(db.String(50))  # watt
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now, index=True)
    source_host_ = db.Column(db.String(50))


class ZoneHeatRelayHistory(db.Model, DbBase):
    __bind_key__ = 'reporting'
    __tablename__ = 'zoneheatrelay_history'  # convention: append '_history' -> 'History' to source table name
    id = db.Column(db.Integer, primary_key=True)
    heat_pin_name = db.Column(db.String(50))
    gpio_host_name = db.Column(db.String(50))
    heat_is_on = db.Column(db.Boolean, default=False)
    updated_on = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now)
