__author__ = 'dcristian'

import os
from main.logger_helper import L
from common import Constant, utils
from main.admin import model_helper, models
from main import thread_pool

#fixme: make it work without plotly
try:
    import plotly.plotly as py
    from plotly import graph_objs
    from plotly.exceptions import PlotlyAccountError
    import graph_plotly_run
except Exception, ex:
    pass


initialised = False


# updated plotly cache on all hosts to allow grid update in case mastership changes
def record_update(obj):
    source_host_name = utils.get_object_field_value(obj, Constant.JSON_PUBLISH_SOURCE_HOST)
    if source_host_name != Constant.HOST_NAME:
        # Log.logger.info("Received plotly cache update from {}".format(source_host_name))
        models.PlotlyCache().save_changed_fields_from_json_object(json_object=obj, notify_transport_enabled=False,
                                                                  save_to_graph=False)


# uploads data directly to a graph object in plotly
# not very reliable since plotly changed the API
def upload_data(obj):
    try:
        L.l.debug('Trying to upload plotly obj {}'.format(obj))
        if Constant.JSON_PUBLISH_GRAPH_X in obj:
            axis_x_field = obj[Constant.JSON_PUBLISH_GRAPH_X]
            graph_id_field = obj[Constant.JSON_PUBLISH_GRAPH_ID]
            graph_legend_field = obj[Constant.JSON_PUBLISH_GRAPH_LEGEND]
            graph_shape_fields = obj[Constant.JSON_PUBLISH_GRAPH_SHAPE]
            graph_y_fields = obj[Constant.JSON_PUBLISH_GRAPH_Y]
            changed_fields = obj[Constant.JSON_PUBLISH_FIELDS_CHANGED]
            # intersect lists and get only graphable fields that had values changed
            list_axis_y = list(set(graph_y_fields) & set(changed_fields))
            if len(list_axis_y) == 0:
                L.l.debug('Ignoring graph upload graph={} changed={} obj={}'.format(graph_y_fields,
                                                                                    changed_fields, obj))
            L.l.debug('Trying to upload y axis {}'.format(list_axis_y))
            if axis_x_field in obj and graph_id_field in obj:
                table = obj[Constant.JSON_PUBLISH_TABLE]
                trace_unique_id = obj[graph_id_field]  # unique record/trace identifier
                x_val = obj[axis_x_field]
                graph_legend_item_name = obj[graph_legend_field]  # unique key for legend
                x_val = utils.parse_to_date(x_val)
                x = [x_val]
                index = 0
                for axis_y in list_axis_y:
                    if axis_y in obj:
                        trace_list = []
                        y = [obj[axis_y]]
                        # shape visual type for this trace
                        shape = graph_shape_fields[index]
                        # unique name used for graph on upload
                        graph_base_name = str(table + ' ' + axis_y)
                        # full name and path to enable archiving
                        graph_unique_name = graph_plotly_run.get_graph_full_name_path(graph_base_name)
                        if not graph_plotly_run.graph_url_exists_in_memory(graph_unique_name):
                            # download series order list to ensure graph consistency, usually done at app start
                            # or when trace is created
                            graph_plotly_run.download_trace_id_list(graph_unique_name=graph_unique_name,
                                                                    shape_type=shape)
                        if graph_unique_name in graph_plotly_run.g_trace_id_list_per_graph:
                            trace_unique_id_pattern = graph_plotly_run.g_trace_id_list_per_graph[graph_unique_name]
                        else:
                            L.l.warning('Unable to get a reference pattern, graph {}'.format(graph_unique_name))
                        known_graph_url = graph_plotly_run.get_graph_url_from_memory(graph_unique_name)
                        if trace_unique_id in trace_unique_id_pattern:
                            trace_list = graph_plotly_run.populate_trace_for_extend(x=x, y=y,
                                                                                    graph_legend_item_name=graph_legend_item_name,
                                                                                    trace_unique_id=trace_unique_id,
                                                                                    trace_unique_id_pattern=trace_unique_id_pattern,
                                                                                    shape_type=shape)
                            L.l.debug('Extending graph {}'.format(graph_unique_name, shape))
                            fileopt = 'extend'
                        else:
                            trace_list = graph_plotly_run.populate_trace_for_append(x=x, y=y,
                                                                                    graph_legend_item_name=graph_legend_item_name,
                                                                                    trace_unique_id=trace_unique_id,
                                                                                    shape_type=shape)
                            L.l.debug('Appending graph {}'.format(graph_unique_name))
                            fileopt = 'append'
                        data = graph_objs.Data(trace_list)
                        try:
                            if known_graph_url is None:
                                L.l.warning('Graph {} is setting up, dropping data'.format(graph_unique_name))
                            else:
                                graph_plotly_run.add_graph_data(data=data, graph_unique_name=graph_unique_name,
                                                                trace_unique_id=trace_unique_id, file_opt=fileopt)
                        except PlotlyAccountError, ex:
                            L.l.warning('Unable to plot graph, err {}'.format(ex))
                    index += 1
            else:
                L.l.critical(
                    'Graphable object missing axis_x [{}], graph_id [{}], in obj {}'.format(axis_x_field,
                                                                                            graph_id_field, obj))
        else:
            L.l.critical('Graphable object missing axis X field {}'.format(Constant.JSON_PUBLISH_GRAPH_X))
    except Exception, ex:
        L.l.exception('General error saving graph, err {} obj={}'.format(ex, obj))


'''
#upload data to a grid object in plotly. grid will be used as main source to generate graphs
def upload_data_to_grid(obj):
    try:
        Log.logger.debug('Trying to upload plotly grid record {}'.format(obj))
        if Constant.JSON_PUBLISH_GRAPH_X in obj:
            #name of x field
            axis_x_field = obj[Constant.JSON_PUBLISH_GRAPH_X]
            graph_id_field = obj[Constant.JSON_PUBLISH_GRAPH_ID]
            graph_legend_field = obj[Constant.JSON_PUBLISH_GRAPH_LEGEND]
            graph_shape_fields = obj[Constant.JSON_PUBLISH_GRAPH_SHAPE]
            graph_y_fields = obj[Constant.JSON_PUBLISH_GRAPH_Y]
            #names of fields that have value changed to record smallest amount of data
            changed_fields = obj[Constant.JSON_PUBLISH_FIELDS_CHANGED]
            #intersect lists and get only graphable fields that had values changed
            list_axis_y = list(set(graph_y_fields) & set(changed_fields))
            if len(list_axis_y)==0:
                Log.logger.debug('Ignoring graph upload graph={} changed fields={} obj={}'.format(graph_y_fields,
                                                                                      changed_fields, obj))
            else:
                Log.logger.debug('Trying to upload y axis {}'.format(list_axis_y))
                if axis_x_field in obj and graph_id_field in obj:
                    table = obj[Constant.JSON_PUBLISH_TABLE]
                    trace_unique_id = obj[graph_id_field] #unique record/trace identifier
                    x_val = obj[axis_x_field]
                    graph_legend_item_name = obj[graph_legend_field] #unique key for legend
                    x_val = utils.parse_to_date(x_val)
                    x = x_val
                    index = 0
                    for axis_y in list_axis_y:
                        if axis_y in obj:
                            trace_list = []
                            y=obj[axis_y]
                            #shape visual type for this trace
                            shape = graph_shape_fields[index]
                            #unique name used for grid on upload
                            grid_base_name = str(table)
                            graph_plotly_run.add_grid_data(grid_unique_name=grid_base_name, x=x, y=y,
                                                           axis_x_name=axis_x_field, axis_y_name=axis_y,
                                                           record_unique_id_name=graph_legend_field,
                                                           record_unique_id_value=graph_legend_item_name)
                        index += 1
                else:
                    Log.logger.critical('Graphable object missing axis_x [{}], graph_id [{}], in obj {}'.format(axis_x_field,
                                                                                              graph_id_field, obj))
        else:
            Log.logger.critical('Graphable object missing axis X field {}'.format(Constant.JSON_PUBLISH_GRAPH_X))
    except Exception, ex:
        Log.logger.exception('General error saving graph, err {} obj={}'.format(ex, obj))
'''


def unload():
    global initialised
    thread_pool.remove_callable(graph_plotly_run.thread_run)
    initialised = False


def init():
    # use auto setup as described here: https://plot.ly/python/getting-started/ to avoid passwords in code
    # or less secure sign_in code below
    # py.sign_in(model_helper.get_param(constant.P_PLOTLY_USERNAME),model_helper.get_param(constant.P_PLOTLY_APIKEY))
    username = ""
    if py.get_credentials()['username'] == '' or py.get_credentials()['api_key'] == '':
        env_var = 'PLOTLY_CREDENTIALS_PATH'
        alt_path = os.environ.get(env_var)
        if not alt_path:
            L.l.info('Plotly config not in environment var: {}'.format(env_var))
            env_var = 'OPENSHIFT_REPO_DIR'
            alt_path = os.environ.get(env_var)
            if alt_path is None:
                L.l.info('Plotly config not in environment var: {}'.format(env_var))
                credential_file = model_helper.get_param(Constant.P_PLOTLY_ALTERNATE_CONFIG)
                alt_path = os.getcwd() + '/' + credential_file
            else:
                L.l.info('Plotly config found in environment var: {}, path={}'.format(env_var, alt_path))
                alt_path = str(alt_path) + '/../data/.plotly.credentials'
        L.l.info("Plotly standard config empty, trying alt_path={}".format(alt_path))
        try:
            with open(alt_path, 'r') as cred_file:
                data = cred_file.read().replace('\n', '')
            if len(data) > 0:
                cred_obj = utils.json2obj(data)
                username = cred_obj['username']
                api_key = cred_obj['api_key']
                if username and api_key:
                    py.sign_in(username, api_key)
                    global initialised
                    initialised = True
                    # else:
                    #    Log.logger.info("Plotly init from db folder config {}{} not ok, trying with db data".format(os.getcwd(),
                    #        credential_file))
                    #    #alternate way if reading data from DB
                    #    py.sign_in(model_helper.get_param(constant.P_PLOTLY_USERNAME),
                    #               model_helper.get_param(constant.P_PLOTLY_APIKEY))

        except Exception, ex:
            L.l.warning("error reading plotly credentials {}".format(ex))
    else:
        L.l.info("Plotly standard config found with username {}".format(py.get_credentials()['username']))
        initialised = True
    if initialised:
        L.l.info('Plotly is connected with username={}'.format(username))
        thread_pool.add_interval_callable(graph_plotly_run.thread_run, run_interval_second=60)
