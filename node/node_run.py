__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import logging
import time
import datetime
from common import constant, variable, utils
from mqtt_io import sender
from main.admin import models, model_helper
from main import db

#save node state
def node_update(obj={}):
    node_host_name = utils.get_object_field_name(obj, models.Node.name)
    logging.debug('Received node state update from '.format(node_host_name))
    #avoid node to update itself in infinite recursion
    if node_host_name != constant.HOST_NAME:
        node = models.Node.query.filter_by(name=node_host_name).first()
        if node is None:
            node = models.Node()
            node.name = node_host_name
            db.session.add(node)
        node.is_master_graph = utils.get_object_field_name(obj, models.Node.is_master_graph)
        node.is_master_db_archive = utils.get_object_field_name(obj, models.Node.is_master_db_archive)
        node.is_master_overall = utils.get_object_field_name(obj, models.Node.is_master_overall)
        node.is_master_rule = utils.get_object_field_name(obj, models.Node.is_master_rule)
        db.session.commit()
    else:
        variable.NODE_THIS_IS_MASTER_OVERALL = utils.get_object_field_name(obj, models.Node.is_master_overall)
        logging.info('Skipping node DB save, this node is master = {}'.format(variable.NODE_THIS_IS_MASTER_OVERALL))


#TODO: implement
def update_master_state():
    try:
        alive_date_time = datetime.datetime.now() - datetime.timedelta(minutes=1)
        node_list = models.Node.query.order_by(models.Node.id).all()
        for node in node_list:
            if node.updated_on >= alive_date_time:
                if node.is_master_overall:
                    logging.debug('Node {} is already master, all good'.format(node.name))
                else:
                    logging.info('Node {} is now becoming a master'.format(node.name))
                    node.is_master_overall = True
                    db.session.commit()
                    break
    except Exception, ex:
        logging.warning('Error try_become_master, err {}'.format(ex))

def announce_node_state():
    logging.debug('I tell everyone my node state')
    node = models.Node.query.filter_by(name=constant.HOST_NAME).first()
    node.updated_on = datetime.datetime.now()
    db.session.commit()

def thread_run():
    logging.info('Processing node_run')
    announce_node_state()
    update_master_state()
    return 'Processed node_run'