__author__ = 'dcristian'
import random
import sys
import datetime
import uuid

from sqlalchemy.exc import IntegrityError, OperationalError, InvalidRequestError

from main import logger
import models
from common import constant, utils
from main import db


def model_row_to_json(obj, operation=''):
    try:
        safe_obj = {}
        obj.event_sent_datetime = str(datetime.datetime.now())
        obj.operation_type=operation
        obj.event_uuid = str(uuid.uuid4())
        table_cols=obj._sa_class_manager
        for attr in table_cols:
            safe_obj[constant.JSON_PUBLISH_TABLE]=str(table_cols[attr]).split('.')[0]
            break

        #safe_obj[constant.JSON_PUBLISH_RECORD_OPERATION]=operation
        safe_obj[constant.JSON_PUBLISH_SOURCE_HOST]=str(constant.HOST_NAME)
        #safe_obj[constant.JSON_PUBLISH_DATE]=str(datetime.datetime.now())
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
                    logger.debug('Ignoring obj to json, not simple primitive {}'.format(value))
        return utils.obj2json(safe_obj)
    except Exception, ex:
        logger.critical('Error convert model obj to json, err {}'.format(ex))

def get_param(name):
    try:
        val = models.Parameter.query.filter_by(name=name).first().value
        return val
    except ValueError:
        logger.warning('Unable to get parameter {} error {}'.format(name, sys.exc_info()[0]))
        raise ValueError

def commit():
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        logger.warning('Unable to commit DB session {}, rolled back'.format(db.session))
    except InvalidRequestError:
        logger.warning('Error on commit {}, ignoring'.format(db.session))


def get_mod_name(module):
    return str(module).split("'")[1]

def check_table_schema(table, model_auto_update=False):
    try:
        count = table.query.all()
    except OperationalError, oex:
        logger.critical('Table {} schema in DB seems outdated, err {}, DROP it and recreate (y/n)?'.format(oex, table))
        read_drop_table(table, oex, model_auto_update)
    except InvalidRequestError:
        logger.warning('Error on check table schema {}, ignoring'.format(table))

def read_drop_table(table, original_exception, drop_without_user_ask=False):
    if not drop_without_user_ask:
        x = sys.stdin.readline(1)
    else:
        x='y'
    if x=='y':
        logger.warning('Dropping table {}'.format(table))
        table_name=table.query._primary_entity.entity_zero._with_polymorphic_selectable.description
        try:
            result = db.engine.execute('DROP TABLE '+table_name)
            commit()
        except Exception, ex:
            logger.warning('Something went wrong on drop, err {}'.format(ex))
        logger.info('Creating missing schema object after table drop')
        db.create_all()
    else:
        raise original_exception

def populate_tables(model_auto_update=False):
    param_list=[
            ['1', constant.P_MZP_SERVER_URL, 'http://192.168.0.10'],
            ['2', constant.P_OWSERVER_HOST_1, '127.0.0.1'],
            ['3', constant.P_OWSERVER_PORT_1, '4304'],
            ['4', constant.P_MQTT_HOST_1, '192.168.0.9'],
            ['5', constant.P_MQTT_PORT_1, '1883'],
            ['6', constant.P_MQTT_TOPIC, 'iot/main'],
            ['7', constant.P_MQTT_HOST_2, '127.0.0.1'],
            ['8', constant.P_MQTT_PORT_2, '1883'],
            ['9', constant.P_PLOTLY_USERNAME, 'xxx'],
            ['10', constant.P_PLOTLY_APIKEY, 'zzz'],
            ['11', constant.P_DDNS_RACKSPACE_CONFIG_FILE, '/home/dcristian/.rackspace.ddnsupdate.config.json'],
            ['12', constant.P_USESUDO_DISKTOOLS, 'False']
        ]
    check_table_schema(models.Parameter, model_auto_update)
    if len(models.Parameter.query.all()) < len(param_list):
        logger.info('Populating Parameter with default values')
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
             [47,'birou'], [48, 'solar jos'], [49, 'congelator']
             ]
    if len(models.Zone.query.all()) < len(zones):
        logger.info('Populating Zone with default values')
        models.Zone.query.delete()
        for pair in zones:
            db.session.add(models.Zone(pair[0], pair[1]))
        commit()

    temptarget_list=[
            [ 1, '.', 18],
            [ 2, '0', 20],
            [ 3, 'a', 20.5],
            [ 4, '1', 21],
            [ 5, 'b', 21.5],
            [ 6, '2', 22],
            [ 7, 'c', 22.5],
            [ 8, '3', 23],
            [ 9, 'd', 23.5],
            [10, '4', 24],
            [11, 'e', 24.5]
            ]
    check_table_schema(models.TemperatureTarget, model_auto_update)
    if len(models.TemperatureTarget.query.all()) < len(temptarget_list):
        logger.info('Populating Temperature Target with default values')
        models.TemperatureTarget.query.delete()
        for tuple in temptarget_list:
            record=models.TemperatureTarget(id=tuple[0], code=tuple[1], target=tuple[2])
            db.session.add(record)
            commit()

    value_list=[
            # hour in day, 24 hr format  0    4    8    12   16   20   
            [1, 'week-bucatarie',       '.... ..22 .... .... ..22 2222'],
            [2, 'weekend-bucatarie',    '.... .... 2222 2222 2222 2222'],
            [3, 'week-living',          '.... .... .... .... ..22 2222'],
            [4, 'weekend-living',       '.... .... 2222 2222 2222 2222'],
            [5, 'week-birou',           '.... .... .... .... ..22 2222'],
            [6, 'weekend-birou',        '.... .... 2222 2222 2222 2222'],
            [7, 'week-dormitor',        'bbbb bbb. .... .... .... bbbb'],
            [8, 'weekend-dormitor',     'bbbb bbb. .... .bbb .... bbbb']
            ]
    check_table_schema(models.SchedulePattern, model_auto_update)
    if len(models.SchedulePattern.query.all()) < len(value_list):
        logger.info('Populating Schedule Pattern with default values')
        models.SchedulePattern.query.delete()
        for tuple in value_list:
            record=models.SchedulePattern(id=tuple[0], name=tuple[1], pattern=tuple[2])
            db.session.add(record)
            commit()

    value_list=[
            #id, zone_id, week_id, weekend_id
            [1,  1, 1, 2], #bucatarie
            [2,  2, 3, 4], #living
            [3, 47, 5, 6], #birou
            [4,  4, 7, 8], #dormitor   
            ]
    check_table_schema(models.HeatSchedule, model_auto_update)
    if len(models.HeatSchedule.query.all()) < len(value_list):
        logger.info('Populating Heat Schedule with default values')
        models.HeatSchedule.query.delete()
        for tuple in value_list:
            record=models.HeatSchedule(id=tuple[0], zone_id=tuple[1], pattern_week_id=tuple[2],
                                       pattern_weekend_id=tuple[3])
            db.session.add(record)
            commit()

    check_table_schema(models.Node, model_auto_update)
    if len(models.Node.query.filter_by(name=constant.HOST_NAME).all()) == 0:
        logger.info('Populating Node {} with default values'.format(constant.HOST_NAME))
        if constant.HOST_NAME=='nas':
            priority = 0
        elif constant.HOST_NAME=='netbook':
            priority = 1
        elif constant.HOST_NAME=='server':
            priority = 2
        else:
            priority=random.randint(3, 100)
        db.session.add(models.Node('', name=constant.HOST_NAME, ip=constant.HOST_MAIN_IP, priority=priority))
        commit()
    else:
        #reseting execute_command field to avoid running last command before shutdown
        node = models.Node.query.filter_by(name=constant.HOST_NAME).first()
        node.execute_command = ''
        commit()
    node = models.Node.query.filter_by(name=constant.HOST_NAME).first()
    constant.HOST_PRIORITY = node.priority

    check_table_schema(models.SystemMonitor, model_auto_update)
    check_table_schema(models.SystemDisk, model_auto_update)
    check_table_schema(models.Sensor, model_auto_update)
    #if len(models.Sensor.query.all()) == 0:
        #logger.info('Populating Sensor with a test value')
        #sens = models.Sensor(address='ADDRESSTEST')
        #db.session.add(models.Sensor(0, address='ADDRESSTEST'))
        #db.session.add(sens)
        #commit(db.session)

    import alarm, heat, sensor, relay, health_monitor, graph_plotly, node, io_bbb, webui, main, ddns
    from transport import mqtt_io
    #import transport.mqtt_io

    module_list_dict = {'default':[
        [1, get_mod_name(main), True, 0],[2, get_mod_name(node), True, 1],[3, get_mod_name(health_monitor), True, 2],
        [4, get_mod_name(mqtt_io), True, 3],[5, get_mod_name(sensor), False, 4],[6, get_mod_name(relay), False, 5],
        [7, get_mod_name(heat), False, 6],[8, get_mod_name(alarm), False, 7],[9, get_mod_name(graph_plotly), False, 8],
        [10, get_mod_name(io_bbb), False, 9],[11, get_mod_name(webui), False, 10],[12, get_mod_name(ddns), False, 11]],
        'netbook':[
        [1, get_mod_name(main), True, 0],[2, get_mod_name(node), True, 1],[3, get_mod_name(health_monitor), True, 2],
        [4, get_mod_name(mqtt_io), True, 3],[5, get_mod_name(sensor), True, 4],[6, get_mod_name(relay), True, 5],
        [7, get_mod_name(heat), True, 6],[8, get_mod_name(alarm), False, 7],[9, get_mod_name(graph_plotly), False, 8],
        [10, get_mod_name(io_bbb), False, 9],[11, get_mod_name(webui), True, 10],[12, get_mod_name(ddns), True, 11]],
        'nas':[
        [1, get_mod_name(main), True, 0],[2, get_mod_name(node), True, 1],[3, get_mod_name(health_monitor), True, 2],
        [4, get_mod_name(mqtt_io), True, 3],[5, get_mod_name(sensor), True, 4],[6, get_mod_name(relay), False, 5],
        [7, get_mod_name(heat), False, 6],[8, get_mod_name(alarm), False, 7],[9, get_mod_name(graph_plotly), True, 8],
        [10, get_mod_name(io_bbb), False, 9],[11, get_mod_name(webui), True, 10],[12, get_mod_name(ddns), True, 11]],
        'pi-power':[
        [1, get_mod_name(main), True, 0],[2, get_mod_name(node), True, 1],[3, get_mod_name(health_monitor), True, 2],
        [4, get_mod_name(mqtt_io), True, 3],[5, get_mod_name(sensor), True, 4],[6, get_mod_name(relay), True, 5],
        [7, get_mod_name(heat), True, 6],[8, get_mod_name(alarm), False, 7],[9, get_mod_name(graph_plotly), False, 8],
        [10, get_mod_name(io_bbb), False, 9],[11, get_mod_name(webui), False, 10],[12, get_mod_name(ddns), False, 11]],
        'beaglebone':[
        [1, get_mod_name(main), True, 0],[2, get_mod_name(node), True, 1],[3, get_mod_name(health_monitor), True, 2],
        [4, get_mod_name(mqtt_io), True, 3],[5, get_mod_name(sensor), True, 4],[6, get_mod_name(relay), True, 5],
        [7, get_mod_name(heat), True, 6],[8, get_mod_name(alarm), False, 7],[9, get_mod_name(graph_plotly), False, 8],
        [10, get_mod_name(io_bbb), True, 9],[11, get_mod_name(webui), True, 10],[12, get_mod_name(ddns), False, 11]],
        'router':[
        [1, get_mod_name(main), True, 0],[2, get_mod_name(node), True, 1],[3, get_mod_name(health_monitor), True, 2],
        [4, get_mod_name(mqtt_io), True, 3],[5, get_mod_name(sensor), False, 4],[6, get_mod_name(relay), False, 5],
        [7, get_mod_name(heat), False, 6],[8, get_mod_name(alarm), False, 7],[9, get_mod_name(graph_plotly), False, 8],
        [10, get_mod_name(io_bbb), False, 9],[11, get_mod_name(webui), False, 10],[12, get_mod_name(ddns), True, 11]]
        }

    check_table_schema(models.Module, model_auto_update)
    if module_list_dict.has_key(constant.HOST_NAME):
        module_list = module_list_dict[constant.HOST_NAME]
        logger.info('Module is initialised with host {} specific values'.format(constant.HOST_NAME))
    else:
        module_list = module_list_dict['default']
        logger.info('Module is initialise with default template values')

    if len(models.Module.query.filter_by(host_name=constant.HOST_NAME).all()) < len(module_list):
        logger.info('Populating Module with default values')
        models.Module.query.filter_by(host_name=constant.HOST_NAME).delete()

        for tuple in module_list:
            db.session.add(models.Module(id=tuple[0], host_name=constant.HOST_NAME,
                                         name=tuple[1], active=tuple[2], start_order=tuple[3]))
        commit()

    check_table_schema(models.GpioPin, model_auto_update)
    bbb_bcm_map={
        'P9_11':30, 'P9_12':60, 'P9_13':31, 'P9_14':40, 'P9_15':48, 'P9_16':51,
        'P8_07':66, 'P8_08':67, 'P8_09':69, 'P8_11':45, 'P8_12':44, 'P8_15':47, 'P8_16':46
    }
    if len(models.GpioPin.query.filter_by(pin_type=constant.GPIO_PIN_TYPE_BBB).all()) != 46*2: #P8_ and P9_ with 46 pins
        models.GpioPin.query.filter_by(pin_type=constant.GPIO_PIN_TYPE_BBB).delete()
        commit()
        for host_name in ['beaglebone', 'netbook']:
            logger.info('Populating GpioPins with default beabglebone {} values'.format(host_name))
            for rail in range(8,10): #last range is not part of the loop
                for pin in range(01, 47):
                    gpio = models.GpioPin()
                    gpio.pin_type = constant.GPIO_PIN_TYPE_BBB
                    gpio.host_name = host_name
                    pincode = '0'+str(pin)
                    gpio.pin_code = 'P'+str(rail)+'_'+pincode[-2:]
                    if bbb_bcm_map.has_key(gpio.pin_code):
                        gpio.pin_index = bbb_bcm_map[gpio.pin_code]
                    else:
                        gpio.pin_index = ''
                    db.session.add(gpio)
        commit()
        for host_name in ['pi-power', 'pi-bell']:
            logger.info('Populating GpioPins with default raspberry pi {} values'.format(host_name))
            for pin in range(01, 27): # -1
                gpio = models.GpioPin()
                gpio.pin_type = constant.GPIO_PIN_TYPE_PI
                gpio.host_name = host_name
                gpio.pin_code = str(pin)
                gpio.pin_index = pin
                db.session.add(gpio)
        commit()

    check_table_schema(models.ZoneAlarm, model_auto_update)
    zonealarm_list={
        'beaglebone':[[47, 'P8_11'],[1,'P8_08'],[2,'P8_16'],[3,'P8_12'],[9,'P8_09'],[10,'P8_07'], [11,'P8_15']]
    }
    if len(models.ZoneAlarm.query.all()) < len(zonealarm_list):
        for host_name in zonealarm_list.keys():
            logger.info('Populating ZoneAlarm for {} with default values'.format(host_name))
            models.ZoneAlarm.query.delete()
            commit()
            for pair in zonealarm_list[host_name]:
                db.session.add(models.ZoneAlarm(pair[0], pair[1], host_name))
            commit()

    check_table_schema(models.ZoneHeatRelay, model_auto_update)
    #fixme: mapping not correct
    heat_relay_list={
        #1=bucatarie, 2=living, 47=birou, 4=dormitor
        'beaglebone': [[1, 'P9_13'], [2, 'P9_12'], [47, 'P9_11'], [4, 'P9_15']],
        #19=heat main
        'pi-power': [[19, '24']]
        #for test only
        #,'netbook':[[47, 'P9_13']]
    }
    #,[4,'P8_16']
    heat_main_source_zone_id=19
    if len(models.ZoneHeatRelay.query.all()) < len(heat_relay_list):
        models.ZoneHeatRelay.query.delete()
        commit()
        for host_name in heat_relay_list.keys():
            logger.info('Populating ZoneHeatRelay for {} with default values'.format(host_name))
            for pair in heat_relay_list[host_name]:
                db.session.add(models.ZoneHeatRelay(zone_id=pair[0], gpio_pin_code=pair[1], host_name=host_name,
                                                    is_main_heat_source=(pair[0] == heat_main_source_zone_id)))
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
            [4, 'B5000004F3285F28', 'dormitor'], [23, 'f9:01','fridge'], [49, 'f3:01', 'congelator']
        ]
    if len(models.ZoneSensor.query.all()) < len(zonesensor_list):
        logger.info('Populating ZoneSensor with default values')
        models.ZoneSensor.query.delete()
        commit()
        for pair in zonesensor_list:
            db.session.add(models.ZoneSensor(zone_id=pair[0], sensor_address=pair[1], sensor_name=pair[2]))
        commit()
