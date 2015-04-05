__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import logging
import time
import datetime
import random
from common import constant, variable, utils
from mqtt_io import sender
from main.admin import models, model_helper
from main import db

first_run = True
since_when_i_should_be_master = datetime.datetime.max
node_state_uuid = None

#save node state to db, except for current node. no decisions taken on node election
def node_update(obj={}):
    try:
        node_host_name = utils.get_object_field_value(obj, 'name')
        logging.debug('Received node state update from {}'.format(node_host_name))
        #avoid node to update itself in infinite recursion
        if node_host_name != constant.HOST_NAME:
            node = models.Node.query.filter_by(name=node_host_name).first()
            if node is None:
                node = models.Node()
                db.session.add(node)
            node.name = node_host_name
            node.is_master_graph = utils.get_object_field_value(obj, 'is_master_graph')
            node.is_master_db_archive = utils.get_object_field_value(obj, 'is_master_db_archive')
            node.is_master_overall = utils.get_object_field_value(obj, 'is_master_overall')
            node.is_master_rule = utils.get_object_field_value(obj, 'is_master_rule')
            node.priority = utils.get_object_field_value(obj, 'priority')
            node.ip = utils.get_object_field_value(obj, 'ip')
            node.execute_command = utils.get_object_field_value(obj, 'execute_command')
            node.updated_on = datetime.datetime.now()
            db.session.commit()
        else:
            logging.debug('Skipping node DB save, this node is master = {}'.format(
                variable.NODE_THIS_IS_MASTER_OVERALL))
            sent_date = utils.get_object_field_value(obj, 'event_sent_datetime_')
            if not sent_date is None:
                event_sent_date_time = utils.parse_to_date(sent_date)
                seconds_elapsed = (datetime.datetime.now()-event_sent_date_time).total_seconds()
                if seconds_elapsed>10:
                    logging.warning('Very slow mqtt processing, message delay is {} seconds'.format(seconds_elapsed))
    except Exception, ex:
        logging.warning('Error on node update, err {}'.format(ex))

def check_if_no_masters():
    node_masters = models.Node.query.filter_by(is_master_overall=True).all()
    return len(node_masters)==0

#elect and set master status in db for current node only. master is elected by node_id priority, if alive
def update_master_state():
    master_selected=False
    try:
        alive_date_time = datetime.datetime.now() - datetime.timedelta(minutes=1)
        node_list = models.Node.query.order_by(models.Node.priority).all()
        for node in node_list:
            #if recently alive, in order of id prio
            if node.updated_on >= alive_date_time and (not master_selected):
                if node.is_master_overall:
                    logging.debug('Node {} is already master, all good we have a master'.format(node.name))
                    master_selected = True
                else:
                    logging.info('Node {} will become a master'.format(node.name))
                    if node.name == constant.HOST_NAME:
                        node.is_master_overall = True
                        node.notify_enabled_ = True
                        db.session.commit()
                    master_selected = True
            else:
                if master_selected and node.is_master_overall:
                    logging.info('Node {} should lose master status, if alive'.format(node.name))
                    if node.name == constant.HOST_NAME:
                        node.is_master_overall = False
                        node.notify_enabled_ = True
                        db.session.commit()
            #applying node master status locally, if changed in db
            if node.name == constant.HOST_NAME:
                if variable.NODE_THIS_IS_MASTER_OVERALL != node.is_master_overall:
                    if not node.is_master_overall:
                        #disabling local mastership immediately
                        variable.NODE_THIS_IS_MASTER_OVERALL = node.is_master_overall
                        logging.info('Immediate change in node mastership, local node is master={}'.format(
                            variable.NODE_THIS_IS_MASTER_OVERALL))
                    else:
                        global since_when_i_should_be_master
                        #check seconds lapsed since cluster agreed I must be or lose master
                        seconds_elapsed = (datetime.datetime.now() - since_when_i_should_be_master).total_seconds()
                        if check_if_no_masters() or seconds_elapsed > 10:
                            variable.NODE_THIS_IS_MASTER_OVERALL = node.is_master_overall
                            logging.info('Change in node mastership, local node is master={}'.format(
                                variable.NODE_THIS_IS_MASTER_OVERALL))
                            since_when_i_should_be_master = datetime.datetime.max
                        else:
                            logging.info('Waiting to set master status, sec. lapsed={}'.format(seconds_elapsed))
                        if not variable.NODE_THIS_IS_MASTER_OVERALL:
                            #record date when cluster agreed I must be master
                            if since_when_i_should_be_master == datetime.datetime.max:
                                since_when_i_should_be_master = datetime.datetime.now()
    except Exception, ex:
        logging.warning('Error try_become_master, err {}'.format(ex))

def announce_node_state():
    logging.debug('I tell everyone my node state')
    node = models.Node.query.filter_by(name=constant.HOST_NAME).first()
    if node is None:
        node = models.Node()
        node.name = constant.HOST_NAME
        node.priority = random.randint(1, 100)
        logging.warning('Detected node host name change, new name={}'.format(constant.HOST_NAME))
        db.session.add(node)
    node.event_sent_datetime_= datetime.datetime.now()
    node.updated_on = datetime.datetime.now()
    node.ip = constant.HOST_MAIN_IP
    node.notify_enabled_ = True
    db.session.commit()

progress_status = None
def get_progress():
    global progress_status
    return progress_status

def thread_run():
    logging.debug('Processing node_run')
    global first_run
    global progress_status
    if first_run:
        progress_status='Sleep on first run'
        logging.info('On first node run I will sleep some seconds to get state updates')
        time.sleep(10)
        first_run = False
        logging.info('Sleep done on first node run')
    progress_status='Updating master state'
    update_master_state()
    progress_status='Announcing node state'
    announce_node_state()
    progress_status='Completed'
    return 'Processed node_run'