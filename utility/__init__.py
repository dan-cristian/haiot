from main.logger_helper import Log
from main import thread_pool
from common import Constant
from pydispatch import dispatcher
from main.admin import models

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


initialised = False


def __utility_update(sensor_name, units_delta_a, units_delta_b, total_units_a, total_units_b):
    index = 0
    for delta in [units_delta_a, units_delta_b]:
        if delta:
            record = models.Utility(sensor_name=sensor_name)
            current_record = models.Utility.query.filter_by(sensor_name=sensor_name, sensor_index=index).first()
            if current_record:
                record.sensor_index = index
                record.units_delta = delta / (current_record.ticks_per_unit * 1.0)  # force float operation
                if not current_record.units_total:
                    current_record.units_total = 0.0
                # force save for history recording
                if current_record:
                    current_record.units_delta = 0.0
                record.units_total = 0.0 + current_record.units_total + record.units_delta
                record.save_changed_fields(current_record=current_record, new_record=record,
                                           notify_transport_enabled=True, save_to_graph=True)
            else:
                Log.logger.critical("Counter sensor [{}] index {} is not defined in Utility table".format(sensor_name,
                                                                                                          index))
        index += 1


def unload():
    Log.logger.info('Utility module unloading')
    # ...
    # thread_pool.remove_callable(template_run.thread_run)
    global initialised
    initialised = False


def init():
    Log.logger.info('Utility module initialising')
    dispatcher.connect(__utility_update, signal=Constant.SIGNAL_UTILITY, sender=dispatcher.Any)
    # thread_pool.add_interval_callable(template_run.thread_run, run_interval_second=60)
    global initialised
    initialised = True
