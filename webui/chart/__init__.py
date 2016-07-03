import json
from urllib2 import urlopen  # python 2 syntax
import pygal
from datetime import datetime
from flask import render_template, request
from main import app
from main.logger_helper import Log
from main.admin import models
from common import Constant

__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

initialised = False


@app.route('/chart-test')
def get_weather_data(date='20140415', state='IA', city='Ames'):
    """
    Date must be in YYYYMMDD
    :param city:
    :param state:
    :param date:
    """
    api_key = 'f0126014c2b9ba66'
    url = 'http://api.wunderground.com/api/{key}/history_{date}/q/{state}/{city}.json'
    new_url = url.format(key=api_key,
                         date=date,
                         state=state,
                         city=city)
    result = urlopen(new_url)
    js_string = result.read()
    parsed = json.loads(js_string)
    history = parsed['history']['observations']

    imp_temps = [float(i['tempi']) for i in history]
    times = ['%s:%s' % (i['utcdate']['hour'], i['utcdate']['min']) for i in history]

    # create a bar chart
    title = 'Temps for %s, %s on %s' % (city, state, date)
    bar_chart = pygal.Bar(width=1200, height=600,
                          explicit_size=True, title=title,
                          style=pygal.style.DefaultStyle,
                          disable_xml_declaration=True)
    bar_chart.x_labels = times
    bar_chart.add('Temps in F', imp_temps)

    return render_template('chart-temp.html',title=title,bar_chart=bar_chart)


def __config_graph(title):
    config = pygal.Config()
    # config.human_readable = True
    #config.style = pygal.style.DefaultStyle
    config.disable_xml_declaration = True
    config.title = title
    #config.show_x_labels = True
    config.legend_at_bottom = True
    return config


@app.route('/chart-temp/')
def graph_temperature():
    chart_list = []
    temp_recs = []
    sensor_name_list = request.args.get('sensor_name')
    config = __config_graph('Temperature')
    datetimeline = pygal.DateTimeLine(x_label_rotation=45, truncate_label=-1,
                                      x_value_formatter=lambda dt: dt.strftime('%d-%b-%Y %H:%M:%S'),
                                      config=config)
    try:
        for sensor_name in sensor_name_list.split(';'):
            temp_recs = models.SensorHistory().query_filter_all(models.SensorHistory.sensor_name == sensor_name,
                                                                models.SensorHistory.updated_on >= '2016-07-01')
            serie = []
            for i in temp_recs:
                serie.append((i.updated_on, i.temperature))
            datetimeline.add(sensor_name, serie)
        chart_list.append(datetimeline)
        result = render_template('chart/chart-temp.html', chart_list=chart_list)
    except Exception, ex:
        pass
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
