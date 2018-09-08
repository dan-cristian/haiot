from common import Constant
from common import utils
from main import L

__author__ = 'Dan Cristian <dan.cristian@gmail.com>'


# saves record to cloud database
def save_to_history_cloud(obj):
    try:
        L.l.debug('Trying to save historical record to cloud {}'.format(obj))
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
            if len(list_axis_y) == 0:
                L.l.info('Ignoring record save graph={} changed fields={} obj={}'.format(graph_y_fields,
                                                                                         changed_fields, obj))
            else:
                L.l.debug('Trying to save y axis {}'.format(list_axis_y))
                if axis_x_field in obj and graph_id_field in obj:
                    table = obj[Constant.JSON_PUBLISH_TABLE]
                    trace_unique_id = obj[graph_id_field]  # unique record/trace identifier
                    x_val = obj[axis_x_field]
                    graph_legend_item_name = obj[graph_legend_field]  # unique key for legend
                    x_val = utils.parse_to_date(x_val)
                    x = x_val
                    index = 0
                    field_pairs = [[axis_x_field, x], [graph_legend_field, graph_legend_item_name],
                                   [Constant.JSON_PUBLISH_RECORD_UUID, obj[Constant.JSON_PUBLISH_RECORD_UUID]],
                                   [Constant.JSON_PUBLISH_SOURCE_HOST, obj[Constant.JSON_PUBLISH_SOURCE_HOST]]]
                    for axis_y in list_axis_y:
                        if axis_y in obj:
                            trace_list = []
                            y = obj[axis_y]
                            # add multiple y values for later save in db as a single record
                            field_pairs.append([axis_y, y])
                            # upload to cloud if plotly is initialised
                            #from cloud import graph_plotly
                            #if graph_plotly.initialised:
                            #    from cloud.graph_plotly import graph_plotly_run
                            #    Log.logger.info('Uploading to cloud field {}'.format(graph_legend_field))
                                # shape visual type for this trace
                                # shape = graph_shape_fields[index]
                                # unique name used for grid on upload
                            #   grid_base_name = str(table)
                            #    graph_plotly_run.add_grid_data(grid_unique_name=grid_base_name, x=x, y=y,
                            #                                   axis_x_name=axis_x_field, axis_y_name=axis_y,
                            #                                   record_unique_id_name=graph_legend_field,
                            #                                   record_unique_id_value=graph_legend_item_name)
                            #Log.logger.debug('Skip upload to cloud, plotly not init')
                        index += 1
                else:
                    L.l.critical('Missing history axis_x [{}], graph_id [{}], in obj {}'.format(
                        axis_x_field,graph_id_field,obj))
        else:
            L.l.critical('Missing history axis X field {}'.format(Constant.JSON_PUBLISH_GRAPH_X))
    except Exception as ex:
        L.l.exception('General error saving historical cloud record, err {} obj={}'.format(ex, obj))


# saves record to cloud database
def save_to_history_db(obj):
    try:
        table = obj[Constant.JSON_PUBLISH_TABLE]
        #L.l.debug('Trying to save historical record to db={}'.format(table))
        # save to local history DB, append history to source table name
        dest_table = str(table) + 'History'
        #L.l.debug('Saving to local db table {} obj={}'.format(dest_table, obj))
        from main.admin import models
        # http://stackoverflow.com/questions/4030982/initialise-class-object-by-name
        try:
            class_table = getattr(models, dest_table)
            new_record = class_table()
            for field in obj:
                if hasattr(new_record, field) and field != "id":
                    setattr(new_record, field, obj[field])
            if new_record.add_commit_record_to_db():
                #L.l.debug('Saved OK to local db table {} obj={}'.format(dest_table, new_record))
                pass
            else:
                L.l.critical("Cannot save history db record={}".format(obj))
        except Exception as ex:
            L.l.critical("Cannot save history db err={} record={}".format(ex, obj))
    except Exception as ex:
        L.l.exception('General error saving historical db record, err {} obj={}'.format(ex, obj))

