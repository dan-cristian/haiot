__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import time
import datetime
import random

from main.logger_helper import L
from common import Constant, variable, utils
from main.admin import models
from main.admin.model_helper import commit
from transport import mqtt_io

first_run = True
since_when_i_should_be_master = datetime.datetime.max
node_state_uuid = None
progress_status = None


#save node state to db, except for current node. no decisions taken on node election
def node_update(obj=None):
    if not obj:
        obj = {}
    try:
        node_host_name = utils.get_object_field_value(obj, 'name')
        L.l.debug('Received node state update from {}'.format(node_host_name))
        #avoid node to update itself in infinite recursion
        if node_host_name != Constant.HOST_NAME:
            models.Node().save_changed_fields_from_json_object(json_object=obj, unique_key_name='name',
                                                               notify_transport_enabled=False, save_to_graph=False)
        else:
            L.l.debug('Skipping node DB save, this node is master = {}'.format(
                variable.NODE_THIS_IS_MASTER_OVERALL))
            sent_date = utils.get_object_field_value(obj, 'event_sent_datetime')
            if sent_date is not None:
                event_sent_date_time = utils.parse_to_date(sent_date)
                seconds_elapsed = (utils.get_base_location_now_date()-event_sent_date_time).total_seconds()
                if seconds_elapsed>15:
                    L.l.warning('Very slow mqtt, delay is {} seconds rate msg {}/min'.format(seconds_elapsed,
                                                                                             mqtt_io.mqtt_msg_count_per_minute))
    except Exception, ex:
        L.l.warning('Error on node update, err {}'.format(ex))

def check_if_no_masters_overall():
    node_masters = models.Node.query.filter_by(is_master_overall=True).all()
    return len(node_masters) == 0

#elect and set master status in db for current node only. master is elected by node_id priority, if alive
def update_master_state():
    master_overall_selected=False
    try:
        alive_date_time = utils.get_base_location_now_date() - datetime.timedelta(minutes=1)
        node_list = models.Node.query.order_by(models.Node.priority).all()
        for node in node_list:
            #if recently alive, in order of id prio
            if node.updated_on >= alive_date_time and (not master_overall_selected):
                if node.is_master_overall:
                    L.l.debug('Node {} is already master, all good we have a master'.format(node.name))
                    master_overall_selected = True
                else:
                    L.l.info('Node {} will become a master'.format(node.name))
                    if node.name == Constant.HOST_NAME:
                        node.is_master_overall = True
                        node.notify_enabled_ = True
                        commit()
                    master_overall_selected = True
            else:
                if master_overall_selected and node.is_master_overall:
                    L.l.debug('Node {} should lose master status, if alive'.format(node.name))
                    if node.name == Constant.HOST_NAME:
                        node.is_master_overall = False
                        node.notify_enabled_ = True
                        commit()
            # applying node master status locally, if changed in db
            if node.name == Constant.HOST_NAME:
                variable.NODE_THIS_IS_MASTER_LOGGING = node.is_master_logging

                if variable.NODE_THIS_IS_MASTER_OVERALL != node.is_master_overall:
                    if not node.is_master_overall:
                        # disabling local mastership immediately
                        variable.NODE_THIS_IS_MASTER_OVERALL = node.is_master_overall
                        L.l.info('Immediate change in node mastership, local node is master={}'.format(
                            variable.NODE_THIS_IS_MASTER_OVERALL))
                    else:
                        global since_when_i_should_be_master
                        # check seconds lapsed since cluster agreed I must be or lose master
                        seconds_elapsed = (utils.get_base_location_now_date() - since_when_i_should_be_master).total_seconds()
                        if check_if_no_masters_overall() or seconds_elapsed > 10:
                            variable.NODE_THIS_IS_MASTER_OVERALL = node.is_master_overall
                            L.l.info('Change in node mastership, local node is master={}'.format(
                                variable.NODE_THIS_IS_MASTER_OVERALL))
                            since_when_i_should_be_master = datetime.datetime.max
                        else:
                            L.l.info('Waiting to set master status, sec. lapsed={}'.format(seconds_elapsed))
                        if not variable.NODE_THIS_IS_MASTER_OVERALL:
                            # record date when cluster agreed I must be master
                            if since_when_i_should_be_master == datetime.datetime.max:
                                since_when_i_should_be_master = utils.get_base_location_now_date()
    except Exception, ex:
        L.l.warning('Error try_become_master, err {}'.format(ex))


def announce_node_state():
    global progress_status
    try:
        L.l.debug('I tell everyone my node state')
        #current_record = models.Node.query.filter_by(name=constant.HOST_NAME).first()
        node = models.Node()
        current_record = models.Node().query_filter_first(models.Node.name.in_([Constant.HOST_NAME, ""]))

        node.name = Constant.HOST_NAME
        if not current_record:
            node.priority = random.randint(1, 100) # todo: clarify why 1 -100?
            node.run_overall_cycles = 0
            node.master_overall_cycles = 0
        else:
            node.run_overall_cycles = current_record.run_overall_cycles
            node.master_overall_cycles = current_record.master_overall_cycles
            node.is_master_logging = current_record.is_master_logging
            node.is_master_overall = current_record.is_master_overall
            if not node.run_overall_cycles:
                node.run_overall_cycles = 0
            if not node.master_overall_cycles:
                node.master_overall_cycles = 0
        node.event_sent_datetime= utils.get_base_location_now_date()
        node.updated_on = utils.get_base_location_now_date()
        node.ip = Constant.HOST_MAIN_IP
        if variable.NODE_THIS_IS_MASTER_OVERALL:
            node.master_overall_cycles += 1
        node.run_overall_cycles += 1
        node.os_type = Constant.OS
        node.machine_type = Constant.HOST_MACHINE_TYPE
        node.notify_transport_enabled = True
        progress_status = 'Announce node status before save fields'
        node.save_changed_fields(current_record=current_record, new_record=node, notify_transport_enabled=True,
                                   save_to_graph=True, graph_save_frequency=120)
    except Exception, ex:
        L.l.error('Unable to announce my state, err={}'.format(ex))



def get_progress():
    global progress_status
    return progress_status


def thread_run():
    L.l.debug('Processing node_run')
    global first_run
    global progress_status
    if first_run:
        progress_status='Sleep on first run'
        L.l.info('On first node run I will sleep some seconds to get state updates')
        time.sleep(30)
        first_run = False
        L.l.info('Sleep done on first node run')
    progress_status='Updating master state'
    update_master_state()
    progress_status='Announcing node state'
    announce_node_state()
    progress_status='Completed'
    return 'Processed node_run'
