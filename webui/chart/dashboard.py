import pygal
from pygal import style
from flask import render_template, request
from main.admin import models
from main import app
from common import utils


def __config_graph():
    config = pygal.Config()
    # config.human_readable = True
    # config.show_x_labels = True
    # config.legend_at_bottom = True
    return config


@app.route('/dashboard')
def render_dashboard():

    #sensors = models.Sensor().query_filter_all(models.Sensor.temperature.isnot(None))
    sensors = models.Sensor.query.order_by(models.Sensor.sensor_name).filter(models.Sensor.temperature.isnot(None)).all()
    config = __config_graph()
    config.print_values = True
    config.print_labels = True
    config.show_legend = True
    config.style = style.DarkStyle
    config.style.value_colors = '#53A0E8'
    # ??
    # config.margin_left = 0

    chart = pygal.Bar(config=config)
    chart.title = 'Temperature'
    now_date = utils.get_base_location_now_date()
    for sensor in sensors:
        age = (now_date - sensor.updated_on).total_seconds()
        chart.add("{}s".format(int(age)),
                  [{'value': sensor.temperature, 'label': sensor.sensor_name}])
    graph = chart.render(is_unicode=True)
    return render_template('dashboard/main.html', graph=graph, sensors=sensors)


@app.route('/chart-sensor-now/')
def graph_sensor_now():
    line_chart = pygal.Bar()
    line_chart.title = 'Browser usage evolution (in %)'
    line_chart.x_labels = map(str, range(2002, 2013))
    line_chart.add('Firefox', [None, None, 0, 16.6, 25, 31, 36.4, 45.5, 46.3, 42.8, 37.1])
    line_chart.add('Chrome', [None, None, None, None, None, None, 0, 3.9, 10.8, 23.8, 35.3])
    line_chart.add('IE', [85.8, 84.6, 84.7, 74.5, 66, 58.6, 54.7, 44.8, 36.2, 26.6, 20.1])
    line_chart.add('Others', [14.2, 15.4, 15.3, 8.9, 9, 10.4, 8.9, 5.8, 6.7, 6.8, 7.5])
    return line_chart.render()
    #line_chart.render_to_file('webui/static/temp/chart-now.svg')
    #return send_file("webui/static/temp/chart-now.svg", mimetype='image/svg+xml')