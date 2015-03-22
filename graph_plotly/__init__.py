from __builtin__ import isinstance

__author__ = 'dcristian'

import logging
import datetime
import re
import plotly.plotly as py
from plotly import graph_objs
#from plotly.graph_objs import *
import plotly.tools as tls
from main.admin import model_helper
from common import constant, utils
from main import db
from main.admin import models

initialised = False
stream_ids = None

figure_list = {}
series_name_list={}

def download_graph_config(graph_name):
    global series_name_list
    graph_rows = models.GraphPlotly.query.filter_by(name=graph_name).all()
    for graph_row in graph_rows:
        series_split = graph_row.field_list.split(',')
        series_name_list[graph_row.name] = series_split

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
        if constant.JSON_PUBLISH_GRAPH_X in obj:
            axis_x_field = obj[constant.JSON_PUBLISH_GRAPH_X]
            graph_id_field = obj[constant.JSON_PUBLISH_GRAPH_ID]
            graph_legend_field = obj[constant.JSON_PUBLISH_GRAPH_LEGEND]

            if axis_x_field in obj and graph_id_field in obj:
                table = obj[constant.JSON_PUBLISH_TABLE]
                #series_id = obj[graph_id_field]#unique record identifier, not used yet
                x_val = obj[axis_x_field]
                graph_legend = obj[graph_legend_field]#unique key used to store series remote
                x_val = utils.parse_to_date(x_val)
                x = [x_val]
                list_axis_y = obj[constant.JSON_PUBLISH_GRAPH_Y]

                trace_list = []
                for axis_y in list_axis_y:
                    if axis_y in obj:
                        y=[obj[axis_y]]
                        graph_name=str(table+' '+axis_y)
                        #get series order list from db to ensure graph consistency
                        if not figure_list.has_key(graph_name):
                            download_graph_config(graph_name)
                        trace = graph_objs.Scatter(x=x, y=y, name=graph_legend)
                        if not series_name_list.has_key(graph_name):
                           series_name_list[graph_name] = []
                        if graph_legend in series_name_list[graph_name]:
                            '''series list must be completely filled'''
                            fileopt = 'extend'
                            trace_pos = series_name_list[graph_name].index(graph_legend)
                            trace_empty = graph_objs.Scatter(x=[], y=[])
                            for i in range (0, trace_pos):
                                trace_list.append(trace_empty)
                            trace_list.append(trace)
                            for i in range (trace_pos + 1, len(series_name_list[graph_name]) - 1):
                                trace_list.append(trace_empty)
                        else:
                            series_name_list[graph_name].append(graph_legend)
                            fileopt = 'append'
                            trace_list = [trace]
                            logging.debug('Appending new graph serie {}'.format(graph_legend))
                        data = graph_objs.Data(trace_list)
                        url = py.plot(data, filename=graph_name, fileopt=fileopt, auto_open=False)
                        if fileopt=='append':
                            add_new_serie(graph_name, url, graph_legend)

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
    tls.set_credentials_file(stream_ids=[
        "fmjbljkeot",
        "1piqv8ti6k",
        "24w1i6s6bs",
        "15ytl1hrhc"
    ])
    global stream_ids
    stream_ids = tls.get_credentials_file()['stream_ids']