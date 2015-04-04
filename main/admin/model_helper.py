__author__ = 'dcristian'
import logging
import json
import random
import sys
import datetime
import models
from common import constant, utils
from main import db
from sqlalchemy.exc import IntegrityError, OperationalError, InvalidRequestError

def model_row_to_json(obj, operation=''):
    try:
        safe_obj = {}
        table_cols=obj._sa_class_manager
        for attr in table_cols:
            safe_obj[constant.JSON_PUBLISH_TABLE]=str(table_cols[attr]).split('.')[0]
            break
        safe_obj[constant.JSON_PUBLISH_RECORD_OPERATION]=operation
        safe_obj[constant.JSON_PUBLISH_SOURCE_HOST]=str(constant.HOST_NAME)
        safe_obj[constant.JSON_PUBLISH_DATE]=str(datetime.datetime.now())
        safe_obj[constant.JSON_PUBLISH_TARGET_HOST]=constant.JSON_PUBLISH_VALUE_TARGET_HOST_ALL
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
                    logging.debug('Ignoring obj to json, not simple primitive {}'.format(value))
        return utils.obj2json(safe_obj)
    except Exception, ex:
        logging.critical('Error convert model obj to json, err {}'.format(ex))

def get_param(name):
    try:
        val = models.Parameter.query.filter_by(name=name).first().value
        return val
    except ValueError:
        logging.warning('Unable to get parameter {} error {}'.format(name, sys.exc_info()[0]))
        raise ValueError

def commit():
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        logging.warning('Unable to commit DB session {}, rolled back'.format(db.session))
    except InvalidRequestError:
        logging.warning('Error on commit {}, ignoring'.format(db.session))


def get_mod_name(module):
    return str(module).split("'")[1]

def check_table_schema(table, model_auto_update=False):
    try:
        count = table.query.all()
    except OperationalError, oex:
        logging.critical('Table {} schema in DB seems outdated, err {}, DROP it and recreate (y/n)?'.format(oex, table))
        read_drop_table(table, oex, model_auto_update)
    except InvalidRequestError:
        logging.warning('Error on check table schema {}, ignoring'.format(table))

def read_drop_table(table, original_exception, drop_without_user_ask=False):
    if not drop_without_user_ask:
        x = sys.stdin.readline(1)
    else:
        x='y'
    if x=='y':
        logging.warning('Dropping table {}'.format(table))
        table_name=table.query._primary_entity.entity_zero._with_polymorphic_selectable.description
        try:
            result = db.engine.execute('DROP TABLE '+table_name)
            commit()
        except Exception, ex:
            logging.warning('Something went wrong on drop, err {}'.format(ex))
        logging.info('Creating missing schema object after table drop')
        db.create_all()
    else:
        raise original_exception

def populate_tables(model_auto_update=False):
    param_list=[
            ['1', constant.P_MZP_SERVER_URL, 'http://192.168.0.10'],
            ['2', constant.P_OWSERVER_HOST_1, '192.168.0.113'],
            ['3', constant.P_OWSERVER_PORT_1, '4304'],
            ['4', constant.P_MQTT_HOST_1, '192.168.0.9'],
            ['5', constant.P_MQTT_PORT_1, '1883'],
            ['6', constant.P_MQTT_TOPIC, 'iot/main'],
            ['7', constant.P_MQTT_HOST_2, '127.0.0.1'],
            ['8', constant.P_MQTT_PORT_2, '1883'],
            ['9', constant.P_PLOTLY_USERNAME, 'dancri77'],
            ['10', constant.P_PLOTLY_APIKEY, 'lw2w6fz9xk']
        ]
    check_table_schema(models.Parameter, model_auto_update)
    if len(models.Parameter.query.all()) < len(param_list):
        logging.info('Populating Parameter with default values')
        models.Parameter.query.delete()
        for param_tuple in param_list:
            param=models.Parameter(id=param_tuple[0], name=param_tuple[1], value=param_tuple[2])
            db.session.add(param)
            commit()

    check_table_schema(models.Zone, model_auto_update)
    zones = [[1,'bucatarie'], [2,'living'],[3,'beci mic'],[4,'dormitor'],[5,'baie mare'],
             [6,'bebe'],[7,'curte fata'],[8,'hol intrare'],[9,'beci mare'],[10,'scari beci'],[11,'etaj hol'],
             [12,'curte fata'],[13,'living tv'],[14,'usa poarta'],[15,'usa casa'],[16, 'usa portita'],
             [17,'usa garaj mare'], [18, 'buton usa'], [19, 'heat main'], [20, 'heat living'], [21, 'heat birou'],
             [22, 'heat bucatarie'], [23, 'fridge'], [24, 'powermeter'], [25,'boiler'], [26,'congelator'],
             [27,'pod fata'], [28,'drum fata'],[29,'hol beci'],[30,'power beci'],[31,'gas heater'],
             [32,'watermain'],[33,'watersecond'],[34,'horn'],[35,'gas meter'],[36,'front valve'],
             [37,'back valve'],[38,'puffer'],[39,'back pump'],[40,'back lights'],[41,'front lights'],
             [42,'hotwater mater'], [43,'headset'],[44,'heat dormitor'],[45,'powerserver'],[46,'ups main'],
             [47,'birou'], [48, 'solar jos']
             ]
    if len(models.Zone.query.all()) < len(zones):
        logging.info('Populating Zone with default values')
        models.Zone.query.delete()
        for pair in zones:
            db.session.add(models.Zone(pair[0], pair[1]))
        commit()

    temptarget_list=[
            [1, 'x', 18],
            [2, '0', 20],
            [3, '1', 21],
            [4, '2', 22],
            [5, '3', 23],
            [6, '4', 24]
            ]
    check_table_schema(models.TemperatureTarget, model_auto_update)
    if len(models.TemperatureTarget.query.all()) < len(temptarget_list):
        logging.info('Populating Temperature Target with default values')
        models.TemperatureTarget.query.delete()
        for tuple in temptarget_list:
            record=models.TemperatureTarget(id=tuple[0], code=tuple[1], target=tuple[2])
            db.session.add(record)
            commit()

    value_list=[
            [1, 'week-bucatarie',       'xxxx-xx22-xxxx-xxxx-xx22-2222'],
            [2, 'weekend-bucatarie',    'xxxx-xxxx-2222-2222-2222-2222'],
            [3, 'week-living',          'xxxx-xxxx-xxxx-xxxx-xx22-2222'],
            [4, 'weekend-living',       'xxxx-xxxx-2222-2222-2222-2222']
            ]
    check_table_schema(models.SchedulePattern, model_auto_update)
    if len(models.SchedulePattern.query.all()) < len(value_list):
        logging.info('Populating Schedule Pattern with default values')
        models.SchedulePattern.query.delete()
        for tuple in value_list:
            record=models.SchedulePattern(id=tuple[0], name=tuple[1], pattern=tuple[2])
            db.session.add(record)
            commit()

    value_list=[
            [1, 1, 1, 2], #bucatarie
            [2, 2, 3, 4], #living
            ]
    check_table_schema(models.HeatSchedule, model_auto_update)
    if len(models.HeatSchedule.query.all()) < len(value_list):
        logging.info('Populating Heat Schedule with default values')
        models.HeatSchedule.query.delete()
        for tuple in value_list:
            record=models.HeatSchedule(id=tuple[0], zone_id=tuple[1], pattern_week_id=tuple[2],
                                       pattern_weekend_id=tuple[3])
            db.session.add(record)
            commit()

    check_table_schema(models.Node, model_auto_update)
    if len(models.Node.query.filter_by(name=constant.HOST_NAME).all()) == 0:
        logging.info('Populating Node {} with default values'.format(constant.HOST_NAME))
        if constant.HOST_NAME=='nas':
            priority = 0
        else:
            priority=random.randint(1, 100)
        db.session.add(models.Node('', name=constant.HOST_NAME, ip=constant.HOST_MAIN_IP, priority=priority))
        commit()
    else:
        #reseting execute_command field to avoid running last command before shutdown
        node = models.Node.query.filter_by(name=constant.HOST_NAME).first()
        node.execute_command = ''
        commit()

    #if len(models.Sensor.query.all()) == 0:
        #logging.info('Populating Sensor with a test value')
        #sens = models.Sensor(address='ADDRESSTEST')
        #db.session.add(models.Sensor(0, address='ADDRESSTEST'))
        #db.session.add(sens)
        #commit(db.session)

    import alarm, heat, sensor, relay, mqtt_io, health_monitor, graph_plotly, node, io_bbb, webui, main
    module_list_dict = {'default':[
        [1, get_mod_name(main), True, 0],[2, get_mod_name(node), True, 1],[3, get_mod_name(health_monitor), True, 2],
        [4, get_mod_name(mqtt_io), True, 3],[5, get_mod_name(sensor), False, 4],[6, get_mod_name(relay), False, 5],
        [7, get_mod_name(heat), False, 6],[8, get_mod_name(alarm), False, 7],[9, get_mod_name(graph_plotly), False, 8],
        [10, get_mod_name(io_bbb), False, 9],[11, get_mod_name(webui), False, 10]],
        'netbook':[
        [1, get_mod_name(main), True, 0],[2, get_mod_name(node), True, 1],[3, get_mod_name(health_monitor), True, 2],
        [4, get_mod_name(mqtt_io), True, 3],[5, get_mod_name(sensor), False, 4],[6, get_mod_name(relay), False, 5],
        [7, get_mod_name(heat), False, 6],[8, get_mod_name(alarm), False, 7],[9, get_mod_name(graph_plotly), True, 8],
        [10, get_mod_name(io_bbb), False, 9],[11, get_mod_name(webui), True, 10]],
        'nas':[
        [1, get_mod_name(main), True, 0],[2, get_mod_name(node), True, 1],[3, get_mod_name(health_monitor), True, 2],
        [4, get_mod_name(mqtt_io), True, 3],[5, get_mod_name(sensor), False, 4],[6, get_mod_name(relay), False, 5],
        [7, get_mod_name(heat), False, 6],[8, get_mod_name(alarm), False, 7],[9, get_mod_name(graph_plotly), True, 8],
        [10, get_mod_name(io_bbb), False, 9],[11, get_mod_name(webui), True, 10]]
        }

    check_table_schema(models.Module, model_auto_update)
    if module_list_dict.has_key(constant.HOST_NAME):
        module_list = module_list_dict[constant.HOST_NAME]
        logging.info('Module is initialised with host {} specific values'.format(constant.HOST_NAME))
    else:
        module_list = module_list_dict['default']
        logging.info('Module is initialise with default template values')

    if len(models.Module.query.filter_by(host_name=constant.HOST_NAME).all()) < len(module_list):
        logging.info('Populating Module with default values')
        models.Module.query.filter_by(host_name=constant.HOST_NAME).delete()

        for tuple in module_list:
            db.session.add(models.Module(id=tuple[0], host_name=constant.HOST_NAME,
                                         name=tuple[1], active=tuple[2], start_order=tuple[3]))
        commit()

    check_table_schema(models.GpioPin, model_auto_update)
    if len(models.GpioPin.query.filter_by(pin_type=constant.GPIO_PIN_TYPE_BBB).all()) != 46 * 2:#P8_ and P9_ with 46 pins
        models.GpioPin.query.filter_by(pin_type=constant.GPIO_PIN_TYPE_BBB).delete()
        commit()
        logging.info('Populating GpioPins with default beabglebone values')
        for rail in range(8,10): #last range is not part of the loop
            for pin in range(01, 47):
                gpio = models.GpioPin()
                gpio.pin_type=constant.GPIO_PIN_TYPE_BBB
                pincode='0'+str(pin)
                gpio.pin_code='P'+str(rail)+'_'+pincode[-2:]
                db.session.add(gpio)
                commit()


    check_table_schema(models.ZoneAlarm, model_auto_update)
    zonealarm_list=[[47, 'P8_11'],[1,'P8_08'],[2,'P8_16'],[3,'P8_12'],[9,'P8_09'],[10,'P8_07'],[11,'P8_15']]
    if len(models.ZoneAlarm.query.all()) < len(zonealarm_list):
        logging.info('Populating ZoneAlarm with default values')
        models.ZoneAlarm.query.delete()
        commit()
        for pair in zonealarm_list:
            db.session.add(models.ZoneAlarm(pair[0], pair[1]))
        commit()

    #if True:
    check_table_schema(models.ZoneSensor, model_auto_update)
    zonesensor_list=[
            [34, '5C000004F344F828','horn'],[3,'95000003BDF98428','beci mic'],[48,'D9000004F3BFA428', 'solar jos'],
            [38,'04000004F3DE2128', 'puffer sus'],[38,'AE000003BDFFB928', 'puffer mijloc'],
            [38,'12000004F3428528', 'puffer jos'], [31,'66000003BE22ED28', 'gas heater'],
            [25, '96000003BDFE5D28', 'boiler sus'], [25, '53000004F296DD28', 'boiler mijloc'],
            [25, 'C8000004F28B0728', 'boiler jos'], [2, '41000003BE099C28', 'living'],
            [1, 'AA000003BDE6C728', 'bucatarie'], [27, 'E400000155E72D26', 'pod fata'],
            [4, 'B5000004F3285F28', 'dormitor']
        ]
    if len(models.ZoneSensor.query.all()) < len(zonesensor_list):
        logging.info('Populating ZoneSensor with default values')
        models.ZoneSensor.query.delete()
        commit()
        for pair in zonesensor_list:
            db.session.add(models.ZoneSensor(zone_id=pair[0], sensor_address=pair[1], sensor_name=pair[2]))
        commit()
