from datetime import datetime
from copy import deepcopy

from main.logger_helper import Log
from main import db
from main.admin.model_helper import commit
import graphs
from common import utils, performance

#TODO: read this
#http://lucumr.pocoo.org/2011/7/19/sqlachemy-and-you/

class DbBase:
    def __check_for_long_query(self, result, start_time, function):
        query_details = function.im_self
        elapsed = performance.add_query(start_time, query_details=query_details)
        if elapsed > 5000:#with sqlite a long query will throw an error
            Log.logger.critical("Long running DB query, seconds elapsed={}, result={}".format(elapsed, query_details))
            db.session.rollback()
            Log.logger.info("Session was rolled back")
        return result

    def __get_result(self, function):
        start_time = utils.get_base_location_now_date()
        result = function()
        return self.__check_for_long_query(result, start_time, function)

    def query_all(self):
        function = self.query.all
        return self.__get_result(function)

    def query_filter_all(self, filter):
        function = self.query.filter(filter).all
        return self.__get_result(function)

    def query_filter_first(self, *filter):
        function = self.query.filter(*filter).first
        return self.__get_result(function)

#    def query_filters_first(self, *filter):
#        function = self.query.filter(*filter).first
#        return self.__get_result(function)

    def delete(self):
        function = self.query.delete
        return self.__get_result(function)


class DbEvent:
    def __init__(self):
        pass

    notified_on_db_commit=False
    notify_transport_enabled=False
    event_sent_datetime = None
    event_uuid = None
    operation_type=None
    last_commit_field_changed_list = []


    def get_deepcopy(self):
        return deepcopy(self)

    def json_to_record(self, json_object):
        for field in json_object:
            if hasattr(self, field):
                setattr(self, field, json_object[field])
        return self

    #copies fields from a json object to an existing or new db record
    def save_changed_fields_from_json_object(self,json_object=None, unique_key_name=None,
                                            notify_transport_enabled=False, save_to_graph=False,
                                            ignore_only_updated_on_change=True, debug=False, graph_save_frequency=0):
        try:
            new_record = self.json_to_record(json_object)
            #let flask assign an id in case unique key name is different, to avoid key integrity error
            if not unique_key_name:
                unique_key_name = 'id'
            else:
                new_record.id = None
            if hasattr(new_record, unique_key_name):
                unique_key_value = getattr(new_record, unique_key_name)
                kwargs = {unique_key_name:unique_key_value}
                new_record.updated_on = utils.get_base_location_now_date()
                current_record = self.query.filter_by(**kwargs).first()
                self.save_changed_fields(current_record=current_record, new_record=new_record,
                                         notify_transport_enabled=False, save_to_graph=False)
                db.session.commit()
            else:
                Log.logger.warning('Unique key not found in json record, save aborted')
        except Exception, ex:
            Log.logger.error('Exception save json to db {}'.format(ex))



    #graph_save_frequency in seconds
    def save_changed_fields(self,current_record='',new_record='',notify_transport_enabled=False, save_to_graph=False,
                            ignore_only_updated_on_change=True, debug=False, graph_save_frequency=0, filter=None):
        try:
            if hasattr(self, 'save_to_graph'):#not all models inherit graph
                if current_record:
                    #if a record in db already exists
                    if not current_record.last_save_to_graph:
                        current_record.last_save_to_graph = datetime.min
                    save_to_graph_elapsed = (utils.get_base_location_now_date() -
                                             current_record.last_save_to_graph).total_seconds()
                    if save_to_graph_elapsed > graph_save_frequency:
                        current_record.save_to_graph = save_to_graph
                    else:
                        current_record.save_to_graph = False
                else:
                    #this is a new record
                    new_record.save_to_graph = save_to_graph

            if current_record:
                current_record.last_commit_field_changed_list=[]
                current_record.notify_transport_enabled = notify_transport_enabled
                for column in new_record.query.statement._columns._all_col_set:
                    column_name = str(column)
                    new_value = getattr(new_record, column_name)
                    old_value = getattr(current_record, column_name)
                    #todo: comparison not working for float, because str appends .0
                    if (not new_value is None) and (str(old_value) != str(new_value)):
                        if column_name != 'updated_on':
                            try:
                                obj_type=str(type(self)).split('\'')[1]
                                obj_type_words=obj_type.split('.')
                                obj_type=obj_type_words[len(obj_type_words)-1]
                            except Exception, ex:
                                obj_type = str(type(self))
                            if debug:
                                Log.logger.info('{} {}={} oldvalue={}'.format(obj_type, column_name, new_value, old_value))
                        setattr(current_record, column_name, new_value)
                        current_record.last_commit_field_changed_list.append(column_name)
                if len(current_record.last_commit_field_changed_list) == 0:
                    current_record.notify_transport_enabled = False
                elif len(current_record.last_commit_field_changed_list) == 1 and ignore_only_updated_on_change and \
                                'updated_on' in current_record.last_commit_field_changed_list:
                    current_record.notify_transport_enabled = False
            else:
                new_record.notify_transport_enabled = notify_transport_enabled
                for column in new_record.query.statement._columns._all_col_set:
                    column_name = str(column)
                    new_value = getattr(new_record, column_name)
                    if new_value:
                        new_record.last_commit_field_changed_list.append(column_name)
                db.session.add(new_record)
            commit()
            if hasattr(new_record, 'last_save_to_graph'):
                new_record.last_save_to_graph = utils.get_base_location_now_date()
        except Exception, ex:
            Log.logger.critical('Error when saving db changes {}, err={}'.format(new_record, ex))
            if len(db.session.dirty) > 0:
                Log.logger.info('Session dirty records={}, rolling back'.format(len(db.session.dirty)))
                db.session.rollback()
            else:
                Log.logger.info('No session dirty records')
            raise ex
        #else:
        #    Log.logger.warning('Incorrect parameters received on save changed fields to db')



class Module(db.Model, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    host_name = db.Column(db.String(50))
    name = db.Column(db.String(50))
    active = db.Column(db.Boolean(), default=False)
    start_order = db.Column(db.Integer)

    def __init__(self, id='', host_name='', name='', active=False, start_order='999'):
        if id:
            self.id = id
        self.host_name = host_name
        self.name = name
        self.active = active
        self.start_order = start_order

    def __repr__(self):
        return 'Module {} {}, {}'.format(self.id, self.host_name, self.name[:50])

class Zone(db.Model, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))

    active_heat_schedule_pattern_id = db.Column(db.Integer)
    heat_is_on = db.Column(db.Boolean)
    last_heat_status_update = db.Column(db.DateTime(), default=datetime.min)
    heat_target_temperature = db.Column(db.Integer)

    def __init__(self, id='', name=''):
        if id:
            self.id = id
        self.name = name

    def __repr__(self):
        return 'Zone id {} {}'.format(self.id, self.name[:20])

class SchedulePattern(db.Model, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    pattern = db.Column(db.String(24))

    def __init__(self, id=None, name='', pattern=''):
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
        if id:
            self.id = id
        self.code = code
        self.target = target

    def __repr__(self):
        return '{} code {}={}'.format(self.id, self.code, self.target)


class HeatSchedule(db.Model, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'), nullable=False)
    #zone = db.relationship('Zone', backref=db.backref('heat schedule zone', lazy='dynamic'))
    pattern_week_id = db.Column(db.Integer, db.ForeignKey('schedule_pattern.id'), nullable=False)
    pattern_weekend_id = db.Column(db.Integer, db.ForeignKey('schedule_pattern.id'), nullable=False)
    #pattern_week = db.relationship('SchedulePattern', foreign_keys='[HeatSchedule.pattern_week_id]',
    #                               backref=db.backref('schedule_pattern_week', lazy='dynamic'))
    #pattern_weekend = db.relationship('SchedulePattern', foreign_keys='[HeatSchedule.pattern_weekend_id]',
    #                                backref=db.backref('schedule_pattern_weekend', lazy='dynamic'))
    active = db.Column(db.Boolean, default=True)

    def __init__(self, id=None, zone_id=None, pattern_week_id=None, pattern_weekend_id=None):
        if id:
            self.id = id
        self.zone_id= zone_id
        self.pattern_week_id= pattern_week_id
        self.pattern_weekend_id= pattern_weekend_id

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
    iad = db.Column(db.Float)
    vdd = db.Column(db.Float)
    vad = db.Column(db.Float)
    pio_a = db.Column(db.Integer)
    pio_b = db.Column(db.Integer)
    sensed_a = db.Column(db.Integer)
    sensed_b = db.Column(db.Integer)
    battery_level = db.Column(db.Integer) #RFXCOM specific
    rssi = db.Column(db.Integer) #RFXCOM specific, rssi - distance
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    #FIXME: now filled manually, try relations
    #zone_name = db.Column(db.String(50))
    sensor_name = db.Column(db.String(50))

    def __init__(self, address=''):
        self.address= address

    def __repr__(self):
        return 'Sensor {}, {}{}'.format(self.type, self.sensor_name, self.address)
    

class Parameter(db.Model, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    value = db.Column(db.String(255))

    def __init__(self, id=None, name='default', value='default'):
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
    #zone = db.relationship('Zone', backref=db.backref('ZoneSensor(zone)', lazy='dynamic'))
    sensor_address = db.Column(db.String(50), db.ForeignKey('sensor.address'))
    #sensor = db.relationship('Sensor', backref=db.backref('ZoneSensor(sensor)', lazy='dynamic'))

    def __init__(self, zone_id='', sensor_address ='', sensor_name=''):
        self.sensor_address= sensor_address
        self.zone_id = zone_id
        self.sensor_name = sensor_name

    def __repr__(self):
        return 'ZoneSensor zone {} sensor {}'.format(self.zone_id,  self.sensor_name)

class Node(db.Model, DbEvent, graphs.NodeGraph, DbBase):
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
    priority = db.Column(db.Integer) # used to decide who becomes main master in case several hosts are active
    master_overall_cycles = db.Column(db.Integer) #count of update cycles while node was master
    run_overall_cycles = db.Column(db.Integer) #count of total update cycles
    execute_command=db.Column(db.String(50))
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, id=None, name=None, ip=None, priority=None, mac=None, is_master_logging=False):
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
        return 'Node {} ip {}'.format(self.name,  self.ip)


class SystemMonitor(db.Model, graphs.SystemMonitorGraph, DbEvent, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    cpu_usage_percent = db.Column(db.Float)
    cpu_temperature = db.Column(db.Float)
    memory_available_percent = db.Column(db.Float)
    uptime_days = db.Column(db.Integer)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

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
    beeper_on =db.Column(db.Boolean(), default=False)
    test_in_progress = db.Column(db.Boolean(), default=False)
    other_status= db.Column(db.String(50))
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    def __repr__(self):
        return '{} {} {}'.format(self.id, self.name, self.updated_on)

class SystemDisk(db.Model, graphs.SystemDiskGraph, DbEvent, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    serial = db.Column(db.String(50), unique=True)
    system_name = db.Column(db.String(50))
    hdd_name = db.Column(db.String(50)) #netbook /dev/sda
    hdd_device = db.Column(db.String(50)) #usually empty?
    hdd_disk_dev = db.Column(db.String(50)) #/dev/sda
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
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self):
        self.hdd_disk_dev = ''

    def __repr__(self):
        return '{} {} {} {} {}'.format(self.id, self.serial,  self.system_name, self.hdd_name, self.hdd_disk_dev)

class GpioPin(db.Model, DbEvent, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    host_name = db.Column(db.String(50))
    pin_type = db.Column(db.String(50)) #bbb, pi
    pin_code = db.Column(db.String(50)) #friendly format, e.g. for Beagle is P9_11, for PI is same with pin_index
    pin_index_bcm = db.Column(db.String(50))#bcm format, 0 to n
    pin_value = db.Column(db.Integer) # 0, 1 or None
    pin_direction = db.Column(db.String(4)) #in, out, None
    description = db.Column(db.String(50))
    is_active = db.Column(db.Boolean) # if pin was setup(exported) through this app. will be unexported when app exit

    def __init__(self):
        pass

    def __repr__(self):
        return 'host={} code={} desc={} type={} value={}'.format(self.host_name, self.pin_code, self.description,
                                                                 self.pin_type, self.pin_value)

class ZoneAlarm(db.Model, DbEvent, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    #friendly display name for pin mapping
    alarm_pin_name = db.Column(db.String(50))
    zone_id = db.Column(db.Integer)#, db.ForeignKey('zone.id'))
    #zone = db.relationship('Zone', backref=db.backref('ZoneAlarm(zone)', lazy='dynamic'))
    #gpio_pin_code = db.Column(db.String(50), db.ForeignKey('gpio_pin.pin_code'))
    gpio_pin_code = db.Column(db.String(50))
    gpio_host_name = db.Column(db.String(50))
    #gpio_pin = db.relationship('GpioPin', backref=db.backref('ZoneAlarm(gpiopincode)', lazy='dynamic'))
    alarm_status = db.Column(db.Integer)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, zone_id='', gpio_pin_code='', host_name=''):
        self.zone_id = zone_id
        self.gpio_pin_code = gpio_pin_code
        self.gpio_host_name = host_name

    def __repr__(self):
        return 'host {} gpiopin {} {}'.format(self.gpio_host_name, self.gpio_pin_code, self.alarm_pin_name)

class ZoneHeatRelay(db.Model, DbEvent, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    #friendly display name for pin mapping
    heat_pin_name = db.Column(db.String(50))
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'))
    gpio_pin_code = db.Column(db.String(50)) #user friendly format, e.g. P8_11
    gpio_host_name = db.Column(db.String(50))
    heat_is_on = db.Column(db.Boolean)
    is_main_heat_source = db.Column(db.Boolean)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, zone_id=None, gpio_pin_code='', host_name='', is_main_heat_source=False):
        self.zone_id = zone_id
        self.gpio_pin_code = gpio_pin_code
        self.gpio_host_name = host_name
        self.is_main_heat_source = is_main_heat_source

    def __repr__(self):
        return 'host {} {} {} {}'.format(self.gpio_host_name, self.gpio_pin_code, self.heat_pin_name, self.heat_is_on)

class ZoneCustomRelay(db.Model, DbEvent, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    #friendly display name for pin mapping
    relay_pin_name = db.Column(db.String(50))
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'))
    gpio_pin_code = db.Column(db.String(50)) #user friendly format, e.g. P8_11
    gpio_host_name = db.Column(db.String(50))
    relay_is_on = db.Column(db.Boolean)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, id=None, zone_id='', gpio_pin_code='', host_name='', relay_pin_name=''):
        if id:
           self.id = id
        self.zone_id = zone_id
        self.gpio_pin_code = gpio_pin_code
        self.gpio_host_name = host_name
        self.relay_pin_name = relay_pin_name

    def __repr__(self):
        return 'host {} {} {} {}'.format(self.gpio_host_name, self.gpio_pin_code, self.relay_pin_name, self.relay_is_on)

class Rule(db.Model, DbEvent, DbBase):
    id = db.Column(db.Integer, primary_key=True)
    host_name = db.Column(db.String(50))
    name = db.Column(db.String(50), unique=True)
    command = db.Column(db.String(50))
    hour = db.Column(db.String(20))
    minute = db.Column(db.String(2))
    second= db.Column(db.String(20))
    day_of_week = db.Column(db.String(20))
    week = db.Column(db.String(20))
    day = db.Column(db.String(20))
    month = db.Column(db.String(20))
    year = db.Column(db.String(20))
    start_date = db.Column(db.DateTime())
    is_active = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '{} {}'.format(self.is_active, self.command)

    def __init__(self, id='', host_name=''):
        #keep host name default to '' rather than None (which does not work on filter in)
        if id:
            self.id = id
        self.host_name = host_name


