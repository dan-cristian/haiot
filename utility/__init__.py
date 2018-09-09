from sqlalchemy import desc
from main.logger_helper import L
from main import thread_pool
from common import Constant
from pydispatch import dispatcher
from main.admin import models, model_helper

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


initialised = False


# water & electricity utility from specialised sensors
def __utility_update_ex(sensor_name, value, unit=None):
    try:
        if value is not None:
            record = models.Utility(sensor_name=sensor_name)
            current_record = models.Utility.query.filter_by(sensor_name=sensor_name).first()
            if current_record is not None:
                if current_record.units_total is None:
                    current_record.units_total = 0.0
                #else: - should not be needed
                #    # force save
                #    if current_record is not None:
                #        current_record.units_total = -1
                record.utility_name = current_record.utility_name
                if current_record.utility_type == Constant.UTILITY_TYPE_WATER_LEVEL:
                    record.units_total = value / (current_record.ticks_per_unit * 1.0)
                    L.l.info("Saving utility water level value={} depth={}".format(value, record.units_total))
                elif current_record.utility_type == Constant.UTILITY_TYPE_ELECTRICITY:
                    if unit == current_record.unit_2_name:
                        record.units_2_delta = value
                        record.units_delta = 0
                    elif unit == current_record.unit_name:
                        record.units_total = value
                        record.units_delta = value - current_record.units_total
                        current_record.units_total = value
                        current_record.commit_record_to_db()
                    #L.l.info("Saving power level value={} depth={}".format(value, record.units_2_delta))
                L.l.debug("Saving utility ex record {} name={}".format(current_record, record.utility_name))
                record.save_changed_fields(current_record=current_record, new_record=record, debug=False,
                                           notify_transport_enabled=True, save_to_graph=True, save_all_fields=True)

            else:
                L.l.critical("Utility ex sensor [{}] is not defined in Utility table".format(sensor_name))
    except Exception as ex:
        L.l.error("Error saving utility ex update {}, try to connect to reporting DB".format(ex))
        if "Bind '" + Constant.DB_REPORTING_ID + "' is not specified" in ex.message:
            model_helper.init_reporting()


def __utility_update(sensor_name, units_delta_a, units_delta_b, total_units_a, total_units_b, sampling_period_seconds):
    try:
        index = 0
        is_debug = False
        ignore_save = False
        for delta in [units_delta_a, units_delta_b]:
            if delta is not None:
                record = models.Utility(sensor_name=sensor_name)
                current_record = models.Utility.query.filter_by(sensor_name=sensor_name, sensor_index=index).first()
                if current_record is not None:
                    record.sensor_index = index
                    record.utility_name = current_record.utility_name
                    if current_record.utility_type == Constant.UTILITY_TYPE_ELECTRICITY:
                        record.units_delta = delta / (current_record.ticks_per_unit * 1.0)  # kwh
                        record.unit_name = current_record.unit_name  # Constant.UTILITY_TYPE_ELECTRICITY_MEASURE
                        record.units_2_delta = (1000 * record.units_delta) / (sampling_period_seconds / 3600.0)  # watts
                        L.l.debug("Watts usage in {} is {}".format(record.utility_name, record.units_2_delta))
                        record.unit_2_name = current_record.unit_2_name
                    elif current_record.utility_type == Constant.UTILITY_TYPE_WATER:
                            L.l.info("Delta={}".format(delta))
                            if delta == 0:
                                ignore_save = True  # no need to save the 0 mark, make graphs prety
                                L.l.debug("Not saving utility water delta={}".format(record.units_delta))
                            else:
                                record.unit_name = current_record.unit_name  # Constant.UTILITY_TYPE_WATER_MEASURE
                                record.units_delta = delta / (current_record.ticks_per_unit * 1.0)
                                record.units_2_delta = 0.0  # to match comparison in field changed
                                L.l.debug("Saving utility water delta={}".format(record.units_delta))
                    elif current_record.utility_type == Constant.UTILITY_TYPE_GAS:
                        record.unit_name = current_record.unit_name  # Constant.UTILITY_TYPE_GAS_MEASURE
                        record.units_delta = delta / (current_record.ticks_per_unit * 1.0)
                        record.units_2_delta = 0.0  # to match comparison in field changed
                        L.l.debug("Saving utility gas delta={}".format(record.units_delta))
                    else:
                        L.l.debug("Saving unknown utility type={} sensor={}".format(
                            current_record.utility_type, sensor_name))
                        if current_record.ticks_per_unit is not None:
                            record.units_delta = delta / (current_record.ticks_per_unit * 1.0)  # force float operation
                            record.units_2_delta = 0.0
                        else:
                            L.l.warning("Null ticks per unit")
                    record.ticks_delta = delta
                    if current_record.unit_cost is None:
                        current_record.unit_cost = 0.0
                    record.cost = 1.0 * record.units_delta * current_record.unit_cost
                    # todo: read previous value from history
                    if current_record.units_total is None:
                        # get val from history db
                        last_rec = models.UtilityHistory.query.filter_by(
                            utility_name=record.utility_name).order_by(desc(models.UtilityHistory.id)).first()
                        if last_rec is not None:
                            current_record.units_total = last_rec.units_total
                        else:
                            L.l.warning("Could not find last history record for {}".format(record.utility_name))
                            current_record.units_total = 0.0
                    # force save for history recording, use negative values to enable recording 0
                    # no need to record 0 as it brokes graphana display
                    # if current_record is not None:
                        #current_record.units_delta = -1
                        #current_record.units_2_delta = -1
                        #current_record.ticks_delta = -1
                        #current_record.cost = -1
                        #current_record.utility_name = ""
                        #current_record.sensor_index = -1
                        #pass
                    if not ignore_save:
                        record.units_total = 0.0 + current_record.units_total + record.units_delta
                        L.l.debug("Saving utility record {} name={}".format(current_record, record.utility_name))
                        record.save_changed_fields(current_record=current_record, new_record=record, debug=is_debug,
                                                   notify_transport_enabled=True, save_to_graph=True,
                                                   save_all_fields=False)
                    else:
                        L.l.info("Ignored saving utility {} name={}".format(current_record, record.utility_name))
                else:
                    L.l.critical("Counter sensor [{}] index {} is not defined in Utility table".format(
                        sensor_name, index))
            index += 1
    except Exception as ex:
        L.l.error("Error saving utility update {}".format(ex), exc_info=True)


def unload():
    L.l.info('Utility module unloading')
    # ...
    # thread_pool.remove_callable(template_run.thread_run)
    global initialised
    initialised = False


def init():
    L.l.debug('Utility module initialising')
    dispatcher.connect(__utility_update, signal=Constant.SIGNAL_UTILITY, sender=dispatcher.Any)
    dispatcher.connect(__utility_update_ex, signal=Constant.SIGNAL_UTILITY_EX, sender=dispatcher.Any)
    # thread_pool.add_interval_callable(template_run.thread_run, run_interval_second=60)
    global initialised
    initialised = True
