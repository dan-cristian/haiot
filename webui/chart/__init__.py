import json
from urllib2 import urlopen  # python 2 syntax
import pygal
from datetime import datetime
from flask import render_template, request
from sqlalchemy import func
from main import app, db
from main.logger_helper import Log
from main.admin import models
from common import Constant

__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

initialised = False


@app.route('/dashboard')
def render_dashboard():
    return render_template('dashboard/main.html')


def __config_graph(title):
    config = pygal.Config()
    # config.human_readable = True
    # config.style = pygal.style.DefaultStyle
    # config.disable_xml_declaration = True
    config.title = title
    config.show_x_labels = True
    config.show_minor_x_labels = False
    config.legend_at_bottom = True
    config.x_label_rotation = 90
    config.truncate_label = -1
    # config.x_value_formatter = lambda dt: dt.strftime('%d-%b-%Y %H:%M:%S')
    return config


@app.route('/chart-temp/')
def graph_temperature():
    chart_list = []
    graph_data = None
    sensor_name_list = request.args.get('sensor_name')
    config = __config_graph('Temperature')
    datetimeline = pygal.DateTimeLine(config=config)
    # try:
    for sensor_name in sensor_name_list.split(';'):
        temp_recs = models.SensorHistory().query_filter_all(models.SensorHistory.sensor_name == sensor_name,
                                                            models.SensorHistory.updated_on >= '2016-07-09')
        serie = []
        for i in temp_recs:
            serie.append((i.updated_on, i.temperature))
        datetimeline.add(sensor_name, serie)
        graph_data = datetimeline.render_data_uri()
    chart_list.append(graph_data)
    result = render_template('chart/chart-generic.html', chart_list=chart_list)
    # except Exception, ex:
    #     pass
    return result


@app.route('/chart-utility/')
def graph_water():
    chart_list = []
    graph_data = None
    sensor_name_list = request.args.get('sensor_name')
    config = __config_graph('Utility Counters')
    graph = pygal.Bar(config=config)
    # try:
    for sensor_name in sensor_name_list.split(';'):
        total = 0
        x_labels = []
        y_values = []
        today = datetime(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day - 1)
        #records = models.UtilityHistory().query_filter_all(models.UtilityHistory.sensor_name == sensor_name,
        #                                                   models.UtilityHistory.updated_on >= today)
        records = db.session.query(func.hour(models.UtilityHistory.updated_on).label('updated_on'),
                                   func.sum(models.UtilityHistory.units_delta).label('units_delta')
                                   ).group_by(func.hour(models.UtilityHistory.updated_on)
                                              ).filter(models.UtilityHistory.sensor_name == sensor_name,
                                                       models.UtilityHistory.updated_on >= today).all()
        for i in records:
            x_labels.append(i.updated_on)
            y_values.append(i.units_delta)
            if i.units_delta is not None:
                total = total + i.units_delta
        graph.x_labels = x_labels
        graph.x_labels_major_every = abs(len(x_labels) / 24)
        graph.add("{}, total={}".format(sensor_name, total), y_values)
        graph_data = graph.render_data_uri()
        chart_list.append(graph_data)
    result = render_template('chart/chart-generic.html', chart_list=chart_list)
    # except Exception, ex:
    #    result = render_template('chart/chart-generic.html', chart_list=[], title=ex)
    return result


@app.route('/chart-ups/key_name=<key_name>')
def graph_ups(key_name):
    ups_recs = models.UpsHistory().query_filter_all(models.UpsHistory.input_voltage.isnot(None))
    values = [i.input_voltage for i in ups_recs]
    times = [i.updated_on for i in ups_recs]
    pass


def unload():
    Log.logger.info('Chart module unloading')
    # ...
    # thread_pool.remove_callable(template_run.thread_run)
    global initialised
    initialised = False


def init():
    Log.logger.info('Chart module initialising')
    # thread_pool.add_interval_callable(template_run.thread_run, run_interval_second=60)
    global initialised
    initialised = True
