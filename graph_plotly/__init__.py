from __builtin__ import isinstance

__author__ = 'dcristian'

import logging
import plotly.plotly as py
from plotly import graph_objs
from plotly.exceptions import PlotlyError, PlotlyAccountError
from main.admin import model_helper
from common import constant, utils
from main import db
from main.admin import models

initialised = False
g_series_id_list={} #list of series unique identifier used to determine trace order remote
g_graph_url_list={} #list of remote url for each graph

def download_graph_config(graph_name):
    global g_series_id_list, g_graph_url_list
    graph_rows = models.GraphPlotly.query.filter_by(name=graph_name).all()
    if len(graph_rows)==0:
        g_series_id_list[graph_name] = []
        g_graph_url_list[graph_name] = []

    for graph_row in graph_rows:
        series_split = graph_row.field_list.split(',')
        g_series_id_list[graph_row.name] = series_split
        g_graph_url_list[graph_row.name] = graph_row.url

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

def clean_graph_in_db(graph_name):
    global g_series_id_list, g_graph_url_list
    g_graph_url_list[graph_name] = []
    g_series_id_list[graph_name] = []
    models.GraphPlotly.query.filter_by(name=graph_name).delete()
    db.session.commit()
    logging.info('Deleted graph {} from db'.format(graph_name))

def upload_data(obj):
    #FIXME: Add caching and multiple series on same graph
    try:
        logging.debug('Trying to upload plotly obj {}'.format(obj))
        global g_series_id_list, g_graph_url_list
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
                        #unique name used for graph on upload
                        graph_name=str(table+' '+axis_y)
                        trace = graph_objs.Scatter(x=x, y=y, name=graph_legend)
                        if not g_series_id_list.has_key(graph_name):
                            #get series order list from db to ensure graph consistency, usually done at app start
                            download_graph_config(graph_name)
                            #TODO: check online if graph exists
                            if g_graph_url_list.has_key(graph_name):
                                graph_url = g_graph_url_list[graph_name]
                                if graph_url == []:
                                    # FIXME if graph online but not in db, will not work
                                    #try to get the url by appending blank data
                                    trace = graph_objs.Scatter(x=[], y=[], name='dummy name', text='dummy check')
                                    trace_list = [trace]
                                    data = graph_objs.Data(trace_list)
                                    graph_url = py.plot(data, filename=graph_name, fileopt='append', auto_open=False)
                                try:
                                    figure = py.get_figure(graph_url)
                                    i = 0
                                    for serie in figure['data']:
                                        remote_type=serie['type']
                                        if 'name' in serie:
                                            remote_name=serie['name']
                                        else:
                                            logging.warning('Unable to find name field in graph, skipping')
                                            remote_name = 'N/A'
                                        #remote_x=serie['x']
                                        #remote_y=serie['y']
                                        if 'text' in serie:
                                            remote_id_text=serie['text']
                                        else:
                                            logging.warning('Could not find serie id field in graph {} serie {}'.format(
                                                graph_name, remote_name))
                                            remote_id_text = remote_name

                                        if len(g_series_id_list[graph_name]) > i:
                                            if g_series_id_list[graph_name][i]==remote_id_text:
                                                logging.info('Serie order for {} is ok'.format(remote_name))
                                            else:
                                                logging.warning('Serie order for remote {} not ok, fixing'.format(
                                                    remote_name))
                                                g_series_id_list[graph_name][i] = remote_name
                                        else:
                                            logging.info('Series {} not yet saved in DB, saving'.format(
                                                remote_name))
                                            # fixme add series in db
                                            add_new_serie(graph_name, graph_url, remote_id_text)
                                        i = i + 1
                                    if len(g_series_id_list[graph_name]) > i:
                                        logging.warning('Too many series saved in db for graph {}'.format(graph_name))
                                except PlotlyError:
                                    logging.info('Graph {} does not exist online'.format(graph_name))
                                    clean_graph_in_db(graph_name)
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
                            logging.debug('Extending graph serie {} {}'.format(graph_legend, series_id))
                        else:
                            graph_series_id_list.append(series_id)
                            fileopt = 'append'
                            trace.text = series_id
                            trace_list = [trace]
                            logging.debug('Appending new graph serie {} {}'.format(graph_legend, series_id))
                        data = graph_objs.Data(trace_list)
                        if fileopt=='append':
                            logging.info('Appending graph {}'.format(graph_name))
                        else:
                            logging.info('Extending graph {}'.format(graph_name))
                        url = py.plot(data, filename=graph_name, fileopt=fileopt, auto_open=False)
                        if fileopt=='append':
                            add_new_serie(graph_name, url, series_id)
            else:
                logging.critical('Graphable object missing axis X or ID {}'.format(axis_x_field))
        else:
            logging.critical('Graphable object missing axis X field {}'.format(constant.JSON_PUBLISH_GRAPH_X))
    except PlotlyAccountError, ex1:
        logging.warning('Unable to plot graph, err {}'.format(ex1))
    except Exception, ex:
        logging.warning('General error saving graph, err {}'.format(ex))

def unload():
    global initialised
    initialised = False

def init():
    #use auto setup as described here: https://plot.ly/python/getting-started/ to avoid passwords in code
    #or less secure sign_in code below
    #py.sign_in(model_helper.get_param(constant.P_PLOTLY_USERNAME),model_helper.get_param(constant.P_PLOTLY_APIKEY))
    global initialised
    initialised = True