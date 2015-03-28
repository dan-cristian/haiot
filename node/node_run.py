__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import logging
import time
import datetime
from common import constant, variable, utils
from mqtt_io import sender
from main.admin import models, model_helper
from main import db

#save node state to db, except for current node. no decisions taken on node election
def node_update(obj={}):
    node_host_name = utils.get_object_field_value(obj, models.Node.name)
    logging.debug('Received node state update from {}'.format(node_host_name))
    #avoid node to update itself in infinite recursion
    if node_host_name != constant.HOST_NAME:
        node = models.Node.query.filter_by(name=node_host_name).first()
        if node is None:
            node = models.Node()
            db.session.add(node)
        node.name = node_host_name
        node.is_master_graph = utils.get_object_field_value(obj, models.Node.is_master_graph)
        node.is_master_db_archive = utils.get_object_field_value(obj, models.Node.is_master_db_archive)
        node.is_master_overall = utils.get_object_field_value(obj, models.Node.is_master_overall)
        node.is_master_rule = utils.get_object_field_value(obj, models.Node.is_master_rule)
        node.priority = utils.get_object_field_value(obj, models.Node.priority)
        node.ip = utils.get_object_field_value(obj, models.Node.ip)
        node.updated_on = datetime.datetime.now()
        db.session.commit()
    else:
        logging.debug('Skipping node DB save, this node is master = {}'.format(
            variable.NODE_THIS_IS_MASTER_OVERALL))


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
                    logging.debug('Node {} is already master, all good'.format(node.name))
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
                    logging.info('Node {} will lose master status'.format(node.name))
                    if node.name == constant.HOST_NAME:
                        node.is_master_overall = False
                        node.notify_enabled_ = True
                        db.session.commit()
            if node.name == constant.HOST_NAME:
                if variable.NODE_THIS_IS_MASTER_OVERALL != node.is_master_overall:
                    variable.NODE_THIS_IS_MASTER_OVERALL = node.is_master_overall
                    logging.info('Change in node mastership, local node is master={}'.format(
                        variable.NODE_THIS_IS_MASTER_OVERALL))

    except Exception, ex:
        logging.warning('Error try_become_master, err {}'.format(ex))

def announce_node_state():
    logging.debug('I tell everyone my node state')
    node = models.Node.query.filter_by(name=constant.HOST_NAME).first()
    node.updated_on = datetime.datetime.now()
    node.notify_enabled_ = True
    db.session.commit()

def thread_run():
    logging.info('Processing node_run')
    announce_node_state()
    update_master_state()
    return 'Processed node_run'