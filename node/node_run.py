__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import logging
import time
from common import constant, variable, utils
import mqtt_io
from main.admin import models, model_helper
from main import db

def init():
    node = None
    try:
        node = models.Node.query.filter_by(name=constant.HOST_NAME).first()
        if node is None:
            node = models.Node()
            node.name = constant.HOST_NAME
            record_is_new = True
        else:
            record_is_new = False
            variable.NODE_THIS_IS_MASTER_DB_ARCHIVE = node.is_master_db_archive
            variable.NODE_THIS_IS_MASTER_RULE = node.is_master_rule
            variable.NODE_THIS_IS_MASTER_GRAPH = node.is_master_graph

        key_compare = node.comparator_unique_graph_record()

        node.name=constant.HOST_NAME
        db.session.autoflush=False
        if key_compare != node.comparator_unique_graph_record():
            if record_is_new:
                db.session.add(node)
            else:
                logging.info('Node {} change, old={} new={}'.format(node.name, key_compare,
                                                                      node.comparator_unique_graph_record()))
            db.session.commit()
        else:
            logging.debug('Ignoring node read {}, no value change'.format(key_compare))
            db.session.rollback()
    except Exception, ex:
        logging.warning('Error saving Node to DB, err {}'.format(ex))
    return node

'''Establishing which node becomes master'''
def node_update(obj={}):
    node_host_name = obj[str(models.Node.name).split('.')[1]]
    is_master_graph_request = utils.get_object_field_name(obj, models.Node.is_master_graph)
    is_master_db_archive_request = utils.get_object_field_name(obj, models.Node.is_master_db_archive)
    if node_host_name == constant.HOST_NAME:
        #wait x seconds until other hosts complain about mastership request
        time.sleep(10)
        #TODO: chech if request was canceled
        #...

        if is_master_graph_request != variable.NODE_THIS_IS_MASTER_GRAPH:
            variable.NODE_THIS_IS_MASTER_GRAPH = is_master_graph_request
        if is_master_db_archive_request != variable.NODE_THIS_IS_MASTER_DB_ARCHIVE:
            variable.NODE_THIS_IS_MASTER_DB_ARCHIVE = is_master_db_archive_request
    else:
        #opportunity to complain about a request
        if variable.NODE_THIS_IS_MASTER_GRAPH and is_master_graph_request:
            #TODO: conflict, cancel request
            #...
            pass

def thread_run():
    logging.info('Processing node_run')
    if not variable.NODE_THIS_IS_MASTER_GRAPH:
        #trying to become a master graph
        node = models.Node()
        node.name = constant.HOST_NAME
        node.is_master_graph = True
        mqtt_io.sender.send_message(model_helper.model_row_to_json(node, 'update'))

    return 'Processed node_run'