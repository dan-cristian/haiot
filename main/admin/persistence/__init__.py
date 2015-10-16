__author__ = 'Dan Cristian <dan.cristian@gmail.com>'


from common import Constant
from common import utils
from main import Log

# saves record to local database
def save_to_history(obj, save_to_local_db=False, upload_to_cloud=False):
    try:
        Log.logger.debug('Trying to save historical record {}'.format(obj))
        if Constant.JSON_PUBLISH_GRAPH_X in obj:
            # name of x field
            axis_x_field = obj[Constant.JSON_PUBLISH_GRAPH_X]
            graph_id_field = obj[Constant.JSON_PUBLISH_GRAPH_ID]
            graph_legend_field = obj[Constant.JSON_PUBLISH_GRAPH_LEGEND]
            graph_shape_fields = obj[Constant.JSON_PUBLISH_GRAPH_SHAPE]
            graph_y_fields = obj[Constant.JSON_PUBLISH_GRAPH_Y]
            # names of fields that have value changed to record smallest amount of data
            changed_fields = obj[Constant.JSON_PUBLISH_FIELDS_CHANGED]
            # intersect lists and get only graphable fields that had values changed
            list_axis_y = list(set(graph_y_fields) & set(changed_fields))
            if len(list_axis_y)==0:
                Log.logger.debug('Ignoring record save graph={} changed fields={} obj={}'.format(graph_y_fields,
                                                                                      changed_fields, obj))
            else:
                Log.logger.debug('Trying to save y axis {}'.format(list_axis_y))
                if axis_x_field in obj and graph_id_field in obj:
                    table = obj[Constant.JSON_PUBLISH_TABLE]
                    trace_unique_id = obj[graph_id_field]  # unique record/trace identifier
                    x_val = obj[axis_x_field]
                    graph_legend_item_name = obj[graph_legend_field]  # unique key for legend
                    x_val = utils.parse_to_date(x_val)
                    x = x_val
                    index = 0
                    for axis_y in list_axis_y:
                        if axis_y in obj:
                            trace_list = []
                            y=obj[axis_y]
                            # save to local DB
                            dest_table = str(table) + 'History'
                            from main.admin import models
                            # http://stackoverflow.com/questions/4030982/initialise-class-object-by-name
                            try:
                                class_table = getattr(models, dest_table)
                                new_record = class_table()
                                setattr(new_record, axis_x_field, x)
                                setattr(new_record, axis_y, y)
                                setattr(new_record, graph_legend_field, graph_legend_item_name)
                                setattr(new_record, Constant.JSON_PUBLISH_RECORD_UUID,
                                        obj[Constant.JSON_PUBLISH_RECORD_UUID])
                                new_record.add_record_to_db()
                            except Exception, ex:
                                Log.logger.critical("Cannot save history db err={} record={}".format(ex, obj))

                            # upload to cloud if plotly is initialised
                            if upload_to_cloud:
                                from cloud import graph_plotly
                                if graph_plotly.initialised:
                                    from cloud.graph_plotly import graph_plotly_run
                                    # shape visual type for this trace
                                    shape = graph_shape_fields[index]
                                    # unique name used for grid on upload
                                    grid_base_name = str(table)
                                    graph_plotly_run.add_grid_data(grid_unique_name=grid_base_name, x=x, y=y,
                                                               axis_x_name=axis_x_field, axis_y_name=axis_y,
                                                               record_unique_id_name=graph_legend_field,
                                                               record_unique_id_value=graph_legend_item_name)

                        index += 1
                else:
                    Log.logger.critical('Missing history axis_x [{}], graph_id [{}], in obj {}'.format(axis_x_field,
                                                                                              graph_id_field, obj))
        else:
            Log.logger.critical('Missing history axis X field {}'.format(Constant.JSON_PUBLISH_GRAPH_X))
    except Exception, ex:
        Log.logger.exception('General error saving historical record, err {} obj={}'.format(ex, obj))


def upload_to_cloud(obj):
    pass