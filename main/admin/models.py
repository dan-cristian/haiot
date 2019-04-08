from datetime import datetime
import traceback
import sys
from copy import deepcopy
from main.logger_helper import L
#from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, BigInteger
from main import db
#from main import Base
from common import Constant
import graphs
from common import utils, performance
from pydispatch import dispatcher
from main.admin.model_helper import commit
from sqlalchemy.orm import attributes

Column = db.Column
Integer = db.Integer
BigInteger = db.BigInteger
String = db.String
Float = db.Float
Boolean = db.Boolean
DateTime = db.DateTime
ForeignKey = db.ForeignKey
Base = db.Model

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
                self.save_changed_fields(current_record=current_record, new_record=new_record, debug=debug,
                                         notify_transport_enabled=False, save_to_graph=False)
                # db.session.commit()
            else:
                L.l.warning('Unique key not found in json record, save aborted')
        except Exception as ex:
            L.l.error('Exception save json to db {}'.format(ex))

    # graph_save_frequency in seconds
    def save_changed_fields(self, current_record=None, new_record=None, notify_transport_enabled=False,
                            save_to_graph=False, ignore_only_updated_on_change=True, debug=False,
                            graph_save_frequency=0, save_all_fields=False, force_dirty=False):
        _start_time = utils.get_base_location_now_date()
        try:
            if debug:
                pass
            if new_record is None:
                new_record = self
            # inherit BaseGraph to enable persistence
            # if hasattr(self, 'save_to_graph'):  # not all models inherit graph, used for periodic save
            if current_record is not None:
                # if a record in db already exists
                if not hasattr(current_record, 'last_save_to_graph') or current_record.last_save_to_graph is None:
                    current_record.last_save_to_graph = datetime.min
                save_to_graph_elapsed = (utils.get_base_location_now_date() -
                                         current_record.last_save_to_graph).total_seconds()
                if save_to_graph_elapsed > graph_save_frequency:
                    if debug:
                        L.l.info('Saving to graph record {}'.format(new_record))
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
            new_record.save_to_graph = save_to_graph
            new_record.notify_transport_enabled = notify_transport_enabled
            # reset to avoid duplication
            new_record.last_commit_field_changed_list = []
            changed_fields = []
            if current_record is not None:
                # ensure is set for both new and existing records
                current_record.save_to_history = save_to_graph
                current_record.last_commit_field_changed_list = []
                current_record.notify_transport_enabled = notify_transport_enabled
                # for column in new_record.query.statement._columns._all_columns: # this iter skips class attributes
                for column in utils.get_primitives(new_record):
                    column_name = str(column)
                    new_value = getattr(new_record, column_name)
                    if hasattr(current_record, column_name):
                        old_value = getattr(current_record, column_name)
                        if debug:
                            L.l.info('DEBUG process Col={} New={} Old={} Saveall={}'.format(
                                column_name, new_value, old_value, save_all_fields))
                        # fixme: comparison not working for float, because str appends .0
                        # if ((new_value is not None) and (str(old_value) != str(new_value)))

                        if ((new_value is not None) and (old_value != new_value)) \
                                or (save_all_fields and (new_value is not None)):
                            if column_name != Constant.DB_FIELD_UPDATE:
                                try:
                                    obj_type = str(type(self)).split('\'')[1]
                                    obj_type_words = obj_type.split('.')
                                    obj_type = obj_type_words[len(obj_type_words) - 1]
                                except Exception as ex:
                                    obj_type = str(type(self))
                            else:
                                pass
                            if column_name != "id":  # do not change primary key with None
                                setattr(current_record, column_name, new_value)
                                # https://stackoverflow.com/questions/41879671/marking-an-object-as-clean-in-sqlalchemy-orm
                                if force_dirty:
                                    attributes.set_attribute(current_record, column_name, new_value)
                                # current_record.last_commit_field_changed_list.append(column_name)
                                changed_fields.append(column_name)
                                if debug:
                                    L.l.info('DEBUG CHANGE COL={} old={} new={}'.format(column_name, old_value, new_value))
                        else:
                            if debug:
                                L.l.info('DEBUG NOT change col={}'.format(column_name))
                    else:
                        L.l.error('Unexpected field {} at savechanged in rec {}'.format(column_name, new_record))
                for field in changed_fields:
                    current_record.last_commit_field_changed_list.append(field)
                fields_changed_len = len(current_record.last_commit_field_changed_list)
                if debug:
                    L.l.info('DEBUG len changed fields={}'.format(fields_changed_len))
                if fields_changed_len == 0:
                    current_record.notify_transport_enabled = False
                # fixme: remove hardcoded field name
                elif fields_changed_len == 1 and ignore_only_updated_on_change and \
                        Constant.DB_FIELD_UPDATE in current_record.last_commit_field_changed_list:
                    current_record.notify_transport_enabled = False
            else:
                new_record.notify_transport_enabled = notify_transport_enabled
                for column in utils.get_primitives(new_record):
                    column_name = str(column)
                    new_value = getattr(new_record, column_name)
                    if new_value:
                        new_record.last_commit_field_changed_list.append(column_name)
                if debug:
                    L.l.info('DEBUG new record={}'.format(new_record))
                fields_changed_len = len(new_record.last_commit_field_changed_list)
                db.session.add(new_record)
            # fixme: remove hardcoded field name
            if hasattr(new_record, 'last_save_to_graph'):
                if current_record is not None:
                    current_record.last_save_to_graph = utils.get_base_location_now_date()
                new_record.last_save_to_graph = utils.get_base_location_now_date()
            # signal other modules we have a new record to process (i.e. upload to cloud)
            if save_to_graph:
                dispatcher.send(signal=Constant.SIGNAL_STORABLE_RECORD, new_record=new_record,
                                current_record=current_record)
            if debug:
                pass
            if fields_changed_len > 0 and len(db.session.dirty) == 0 and len(db.session.new) == 0:
                L.l.warning("Warning, fields={} but empty commit rec={}".format(fields_changed_len, current_record))
                # db.session.merge(current_record)
                pass
            commit()
        except Exception as ex:
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
    source_host_ = None
    event_sent_datetime = None
    is_event_external = None

    operation_type = None
    last_commit_field_changed_list = []

    def get_deepcopy(self):
        return deepcopy(self)

    def commit_record_to_db_notify(self):
        self.notify_transport_enabled = True
        return commit()

    # def json_to_record(self, json_object):
    #    return utils.json_to_record(self, json_object)


class DbHistory:
    record_uuid = Column(String(36))
    #source_host_ = Column(String(50)) # moved to dbase

    def __init__(self):
        pass


class Module(Base, DbBase):
    __tablename__ = 'module'
    id = Column(Integer, primary_key=True)
    host_name = Column(String(50))
    name = Column(String(50))
    active = Column(Boolean, default=False)  # does not work well as Boolean due to all values by default are True
    start_order = Column(Integer)

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


class Zone(Base, DbBase):
    __tablename__ = 'zone'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    # active_heat_schedule_pattern_id = Column(Integer)
    # heat_is_on = Column(Boolean, default=False)
    # last_heat_status_update = Column(DateTime(), default=None)
    # heat_target_temperature = Column(Integer)
    is_indoor_heated = Column(Boolean)
    is_indoor = Column(Boolean)
    is_outdoor = Column(Boolean)
    is_outdoor_heated = Column(Boolean)

    def __init__(self, id='', name=''):
        super(Zone, self).__init__()
        if id:
            self.id = id
        self.name = name

    def __repr__(self):
        return 'Zone id {} {}'.format(self.id, self.name[:20])


class Area(Base, DbBase):
    __tablename__ = 'area'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    is_armed = Column(Boolean, default=False)

    def __init__(self, id='', name=''):
        super(Area, self).__init__()
        if id:
            self.id = id
        self.name = name

    def __repr__(self):
        return 'Area id {} {} armed={}'.format(self.id, self.name[:20], self.is_armed)


class ZoneArea(Base, DbBase):
    __tablename__ = 'zone_area'
    id = Column(Integer, primary_key=True)
    area_id = Column(Integer, ForeignKey('area.id'), nullable=False)
    zone_id = Column(Integer, ForeignKey('zone.id'), nullable=False)

    def __init__(self, id=''):
        super(ZoneArea, self).__init__()
        if id:
            self.id = id

    def __repr__(self):
        return 'ZoneArea id {} zone={} area={}'.format(self.id, self.zone_id, self.area_id)


class ZoneMusic(Base, DbBase):
    __tablename__ = 'zone_music'
    id = Column(Integer, primary_key=True)
    zone_id = Column(Integer, ForeignKey('zone.id'), nullable=False)
    server_ip = Column(String(15))
    server_port = Column(Integer)

    def __init__(self, id=''):
        super(ZoneMusic, self).__init__()
        if id:
            self.id = id

    def __repr__(self):
        return 'ZoneMusic id {} zone={} port={}'.format(self.id, self.zone_id, self.area_id)


class Presence(Base, DbBase, DbEvent):
    __tablename__ = 'presence'
    id = Column(Integer, primary_key=True)
    zone_id = Column(Integer, ForeignKey('zone.id'), nullable=False)
    zone_name = Column(String(50))
    sensor_name = Column(String(50))
    event_type = Column(String(25))  # cam, pir, contact, wifi, bt
    event_camera_date = Column(DateTime(), default=None)
    event_alarm_date = Column(DateTime(), default=None)
    event_io_date = Column(DateTime(), default=None)
    event_wifi_date = Column(DateTime(), default=None)
    event_bt_date = Column(DateTime(), default=None)
    is_connected = Column(Boolean, default=False)  # pin connected? true on unarmed sensors, false on alarm/move
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)

    def __init__(self, zone_id=None):
        super(Presence, self).__init__()

    def __repr__(self):
        return 'Presence id {} zone_id {} sensor {} connected {}'.format(
            self.id, self.zone_id, self.sensor_name, self.is_connected)


class SchedulePattern(Base, DbBase):
    __tablename__ = 'schedule_pattern'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    pattern = Column(String(24))
    keep_warm = Column(Boolean, default=False)  # keep the zone warm, used for cold floors
    keep_warm_pattern = Column(String(12))  # pattern, 5 minutes increments of on/off: 100001000100
    activate_on_condition = Column(Boolean, default=False)  # activate heat only if relay state condition is meet
    activate_condition_relay = Column(String(50))  # the relay that must be on to activate this schedule pattern
    season_name = Column(String(50))  # season name when this will apply
    main_source_needed = Column(Boolean, default=True)  # main source must be on as well (i.e. gas heater)

    def __init__(self, id=None, name='', pattern=''):
        super(SchedulePattern, self).__init__()
        if id:
            self.id = id
        self.name = name
        self.pattern = pattern

    def __repr__(self):
        return self.name[:len('1234-5678-9012-3456-7890-1234')]


class TemperatureTarget(Base, DbBase):
    __tablename__ = 'temperature_target'
    id = Column(Integer, primary_key=True)
    code = Column(String(1))
    target = Column(Float)

    def __init__(self, id=None, code='', target=''):
        super(TemperatureTarget, self).__init__()
        if id:
            self.id = id
        self.code = code
        self.target = target

    def __repr__(self):
        return '{} code {}={}'.format(self.id, self.code, self.target)


class ZoneThermostat(Base, DbBase):
    __tablename__ = 'zone_thermostat'
    id = Column(Integer, primary_key=True)
    zone_id = Column(Integer)
    zone_name = Column(String(50))
    active_heat_schedule_pattern_id = Column(Integer)
    heat_is_on = Column(Boolean, default=False)
    last_heat_status_update = Column(DateTime(), default=None)
    heat_target_temperature = Column(Float)
    mode_presence_auto = Column(Boolean, default=False)  # fixme: not used yet
    last_presence_set = Column(DateTime())
    is_mode_manual = Column(Boolean, default=False)
    manual_duration_min = Column(Integer, default=120)  # period to keep heat on for manual mode
    manual_temp_target = Column(Float)
    last_manual_set = Column(DateTime())

    def __repr__(self):
        return '{} zoneid={} name={} target={}'.format(self.id, self.zone_id, self.zone_name,
                                                       self.heat_target_temperature)


class HeatSchedule(Base, DbBase):
    __tablename__ = 'heat_schedule'
    id = Column(Integer, primary_key=True)
    zone_id = Column(Integer, ForeignKey('zone.id'), nullable=False)
    # zone = db.relationship('Zone', backref=db.backref('heat schedule zone', lazy='dynamic'))
    pattern_week_id = Column(Integer, ForeignKey('schedule_pattern.id'), nullable=False)
    pattern_weekend_id = Column(Integer, ForeignKey('schedule_pattern.id'), nullable=False)
    ''' temp pattern if there is move in a zone, to ensure there is heat if someone is at home unplanned'''
    pattern_id_presence = Column(Integer)
    ''' temp pattern if there is no move, to preserve energy'''
    pattern_id_no_presence = Column(Integer)
    season = Column(String(50))  # season name when this schedule will apply
    # active = Column(Boolean, default=True)

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
        return 'Zone {}, Week {}, Weekend {}'.format(self.zone_id, self.pattern_week_id, self.pattern_weekend_id)


class Sensor(Base, graphs.SensorGraph, DbEvent, DbBase):
    __tablename__ = 'sensor'
    id = Column(Integer, primary_key=True)
    address = Column(String(50), unique=True)
    type = Column(String(50))
    temperature = Column(Float)
    humidity = Column(Float)
    pressure = Column(Float)
    counters_a = Column(BigInteger)
    counters_b = Column(BigInteger)
    delta_counters_a = Column(BigInteger)
    delta_counters_b = Column(BigInteger)
    iad = Column(Float)  # current in Amper for qubino sensors
    vdd = Column(Float)  # power factor for qubino sensors
    vad = Column(Float)  # voltage in Volts for qubino sensors
    pio_a = Column(Integer)
    pio_b = Column(Integer)
    sensed_a = Column(Integer)
    sensed_b = Column(Integer)
    battery_level = Column(Integer)  # RFXCOM specific, sensor battery
    rssi = Column(Integer)  # RFXCOM specific, rssi - distance
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)
    added_on = Column(DateTime(), default=datetime.now)
    # FIXME: now filled manually, try relations
    # zone_name = Column(String(50))
    sensor_name = Column(String(50))
    alt_address = Column(String(50)) # alternate address format, use for 1-wire, better readability
    comment = Column(String(50))

    def __init__(self, address='', sensor_name=''):
        super(Sensor, self).__init__()
        self.address = address
        self.sensor_name = sensor_name

    def __repr__(self):
        return '{}, {}, {}, {}'.format(self.type, self.sensor_name, self.address, self.temperature)


class DustSensor(Base, DbEvent, DbBase, graphs.BaseGraph):
    __tablename__ = 'dust_sensor'
    id = Column(Integer, primary_key=True)
    address = Column(String(50), unique=True)
    pm_1 = Column(Integer)
    pm_2_5 = Column(Integer)
    pm_10 = Column(Integer)
    p_0_3 = Column(Integer)
    p_0_5 = Column(Integer)
    p_1 = Column(Integer)
    p_2_5 = Column(Integer)
    p_5 = Column(Integer)
    p_10 = Column(Integer)
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)

    def __init__(self):
        super(DustSensor, self).__init__()

    def __repr__(self):
        return '{}'.format(self.address)


class SensorError(Base, DbBase, DbEvent):
    __tablename__ = 'sensor_error'
    id = Column(Integer, primary_key=True)
    sensor_name = Column(String(50), index=True)
    sensor_address = Column(String(50))
    error_type = Column(Integer)  # 0=not found, 1=other err
    error_count = Column(Integer)
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now, index=True)

    def __repr__(self):
        return '{} {} errors={}'.format(self.id, self.sensor_name, self.error_count)


class Parameter(Base, DbBase):
    __tablename__ = 'parameter'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    value = Column(String(255))
    description = Column(String(255))

    def __init__(self, id=None, name='default', value='default'):
        super(Parameter, self).__init__()
        if id:
            self.id = id
        self.name = name
        self.value = value

    def __repr__(self):
        return '{}, {}'.format(self.name, self.value)


class ZoneSensor(Base, DbBase):
    __tablename__ = 'zone_sensor'
    id = Column(Integer, primary_key=True)
    sensor_name = Column(String(50))
    zone_id = Column(Integer, ForeignKey('zone.id'))
    # zone = db.relationship('Zone', backref=db.backref('ZoneSensor(zone)', lazy='dynamic'))
    sensor_address = Column(String(50), ForeignKey('sensor.address'))
    target_material = Column(String(50))  # what material is being measured, water, air, etc
    alt_address = Column(String(50))
    is_main = Column(Boolean(), default=False)  # is main temperature sensor for heat reference
    # priority = Column(Integer, default=0)  # if multiple sensors exists - i.e. temperature
    # sensor = db.relationship('Sensor', backref=db.backref('ZoneSensor(sensor)', lazy='dynamic'))

    def __init__(self, zone_id='', sensor_address='', sensor_name=''):
        super(ZoneSensor, self).__init__()
        self.sensor_address = sensor_address
        self.zone_id = zone_id
        self.sensor_name = sensor_name

    def __repr__(self):
        return 'ZoneSensor zone {} sensor {}'.format(self.zone_id, self.sensor_name)


class Node(Base, DbEvent, DbBase):
    __tablename__ = 'node'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    ip = Column(String(15))
    mac = Column(String(17))
    os_type = Column(String(50))
    machine_type = Column(String(50))
    app_start_time = Column(DateTime())
    is_master_overall = Column(Boolean(), default=False)
    is_master_db_archive = Column(Boolean(), default=False)
    is_master_graph = Column(Boolean(), default=False)
    is_master_rule = Column(Boolean(), default=False)
    is_master_logging = Column(Boolean(), default=False)
    priority = Column(Integer)  # used to decide who becomes main master in case several hosts are active
    master_overall_cycles = Column(Integer)  # count of update cycles while node was master
    run_overall_cycles = Column(Integer)  # count of total update cycles
    execute_command = Column(String(50))
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)

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


class SystemMonitor(Base, graphs.SystemMonitorGraph, DbEvent, DbBase):
    __tablename__ = 'system_monitor'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    cpu_usage_percent = Column(Float)
    cpu_temperature = Column(Float)
    memory_available_percent = Column(Float)
    uptime_days = Column(Integer)
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return '{} {} {}'.format(self.id, self.name, self.updated_on)


class Ups(Base, graphs.UpsGraph, DbEvent, DbBase):
    __tablename__ = 'ups'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    system_name = Column(String(50))
    port = Column(String(50))
    input_voltage = Column(Float)
    remaining_minutes = Column(Float)
    output_voltage = Column(Float)
    load_percent = Column(Float)
    power_frequency = Column(Float)
    battery_voltage = Column(Float)
    temperature = Column(Float)
    power_failed = Column(Boolean(), default=False)
    beeper_on = Column(Boolean(), default=False)
    test_in_progress = Column(Boolean(), default=False)
    other_status = Column(String(50))
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return '{} {} {}'.format(self.id, self.name, self.updated_on)


class PowerMonitor(Base, graphs.UpsGraph, DbEvent, DbBase):
    __tablename__ = 'power_monitor'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    type = Column(String(50))  # INA, etc
    host_name = Column(String(50))
    voltage = Column(Float)  # volts, estimated voltage when using divider and batteries in series
    current = Column(Float)  # miliamps
    power = Column(Float)
    raw_voltage = Column(Float)  # volts, read from sensor without
    max_voltage = Column(Float)
    warn_voltage = Column(Float)
    critical_voltage = Column(Float)
    min_voltage = Column(Float)
    warn_current = Column(Integer)
    critical_current = Column(Integer)
    i2c_addr = Column(String(50))
    voltage_divider_ratio = Column(Float)  # divider (0.5 etc)
    subtracted_sensor_id_list = Column(String(50))  # comma separated sensor ids, total voltage to be subtracted
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)

    def __init__(self):
        super(PowerMonitor, self).__init__()

    def __repr__(self):
        return '{} {} v={} {}'.format(self.id, self.name, self.voltage, self.updated_on)


class SystemDisk(Base, graphs.SystemDiskGraph, DbEvent, DbBase):
    __tablename__ = 'system_disk'
    id = Column(Integer, primary_key=True)
    serial = Column(String(50), unique=True)
    system_name = Column(String(50))
    hdd_name = Column(String(50))  # netbook /dev/sda
    hdd_device = Column(String(50))  # usually empty?
    hdd_disk_dev = Column(String(50))  # /dev/sda
    temperature = Column(Float)
    sector_error_count = Column(Integer)
    smart_status = Column(String(50))
    power_status = Column(Integer)
    load_cycle_count = Column(Integer)
    start_stop_count = Column(Integer)
    last_reads_completed_count = Column(Float)
    last_reads_datetime = Column(DateTime())
    last_writes_completed_count = Column(Float)
    last_writes_datetime = Column(DateTime())
    last_reads_elapsed = Column(Float)
    last_writes_elapsed = Column(Float)
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)

    def __init__(self):
        super(SystemDisk, self).__init__()
        self.hdd_disk_dev = ''

    def __repr__(self):
        return '{} {} {} {} {}'.format(self.id, self.serial, self.system_name, self.hdd_name, self.hdd_disk_dev)


class GpioPin(Base, DbEvent, DbBase):
    __tablename__ = 'gpio_pin'
    id = Column(Integer, primary_key=True)
    host_name = Column(String(50))
    pin_type = Column(String(50))  # bbb, pi, piface
    pin_code = Column(String(50))  # friendly format, unique for host, Beagle = P9_11, PI = pin_index
    pin_index_bcm = Column(String(50))  # bcm format, 0 to n
    pin_value = Column(Integer)  # 0, 1 or None
    pin_direction = Column(String(4))  # in, out, None
    board_index = Column(Integer)  # 0 to n (max 3 for piface)
    description = Column(String(50))
    is_active = Column(Boolean, default=False)  # if pin was setup(exported) through this app. will be unexported when app exit
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)

    def __init__(self):
        super(GpioPin, self).__init__()

    def __repr__(self):
        return 'id {} host={} code={} index={} type={} value={}'.format(
            self.id, self.host_name, self.pin_code, self.pin_index_bcm, self.pin_type, self.pin_value)


class ZoneAlarm(Base, DbEvent, DbBase):
    __tablename__ = 'zone_alarm'
    """not all gpios are alarm events, some are contacts, some are movement sensors"""
    # fixme: should be more generic, i.e. ZoneContact (with types = sensor, contact)
    id = Column(Integer, primary_key=True)
    # friendly display name for pin mapping
    alarm_pin_name = Column(String(50))
    zone_id = Column(Integer)  # , ForeignKey('zone.id'))
    # zone = db.relationship('Zone', backref=db.backref('ZoneAlarm(zone)', lazy='dynamic'))
    # gpio_pin_code = Column(String(50), ForeignKey('gpio_pin.pin_code'))
    gpio_pin_code = Column(String(50))
    gpio_host_name = Column(String(50))
    sensor_type = Column(String(25))
    # gpio_pin = db.relationship('GpioPin', backref=db.backref('ZoneAlarm(gpiopincode)', lazy='dynamic'))
    alarm_pin_triggered = Column(Boolean, default=False)  # True if alarm sensor is connected (move detected)
    is_false_alarm_prone = Column(Boolean, default=False)  # True if sensor can easily trigger false alarms (gate move by wind)
    start_alarm = Column(Boolean, default=False)  # True if alarm must start (because area/zone is armed)
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)

    def __init__(self, zone_id='', gpio_pin_code='', host_name=''):
        super(ZoneAlarm, self).__init__()
        self.zone_id = zone_id
        self.gpio_pin_code = gpio_pin_code
        self.gpio_host_name = host_name

    def __repr__(self):
        return 'host:{} pin_name:{} host:{} pin:{} triggered:{}'.format(
            self.gpio_host_name, self.alarm_pin_name, self.gpio_host_name, self.gpio_pin_code, self.alarm_pin_triggered)


class ZoneHeatRelay(Base, DbEvent, DbBase, graphs.BaseGraph):
    __tablename__ = 'zone_heat_relay'
    id = Column(Integer, primary_key=True)
    # friendly display name for pin mapping
    heat_pin_name = Column(String(50))
    zone_id = Column(Integer, ForeignKey('zone.id'))
    gpio_pin_code = Column(String(50))  # user friendly format, e.g. P8_11
    gpio_host_name = Column(String(50))
    heat_is_on = Column(Boolean, default=False)
    is_main_heat_source = Column(Boolean, default=False)
    is_alternate_source_switch = Column(Boolean, default=False)  # switch to alternate source
    is_alternate_heat_source = Column(Boolean, default=False)  # used for low cost/eco main heat sources

    temp_sensor_name = Column(String(50))  # temperature sensor name for heat sources to check for heat limit
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)

    def __init__(self, zone_id=None, gpio_pin_code='', host_name=''):
        super(ZoneHeatRelay, self).__init__()
        self.zone_id = zone_id
        self.gpio_pin_code = gpio_pin_code
        self.gpio_host_name = host_name

    def __repr__(self):
        return 'host {} {} {} {}'.format(self.gpio_host_name, self.gpio_pin_code, self.heat_pin_name, self.heat_is_on)


class ZoneCustomRelay(Base, DbEvent, DbBase):
    __tablename__ = 'zone_custom_relay'
    id = Column(Integer, primary_key=True)
    # friendly display name for pin mapping
    relay_pin_name = Column(String(50))
    zone_id = Column(Integer, ForeignKey('zone.id'))
    gpio_pin_code = Column(String(50))  # user friendly format, e.g. P8_11
    gpio_host_name = Column(String(50))
    relay_is_on = Column(Boolean, default=False)
    relay_type = Column(String(20))
    expire = Column(Integer)  # after how many seconds state goes back to original state
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)

    def __init__(self, id=None, zone_id=None, gpio_pin_code=None, gpio_host_name=None, relay_pin_name=None):
        super(ZoneCustomRelay, self).__init__()
        if id:
            self.id = id
        self.zone_id = zone_id
        self.gpio_pin_code = gpio_pin_code
        self.gpio_host_name = gpio_host_name
        self.relay_pin_name = relay_pin_name

    def __repr__(self):
        return 'id {} host {} {} {} {}'.format(self.id, self.gpio_host_name, self.gpio_pin_code, self.relay_pin_name,
                                               self.relay_is_on)


class CommandOverrideRelay(Base, DbEvent, DbBase):
    __tablename__ = 'command_overide_relay'
    id = Column(Integer, primary_key=True)
    host_name = Column(String(50))
    is_gui_source = Column(Boolean, default=False)  # gui has priority over rule
    is_rule_source = Column(Boolean, default=False)
    relay_pin_name = Column(String(50))
    start_date = Column(DateTime(), default=datetime.now)
    end_date = Column(DateTime(), default=datetime.now)
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)


class Rule(Base, DbEvent, DbBase):
    __tablename__ = 'rule'
    id = Column(Integer, primary_key=True)
    host_name = Column(String(50))
    name = Column(String(50), unique=True)
    command = Column(String(50))
    hour = Column(String(20))
    minute = Column(String(2))
    second = Column(String(20))
    day_of_week = Column(String(20))
    week = Column(String(20))
    day = Column(String(20))
    month = Column(String(20))
    year = Column(String(20))
    start_date = Column(DateTime())
    execute_now = Column(Boolean, default=False)
    is_async = Column(Boolean, default=False)
    is_active = Column(Boolean, default=False)

    def __repr__(self):
        return '{} {}:{}'.format(self.is_active, self.name, self.command)

    def __init__(self, id='', host_name=''):
        # keep host name default to '' rather than None (which does not work on filter in)
        super(Rule, self).__init__()
        if id:
            self.id = id
        self.host_name = host_name


class PlotlyCache(Base, DbEvent, DbBase):
    __tablename__ = 'plotly_cache'
    id = Column(Integer, primary_key=True)
    grid_name = Column(String(50), unique=True)
    grid_url = Column(String(250))
    column_name_list = Column(String(250))
    created_by_node_name = Column(String(50))
    announced_on = Column(DateTime())

    def __repr__(self):
        return '{} {}'.format(self.grid_name, self.grid_url)

    def __init__(self, id='', grid_name=''):
        # keep host name default to '' rather than None (which does not work on filter in)
        super(PlotlyCache, self).__init__()
        if id:
            self.id = id
        self.grid_name = grid_name


class Utility(Base, graphs.BaseGraph, DbEvent, DbBase):
    __tablename__ = 'utility'
    id = Column(Integer, primary_key=True)
    utility_name = Column(String(50))  # unique name, can be different than sensor name for dual counter
    sensor_name = Column(String(50), ForeignKey('sensor.sensor_name'))
    sensor_index = Column(Integer)  # 0 for counter_a, 1 for counter_b
    units_total = Column(Float)  # total number of units measured
    units_delta = Column(Float)  # total number of units measured since last measurement
    units_2_delta = Column(Float)  # total number of units measured since last measurement
    ticks_delta = Column(BigInteger)
    ticks_per_unit = Column(Float, default=1)  # number of counter ticks in a unit (e.g. 10 for a watt)
    unit_name = Column(String(50))  # kwh, liter etc.
    unit_2_name = Column(String(50))  # 2nd unit type, optional, i.e. watts
    unit_cost = Column(Float)
    cost = Column(Float)
    utility_type = Column(String(50))  # water, electricity, gas
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)

    def __init__(self, sensor_name=''):
        super(Utility, self).__init__()
        self.sensor_name = sensor_name

    def __repr__(self):
        return '{} {} {}'.format(self.id, self.utility_name, self.updated_on)


class State(Base, DbEvent, DbBase):
    __tablename__ = 'state'
    id = Column(Integer, primary_key=True)
    entry_name = Column(String(50))  # unique name
    entry_value = Column(String(50))
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)

    def __init__(self, entry_name=''):
        super(State, self).__init__()
        self.entry_name = entry_name

    def __repr__(self):
        return '{} {} {}'.format(self.id, self.entry_name, self.entry_value)


class Device(Base, DbEvent, DbBase):
    __tablename__ = 'device'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))  # unique name
    type = Column(String(50))
    bt_address = Column(String(50))
    wifi_address = Column(String(50))
    bt_signal = Column(Integer)
    wifi_signal = Column(Integer)
    last_bt_active = Column(DateTime())
    last_wifi_active = Column(DateTime())
    last_active = Column(DateTime())
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)

    def __init__(self, name=''):
        super(Device, self).__init__()
        self.name = name

    def __repr__(self):
        return '{} {}'.format(self.id, self.name)


class People(Base, DbEvent, DbBase):
    __tablename__ = 'people'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))  # unique name
    email = Column(String(50))
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)

    def __init__(self, name=''):
        super(People, self).__init__()
        self.name = name

    def __repr__(self):
        return '{} {}'.format(self.id, self.name)


class PeopleDevice(Base, DbEvent, DbBase):
    __tablename__ = 'people_device'
    id = Column(Integer, primary_key=True)
    people_id = Column(Integer)
    device_id = Column(Integer)
    give_presence = Column(Boolean, default=False)
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)


class Position(Base, DbEvent, DbBase):
    __tablename__ = 'position'
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer)
    latitude = Column(String(20))
    longitude = Column(String(20))
    altitude = Column(Float)
    hspeed = Column(Float)
    vspeed = Column(Float)
    hprecision = Column(Integer)
    vprecision = Column(Integer)
    battery = Column(Integer)
    satellite = Column(Integer)
    satellite_valid = Column(Integer)
    updated_on = Column(DateTime())


class Music(Base, DbEvent, DbBase):
    __tablename__ = 'music'
    id = Column(Integer, primary_key=True)
    zone_name = Column(String(50))  # unique name
    state = Column(String(50))
    volume = Column(Integer)
    position = Column(Integer)  # percent
    title = Column(String(100))
    artist = Column(String(100))
    song = Column(String(200))
    album = Column(String(100))

    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)

    def __init__(self, zone_name=None):
        super(Music, self).__init__()
        self.zone_name = zone_name

    def __repr__(self):
        return '{} {} {} {}'.format(self.id, self.zone_name, self.state, self.song)


class MusicLoved(Base, DbEvent, DbBase):
    __tablename__ = 'music_loved'
    id = Column(Integer, primary_key=True)
    lastfmloved = Column(Boolean, default=False)
    lastfmsong = Column(String(200))

    def __init__(self, lastfmsong=None):
        super(MusicLoved, self).__init__()
        self.lastfmsong = lastfmsong

    def __repr__(self):
        return '{} {} {}'.format(self.id, self.lastfmsong, self.lastfmloved)


class Pwm(Base, DbEvent, DbBase, graphs.BaseGraph):
    __tablename__ = 'pwm'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    frequency = Column(Integer)
    duty_cycle = Column(Integer)  # 0-1e6
    gpio_pin_code = Column(Integer)
    host_name = Column(String(50))
    is_started = Column(Boolean, default=False)
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)

    def __init__(self, id=None):
        super(Pwm, self).__init__()
        self.id = id
        self.duty_cycle = None
        self.frequency = None
        self.name = None
        self.host_name = None
        self.gpio_pin_code = None
        self.is_started = False

    def __repr__(self):
        return '{} {}'.format(self.id, self.name)


'''
tables used to store historical data
column names must match the source model names as save is done automatically
'''


class NodeHistory(Base, DbBase):
    __bind_key__ = 'reporting'
    __tablename__ = 'node_history'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    master_overall_cycles = Column(Integer)  # count of update cycles while node was master
    run_overall_cycles = Column(Integer)  # count of total update cycles
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now, index=True)
    source_host_ = Column(String(50))

    def __repr__(self):
        return '{} {}'.format(self.id, self.name)


class SensorHistory(Base, DbBase):
    __bind_key__ = 'reporting'
    __tablename__ = 'sensor_history'
    id = Column(Integer, primary_key=True)
    sensor_name = Column(String(50), index=True)
    address = Column(String(50))
    temperature = Column(Float)
    humidity = Column(Float)
    pressure = Column(Float)
    counters_a = Column(BigInteger)
    counters_b = Column(BigInteger)
    delta_counters_a = Column(BigInteger)
    delta_counters_b = Column(BigInteger)
    iad = Column(Float)
    vdd = Column(Float)
    vad = Column(Float)
    pio_a = Column(Integer)
    pio_b = Column(Integer)
    sensed_a = Column(Integer)
    sensed_b = Column(Integer)
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now, index=True)
    added_on = Column(DateTime(), default=datetime.now)
    source_host_ = Column(String(50))

    def __repr__(self):
        return '{} {} adr={} t={} ca={} cb={}'.format(self.id, self.sensor_name, self.address, self.temperature,
                                                      self.counters_a, self.counters_b)


class SensorErrorHistory(Base, DbBase):
    __bind_key__ = 'reporting'
    __tablename__ = 'sensor_error_history'
    id = Column(Integer, primary_key=True)
    sensor_name = Column(String(50), index=True)
    error_type = Column(Integer)  # 0=not found, 1=other err
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now, index=True)

    def __repr__(self):
        return '{} {}'.format(self.id, self.sensor_name)


class SystemMonitorHistory(Base, DbBase):
    __bind_key__ = 'reporting'
    __tablename__ = 'systemmonitor_history'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), index=True)
    cpu_usage_percent = Column(Float)
    cpu_temperature = Column(Float)
    memory_available_percent = Column(Float)
    uptime_days = Column(Integer)
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now, index=True)
    source_host_ = Column(String(50))

    def __repr__(self):
        return '{} {} {}'.format(self.id, self.name, self.updated_on)


class UpsHistory(Base, DbBase):
    __bind_key__ = 'reporting'
    __tablename__ = 'ups_history'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    system_name = Column(String(50))
    port = Column(String(50))
    input_voltage = Column(Float)
    remaining_minutes = Column(Float)
    output_voltage = Column(Float)
    load_percent = Column(Float)
    power_frequency = Column(Float)
    battery_voltage = Column(Float)
    temperature = Column(Float)
    power_failed = Column(Boolean(), default=False)
    beeper_on = Column(Boolean(), default=False)
    test_in_progress = Column(Boolean(), default=False)
    other_status = Column(String(50))
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now, index=True)
    source_host_ = Column(String(50))

    def __repr__(self):
        return '{} {} {}'.format(self.id, self.name, self.updated_on)


class SystemDiskHistory(Base, DbBase):
    __bind_key__ = 'reporting'
    __tablename__ = 'systemdisk_history'  # convention: append '_history' -> 'History' to source table name
    id = Column(Integer, primary_key=True)
    serial = Column(String(50))
    system_name = Column(String(50))
    hdd_name = Column(String(50))  # netbook /dev/sda
    hdd_device = Column(String(50))  # usually empty?
    hdd_disk_dev = Column(String(50))  # /dev/sda
    temperature = Column(Float)
    sector_error_count = Column(Integer)
    smart_status = Column(String(50))
    power_status = Column(Integer)
    load_cycle_count = Column(Integer)
    start_stop_count = Column(Integer)
    last_reads_completed_count = Column(Float)
    last_reads_datetime = Column(DateTime())
    last_writes_completed_count = Column(Float)
    last_writes_datetime = Column(DateTime())
    last_reads_elapsed = Column(Float)
    last_writes_elapsed = Column(Float)
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now, index=True)
    source_host_ = Column(String(50))

    def __init__(self):
        super(SystemDiskHistory, self).__init__()
        self.hdd_disk_dev = ''

    def __repr__(self):
        return '{} {} {} {} {}'.format(self.id, self.serial, self.system_name, self.hdd_name, self.hdd_disk_dev)


class PresenceHistory(Base, DbBase):
    __bind_key__ = 'reporting'
    __tablename__ = 'presence_history'  # convention: append '_history' -> 'History' to source table name
    id = Column(Integer, primary_key=True)
    zone_name = Column(String(50))
    sensor_name = Column(String(50))
    event_type = Column(String(25)) # cam, pir, contact, wifi, bt
    event_camera_date = Column(DateTime(), default=None)
    event_alarm_date = Column(DateTime(), default=None)
    event_io_date = Column(DateTime(), default=None)
    # event_wifi_date = Column(DateTime(), default=None)
    # event_bt_date = Column(DateTime(), default=None)
    is_connected = Column(Boolean, default=False)  # pin connected? true on unarmed sensors, false on alarm/move
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now, index=True)
    source_host_ = Column(String(50))

    def __repr__(self):
        return 'PresenceHistory zone {} sensor {} connected {} type {}'.format(
            self.zone_name, self.sensor_name, self.is_connected, self.event_type)


class UtilityHistory(Base, DbBase):
    __bind_key__ = 'reporting'
    __tablename__ = 'utility_history'  # convention: append '_history' -> 'History' to source table name
    id = Column(Integer, primary_key=True)
    utility_name = Column(String(50), index=True)
    sensor_name = Column(String(50), index=True)
    units_total = Column(Float)  # total number of units measured
    units_delta = Column(Float)  # total number of units measured since last measurement
    units_2_delta = Column(Float)  # total number of units measured since last measurement
    ticks_delta = Column(BigInteger)
    cost = Column(Float)
    unit_name = Column(String(50))  # kwh, liter etc.
    unit_2_name = Column(String(50))  # watt
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now, index=True)
    source_host_ = Column(String(50))


class ZoneHeatRelayHistory(Base, DbBase):
    __bind_key__ = 'reporting'
    __tablename__ = 'zoneheatrelay_history'  # convention: append '_history' -> 'History' to source table name
    id = Column(Integer, primary_key=True)
    heat_pin_name = Column(String(50))
    gpio_host_name = Column(String(50))
    heat_is_on = Column(Boolean, default=False)
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)


class ZoneCustomRelayHistory(Base, DbBase):
    __bind_key__ = 'reporting'
    __tablename__ = 'zonecustomrelay_history'  # convention: append '_history' -> 'History' to source table name
    id = Column(Integer, primary_key=True)
    relay_pin_name = Column(String(50))
    gpio_host_name = Column(String(50))
    relay_is_on = Column(Boolean, default=False)
    relay_type = Column(String(20))
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)


class PowerMonitorHistory(Base, DbBase):
    __bind_key__ = 'reporting'
    __tablename__ = 'powermonitor_history'  # convention: append '_history' -> 'History' to source table name
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    type = Column(String(50))  # INA, etc
    host_name = Column(String(50))
    voltage = Column(Float)  # volts
    current = Column(Float)  # miliamps
    power = Column(Float)
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)


class DustSensorHistory(Base, DbBase):
    __bind_key__ = 'reporting'
    __tablename__ = 'dustsensor_history'  # convention: append '_history' -> 'History' to source table name
    id = Column(Integer, primary_key=True)
    address = Column(String(50))
    pm_1 = Column(Integer)
    pm_2_5 = Column(Integer)
    pm_10 = Column(Integer)
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)
