__author__ = 'dcristian'
import random
import sys
import uuid
import json

from sqlalchemy.exc import IntegrityError, OperationalError, InvalidRequestError

from main.logger_helper import Log
import models
from common import Constant, utils, performance
from main import db

__db_values_json = None
table_collection = None


def model_row_to_json(obj, operation=''):
    try:
        safe_obj = {}
        obj.event_sent_datetime = str(utils.get_base_location_now_date())
        obj.operation_type=operation
        obj.event_uuid = str(uuid.uuid4())
        table_cols=obj._sa_class_manager
        for attr in table_cols:
            safe_obj[Constant.JSON_PUBLISH_TABLE]=str(table_cols[attr]).split('.')[0]
            break

        #safe_obj[constant.JSON_PUBLISH_RECORD_OPERATION]=operation
        safe_obj[Constant.JSON_PUBLISH_SOURCE_HOST]=str(Constant.HOST_NAME)
        #safe_obj[constant.JSON_PUBLISH_DATE]=str(utils.get_base_location_now_date())
        #safe_obj[constant.JSON_PUBLISH_TARGET_HOST]=constant.JSON_PUBLISH_VALUE_TARGET_HOST_ALL
        #removing infinite recursions and class noise
        #for attr in obj._sa_class_manager:
        for attr in dir(obj):
            if not attr.startswith('_') and not '(' in attr \
                    and attr != 'query' and not callable(getattr(obj, attr))\
                    and attr != 'metadata':
                value=getattr(obj, attr)
                #only convert to json simple primitives
                if value is not None and not hasattr(value,'_sa_class_manager'):
                    safe_obj[attr] = value
                else:
                    Log.logger.debug('Ignoring obj to json, not simple primitive {}'.format(value))
        return utils.safeobj2json(safe_obj)
    except Exception, ex:
        logger.critical('Error convert model obj to json, err {}'.format(ex))

def get_param(name):
    global __db_values_json
    try:
        val = models.Parameter().query_filter_first(models.Parameter.name.in_([name])).value
        return val
    except ValueError, ex:
        Log.logger.warning('Unable to get parameter {} error {}'.format(name, ex))
        raise ValueError
    except Exception, ex:
        logger.critical('Exception when getting param {}, err={}'.format(name, ex))
        #db.session.rollback()
        raise ex


def commit():
    time_start = utils.get_base_location_now_date()
    query_details = "COMMIT " + str(db.session.identity_map)
    try:
        db.session.commit()
    except IntegrityError, ex:
        #db.session.rollback()
        Log.logger.warning('Unable to commit DB session={}, rolled back, err={}'.format(db.session, ex))
    except InvalidRequestError, ex:
        Log.logger.warning('Error on commit, session={}, ignoring, err={}'.format(db.session, ex))
    except Exception, ex:
        Log.logger.warning('Exception on commit, session={} err={}'.format(db.session, ex))
    performance.add_query(time_start, query_details=query_details)


def get_mod_name(module):
    return str(module).split("'")[1]

def check_table_schema(table, model_auto_update=False):
    try:
        #count = table.query.all()
        count = table().query_all()
    except OperationalError, oex:
        logger.critical('Table {} schema in DB seems outdated, err {}, DROP it and recreate (y/n)?'.format(oex, table))
        read_drop_table(table, oex, model_auto_update)
    except InvalidRequestError:
        Log.logger.warning('Error on check table schema {}, ignoring'.format(table))
    except Exception, ex:
        Log.logger.warning('Unexpected error on check table, err={}'.format(ex))

def read_drop_table(table, original_exception, drop_without_user_ask=False):
    if not drop_without_user_ask:
        x = sys.stdin.readline(1)
    else:
        x='y'
    if x=='y':
        Log.logger.warning('Dropping table {}'.format(table))
        try:
            table_name=table.query._primary_entity.entity_zero._with_polymorphic_selectable.description
            result = db.engine.execute('DROP TABLE '+table_name)
            commit()
        except Exception, ex:
            Log.logger.info('Something went wrong on drop, ignoring err {}'.format(ex))
            db.session.rollback()
        Log.logger.info('Creating missing schema object after table drop')
        db.create_all()
    else:
        raise original_exception

def populate_tables(model_auto_update=False):
    var_path = utils.get_app_root_path() + 'scripts/config/default_db_values.json'
    Log.logger.info('Loading variables from config file [{}]'.format(var_path))
    global __db_values_json
    with open(var_path, 'r') as f:
        __db_values_json = json.load(f)
    global table_collection
    table_collection = [models.Parameter, models.Module,
        models.Zone, models.ZoneCustomRelay,
        models.TemperatureTarget, models.SchedulePattern, models.HeatSchedule, models.ZoneHeatRelay,
        models.ZoneSensor, models.ZoneAlarm,
        models.SystemMonitor, models.SystemDisk, models.Sensor, models.Ups, models.Rule]

    for table in table_collection:
        table_str = utils.get_table_name(table)
        check_table_schema(table, model_auto_update)
        if table_str in __db_values_json:
            default_values = __db_values_json[table_str]
            if len(table().query_all()) != len(default_values):
                Log.logger.info('Populating {} with default values as config record count != db count'.format(table_str))
                table().delete()
                commit()
                for config_record in default_values:
                    new_record = table()
                    #setattr(new_record, config_record, default_values[config_record])
                    for field in config_record:
                        setattr(new_record, field, config_record[field])
                    db.session.add(new_record)
                commit()

    check_table_schema(models.Node, model_auto_update)
    if len(models.Node.query.filter_by(name=Constant.HOST_NAME).all()) == 0:
        Log.logger.info('Populating Node {} with default values'.format(Constant.HOST_NAME))
        master_logging = False
        if Constant.HOST_NAME=='nas':
            master_logging = True
            priority = 2
        elif Constant.HOST_NAME=='netbook':
            priority = 0
        elif Constant.HOST_NAME=='server':
            priority = 3
        elif Constant.HOST_NAME=='ex-std-node466.prod.rhcloud.com':
            priority = 4
        else:
            priority=random.randint(10, 100)
        db.session.add(models.Node('', name=Constant.HOST_NAME, ip=Constant.HOST_MAIN_IP, priority=priority,
                                   mac=Constant.HOST_MAC, is_master_logging=master_logging))
        commit()
    else:
        #reseting execute_command field to avoid running last command before shutdown
        node_obj = models.Node.query.filter_by(name=Constant.HOST_NAME).first()
        node_obj.execute_command = ''
        commit()
    node_obj = models.Node.query.filter_by(name=Constant.HOST_NAME).first()
    Constant.HOST_PRIORITY = node_obj.priority


    check_table_schema(models.GpioPin, model_auto_update)
    bbb_bcm_map={
        'P9_11':30, 'P9_12':60, 'P9_13':31, 'P9_14':40, 'P9_15':48, 'P9_16':51, 'P9_24':15, 'P9_23':49,
        'P9_22':2,  'P9_21':3,
        'P8_07':66, 'P8_08':67, 'P8_09':69, 'P8_11':45, 'P8_12':44, 'P8_15':47, 'P8_16':46
    }
    if len(models.GpioPin.query.filter_by(pin_type=Constant.GPIO_PIN_TYPE_BBB,
                                          host_name=Constant.HOST_NAME).all()) != 46*2: #P8_ and P9_ with 46 pins
        models.GpioPin.query.filter_by(pin_type=Constant.GPIO_PIN_TYPE_BBB, host_name=Constant.HOST_NAME).delete()
        commit()
        for host_name in ['beaglebone', 'netbook', 'EN62395']:
            Log.logger.info('Populating GpioPins with default beabglebone {} values'.format(host_name))
            for rail in range(8,10): #last range is not part of the loop
                for pin in range(01, 47):
                    gpio = models.GpioPin()
                    gpio.pin_type = Constant.GPIO_PIN_TYPE_BBB
                    gpio.host_name = host_name
                    pincode = '0'+str(pin)
                    gpio.pin_code = 'P'+str(rail)+'_'+pincode[-2:]
                    if bbb_bcm_map.has_key(gpio.pin_code):
                        gpio.pin_index_bcm = bbb_bcm_map[gpio.pin_code]
                    else:
                        gpio.pin_index_bcm = ''
                    db.session.add(gpio)
        commit()

    #fixme: check for other PI revisions
    if len(models.GpioPin.query.filter_by(pin_type=Constant.GPIO_PIN_TYPE_PI,host_name=Constant.HOST_NAME).all()) != 26:
        models.GpioPin.query.filter_by(pin_type=Constant.GPIO_PIN_TYPE_PI, host_name=Constant.HOST_NAME).delete()
        commit()
        for host_name in ['pi-power', 'pi-bell', 'netbook', 'EN62395']:
            Log.logger.info('Populating GpioPins with default raspberry pi {} values'.format(host_name))
            for pin in range(01, 27): # -1
                gpio = models.GpioPin()
                gpio.pin_type = Constant.GPIO_PIN_TYPE_PI
                gpio.host_name = host_name
                gpio.pin_code = str(pin)
                gpio.pin_index_bcm = pin
                db.session.add(gpio)
        commit()

