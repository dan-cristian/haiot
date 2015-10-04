__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

import datetime
import threading

from plotly import graph_objs
import plotly.plotly as py
from plotly.exceptions import PlotlyError, PlotlyAccountError, PlotlyListEntryError, PlotlyRequestError

from common import utils
from main.logger_helper import Log


#list of series unique identifier used to determine trace order remote, key is graph name
#each trace id list starts with a standard reference element used to get graph url, not ideal!
#e.g.{'Sensor temperature':['ref','ADDRESS1', 'ADDRESS2', ...], 'System cpu usage':['ref','server','beaglebone',...]}
g_trace_id_list_per_graph={}
#list of remote plotly url path for each graph, key is graph name
#e.g. {'Sensor temperature':'http://plotly.../567','':''}
g_graph_url_list={}
g_reference_trace_id='reference-id'
#list with cached graph data for future upload
graph_list = {}


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


def populate_trace_for_extend(x=[], y=[], graph_legend_item_name='', trace_unique_id='', trace_unique_id_pattern=[],
                              shape_type=''):
    #series list must be completely filled in using graph create order
    #'text' param if added generates error
    trace_pos = trace_unique_id_pattern.index(trace_unique_id)
    trace_list=[]
    for i in range(len(trace_unique_id_pattern)):
        if i == trace_pos:
            trace_extend = graph_objs.Scatter(x=x, y=y, name=graph_legend_item_name,
                                              line = graph_objs.Line(shape=shape_type))
            trace_list.append(trace_extend)
        else:
            trace_empty = graph_objs.Scatter(x=[], y=[], line = graph_objs.Line(shape=shape_type))
            trace_list.append(trace_empty)
    Log.logger.debug('Extending graph serie {} {}'.format(graph_legend_item_name, trace_unique_id))
    return trace_list

def populate_trace_for_append(x=[], y=[], graph_legend_item_name='', trace_unique_id='', show_legend=True,
                              shape_type=''):
    #'text' param should only be added at trace creation
    trace_append = graph_objs.Scatter(x=x, y=y, name=graph_legend_item_name, text=trace_unique_id,
                                      showlegend=show_legend, line = graph_objs.Line(shape=shape_type))
    trace_list = [trace_append]
    Log.logger.debug('Appending new graph serie {} {}'.format(graph_legend_item_name, trace_unique_id))
    return trace_list

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

def clean_graph_memory(graph_unique_name=''):
    global g_reference_trace_id, g_trace_id_list_per_graph, g_graph_url_list
    #reseting known series and graphs to download again clean
    if graph_unique_name in g_trace_id_list_per_graph:
        g_trace_id_list_per_graph[graph_unique_name] = []
    if graph_unique_name in g_graph_url_list:
        g_graph_url_list.pop(graph_unique_name)

#called first time when the app is started to force url retrieval
#as a side effect this creates a hidden dummy trace
def upload_reference_graph(graph_unique_name=''):
    trace_list = get_reference_trace_for_append(graph_unique_name)
    try:
        #update reference trace
        fig = graph_objs.Figure(data=graph_objs.Data([trace_list]), layout=get_layout(graph_unique_name))
        py.plot(fig, filename=graph_unique_name, fileopt='overwrite', auto_open=False)
        #clean graph from memory to force graph traces reload in the right order
        clean_graph_memory(graph_unique_name)
        Log.logger.info('New reference graph {} uploaded ok'.format(graph_unique_name))
    except PlotlyListEntryError, ex:
        Log.logger.warning('Error uploading new reference graph {} err {}'.format(graph_unique_name, ex))
    except PlotlyAccountError, ex:
        Log.logger.warning('Unable to upload new reference graph {} err {}'.format(graph_unique_name, ex))



#add graph url and trace id list in memory to keep order when extending graphs
def add_new_serie(graph_unique_name, url, trace_unique_id):
    global g_trace_id_list_per_graph, g_graph_url_list
    if not graph_unique_name in g_trace_id_list_per_graph:
        g_trace_id_list_per_graph[graph_unique_name]=[]
    g_trace_id_list_per_graph[graph_unique_name].append(trace_unique_id)
    #if not graph_unique_name in g_graph_url_list:
    g_graph_url_list[graph_unique_name]=url


def get_folder_name():
    year = utils.get_base_location_now_date().year
    month = utils.get_base_location_now_date().month
    #week =  utils.get_base_location_now_date().weekday()
    return str(year) + '-' + ('0'+str(month))[-2:]

def get_graph_full_name_path(graph_unique_name=''):
    return  get_folder_name() + '/' + graph_unique_name

def get_reference_trace_for_append(graph_unique_name='', shape_type=''):
    global g_reference_trace_id
    return graph_objs.Scatter(x=[utils.get_base_location_now_date()], y=[0], name=graph_unique_name,
                              text=g_reference_trace_id,
                              mode='none', showlegend=False, line = graph_objs.Line(shape=shape_type))

def download_trace_id_list(graph_unique_name='', shape_type=''):
    Log.logger.info('Downloading online traces in memory, graph {} shape {}'.format(graph_unique_name, shape_type))
    start_date = utils.get_base_location_now_date()
    result = -1
    try:
        result=py.file_ops.mkdirs(get_folder_name())
        Log.logger.debug('Created archiving folder {} result {}'.format(get_folder_name(), result))
    except PlotlyRequestError, ex:
        if hasattr(ex, 'HTTPError'):
            msg = str(ex.HTTPError) + ex.HTTPError.response.content
        else:
            msg = str(ex)
        Log.logger.info('Ignoring error on create archive folder {} err={}'.format(get_folder_name(), msg))
    except Exception, ex:
        Log.logger.warning('Unable to create archive folder {} err={} res={}'.format(get_folder_name(), ex, result))

    global g_reference_trace_id
    #reseting known series and graphs to download again clean
    clean_graph_memory(graph_unique_name)
    #extending graph with a reference trace to force getting remote url, which is unknown
    trace_list = []
    graph_url = None
    trace_ref_append = get_reference_trace_for_append(graph_unique_name=graph_unique_name, shape_type=shape_type)
    trace_ref_extend = graph_objs.Scatter(x=[utils.get_base_location_now_date()],y=[0],name=graph_unique_name,mode='none',
                                          showlegend=False, line = graph_objs.Line(shape=shape_type))
    trace_empty = graph_objs.Scatter(x=[], y=[], line = graph_objs.Line(shape=shape_type))
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
                Log.logger.info('Error extending graph {} in pass {}, err={}'.format(graph_unique_name, i, ex))
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
                    Log.logger.warning('Unable to find name field in graph, skipping')
                    remote_name = 'N/A'
                #remote_x=serie['x']
                #remote_y=serie['y']
                if 'text' in serie:
                    remote_id_text=serie['text']
                else:
                    #FIXME: plotly api changed, fix this!
                    #Log.logger.warning('Could not find serie [{}] field in graph [{}]'.format(remote_name,graph_unique_name))
                    remote_id_text = remote_name
                add_new_serie(graph_unique_name=graph_unique_name, url=graph_url, trace_unique_id=remote_id_text)
        except PlotlyError, ex:
            Log.logger.warning('Unable to get figure {} err={}'.format(graph_url, ex))
    else:
        logger.critical('Unable to get or setup remote graph {}'.format(graph_unique_name))
    elapsed = (utils.get_base_location_now_date()-start_date).seconds
    Log.logger.info('Download {} completed in {} seconds'.format(graph_unique_name, elapsed))

def add_graph_data(data, graph_unique_name, trace_unique_id, file_opt):
    if graph_list.has_key(graph_unique_name):
        graph = graph_list[graph_unique_name]
    else:
        graph = PlotlyGraph()
        graph.trace_unique_id = trace_unique_id
        graph.graph_unique_name = graph_unique_name
        graph.file_opt = file_opt
        graph_list[graph_unique_name] = graph
    graph.add_data(data)

#iterate and upload graphs with valid data not saved older than 5 minutes
def __upload_cached_plotly_data():
    for graph in graph_list.values():
        if (utils.get_base_location_now_date() - graph.last_save).total_seconds() > 300:
            graph.upload_data()

def thread_run():
    Log.logger.debug('Processing graph_plotly_run')
    __upload_cached_plotly_data()
    return 'Processed graph_plotly_run'

class PlotlyGraph:
    data = []
    graph_unique_name = None
    trace_unique_id = None
    file_opt = None
    last_save = datetime.datetime.min
    lock = threading.Lock()
    def add_data(self, data):
        self.lock.acquire()
        try:
            if len(self.data) == 0:
                #init data records on first add
                self.data = data
            else:
                i = 0
                for data_line in data:
                    if len(self.data) <= i:
                        #missing records
                        self.data.append(data_line)
                    if len(data_line['x']) > 0:
                        self.data[i]['x'].append(data_line['x'][0])
                        self.data[i]['y'].append(data_line['y'][0])
                        self.data[i]['name'] = data_line['name']
                    i += 1
        except Exception, ex:
            Log.logger.warning('Err {} add_data data={}'.format(ex, data))
        finally:
            self.lock.release()

    def upload_data(self):
        self.lock.acquire()
        try:
            if len(self.data) > 0:
                fig = graph_objs.Figure(data=self.data, layout=get_layout(self.graph_unique_name))
                url = py.plot(fig, filename=self.graph_unique_name, fileopt=self.file_opt, auto_open=False)
                self.last_save = utils.get_base_location_now_date()
                self.data = [] #reset data as it was uploaded
                known_graph_url = get_graph_url_from_memory(self.graph_unique_name)
                if url != known_graph_url:
                    Log.logger.warning('Original graph {} removed from plotly'.format(self.graph_unique_name))
                    upload_reference_graph(self.graph_unique_name)
                    if self.file_opt=='append' or self.file_opt=='new':
                        add_new_serie(self.graph_unique_name, url, self.trace_unique_id)
        except PlotlyAccountError, ex:
            Log.logger.warning('Unable to plot graph, err {}'.format(ex))
        finally:
            self.lock.release()