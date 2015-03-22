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
from common import constant
from main import db
from main.admin import models

initialised = False
stream_ids = None

figure_list = {}
series_name_list={}

def download_graph_config(graph_name):
    graph_rows = models.GraphPlotly.query.filter_by(name=graph_name).all()
    for graph_row in graph_rows:
        series_name_list[graph_row.name] = graph_row.field_list.split(',')

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
            axis_x = obj[constant.JSON_PUBLISH_GRAPH_X]
            graph_id = obj[constant.JSON_PUBLISH_GRAPH_ID]
            if axis_x in obj and graph_id in obj:
                table = obj[constant.JSON_PUBLISH_TABLE]
                series_id = obj[graph_id]
                x_val = obj[axis_x]
                if re.search("....-..-..T..:..:..\.......",  x_val):
                    x_val = x_val.replace('T',' ')
                    x_val = datetime.datetime.strptime(x_val, "%Y-%m-%d %H:%M:%S.%f")
                x = [x_val]
                list_axis_y = obj[constant.JSON_PUBLISH_GRAPH_Y]

                trace_list = []
                for axis_y in list_axis_y:
                    if axis_y in obj:
                        y=[obj[axis_y]]
                        graph_name=str(table+' '+axis_y)
                        if not figure_list.has_key(graph_name):
                            download_graph_config(graph_name)
                        trace = graph_objs.Scatter(x=x, y=y, name=series_id)
                        if not series_name_list.has_key(graph_name):
                           series_name_list[graph_name] = []
                        if series_id in series_name_list:
                            '''series list must be completely filled'''
                            fileopt = 'extend'
                            trace_pos = series_name_list.index(series_id)
                            trace_empty = graph_objs.Scatter(x=[], y=[], name=series_id)
                            for i in range (0, trace_pos):
                                trace_list.append(trace_empty)
                            trace_list.append(trace)
                            for i in range (trace_pos + 1, len(series_name_list) - 1):
                                trace_list.append(trace_empty)
                        else:
                            series_name_list[graph_name].append(series_id)
                            fileopt = 'append'
                            trace_list = [trace]

                        logging.debug('Uploading new graph serie {}'.format(series_id))
                        data = graph_objs.Data(trace_list)
                        url = py.plot(data, filename=graph_name, fileopt=fileopt, auto_open=False)
                        if fileopt=='append':
                            add_new_serie(graph_name, url, series_id)

            else:
                logging.critical('Graphable object missing axis X or ID {}'.format(axis_x))
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