__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

import json
from urllib2 import urlopen  # python 2 syntax

import pygal
from flask import render_template

from main import app
from main.logger_helper import Log
from main.admin import models

initialised = False

@app.route('/chart-test')
def get_weather_data(date='20140415', state='IA', city='Ames'):
    """
    Date must be in YYYYMMDD
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

    return render_template('chart.html',title=title,bar_chart=bar_chart)


@app.route('/chart-temp')
def get_temperature():
    temp_recs = models.SensorHistory().query_filter_all(models.SensorHistory.sensor_name.in_(['pod fata']))
    values = [i.temperature for i in temp_recs]
    times = [i.updated_on for i in temp_recs]

# create a bar chart
    title = 'Temp pod fata'
    config = pygal.Config()
    #config.human_readable = True
    config.style = pygal.style.DefaultStyle
    config.disable_xml_declaration = True
    config.title = title
    config.show_x_labels = True


    bar_chart = pygal.Line(config)
    bar_chart.x_labels = times
    bar_chart.add('Temp in C', values)

    return render_template('chart/chart.html',title=title,bar_chart=bar_chart)

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