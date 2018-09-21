__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

import datetime
import threading
import prctl
from plotly import graph_objs
import plotly.plotly as py
from plotly.exceptions import PlotlyError, PlotlyAccountError, PlotlyListEntryError, PlotlyRequestError
from plotly.grid_objs import Column, Grid

from requests import HTTPError

from common import utils
from common import Constant
from main.logger_helper import L
from main.admin import models



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


def populate_trace_for_extend(x=None, y=None, graph_legend_item_name='', trace_unique_id='',
                              trace_unique_id_pattern=None, shape_type=''):
    #series list must be completely filled in using graph create order
    #'text' param if added generates error
    if not trace_unique_id_pattern:
        trace_unique_id_pattern = []
    if not x:
        x = []
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
    L.l.debug('Extending graph serie {} {}'.format(graph_legend_item_name, trace_unique_id))
    return trace_list

def populate_trace_for_append(x=None, y=None, graph_legend_item_name='', trace_unique_id='', show_legend=True,
                              shape_type=''):
    #'text' param should only be added at trace creation
    if not y:
        y = []
    if not x:
        x = []
    trace_append = graph_objs.Scatter(x=x, y=y, name=graph_legend_item_name, text=trace_unique_id,
                                      showlegend=show_legend, line = graph_objs.Line(shape=shape_type))
    trace_list = [trace_append]
    L.l.debug('Appending new graph serie {} {}'.format(graph_legend_item_name, trace_unique_id))
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
        L.l.info('New reference graph {} uploaded ok'.format(graph_unique_name))
    except PlotlyListEntryError, ex:
        L.l.warning('Error uploading new reference graph {} err {}'.format(graph_unique_name, ex))
    except PlotlyAccountError, ex:
        L.l.warning('Unable to upload new reference graph {} err {}'.format(graph_unique_name, ex))



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
    L.l.info('Downloading online traces in memory, graph {} shape {}'.format(graph_unique_name, shape_type))
    start_date = utils.get_base_location_now_date()
    result = -1
    try:
        result=py.file_ops.mkdirs(get_folder_name())
        L.l.debug('Created archiving folder {} result {}'.format(get_folder_name(), result))
    except PlotlyRequestError, ex:
        if hasattr(ex, 'HTTPError'):
            msg = str(ex.HTTPError) + ex.HTTPError.response.content
        else:
            msg = str(ex)
        L.l.info('Ignoring error on create archive folder {} err={}'.format(get_folder_name(), msg))
    except Exception, ex:
        L.l.warning('Unable to create archive folder {} err={} res={}'.format(get_folder_name(), ex, result))

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
                L.l.info('Error extending graph {} in pass {}, err={}'.format(graph_unique_name, i, ex))
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
                    L.l.warning('Unable to find name field in graph, skipping')
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
            L.l.warning('Unable to get figure {} err={}'.format(graph_url, ex))
    else:
        L.l.critical('Unable to get or setup remote graph {}'.format(graph_unique_name))
    elapsed = (utils.get_base_location_now_date()-start_date).seconds
    L.l.info('Download {} completed in {} seconds'.format(graph_unique_name, elapsed))

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

#list with cached grid objs for future upload
__grid_list = {}


def add_grid_data(grid_unique_name, x, y, axis_x_name, axis_y_name, record_unique_id_name, record_unique_id_value):
    global __grid_list
    if grid_unique_name not in __grid_list:
        grid = PlotlyGrid()
        grid.grid_unique_name = grid_unique_name #"grids/" + grid_unique_name
        __grid_list[grid_unique_name] = grid
    __grid_list[grid_unique_name].add_data(x, y, axis_x_name=axis_x_name, axis_y_name=axis_y_name,
                                           record_unique_id_name=record_unique_id_name,
                                           record_unique_id_value=record_unique_id_value)
    pass

#iterate and upload graphs with valid data not saved older than 5 minutes
def __upload_cached_plotly_data():
    #for graph in graph_list.values():
    #    if (utils.get_base_location_now_date() - graph.last_save).total_seconds() > 300:
    #        graph.upload_data()

    for grid in __grid_list.values():
        if (utils.get_base_location_now_date() - grid.last_save).total_seconds() > PlotlyGrid.save_interval_seconds:
            grid.upload_data()

# let other nodes know the grid urls I got when uploading new grids
def __announce_grid_cache():
    grids_i_created = models.PlotlyCache().query_filter_all(models.PlotlyCache.created_by_node_name.in_(
        [Constant.HOST_NAME]))
    for grid in grids_i_created:
        new_record = models.PlotlyCache()
        new_record.created_by_node_name = grid.created_by_node_name
        new_record.column_name_list = grid.column_name_list
        new_record.grid_url = grid.grid_url
        new_record.grid_name = grid.grid_name
        new_record.announced_on = utils.get_base_location_now_date()
        grid.save_changed_fields(current_record=grid, new_record=new_record, notify_transport_enabled=True,
                                   save_to_graph=False)

def thread_run():
    prctl.set_name("plotly")
    threading.current_thread().name = "plotly"
    L.l.debug('Processing graph_plotly_run')
    __upload_cached_plotly_data()
    __announce_grid_cache()
    return 'Processed graph_plotly_run'


class PlotlyGrid:
    save_interval_seconds = 120

    def __init__(self):
        # table name stored in this grid
        self.grid_unique_name = None
        # list of cached rows waiting to be uploaded columns{}[rows]
        self.columns_cache = {}
        # list with column names already uploaded. keeping the same column order is vital when uploading to plotly
        self.column_name_list_uploaded = []
        # last cache upload
        self.last_save = datetime.datetime.min
        self.max_row_count = 0
        self.uploading_data = False
        self.axis_x_name = None
        self.grid_url = None

    def add_data(self, x, y, axis_x_name, axis_y_name, record_unique_id_name, record_unique_id_value):
        while self.uploading_data:
            # Log.logger.info("Not adding data to grid {} as it is uploading currently".format(self.grid_unique_name))
            threading._sleep(1)
        self.axis_x_name = axis_x_name
        # this column has the primary key - usually a datetime type (updated_on)
        if axis_x_name not in self.columns_cache:
            self.columns_cache[axis_x_name] = []
        if axis_y_name not in self.columns_cache:
            self.columns_cache[axis_y_name] = []
        if record_unique_id_name not in self.columns_cache:
            self.columns_cache[record_unique_id_name] = []

        self.columns_cache[axis_x_name].append(x)
        self.max_row_count = len(self.columns_cache[axis_x_name])
        # populate each columns with rows, keep no of rows identical in all columns
        for column_name in self.columns_cache.keys():
            if len(self.columns_cache[column_name]) < self.max_row_count:
                # fill in with empty rows to ensure each column has same no. of records
                while len(self.columns_cache[column_name]) < self.max_row_count:
                    self.columns_cache[column_name].append(None)
            # replace last appended None value above with current y & unique record value
            if column_name == axis_y_name:
                self.columns_cache[column_name][self.max_row_count - 1] = y
            if column_name == record_unique_id_name:
                self.columns_cache[column_name][self.max_row_count - 1] = record_unique_id_value

    def _create_or_get_grid(self):
        grid = models.PlotlyCache().query_filter_first(models.PlotlyCache.grid_name.in_([self.grid_unique_name]))
        if grid:
            L.l.info("Loading {} grid metadata from db cache".format(self.grid_unique_name))
            self.grid_url = grid.grid_url
            # loading the column names for appending data in the right order
            self.column_name_list_uploaded = grid.column_name_list.split(",")
            self._update_grid()
        else:
            self._upload_new_grid()

    def _upload_new_grid(self):
        L.l.info("Uploading new {} grid metadata to plot.ly".format(self.grid_unique_name))
        # grid was not retrieved yet from plotly, create it
        upload_columns = []
        # create column list for grid upload, put first column = x axis
        upload_columns.append(Column(self.columns_cache[self.axis_x_name], self.axis_x_name))
        # then add the remaining columns, except the above one that is already added
        for column_name in self.columns_cache.keys():
            if column_name != self.axis_x_name:
                upload_columns.append(Column(self.columns_cache[column_name], column_name))
        grid = Grid(upload_columns)
        self.grid_url = py.grid_ops.upload(grid,
                     self.grid_unique_name,      # name of the grid in your plotly account
                     world_readable=True, # public or private
                     auto_open=False)      # open the grid in the browser
        # save new uploaded column names to maintain upload order
        for grid_column in upload_columns:
            if grid_column.name not in self.column_name_list_uploaded:
                self.column_name_list_uploaded.append(grid_column.name)
        # save to db cache. expect record to be empty
        plotly_cache_record = models.PlotlyCache().query_filter_first(models.PlotlyCache.grid_name.in_(
            [self.grid_unique_name]))
        if plotly_cache_record:
            L.l.critical("While uploading a new grid found a cached one in DB, unexpected failure!")
        else:
            plotly_cache_record = models.PlotlyCache(grid_name=self.grid_unique_name)
            plotly_cache_record.grid_url = self.grid_url
            my_column_list = ','.join(map(str, self.column_name_list_uploaded))
            plotly_cache_record.column_name_list = my_column_list
            plotly_cache_record.created_by_node_name = Constant.HOST_NAME
            plotly_cache_record.save_changed_fields(new_record=plotly_cache_record, notify_transport_enabled=True,
                                   save_to_graph=False)
        L.l.info("Uploading {} grid completed".format(self.grid_unique_name))

    def _update_grid(self):
        # append empty new columns that were not yet uploaded to cloud grid
        upload_columns = []
        for column_name in self.columns_cache.keys():
            if column_name not in self.column_name_list_uploaded:
                upload_columns.append(Column([], column_name))
        if len(upload_columns) > 0:
            L.l.info("Appending new columns grid={} count={}".format(self.grid_unique_name,
                                                                     len(upload_columns)))
            py.grid_ops.append_columns(columns=upload_columns, grid_url=self.grid_url)
        # save new uploaded column names to maintain upload order
        for grid_column in upload_columns:
            if grid_column.name not in self.column_name_list_uploaded:
                self.column_name_list_uploaded.append(grid_column.name)
        # append rows to grid, already in memory
        # convert data from columns to a list of rows
        upload_rows = []
        rows_left = True
        index = 0
        while index < self.max_row_count:
            row = [self.columns_cache[self.axis_x_name][index]]
            # adding primary key value
            # adding row value from each column at current index position
            for column_name in self.columns_cache.keys():
                if column_name != self.axis_x_name:
                    value = self.columns_cache[column_name][index]
                    if value is None:
                        value = ''
                    row.append(value)
            upload_rows.append(row)
            index += 1
        if len(upload_rows) > 0:
            L.l.info("Appending grid {} rows={}".format(self.grid_unique_name, len(upload_rows)))
            # upload all rows. column order and number of columns must match the grid in the cloud
            py.grid_ops.append_rows(grid_url=self.grid_url, rows=upload_rows)
        L.l.info("Uploading {} grid completed".format(self.grid_unique_name))

    def upload_data(self):
        try:
            self.uploading_data = True
            L.l.info("Uploading plotly grid {}".format(self.grid_unique_name))
            if self.grid_url:
                self._update_grid()
            else:
                self._create_or_get_grid()
            # delete from cache all rows that have been uploaded
            for column_name in self.columns_cache.keys():
                self.columns_cache[column_name] = []
            self.last_save = utils.get_base_location_now_date()
            PlotlyGrid.save_interval_seconds = max(300, PlotlyGrid.save_interval_seconds - 60)
        except HTTPError, er:
            L.l.warning("Error uploading plotly grid={}, er={} cause={}".format(self.grid_unique_name,
                                                                                er, er.response.text))
            if "file already exists" in er.response.text:
                L.l.critical("Fatal error, unable to resume saving data to plotly grid")

            if "throttled" in er.response.text:
                PlotlyGrid.save_interval_seconds = min(1200, PlotlyGrid.save_interval_seconds + 60)
                L.l.info("Plotly upload interval is {}s".format(PlotlyGrid.save_interval_seconds))
        except Exception, ex:
            L.l.warning("Exception uploading plotly grid={}, er={}".format(self.grid_unique_name, ex))
        finally:
            self.uploading_data = False

class PlotlyGraph:
    def __init__(self):
        pass

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
            L.l.warning('Err {} add_data data={}'.format(ex, data))
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
                    L.l.warning('Original graph {} removed from plotly'.format(self.graph_unique_name))
                    upload_reference_graph(self.graph_unique_name)
                    if self.file_opt=='append' or self.file_opt=='new':
                        add_new_serie(self.graph_unique_name, url, self.trace_unique_id)
        except PlotlyAccountError, ex:
            L.l.warning('Unable to plot graph, err {}'.format(ex))
        finally:
            self.lock.release()