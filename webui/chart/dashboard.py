import pygal
from pygal import style
from flask import render_template, request
from storage.sqalc import models
from main import app
from common import utils
import time

def __config_graph():
    config = pygal.Config()
    config.style = style.DarkStyle
    # config.human_readable = True
    # config.show_x_labels = True
    # config.legend_at_bottom = True
    return config


@app.route('/dashboard')
def render_dashboard():

    #sensors = models.Sensor().query_filter_all(models.Sensor.temperature.isnot(None))
    sensors = models.Sensor.query.order_by(models.Sensor.sensor_name).filter(
        models.Sensor.temperature.isnot(None)).all()
    config = __config_graph()
    config.height = 400
    config.explicit_size = True
    config.print_values = True
    config.print_labels = True
    config.show_legend = True
    config.style.value_colors = '#53A0E8'
    # ??
    # config.margin_left = 0

    chart = pygal.Bar(config=config)
    chart.title = 'Temperature'
    now_date = utils.get_base_location_now_date()
    for sensor in sensors:
        age = (now_date - sensor.updated_on).total_seconds()
        age_nice = time.strftime('%H:%M:%S', time.gmtime(age))
        if age <= 300:
            stroke_width = 3 * (300 - age) / 100
        else:
            stroke_width = 0
        chart.add("{}".format(age_nice),
                  [{'value': sensor.temperature, 'label': sensor.sensor_name,
                    'style': 'stroke: red; stroke-width: {}'.format(int(stroke_width))}])
    graph_temperature = chart.render(is_unicode=True)

    relays = models.ZoneHeatRelay.query.order_by(models.ZoneHeatRelay.heat_pin_name).all()
    config = __config_graph()
    config.height = 150
    config.explicit_size = True
    #config.style = style.DefaultStyle
    config.print_values = True
    config.print_labels = False
    config.show_legend = True
    config.print_zeroes = False
    config.show_y_labels = False
    config.show_x_guides = False
    config.show_y_guides = False
    config.x_label_rotation = 1
    config.show_x_labels = True
    dot_chart = pygal.Dot(x_label_rotation=30, config=config)
    y_values = []
    x_values = []
    for relay in relays:
        age_mins = int(min((now_date - relay.updated_on).total_seconds() / 60, 60))
        if relay.heat_is_on is None:
            dot_size = 0
        else:
            sign = relay.heat_is_on - 1 + 1 * relay.heat_is_on
            dot_size = sign * age_mins
        y_values.append(dot_size)
        x_values.append(relay.heat_pin_name)
        # dot_chart.add(relay.heat_pin_name, [{'value': dot_size, 'label': relay.heat_pin_name}])
    dot_chart.x_labels = x_values
    dot_chart.add('Heat', y_values)
    graph_heat = dot_chart.render(is_unicode=True)

    return render_template('dashboard/main.html', graph_temperature=graph_temperature, graph_heat=graph_heat)


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