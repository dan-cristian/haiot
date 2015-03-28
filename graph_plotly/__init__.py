from __builtin__ import isinstance

__author__ = 'dcristian'

import logging
import plotly.plotly as py
from plotly import graph_objs
from main.admin import model_helper
from common import constant, utils
from main import db
from main.admin import models

initialised = False
g_series_id_list={} #list of series unique identifier used to determine trace order remote

def download_graph_config(graph_name):
    global g_series_id_list
    graph_rows = models.GraphPlotly.query.filter_by(name=graph_name).all()
    if len(graph_rows)==0:
        g_series_id_list[graph_name] = []

    for graph_row in graph_rows:
        series_split = graph_row.field_list.split(',')
        g_series_id_list[graph_row.name] = series_split

def add_new_serie(graph_name, url, series_id):
    graph_row = models.GraphPlotly.query.filter_by(name=graph_name).first()
    if graph_row:
        if graph_row.field_list:
            graph_row.field_list = graph_row.field_list + ',' + series_id
        else:
            graph_row.field_list = series_id
    else:
        graph_row = models.GraphPlotly(name=graph_name, url=url)
        graph_row.field_list = series_id
        logging.info('Created new graph plotly {} serie {}'.format(graph_name, series_id))
        db.session.add(graph_row)
    db.session.commit()

def upload_data(obj):
    #FIXME: Add caching and multiple series on same graph
    try:
        #logging.info('Trying to upload plotly obj {}'.format(obj))
        global g_series_id_list

        if constant.JSON_PUBLISH_GRAPH_X in obj:
            axis_x_field = obj[constant.JSON_PUBLISH_GRAPH_X]
            graph_id_field = obj[constant.JSON_PUBLISH_GRAPH_ID]
            graph_legend_field = obj[constant.JSON_PUBLISH_GRAPH_LEGEND]
            list_axis_y = obj[constant.JSON_PUBLISH_GRAPH_Y]
            logging.info('Trying to upload plotly obj {}'.format(list_axis_y))
            if axis_x_field in obj and graph_id_field in obj:
                table = obj[constant.JSON_PUBLISH_TABLE]
                series_id = obj[graph_id_field]#unique record/trace identifier
                x_val = obj[axis_x_field]
                graph_legend = obj[graph_legend_field]#unique key for legend
                x_val = utils.parse_to_date(x_val)
                x = [x_val]
                for axis_y in list_axis_y:
                    if axis_y in obj:
                        trace_list = []
                        y=[obj[axis_y]]
                        graph_name=str(table+' '+axis_y)
                        trace = graph_objs.Scatter(x=x, y=y, name=graph_legend)
                        if not g_series_id_list.has_key(graph_name):
                            download_graph_config(graph_name) #get series order list from db to ensure graph consistency
                        graph_series_id_list = g_series_id_list[graph_name]
                        if series_id in graph_series_id_list:
                            '''series list must be completely filled'''
                            fileopt = 'extend'
                            trace_pos = graph_series_id_list.index(series_id)
                            trace_empty = graph_objs.Scatter(x=[], y=[])
                            for i in range(len(graph_series_id_list)):
                                if i is trace_pos:
                                    trace_list.append(trace)
                                else:
                                    trace_list.append(trace_empty)
                        else:
                            graph_series_id_list.append(series_id)
                            fileopt = 'append'
                            trace_list = [trace]
                            logging.debug('Appending new graph serie {} {}'.format(graph_legend, series_id))
                        data = graph_objs.Data(trace_list)
                        py.grid_ops
                        url = py.plot(data, filename=graph_name, fileopt=fileopt, auto_open=False)
                        if fileopt=='append':
                            add_new_serie(graph_name, url, series_id)
                            logging.info('Appended graph on url {}'.format(url))
                        else:
                            logging.info('Extended graph on url {}'.format(url))
            else:
                logging.critical('Graphable object missing axis X or ID {}'.format(axis_x_field))
        else:
            logging.critical('Graphable object missing axis X field {}'.format(constant.JSON_PUBLISH_GRAPH_X))
    except Exception, ex:
        logging.warning('Unable to upload graph, err {}'.format(ex))

def unload():
    global initialised
    initialised = False

def init():
    py.sign_in(model_helper.get_param(constant.P_PLOTLY_USERNAME),model_helper.get_param(constant.P_PLOTLY_APIKEY))
    global initialised
    initialised = True