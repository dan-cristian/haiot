from pydispatch import dispatcher
import logging
import paho.mqtt.client as mqtt
import json
import sys
from common import constant, variable
import common.utils
import models
import main
import model_helper
import mqtt_io
import graph_plotly
import node

from main import db
from common import utils

def handle_event_sensor(sender):
    #print "Signal was sent by ", sender
    sensor = models.Sensor.query.filter_by(address=sender.address).first()
    if sensor==None:
        sensor = models.Sensor(sender)
        db.session.add(sensor)
    else:
        sensor.update(sender)
    db.session.commit()

def handle_event_db_model_post(model, row):
    print 'Signal was sent by model {} row {}'.format(model, row)
    if str(models.Parameter) in str(model):
        logging.info('Detected Parameter change ' + row)
    elif str(models.Module) in str(model):
        logging.info('Detected Module change, applying potential changes')
        if row.host_name == constant.HOST_NAME:
            main.init_module(row.name, row.active)
    #print model_row_to_json(row._sa_instance_state.dict)

def handle_event_mqtt_received(client, userdata, topic, obj):
    if constant.JSON_PUBLISH_TABLE in obj:
        table = str(obj[constant.JSON_PUBLISH_TABLE])
        if table == 'Node':
            node.node_run.node_update(obj)
            if 'execute_command' in obj:
                execute_command = obj['execute_command']
                host_name = obj[constant.JSON_PUBLISH_SOURCE_HOST]
                if host_name == constant.HOST_NAME:
                    main.execute_command(execute_command)
        #elif table == 'Module':

    if variable.NODE_THIS_IS_MASTER_OVERALL:
        if constant.JSON_PUBLISH_GRAPH_X in obj:
            if obj[constant.JSON_PUBLISH_SAVE_TO_GRAPH]:
                if graph_plotly.initialised:
                    graph_plotly.upload_data(obj)
                else:
                    logging.debug('Graph not initialised on obj upload to graph')
            else:
                pass
        else:
            logging.debug('Mqtt event without graphing capabilities {}'.format(obj))

def on_models_committed(sender, changes):
    try:
        for obj, change in changes:
            #avoid recursion
            if hasattr(obj, 'notify_enabled_'):
                if obj.notify_enabled_:
                    if hasattr(obj, 'db_notified_'):
                        if not obj.db_notified_:
                            obj.db_notified_ = True
                            txt = model_helper.model_row_to_json(obj, operation=change)
                            mqtt_io.sender.send_message(txt)
                else:
                    pass
    except Exception, ex:
        logging.critical('Error in DB commit hook, {}'.format(ex))

def init():
    #http://pydispatcher.sourceforge.net/
    dispatcher.connect(handle_event_sensor, signal=common.constant.SIGNAL_SENSOR, sender=dispatcher.Any)
    dispatcher.connect(handle_event_db_model_post, signal=common.constant.SIGNAL_SENSOR_DB_POST, sender=dispatcher.Any)
    dispatcher.connect(handle_event_mqtt_received, signal=common.constant.SIGNAL_MQTT_RECEIVED, sender=dispatcher.Any)