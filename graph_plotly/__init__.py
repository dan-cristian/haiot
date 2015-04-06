from __builtin__ import isinstance

__author__ = 'dcristian'

import logging
import datetime
import plotly.plotly as py
from plotly import graph_objs
from plotly.exceptions import PlotlyError, PlotlyAccountError, PlotlyListEntryError
from common import constant, utils
from main import db
from main.admin import models


initialised = False
#list of series unique identifier used to determine trace order remote, key is graph name
#each trace id list starts with a standard reference element used to get graph url, not ideal!
#e.g.{'Sensor temperature':['ref','ADDRESS1', 'ADDRESS2', ...], 'System cpu usage':['ref','server','beaglebone',...]}
g_trace_id_list_per_graph={}
#list of remote plotly url path for each graph, key is graph name
#e.g. {'Sensor temperature':'http://plotly.../567','':''}
g_graph_url_list={}
g_reference_trace_id='reference-id'

#add graph url and trace id list in memory to keep order when extending graphs
def add_new_serie(graph_unique_name, url, trace_unique_id):
    global g_trace_id_list_per_graph, g_graph_url_list
    if not graph_unique_name in g_trace_id_list_per_graph:
        g_trace_id_list_per_graph[graph_unique_name]=[]
    g_trace_id_list_per_graph[graph_unique_name].append(trace_unique_id)
    #if not graph_unique_name in g_graph_url_list:
    g_graph_url_list[graph_unique_name]=url

def get_layout(title='', ):
    title = title.replace('_', ' ')
    layout = graph_objs.Layout(
        title=title,
        showlegend=True,
        autosize=True,
        legend = graph_objs.Legend(
            xanchor='left',
            yanchor='top'
        )
    )
    return layout

def populate_trace_for_extend(x=[], y=[], graph_legend_item_name='', trace_unique_id='', trace_unique_id_pattern=[]):
    #series list must be completely filled in using graph create order
    #'text' param if added generates error
    trace_extend = graph_objs.Scatter(x=x, y=y, name=graph_legend_item_name)
    trace_pos = trace_unique_id_pattern.index(trace_unique_id)
    trace_empty = graph_objs.Scatter(x=[], y=[])
    trace_list=[]
    for i in range(len(trace_unique_id_pattern)):
        if i == trace_pos:
            trace_list.append(trace_extend)
        else:
            trace_list.append(trace_empty)
    logging.debug('Extending graph serie {} {}'.format(graph_legend_item_name, trace_unique_id))
    return trace_list

def populate_trace_for_append(x=[], y=[], graph_legend_item_name='', trace_unique_id='', show_legend=True):
    #'text' param should only be added at trace creation
    trace_append = graph_objs.Scatter(x=x, y=y, name=graph_legend_item_name, text=trace_unique_id,
                                      showlegend=show_legend)
    trace_list = [trace_append]
    logging.debug('Appending new graph serie {} {}'.format(graph_legend_item_name, trace_unique_id))
    return trace_list

def clean_graph_memory(graph_unique_name=''):
    global g_reference_trace_id, g_trace_id_list_per_graph, g_graph_url_list
    #reseting known series and graphs to download again clean
    if graph_unique_name in g_trace_id_list_per_graph:
        g_trace_id_list_per_graph[graph_unique_name] = []
    if graph_unique_name in g_graph_url_list:
        g_graph_url_list.pop(graph_unique_name)

def get_reference_trace_for_append(graph_unique_name=''):
    global g_reference_trace_id
    return graph_objs.Scatter(x=[datetime.datetime.now()], y=[0], name=graph_unique_name, text=g_reference_trace_id,
                              mode='none', showlegend=False)

def download_trace_id_list(graph_unique_name=''):
    try:
        result=py.file_ops.mkdirs(get_folder_name())
        logging.info('Created archiving folder {} result {}'.format(get_folder_name(), result))
    except Exception, ex:
        logging.warning('Unable to create archive folder {} err {}'.format(get_folder_name(), ex))

    logging.info('Downloading existing online traces in memory, graph {}'.format(graph_unique_name))
    global g_reference_trace_id
    #reseting known series and graphs to download again clean
    clean_graph_memory(graph_unique_name)
    #extending graph with a reference trace to force getting remote url, which is unknown
    trace_list = []
    graph_url = None
    trace_ref_append = get_reference_trace_for_append(graph_unique_name)
    trace_ref_extend = graph_objs.Scatter(x=[datetime.datetime.now()],y=[0],name=graph_unique_name,mode='none',
                                          showlegend=False)
    trace_empty = graph_objs.Scatter(x=[], y=[])
    #first time we try an append, assuming trace does not exist
    trace_list.append(trace_ref_append)
    #trying several times to guess number of graph traces so I can get the graph url
    for i in range(1,30):
        try:
            fig = graph_objs.Figure(data=graph_objs.Data(trace_list), layout=get_layout(graph_unique_name))
            graph_url = py.plot(fig,filename=graph_unique_name,fileopt='extend',auto_open=False)
            break
        except PlotlyError, ex:
            #usually first try will give an error
            if i>1:
                logging.info('Error extending graph {} in pass {}, err={}'.format(graph_unique_name, i, ex))
            #first time failed, so second time we try an extend, but trace definition will change
            trace_list[0]=trace_ref_extend
            if i>1:
                trace_list.append(trace_empty)
    if not graph_url is None:
        try:
            figure = py.get_figure(graph_url)
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
                    logging.warning('Could not find serie {} field in graph {}'.format(remote_name,graph_unique_name))
                    remote_id_text = remote_name
                add_new_serie(graph_unique_name=graph_unique_name, url=graph_url, trace_unique_id=remote_id_text)
        except PlotlyError, ex:
            logging.warning('Unable to get figure {} err={}'.format(graph_url, ex))
    else:
        logging.critical('Unable to get or setup remote graph {}'.format(graph_unique_name))

def get_folder_name():
    year = datetime.datetime.now().year
    month = datetime.datetime.now().month
    #week =  datetime.datetime.now().weekday()
    return str(year) + '-' + ('0'+str(month))[-2:]

def get_graph_full_name_path(graph_unique_name=''):
    return  get_folder_name() + '/' + graph_unique_name

#called first time when the app is started to force url retrieval
#as a side effect this creates a hidden trace
def upload_reference_graph(graph_unique_name=''):
    trace_list = get_reference_trace_for_append(graph_unique_name)
    try:
        #update reference trace
        fig = graph_objs.Figure(data=graph_objs.Data([trace_list]), layout=get_layout(graph_unique_name))
        py.plot(fig, filename=graph_unique_name, fileopt='overwrite', auto_open=False)
        #clean graph from memory to force graph traces reload in the right order
        clean_graph_memory(graph_unique_name)
        logging.info('New reference graph {} uploaded ok'.format(graph_unique_name))
    except PlotlyListEntryError, ex:
        logging.warning('Error uploading new reference graph {} err {}'.format(graph_unique_name, ex))
    except PlotlyAccountError, ex:
        logging.warning('Unable to upload new reference graph {} err {}'.format(graph_unique_name, ex))

#check if graph exists in memory. Used this function rather than checking graph dict variable directly
#as this function enables archiving in different folders
def graph_url_exists_in_memory(graph_unique_name=''):
    global g_graph_url_list
    return graph_unique_name in g_graph_url_list

def get_graph_url_from_memory(graph_unique_name=''):
    global g_graph_url_list
    if graph_url_exists_in_memory(graph_unique_name):
        return g_graph_url_list[graph_unique_name]
    else:
        return None

def upload_data(obj):
    try:
        logging.debug('Trying to upload plotly obj {}'.format(obj))
        global g_trace_id_list_per_graph
        if constant.JSON_PUBLISH_GRAPH_X in obj:
            axis_x_field = obj[constant.JSON_PUBLISH_GRAPH_X]
            graph_id_field = obj[constant.JSON_PUBLISH_GRAPH_ID]
            graph_legend_field = obj[constant.JSON_PUBLISH_GRAPH_LEGEND]
            list_axis_y = obj[constant.JSON_PUBLISH_GRAPH_Y]
            logging.debug('Trying to upload y axis {}'.format(list_axis_y))
            if axis_x_field in obj and graph_id_field in obj:
                table = obj[constant.JSON_PUBLISH_TABLE]
                trace_unique_id = obj[graph_id_field] #unique record/trace identifier
                x_val = obj[axis_x_field]
                graph_legend_item_name = obj[graph_legend_field] #unique key for legend
                x_val = utils.parse_to_date(x_val)
                x = [x_val]
                for axis_y in list_axis_y:
                    if axis_y in obj:
                        trace_list = []
                        y=[obj[axis_y]]
                        #unique name used for graph on upload
                        graph_base_name = str(table+' '+axis_y)
                        #full name and path to enable archiving
                        graph_unique_name = get_graph_full_name_path(graph_base_name)
                        if not graph_url_exists_in_memory(graph_unique_name):
                            #download series order list to ensure graph consistency, usually done at app start
                            #or when trace is created
                            download_trace_id_list(graph_unique_name=graph_unique_name)
                        if graph_unique_name in g_trace_id_list_per_graph:
                            trace_unique_id_pattern = g_trace_id_list_per_graph[graph_unique_name]
                        else:
                            logging.warning('Unable to get a reference pattern, graph {}'.format(graph_unique_name))
                        known_graph_url = get_graph_url_from_memory(graph_unique_name)
                        if trace_unique_id in trace_unique_id_pattern:
                            trace_list = populate_trace_for_extend(x=x, y=y,
                                    graph_legend_item_name=graph_legend_item_name, trace_unique_id=trace_unique_id,
                                    trace_unique_id_pattern=trace_unique_id_pattern)
                            logging.debug('Extending graph {}'.format(graph_unique_name))
                            fileopt = 'extend'
                        else:
                            trace_list = populate_trace_for_append(x=x, y=y,
                                        graph_legend_item_name=graph_legend_item_name,trace_unique_id=trace_unique_id)
                            logging.debug('Appending graph {}'.format(graph_unique_name))
                            fileopt = 'append'
                        data = graph_objs.Data(trace_list)
                        try:
                            if known_graph_url is None:
                                logging.warning('Graph {} is setting up, dropping data'.format(graph_unique_name))
                            else:
                                fig = graph_objs.Figure(data=data, layout=get_layout(graph_unique_name))
                                url = py.plot(fig, filename=graph_unique_name, fileopt=fileopt, auto_open=False)
                                if url != known_graph_url:
                                    logging.warning('Original graph {} removed from plotly'.format(graph_unique_name))
                                    upload_reference_graph(graph_unique_name)
                                if fileopt=='append' or fileopt=='new':
                                    add_new_serie(graph_unique_name, url, trace_unique_id)
                        except PlotlyAccountError, ex:
                            logging.warning('Unable to plot graph, err {}'.format(ex))
            else:
                logging.critical('Graphable object missing axis X or ID {} obj {}'.format(axis_x_field, obj))
        else:
            logging.critical('Graphable object missing axis X field {}'.format(constant.JSON_PUBLISH_GRAPH_X))
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