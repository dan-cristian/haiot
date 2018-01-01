import json
from urllib2 import urlopen  # python 2 syntax
import pygal
from datetime import datetime, timedelta
from flask import render_template, request, send_file
from sqlalchemy import func, extract
from main import app, db
from main.logger_helper import L
from main.admin import models
from common import Constant, utils
import dashboard

__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

initialised = False
_period_list = ['year', 'month', 'day', 'hour']

def __config_graph(title, start, end):
    config = pygal.Config()
    config.human_readable = True
    # config.style = pygal.style.DefaultStyle
    # config.disable_xml_declaration = True
    config.title = title
    config.show_x_labels = True
    # config.show_minor_x_labels = False
    config.legend_at_bottom = True
    # config.x_label_rotation = 90
    config.truncate_label = -1
    # config.x_value_formatter = lambda dt: dt.strftime('%d-%b-%Y %H:%M:%S')
    config.x_title = "({}) - ({})".format(start.strftime('%d-%b-%Y %H:%M:%S'), end.strftime('%d-%b-%Y %H:%M:%S'))
    return config


def _get_utility_records(group_by, function, sensor_name, start, end):
    records = db.session.query(extract(group_by, models.UtilityHistory.updated_on).label('date'),
                               function(models.UtilityHistory.units_delta).label('units_delta')
                               ).group_by('date').filter(models.UtilityHistory.sensor_name == sensor_name,
                                                         models.UtilityHistory.updated_on >= start,
                                                         models.UtilityHistory.updated_on <= end).all()
    '''
    records = db.session.query(func.hour(models.UtilityHistory.updated_on).label('updated_on'),
                               func.sum(models.UtilityHistory.units_delta).label('units_delta')
                               ).group_by(func.hour(models.UtilityHistory.updated_on)
                                          ).filter(models.UtilityHistory.sensor_name == sensor_name,
                                                   models.UtilityHistory.updated_on >= today).all()
    '''
    return records


def _get_sensor_records(group_by, function, sensor_name, start, end, sensor_type, group_by_prefix):
    if sensor_type == 'temperature':
        field = models.SensorHistory.temperature
    elif sensor_type == 'humidity':
        field = models.SensorHistory.humidity
    elif sensor_type == 'vad':
        field = models.SensorHistory.vad
    else:
        L.l.warning("Unknown sensor type {}".format(sensor_type))
        field = models.SensorHistory.temperature

    records = db.session.query(
        extract(group_by_prefix, models.SensorHistory.updated_on).label('prefix'),
        extract(group_by, models.SensorHistory.updated_on).label('date'),
        function(field).label('value')).group_by('prefix', 'date').filter(
        models.SensorHistory.sensor_name == sensor_name,
        models.SensorHistory.updated_on >= start,
        models.SensorHistory.updated_on <= end).all()
    '''
    records = db.session.query(func.hour(models.UtilityHistory.updated_on).label('updated_on'),
                               func.sum(models.UtilityHistory.units_delta).label('units_delta')
                               ).group_by(func.hour(models.UtilityHistory.updated_on)
                                          ).filter(models.UtilityHistory.sensor_name == sensor_name,
                                                   models.UtilityHistory.updated_on >= today).all()
    '''
    return records


def _get_interval(args):
    """get graphic sampling dates from http request"""
    sensor_name_list = request.args.get('sensor_name')

    if request.args.get('temperature') is not None:
        sensor_type = 'temperature'
    elif request.args.get('humidity') is not None:
        sensor_type = 'humidity'
    elif request.args.get('vad') is not None:
        sensor_type = 'vad'
    elif request.args.get('electricity') is not None:
        sensor_type = 'electricity'
    elif request.args.get('water') is not None:
        sensor_type = 'water'
    else:
        L.l.warning("Unspecified sensor type, defaulting to temperature")
        sensor_type = 'temperature'

    '''
    year = args.get('year')
    month = args.get('month')
    day = args.get('day')
    hour = args.get('hour')
    if year is not None or month is not None or day is not None or hour is not None:
        if year is None:
            year = datetime.now().year
        else:

            month = int(month) if month is not None else datetime.now().month
            day = int(day) if day is not None else datetime.now().day
            hour = int(hour) if hour is not None else datetime.now().hour

        start = datetime(year=year, month=month, day=day, hour=hour)
        end = start
    else:
    '''
    if args.get('today') is not None:
        start = datetime(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)
        end = datetime.now()
    elif args.get('yesterday') is not None:
        start = datetime(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day - 1)
        end = start + timedelta(days=1)
    elif args.get('this_hour') is not None:
        start = datetime(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day,
                         hour=datetime.now().hour)
        end = datetime.now()
    elif args.get('this_month') is not None:
        start = datetime(year=datetime.now().year, month=datetime.now().month, day=1)
        end = datetime.now()
    elif args.get('last_month') is not None:
        start = datetime(year=datetime.now().year, month=datetime.now().month - 1, day=1)
        end = utils.add_months(start, 1)
    elif args.get('this_year') is not None:
        start = datetime(year=datetime.now().year, month=1, day=1)
        end = datetime.now()
    else:
        start = datetime(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)
        end = datetime.now()

    if args.get('group_by') is not None:
        group_by = args.get('group_by')
    else:
        group_by = 'hour'

    # get previous period for grouping
    global _period_list
    group_by_prefix = group_by  # default value
    for i in range(0, len(_period_list)):
        if _period_list[i] == group_by:
            if i > 0:
                group_by_prefix = _period_list[i-1]

    function_name_list = args.get('function')
    function_list = []
    if function_name_list is not None:
        for function in function_name_list .split(';'):
            if function == 'sum':
                function_list.append(func.sum)
            elif function == 'count':
                function_list.append(func.count)
            elif function == 'max':
                function_list.append(func.max)
            elif function == 'min':
                function_list.append(func.min)
            elif function == 'avg':
                function_list.append(func.avg)
            else:
                function_list.append(func.avg)
                L.l.warning("Unknown function {}, set default as AVG".format(args.get('function')))
    else:
        function_list.append(func.avg)
        L.l.warning("Unspecified function, set default as AVG")
    return sensor_name_list, start, end, group_by, function_list, sensor_type, group_by_prefix


@app.route('/chart-sensor/')
def graph_temperature():
    chart_list = []
    graph_data = None
    sensor_name_list, start, end, group_by, function_list, sensor_type, group_by_prefix = _get_interval(request.args)
    config = __config_graph("{} by {}".format(sensor_type, group_by), start, end)
    config.x_value_formatter = lambda dt: dt.strftime('%S')
    datetimeline = pygal.DateTimeLine(config=config)
    for sensor_name in sensor_name_list.split(';'):
        for function in function_list:
            records = _get_sensor_records(group_by, function, sensor_name, start, end, sensor_type, group_by_prefix)
            # if len(records) > 20:
            #    datetimeline.show_minor_x_labels = False
            #    datetimeline.x_labels_major_every = abs(len(records)/20)
            serie = []
            for i in records:
                serie.append((100 * i.prefix + i.date, i.value))
            datetimeline.add("{} [{}]".format(sensor_name, function._FunctionGenerator__names[0]), serie)
    graph_data = datetimeline.render_data_uri()
    chart_list.append(graph_data)
    result = render_template('chart/chart-generic.html', chart_list=chart_list)
    return result, 'buba mica buba mare'


@app.route('/chart-utility/')
def graph_water():
    chart_list = []
    sensor_name_list, start, end, group_by, function_list, sensor_type, group_by_prefix = _get_interval(request.args)
    config = __config_graph("{} by {}".format(sensor_type, group_by), start, end)
    graph = pygal.Bar(config=config)
    for sensor_name in sensor_name_list.split(';'):
        for function in function_list:
            total = 0
            x_labels = []
            y_values = []
            records = _get_utility_records(group_by, function, sensor_name, start, end)
            for i in records:
                x_labels.append(i.date)
                y_values.append(i.units_delta)
                if i.units_delta is not None:
                    total = total + i.units_delta
            graph.x_labels = x_labels
            total = round(total, 2)
            graph.add("{} [{}], total={}".format(sensor_name, function._FunctionGenerator__names[0], total), y_values)
    graph_data = graph.render_data_uri()
    chart_list.append(graph_data)
    result = render_template('chart/chart-generic.html', chart_list=chart_list)
    return result


@app.route('/chart-ups/key_name=<key_name>')
def graph_ups(key_name):
    ups_recs = models.UpsHistory().query_filter_all(models.UpsHistory.input_voltage.isnot(None))
    values = [i.input_voltage for i in ups_recs]
    times = [i.updated_on for i in ups_recs]
    pass


def unload():
    L.l.info('Chart module unloading')
    # ...
    # thread_pool.remove_callable(template_run.thread_run)
    global initialised
    initialised = False


def init():
    L.l.info('Chart module initialising')
    # thread_pool.add_interval_callable(template_run.thread_run, run_interval_second=60)
    global initialised
    initialised = True
