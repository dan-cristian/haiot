from pydispatch import dispatcher

from main.logger_helper import Log
from main import thread_pool, persistence
from common import Constant, variable, utils
import transport
import models
import main
import model_helper
import node
import sensor
import heat
import gpio
import rule
import main.persistence


__mqtt_event_list = []
#__mqtt_lock = threading.Lock()

def handle_local_event_db_post(model, row):
    #executed on local db changes done via web ui only (includes API calls)
    processed = False
    Log.logger.info('Local DB change sent by model {} row {}'.format(model, row))
    if str(models.Parameter) in str(model):
        #fixme: update app if params are changing to avoid need for restart
        processed = True
    #no need to propagate changes to other nodes
    elif str(models.Module) in str(model):
        if row.host_name == Constant.HOST_NAME:
            main.init_module(row.name, row.active)
            processed = True
    #propagate changes to all nodes as eac must execute db sync or other commands locally
    elif str(models.Node) in str(model) \
            or str(models.GpioPin) in str(model) or str(models.ZoneCustomRelay) in str(model) \
            or str(models.Rule) in str(model):
        txt = model_helper.model_row_to_json(row, operation='update')
        #fixme: execute critical events directly
        if transport.mqtt_io.client_connected:
            transport.send_message_json(json = txt)
        else:
            #execute event directly as a shortcut as mqtt is not available
            handle_event_mqtt_received(None, None, 'direct-event', txt)
        processed = True

    if processed:
        Log.logger.info('Detected {} record change, row={}, trigger executed'.format(model, row))


def handle_event_mqtt_received(client, userdata, topic, obj):
    #executed on every mqqt message received
    #global __mqtt_lock
    #__mqtt_lock.acquire()
    try:
        __mqtt_event_list.append(obj)
    finally:
        #__mqtt_lock.release()
        pass


def on_models_committed(sender, changes):
    # executed on all db commits
    try:
        for obj, change in changes:
            # avoid recursion
            if hasattr(obj, Constant.JSON_PUBLISH_NOTIFY_TRANSPORT):
                # only send mqtt message once for db saves intended to be distributed
                if obj.notify_transport_enabled:
                    if hasattr(obj, Constant.JSON_PUBLISH_NOTIFY_DB_COMMIT):
                        if not obj.notified_on_db_commit:
                            obj.notified_on_db_commit = True
                            txt = model_helper.model_row_to_json(obj, operation=change)
                            transport.send_message_json(json=txt)
                else:
                    pass
            #send object to rule parser, if connected
            dispatcher.send(Constant.SIGNAL_DB_CHANGE_FOR_RULES, obj=obj, change=change)
    except Exception, ex:
        Log.logger.exception('Error in DB commit hook, {}'.format(ex))


def mqtt_thread_run():
    #runs periodically and executes received mqqt messages from queue
    #global __mqtt_lock
    #__mqtt_lock.acquire()
    from cloud import graph_plotly
    try:
        last_count = len(__mqtt_event_list)
        for obj in __mqtt_event_list:
            try:
                __mqtt_event_list.remove(obj)
                # events received via mqtt transport
                table = None
                # fixme: make it generic to work with any transport
                source_host = obj[Constant.JSON_PUBLISH_SOURCE_HOST]
                if Constant.JSON_PUBLISH_TABLE in obj:
                    table = str(obj[Constant.JSON_PUBLISH_TABLE])
                    if table == utils.get_table_name(models.Node):#'Node':
                        node.node_run.node_update(obj)
                        if 'execute_command' in obj:
                            execute_command = obj['execute_command']
                            host_name = obj['name']
                            # execute command on target host or on current host
                            # (usefull when target is down - e.g. wake cmd
                            if (host_name == Constant.HOST_NAME or source_host == Constant.HOST_NAME) \
                                    and execute_command != '':
                                server_node = models.Node.query.filter_by(name=host_name).first()
                                main.execute_command(execute_command, node=server_node)
                    elif table == utils.get_table_name(models.ZoneHeatRelay):
                        if heat.initialised:
                            heat.heat_update(obj)
                    elif table == utils.get_table_name(models.Sensor):
                        sensor.sensor_update(obj)
                    elif table == utils.get_table_name(models.ZoneCustomRelay):
                        gpio.zone_custom_relay_record_update(obj)
                    elif table == utils.get_table_name(models.GpioPin):
                        gpio.gpio_record_update(obj)
                    elif table == utils.get_table_name(models.Rule):
                        rule.rule_record_update(obj)
                    elif table == utils.get_table_name(models.PlotlyCache):
                        graph_plotly.cache_record_update(obj)

                if Constant.JSON_MESSAGE_TYPE in obj:
                    if variable.NODE_THIS_IS_MASTER_LOGGING:
                        if source_host != Constant.HOST_NAME:
                            levelname = obj['level']
                            msg = obj['message']
                            msgdatetime = obj['datetime']
                            message = '{}, {}, {}'.format(source_host, msgdatetime, msg)
                            if levelname == 'INFO':
                                Log.remote_logger.info(message)
                            elif levelname == 'WARNING':
                                Log.remote_logger.warning(message)
                            elif levelname == 'CRITICAL':
                                Log.remote_logger.critical(message)
                            elif levelname == 'ERROR':
                                Log.remote_logger.error(message)
                            elif levelname == 'DEBUG':
                                Log.remote_logger.debug(message)
                        # else:
                            # Log.logger.warning('This node is master logging but emits remote logs, is a circular reference')

                # if record has fields that enables persistence (in cloud or local)
                if variable.NODE_THIS_IS_MASTER_OVERALL and Constant.JSON_PUBLISH_GRAPH_X in obj:
                    if Constant.JSON_PUBLISH_SAVE_TO_HISTORY in obj:
                        # if record must be saved to local db
                        if obj[Constant.JSON_PUBLISH_SAVE_TO_HISTORY] and Constant.HAS_LOCAL_DB_REPORTING_CAPABILITY:
                            persistence.save_to_history(obj, save_to_local_db=True)

                        # if record is marked to be uploaded to a graph
                        if obj[Constant.JSON_PUBLISH_SAVE_TO_GRAPH]:
                            persistence.save_to_history(obj, upload_to_cloud=True)
                            # lazy init as plotly is an optional module
                            from cloud import graph_plotly
                            if graph_plotly.initialised:
                                start = utils.get_base_location_now_date()
                                # initial implementation
                                # graph_plotly.upload_data(obj)
                                persistence.save_to_history(obj, upload_to_cloud=True)
                                elapsed = (utils.get_base_location_now_date() - start).total_seconds()
                                Log.logger.debug('Plotly upload took {}s'.format(elapsed))
                            else:
                                Log.logger.debug('Graph not initialised on obj upload to graph')
                if len(__mqtt_event_list) > last_count:
                    Log.logger.debug('Not keeping up with {} mqtt events'.format(len(__mqtt_event_list)))
            except Exception, ex:
                Log.logger.critical("Error processing err={}, mqtt={}".format(ex, obj))
    except Exception, ex:
        Log.logger.critical("General error processing mqtt: {}".format(ex))
    finally:
        #__mqtt_lock.release()
        pass

def init():
    #http://pydispatcher.sourceforge.net/
    dispatcher.connect(handle_local_event_db_post, signal=Constant.SIGNAL_SENSOR_DB_POST, sender=dispatcher.Any)
    dispatcher.connect(handle_event_mqtt_received, signal=Constant.SIGNAL_MQTT_RECEIVED, sender=dispatcher.Any)

    thread_pool.add_interval_callable(mqtt_thread_run, run_interval_second=1)

