from pydispatch import dispatcher
import threading
from main import logger, remote_logger
from main.admin import thread_pool
from common import constant, variable, utils
import common.utils
import transport
import models
import main
import model_helper
import graph_plotly
import node
import sensor
import heat


__mqtt_event_list = []
#__mqtt_lock = threading.Lock()

def handle_local_event_db_post(model, row):
    #executed on local db changes done via web ui only
    print 'Signal was sent by model {} row {}'.format(model, row)
    if str(models.Parameter) in str(model):
        logger.info('Detected Parameter change ' + row)
    elif str(models.Module) in str(model):
        logger.info('Detected Module change, applying potential changes')
        if row.host_name == constant.HOST_NAME:
            main.init_module(row.name, row.active)
    elif str(models.Node) in str(model):
        logger.info('Detected Node change, applying potential changes')
        txt = model_helper.model_row_to_json(row, operation='update')
        transport.send_message_json(json = txt)

def handle_event_mqtt_received(client, userdata, topic, obj):
    #global __mqtt_lock
    #__mqtt_lock.acquire()
    try:
        __mqtt_event_list.append(obj)
    finally:
        #__mqtt_lock.release()
        pass

def on_models_committed(sender, changes):
    try:
        for obj, change in changes:
            #avoid recursion
            if hasattr(obj, 'notify_transport_enabled'):
                if obj.notify_transport_enabled:
                    if hasattr(obj, 'notified_on_db_commit'):
                        if not obj.notified_on_db_commit:
                            obj.notified_on_db_commit = True
                            txt = model_helper.model_row_to_json(obj, operation=change)
                            transport.send_message_json(json = txt)
                else:
                    pass
    except Exception, ex:
        logger.critical('Error in DB commit hook, {}'.format(ex))


def mqtt_thread_run():
    #global __mqtt_lock
    #__mqtt_lock.acquire()
    try:
        last_count = len(__mqtt_event_list)
        for obj in __mqtt_event_list:
            __mqtt_event_list.remove(obj)
            #events received via mqtt transport
            table = None
            #fixme: make it generic to work with any transport
            if constant.JSON_PUBLISH_TABLE in obj:
                table = str(obj[constant.JSON_PUBLISH_TABLE])
                if table == utils.get_table_name(models.Node):#'Node':
                    node.node_run.node_update(obj)
                    if 'execute_command' in obj:
                        execute_command = obj['execute_command']
                        host_name = obj['name']
                        if host_name == constant.HOST_NAME and execute_command != '':
                            main.execute_command(execute_command)
                elif table == utils.get_table_name(models.ZoneHeatRelay):
                    if heat.initialised:
                        heat.heat_update(obj)
                elif table == utils.get_table_name(models.Sensor):
                    sensor.sensor_update(obj)

            if constant.JSON_MESSAGE_TYPE in obj:
                if variable.NODE_THIS_IS_MASTER_LOGGING:
                    if obj['source_host'] != constant.HOST_NAME:
                        levelname = obj['level']
                        msg = obj['message']
                        msgdatetime = obj['datetime']
                        source_host = obj['source_host']
                        message = '{}, {}, {}'.format(source_host, msgdatetime, msg)
                        remote_logger
                        if levelname == 'INFO':
                            remote_logger.info(message)
                        elif levelname == 'WARNING':
                            remote_logger.warning(message)
                        elif levelname == 'CRITICAL':
                            remote_logger.critical(message)
                        elif levelname == 'ERROR':
                            remote_logger.error(message)
                        elif levelname == 'DEBUG':
                            remote_logger.debug(message)
                    #else:
                        #logger.warning('This node is master logging but emits remote logs, is a circular reference')

            if variable.NODE_THIS_IS_MASTER_OVERALL:
                if constant.JSON_PUBLISH_GRAPH_X in obj:
                    if obj[constant.JSON_PUBLISH_SAVE_TO_GRAPH]:
                        if graph_plotly.initialised:
                            start = utils.get_base_location_now_date()
                            graph_plotly.upload_data(obj)
                            elapsed = (utils.get_base_location_now_date() - start).total_seconds()
                            logger.debug('Plotly upload took {}s'.format(elapsed))
                        else:
                            logger.debug('Graph not initialised on obj upload to graph')
                    else:
                        pass
                else:
                    logger.debug('Mqtt event without graphing capabilities {}'.format(obj))

            if len(__mqtt_event_list) > last_count:
                logger.debug('Not keeping up with {} mqtt events'.format(len(__mqtt_event_list)))
    finally:
        #__mqtt_lock.release()
        pass

def init():
    #http://pydispatcher.sourceforge.net/
    #dispatcher.connect(handle_event_sensor, signal=common.constant.SIGNAL_SENSOR, sender=dispatcher.Any)
    dispatcher.connect(handle_local_event_db_post, signal=common.constant.SIGNAL_SENSOR_DB_POST, sender=dispatcher.Any)
    dispatcher.connect(handle_event_mqtt_received, signal=common.constant.SIGNAL_MQTT_RECEIVED, sender=dispatcher.Any)
    thread_pool.add_callable(mqtt_thread_run, run_interval_second=1)

