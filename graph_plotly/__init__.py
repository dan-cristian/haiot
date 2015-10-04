__author__ = 'dcristian'

import os

import plotly.plotly as py
from plotly import graph_objs
from plotly.exceptions import PlotlyAccountError

from main.logger_helper import Log
from common import Constant, utils
from main.admin import model_helper, thread_pool
import graph_plotly_run

initialised = False

def upload_data(obj):
    try:
        Log.logger.debug('Trying to upload plotly obj {}'.format(obj))
        if Constant.JSON_PUBLISH_GRAPH_X in obj:
            axis_x_field = obj[Constant.JSON_PUBLISH_GRAPH_X]
            graph_id_field = obj[Constant.JSON_PUBLISH_GRAPH_ID]
            graph_legend_field = obj[Constant.JSON_PUBLISH_GRAPH_LEGEND]
            graph_shape_fields = obj[Constant.JSON_PUBLISH_GRAPH_SHAPE]
            graph_y_fields = obj[Constant.JSON_PUBLISH_GRAPH_Y]
            changed_fields = obj[Constant.JSON_PUBLISH_FIELDS_CHANGED]
            #intersect lists and get only graphable fields that had values changed
            list_axis_y = list(set(graph_y_fields) & set(changed_fields))
            if len(list_axis_y)==0:
                Log.logger.debug('Ignoring graph upload graph={} changed={} obj={}'.format(graph_y_fields,
                                                                                       changed_fields, obj))
            Log.logger.debug('Trying to upload y axis {}'.format(list_axis_y))
            if axis_x_field in obj and graph_id_field in obj:
                table = obj[Constant.JSON_PUBLISH_TABLE]
                trace_unique_id = obj[graph_id_field] #unique record/trace identifier
                x_val = obj[axis_x_field]
                graph_legend_item_name = obj[graph_legend_field] #unique key for legend
                x_val = utils.parse_to_date(x_val)
                x = [x_val]
                index = 0
                for axis_y in list_axis_y:
                    if axis_y in obj:
                        trace_list = []
                        y=[obj[axis_y]]
                        #shape visual type for this trace
                        shape = graph_shape_fields[index]
                        #unique name used for graph on upload
                        graph_base_name = str(table+' '+axis_y)
                        #full name and path to enable archiving
                        graph_unique_name = graph_plotly_run.get_graph_full_name_path(graph_base_name)
                        if not graph_plotly_run.graph_url_exists_in_memory(graph_unique_name):
                            #download series order list to ensure graph consistency, usually done at app start
                            #or when trace is created
                            graph_plotly_run.download_trace_id_list(graph_unique_name=graph_unique_name,
                                                                    shape_type=shape)
                        if graph_unique_name in graph_plotly_run.g_trace_id_list_per_graph:
                            trace_unique_id_pattern = graph_plotly_run.g_trace_id_list_per_graph[graph_unique_name]
                        else:
                            Log.logger.warning('Unable to get a reference pattern, graph {}'.format(graph_unique_name))
                        known_graph_url = graph_plotly_run.get_graph_url_from_memory(graph_unique_name)
                        if trace_unique_id in trace_unique_id_pattern:
                            trace_list = graph_plotly_run.populate_trace_for_extend(x=x, y=y,
                                    graph_legend_item_name=graph_legend_item_name, trace_unique_id=trace_unique_id,
                                    trace_unique_id_pattern=trace_unique_id_pattern, shape_type=shape)
                            Log.logger.debug('Extending graph {}'.format(graph_unique_name, shape))
                            fileopt = 'extend'
                        else:
                            trace_list = graph_plotly_run.populate_trace_for_append(x=x, y=y,
                                        graph_legend_item_name=graph_legend_item_name,trace_unique_id=trace_unique_id,
                                        shape_type=shape)
                            Log.logger.debug('Appending graph {}'.format(graph_unique_name))
                            fileopt = 'append'
                        data = graph_objs.Data(trace_list)
                        try:
                            if known_graph_url is None:
                                Log.logger.warning('Graph {} is setting up, dropping data'.format(graph_unique_name))
                            else:
                                graph_plotly_run.add_graph_data(data=data, graph_unique_name=graph_unique_name,
                                                                trace_unique_id = trace_unique_id, file_opt=fileopt)

                                #fig = graph_objs.Figure(data=data, layout=get_layout(graph_unique_name))
                                #url = py.plot(fig, filename=graph_unique_name, fileopt=fileopt, auto_open=False)
                                #if url != known_graph_url:
                                #    Log.logger.warning('Original graph {} removed from plotly'.format(graph_unique_name))
                                #    upload_reference_graph(graph_unique_name)
                                #if fileopt=='append' or fileopt=='new':
                                #    add_new_serie(graph_unique_name, url, trace_unique_id)
                        except PlotlyAccountError, ex:
                            Log.logger.warning('Unable to plot graph, err {}'.format(ex))
                    index += 1
            else:
                Log.logger.critical('Graphable object missing axis_x [{}], graph_id [{}], in obj {}'.format(axis_x_field,
                                                                                          graph_id_field, obj))
        else:
            Log.logger.critical('Graphable object missing axis X field {}'.format(Constant.JSON_PUBLISH_GRAPH_X))
    except Exception, ex:
        Log.logger.exception('General error saving graph, err {} obj={}'.format(ex, obj))

def unload():
    global initialised
    thread_pool.remove_callable(graph_plotly_run.thread_run)
    initialised = False

def init():
    #use auto setup as described here: https://plot.ly/python/getting-started/ to avoid passwords in code
    #or less secure sign_in code below
    #py.sign_in(model_helper.get_param(constant.P_PLOTLY_USERNAME),model_helper.get_param(constant.P_PLOTLY_APIKEY))
    if py.get_credentials()['username'] == '' or py.get_credentials()['api_key'] == '':
        env_var='PLOTLY_CREDENTIALS_PATH'
        alt_path = os.environ.get(env_var)
        if not alt_path:
            Log.logger.info('Plotly config not in environment var: {}'.format(env_var))
            env_var = 'OPENSHIFT_REPO_DIR'
            alt_path = os.environ.get(env_var)
            if alt_path is None:
                Log.logger.info('Plotly config not in environment var: {}'.format(env_var))
                credential_file = model_helper.get_param(Constant.P_PLOTLY_ALTERNATE_CONFIG)
                alt_path = os.getcwd()+'/'+credential_file
            else:
                Log.logger.info('Plotly config found in environment var: {}, path={}'.format(env_var, alt_path))
                alt_path = str(alt_path) + '/../data/.plotly.credentials'
        Log.logger.info("Plotly standard config empty, trying alt_path={}".format(alt_path))
        try:
            with open(alt_path, 'r') as cred_file:
                data = cred_file.read().replace('\n','')
            if len(data) > 0:
                cred_obj = utils.json2obj(data)
                username=cred_obj['username']
                api_key=cred_obj['api_key']
                if username and api_key:
                    py.sign_in(username, api_key)
                    global initialised
                    initialised = True
                #else:
                #    Log.logger.info("Plotly init from db folder config {}{} not ok, trying with db data".format(os.getcwd(),
                #        credential_file))
                #    #alternate way if reading data from DB
                #    py.sign_in(model_helper.get_param(constant.P_PLOTLY_USERNAME),
                #               model_helper.get_param(constant.P_PLOTLY_APIKEY))

        except Exception, ex:
            Log.logger.warning("error reading plotly credentials {}".format(ex))
    else:
        Log.logger.info("Plotly standard config found with username {}".format(py.get_credentials()['username']))
        initialised = True
    if initialised:
        Log.logger.info('Plotly is connected')
        thread_pool.add_interval_callable(graph_plotly_run.thread_run, run_interval_second=60)