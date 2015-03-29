__author__ = 'dcristian'
import logging
import json
import random
import sys
import datetime
import models
from common import constant, utils
from main import db
from sqlalchemy.exc import IntegrityError, OperationalError

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
                if value is not None: safe_obj[attr] = value
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

def commit(session):
    try:
        session.commit()
        session.flush()
    except IntegrityError:
        session.rollback()
        logging.warning('Unable to commit DB session {}, rolled back'.format(session))


def get_mod_name(module):
    return str(module).split("'")[1]

def check_table_schema(table):
    try:
        count = table.query.all()
    except OperationalError, oex:
        logging.critical('Table {} schema in DB seems outdated, DROP it and recreate (y/n)?'.format(table))
        read_drop_table(table, oex)

def read_drop_table(table, original_exception):
    x = sys.stdin.readline(1)
    if x=='y':
        logging.warning('Dropping table {}'.format(table))
        table_name=table.query._primary_entity.entity_zero._with_polymorphic_selectable.description
        result = db.engine.execute('DROP TABLE '+table_name)
        commit(db.session)
        logging.info('Creating missing schema object after table drop')
        db.create_all()
    else:
        raise original_exception

def populate_tables():
    if len(models.Parameter.query.all()) < 3:
        logging.info('Populating Parameter with default values')
        db.session.add(models.Parameter('1', constant.P_MZP_SERVER_URL, 'http://192.168.0.10'))
        commit(db.session)
        db.session.add(models.Parameter('2', constant.P_OWSERVER_HOST_1, '192.168.0.113'))
        commit(db.session)
        db.session.add(models.Parameter('3', constant.P_OWSERVER_PORT_1, '4304'))
        commit(db.session)
        db.session.add(models.Parameter('4', constant.P_MQTT_HOST, '192.168.0.9'))
        commit(db.session)
        db.session.add(models.Parameter('5', constant.P_MQTT_PORT, '1883'))
        commit(db.session)
        db.session.add(models.Parameter('6', constant.P_MQTT_TOPIC, 'iot/main'))
        commit(db.session)
        db.session.add(models.Parameter('7', constant.P_PLOTLY_USERNAME, 'dancri77'))
        commit(db.session)
        db.session.add(models.Parameter('8', constant.P_PLOTLY_APIKEY, 'lw2w6fz9xk'))
        commit(db.session)


    if len(models.Node.query.all()) == 0:
        logging.info('Populating Node with default values')
        if constant.HOST_NAME=='nas': priority = 0
        else: priority=random.randint(1, 100)
        db.session.add(models.Node('', name=constant.HOST_NAME, ip=constant.HOST_MAIN_IP, priority=priority))
        commit(db.session)

    if len(models.Sensor.query.all()) == 0:
        logging.info('Populating Sensor with a test value')

        sens = models.Sensor(address='ADDRESSTEST')
        #db.session.add(models.Sensor(0, address='ADDRESSTEST'))
        db.session.add(sens)
        commit(db.session)

    import alarm, heat, sensor, relay, mqtt_io, health_monitor, graph_plotly, node, io_bbb
    module_list=[
        ['1', get_mod_name(node), True, 0], ['2', get_mod_name(health_monitor), True, 1],
        ['3', get_mod_name(mqtt_io), True, 2], ['4', get_mod_name(sensor), False, 3],
        ['5', get_mod_name(relay), False, 4], ['6', get_mod_name(heat), False, 5],
        ['7', get_mod_name(alarm), False, 6], ['8', get_mod_name(graph_plotly), False, 7],
        ['9', get_mod_name(io_bbb), False, 8]
    ]
    check_table_schema(models.Module)
    if len(models.Module.query.all()) < len(module_list):
        logging.info('Populating Module with default values')
        models.Module.query.delete()
        for tuple in module_list:
            db.session.add(models.Module(id=tuple[0], name=tuple[1], active=tuple[2], start_order=tuple[3]))
        commit(db.session)

    check_table_schema(models.GpioPin)
    if len(models.GpioPin.query.filter_by(pin_type=constant.GPIO_PIN_TYPE_BBB).all()) != 46 * 2:#P8_ and P9_ with 46 pins
        models.GpioPin.query.filter_by(pin_type=constant.GPIO_PIN_TYPE_BBB).delete()
        commit(db.session)
        logging.info('Populating GpioPins with default beabglebone values')
        for rail in range(8,10): #last range is not part of the loop
            for pin in range(01, 47):
                gpio = models.GpioPin()
                gpio.pin_type=constant.GPIO_PIN_TYPE_BBB
                pincode='0'+str(pin)
                gpio.pin_code='P'+str(rail)+'_'+pincode[-2:]
                db.session.add(gpio)
                commit(db.session)

    check_table_schema(models.Zone)
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
        commit(db.session)

    check_table_schema(models.ZoneAlarm)
    zonealarm_list=[[47, 'P8_11'],[1,'P8_08'],[2,'P8_16'],[3,'P8_12'],[9,'P8_09'],[10,'P8_07'],[11,'P8_15']]
    if len(models.ZoneAlarm.query.all()) < len(zonealarm_list):
        logging.info('Populating ZoneAlarm with default values')
        models.ZoneAlarm.query.delete()
        commit(db.session)
        for pair in zonealarm_list:
            db.session.add(models.ZoneAlarm(pair[0], pair[1]))
        commit(db.session)

    check_table_schema(models.ZoneSensor)
    zonesensor_list=[
            [34, '5C000004F344F828','horn'],[3,'95000003BDF98428','beci mic'],[48,'D9000004F3BFA428', 'solar jos'],
            [38,'04000004F3DE2128', 'puffer sus'],[38,'AE000003BDFFB928', 'puffer mijloc'],
            [38,'12000004F3428528', 'puffer jos'], [31,'66000003BE22ED28', 'gas heater'],
            [25, '96000003BDFE5D28', 'boiler sus'], [25, '53000004F296DD28', 'boiler mijloc'],
            [25, 'C8000004F28B0728', 'boiler jos'], [2, '41000003BE099C28', 'living'],
            [1, 'AA000003BDE6C728', 'bucatarie'], [27, 'E400000155E72D26', 'pod fata']
        ]
    if len(models.ZoneSensor.query.all()) < len(zonesensor_list):
        logging.info('Populating ZoneSensor with default values')
        models.ZoneSensor.query.delete()
        commit(db.session)
        for pair in zonesensor_list:
            db.session.add(models.ZoneSensor(zone_id=pair[0], sensor_address=pair[1], sensor_name=pair[2]))
        commit(db.session)
