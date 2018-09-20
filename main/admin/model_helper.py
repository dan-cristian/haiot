import sys
import uuid
from sqlalchemy.exc import IntegrityError, OperationalError, InvalidRequestError
from main.logger_helper import L
from common import Constant, utils, performance
from main import db, app
import models

__author__ = 'dcristian'

__db_values_json = None
table_collection = None


def model_row_to_json(obj, operation=''):
    try:
        safe_obj = {}
        obj.event_sent_datetime = str(utils.get_base_location_now_date())
        obj.operation_type = operation
        if hasattr(obj, 'record_uuid'):
            obj.record_uuid = str(uuid.uuid4())
        table_cols = obj._sa_class_manager
        for attr in table_cols:
            safe_obj[Constant.JSON_PUBLISH_TABLE] = str(table_cols[attr]).split('.')[0]
            break

        # safe_obj[constant.JSON_PUBLISH_RECORD_OPERATION]=operation
        safe_obj[Constant.JSON_PUBLISH_SOURCE_HOST] = str(Constant.HOST_NAME)
        # safe_obj[constant.JSON_PUBLISH_DATE]=str(utils.get_base_location_now_date())
        # safe_obj[constant.JSON_PUBLISH_TARGET_HOST]=constant.JSON_PUBLISH_VALUE_TARGET_HOST_ALL
        # removing infinite recursions and class noise
        # for attr in obj._sa_class_manager:
        for attr in dir(obj):
            if not attr.startswith('_') and not '(' in attr \
                    and attr != 'query' and not callable(getattr(obj, attr)) \
                    and attr != 'metadata':
                value = getattr(obj, attr)
                # only convert to json simple primitives
                if value is not None and not hasattr(value, '_sa_class_manager'):
                    safe_obj[attr] = value
                else:
                    L.l.debug('Ignoring obj to json, not simple primitive {}'.format(value))
        return utils.safeobj2json(safe_obj)
    except Exception as ex:
        L.l.critical('Error convert model obj to json, err {}'.format(ex))


def get_param(name):
    global __db_values_json
    try:
        val = models.Parameter().query_filter_first(models.Parameter.name.in_([name])).value
        return val
    except ValueError as ex:
        L.l.warning('Unable to get parameter {} error {}'.format(name, ex))
        raise ValueError
    except Exception as ex:
        L.l.critical('Exception when getting param {}, err={}'.format(name, ex))
        # db.session.rollback()
        raise ex


def commit():
    try:
        time_start = utils.get_base_location_now_date()
        query_details = "COMMIT " + str(db.session.identity_map)
        db.session.commit()
        performance.add_query(time_start, query_details=query_details)
        return True
    except IntegrityError as ex:
        L.l.error('Unable to commit DB session={}, ignored, err={}'.format(db.session, ex), exc_info=True)
        db.session.rollback()
    except InvalidRequestError as ex:
        L.l.error('Error on commit, session={}, ignoring, err={}'.format(db.session, ex), exc_info=1)
    except Exception as ex:
        L.l.warning('Exception on commit, session={} err={}'.format(db.session, ex))
        db.session.remove()
    return False


def get_mod_name(module):
    return str(module).split("'")[1]


def save_db_log(entry_name, entry_value):
    record = models.L.query.filter_by(entry_name=entry_name).first()
    if record is None:
        record = models.L(entry_name = entry_name)
    record.entry_value = entry_value
    commit()


def init_reporting():
    # http://docs.sqlalchemy.org/en/rel_0_9/dialects/mysql.html#module-sqlalchemy.dialects.mysql.mysqlconnector
    user = get_param(Constant.DB_REPORTING_USER)
    passwd = get_param(Constant.DB_REPORTING_PASS)
    uri = str(get_param(Constant.DB_REPORTING_LOCATION))
    uri_final = uri.replace('<user>', user).replace('<passwd>', passwd)
    SQLALCHEMY_BINDS = {
        Constant.DB_REPORTING_ID: uri_final
        # , 'appmeta':      'sqlite:////path/to/appmeta.db'
    }
    app.config['SQLALCHEMY_BINDS'] = SQLALCHEMY_BINDS
    db.create_all(bind=Constant.DB_REPORTING_ID)
    Constant.HAS_LOCAL_DB_REPORTING_CAPABILITY = True
    check_history_tables()


def check_table_schema(table, model_auto_update=False):
    recreate_table = False
    ex_msg = None
    try:
        # count = table.query.all()
        rec = table().query_filter_first()
    except OperationalError as oex:
        recreate_table = True
        ex_msg = str(oex)
    except InvalidRequestError:
        L.l.warning('Error on check table schema {}, ignoring'.format(table))
    except Exception as ex:
        if "ProgrammingError" in str(ex) or "pymysql.err.InternalError" in str(ex):
            recreate_table = True
            ex_msg = str(ex)
        else:
            L.l.warning('Unexpected error on check table {}, err={}'.format(table, ex))
    if recreate_table:
        L.l.critical('Table {} schema in DB seems outdated, err {}, DROP it and recreate (y/n)?'.format(ex_msg,
                                                                                                        table))
        read_drop_table(table, ex_msg, drop_without_user_ask=model_auto_update)


def read_drop_table(table, original_exception, drop_without_user_ask=False):
    if not drop_without_user_ask:
        raise Exception("Database model for table {} is not matching app tables definition".format(table))
        # x = sys.stdin.readline(1)
    else:
        x = 'y'
    if x == 'y':
        L.l.info('Dropping table {}'.format(table))
        try:
            table_name = table.query._primary_entity.entity_zero._with_polymorphic_selectable.description
            # fixme: does not work with multiple db sources
            result = db.engine.execute('DROP TABLE ' + table_name)
            commit()
        except Exception as ex:
            L.l.info('Something went wrong on drop, ignoring err {}'.format(ex))
            db.session.rollback()
        L.l.info('Creating missing schema object after table drop')
        db.create_all()
    else:
        raise original_exception


def check_history_tables():
    """Add below all history tables you want to be initialised"""
    table_collection_list = [
        models.NodeHistory, models.SensorHistory, models.SystemDiskHistory, models.SystemMonitorHistory,
        models.UpsHistory, models.PresenceHistory, models.SensorErrorHistory, models.ZoneHeatRelayHistory]
    for table in table_collection_list:
        table_str = utils.get_table_name(table)
        # do not drop and recreate historic ones
        # if table is models.PresenceHistory:
        #    check_table_schema(table, model_auto_update=True)
        # else:
        check_table_schema(table, model_auto_update=False)


def populate_tables(model_auto_update=False):
    """Add below all tables you want to be initialised"""
    global table_collection
    table_collection = [models.Node, models.Parameter, models.Module,
                        models.Area, models.Zone, models.ZoneArea, models.ZoneCustomRelay,
                        models.TemperatureTarget, models.SchedulePattern, models.HeatSchedule, models.ZoneHeatRelay,
                        models.ZoneSensor, models.ZoneAlarm,
                        models.SystemMonitor, models.SystemDisk,
                        models.Sensor, models.Ups, models.Rule,
                        models.CommandOverrideRelay, models.PlotlyCache, models.Utility, models.Presence,
                        models.SensorError, models.State, models.People,
                        models.Device, models.PeopleDevice, models.Position,
                        models.PowerMonitor]
    # tables that will be cleaned on every app start
    table_force_clean = [models.Parameter, models.Zone, models.Presence, models.Module, models.Node, models.Rule,
                         models.ZoneHeatRelay]
    # , models.Sensor]

    for table in table_collection:
        table_str = utils.get_table_name(table)
        if table in table_force_clean:
            read_drop_table(table, "Forcing table clean", drop_without_user_ask=True)
        else:
            check_table_schema(table, model_auto_update)
        if table_str in Constant.db_values_json:
            default_values = Constant.db_values_json[table_str]
            if len(table().query_all()) != len(default_values):
                L.l.info(
                    'Populating {} with default values as config record count != db count'.format(table_str))
                table().delete()
                commit()
                for config_record in default_values:
                    new_record = table()
                    # setattr(new_record, config_record, default_values[config_record])
                    for field in config_record:
                        setattr(new_record, field, config_record[field])
                    # Log.logger.info("Adding conf record: {}".format(new_record))
                    db.session.add(new_record)
                commit()

    check_table_schema(models.Node, model_auto_update)

    # reseting execute_command field to avoid running last command before shutdown
    node_obj = models.Node.query.filter_by(name=Constant.HOST_NAME).first()
    if node_obj:
        node_obj.execute_command = ''
    else:
        node_obj = models.Node()
        node_obj.add_record_to_session()
    # let this commented for test purposes (make netbook Windows look like PI)
    if Constant.HOST_NAME != 'netbook':
        #Log.logger.info("Setting current machine type to {}".format(Constant.HOST_MACHINE_TYPE))
        node_obj.machine_type = Constant.HOST_MACHINE_TYPE
    Constant.HOST_PRIORITY = node_obj.priority
    commit()

    node_list = models.Node().query_all()
    check_table_schema(models.GpioPin, model_auto_update)
    # todo: worth implementing beabglebone white?
    # populate all beaglebone black pins in db for all nodes. only used ones are mapped below, extend if more are used
    # mapping found here: https://insigntech.files.wordpress.com/2013/09/bbb_pinouts.jpg
    bbb_bcm_map = {
        'P9_11': 30, 'P9_12': 60, 'P9_13': 31, 'P9_14': 40, 'P9_15': 48, 'P9_16': 51, 'P9_24': 15, 'P9_23': 49,
        'P9_22': 2, 'P9_21': 3,
        'P8_07': 66, 'P8_08': 67, 'P8_09': 69, 'P8_11': 45, 'P8_12': 44, 'P8_15': 47, 'P8_16': 46
    }
    for node in node_list:
        if node.machine_type == Constant.MACHINE_TYPE_BEAGLEBONE:
            if len(models.GpioPin.query.filter_by(pin_type=Constant.GPIO_PIN_TYPE_BBB,
                                                  host_name=node.name).all()) != 46 * 2:  # P8_ & P9_ rows have 46 pins
                models.GpioPin.query.filter_by(pin_type=Constant.GPIO_PIN_TYPE_BBB, host_name=node.name).delete()
                commit()
                L.l.info('Populating default {} GpioPins on {} '.format(node.machine_type, node.name))
                for rail in range(8, 10):  # last range is not part of the loop
                    for pin in range(01, 47):
                        gpio = models.GpioPin()
                        gpio.pin_type = Constant.GPIO_PIN_TYPE_BBB
                        gpio.host_name = node.name
                        pincode = '0' + str(pin)
                        gpio.pin_code = 'P' + str(rail) + '_' + pincode[-2:]
                        if bbb_bcm_map.has_key(gpio.pin_code):
                            gpio.pin_index_bcm = bbb_bcm_map[gpio.pin_code]
                        else:
                            gpio.pin_index_bcm = ''
                        db.session.add(gpio)
                commit()
        # fixme: check for other PI revisions
        elif node.machine_type == Constant.MACHINE_TYPE_RASPBERRY:
            if len(models.GpioPin.query.filter_by(
                    pin_type=Constant.GPIO_PIN_TYPE_PI_STDGPIO, host_name=node.name).all()) != 40:
                models.GpioPin.query.filter_by(pin_type=Constant.GPIO_PIN_TYPE_PI_STDGPIO, host_name=node.name).delete()
                commit()
                L.l.info('Populating standard {} GpioPins on {} '.format(node.machine_type, node.name))
                for pin in range(0, 40):
                    gpio = models.GpioPin()
                    gpio.pin_type = Constant.GPIO_PIN_TYPE_PI_STDGPIO
                    gpio.host_name = node.name
                    gpio.pin_code = str(pin)
                    gpio.pin_index_bcm = pin
                    db.session.add(gpio)
            if len(models.GpioPin.query.filter_by(pin_type=Constant.GPIO_PIN_TYPE_PI_FACE_SPI,
                                                  host_name=node.name).all()) \
                    != 2 * 8 * 4:  # input/output * 8 pins * max 4 boards
                models.GpioPin.query.filter_by(pin_type=Constant.GPIO_PIN_TYPE_PI_FACE_SPI,
                                               host_name=node.name).delete()
                commit()
                L.l.info('Populating piface {} pins on {} '.format(node.machine_type, node.name))
            for board in range(0, 4):
                for pin_dir in (Constant.GPIO_PIN_DIRECTION_IN, Constant.GPIO_PIN_DIRECTION_OUT):
                    for pin in range(0, 8):  # -1
                        gpio = models.GpioPin()
                        gpio.pin_type = Constant.GPIO_PIN_TYPE_PI_FACE_SPI
                        gpio.host_name = node.name
                        gpio.pin_code = str(board) + ":" + pin_dir + ":" + str(pin)  # same as piface.format_pin_code()
                        gpio.pin_index_bcm = pin
                        gpio.board_index = board
                        db.session.add(gpio)
            commit()
        else:
            L.l.warning("Unknown machine type {} for node {}".format(node.machine_type, node))
