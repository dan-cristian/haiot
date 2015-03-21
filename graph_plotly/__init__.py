from __builtin__ import isinstance

__author__ = 'dcristian'

import logging
import datetime
import re
import plotly.plotly as py
from plotly import graph_objs
#from plotly.graph_objs import *
import plotly.tools as tls
from main.admin import model_helper
from common import constant

initialised = False
stream_ids = None

def upload_data(obj):
    #FIXME: Add caching and multiple series on same graph
    try:
        axis_x = obj[constant.JSON_PUBLISH_GRAPH_X]
        graph_id = obj[constant.JSON_PUBLISH_GRAPH_ID]
        table = obj[constant.JSON_PUBLISH_TABLE]
        if axis_x in obj and graph_id in obj:
            series_id = obj[graph_id]
            x_val = obj[axis_x]
            if re.search("....-..-..T..:..:..\.......",  x_val):
                x_val = x_val.replace('T',' ')
                x_val = datetime.datetime.strptime(x_val, "%Y-%m-%d %H:%M:%S.%f")
            x = [x_val]
            list_axis_y = obj[constant.JSON_PUBLISH_GRAPH_Y]
            for axis_y in list_axis_y:
                if axis_y in obj:
                    y=[obj[axis_y]]
                    graph_name=table+' '+axis_y + ' ' + series_id
                    trace = graph_objs.Scatter(x=x, y=y, name=series_id)
                    data = graph_objs.Data([trace])
                    py.plot(data, filename=graph_name, fileopt='extend', auto_open=False)

        else:
            logging.warning('Graphable object missing axis X or ID {}'.format(axis_x))
    except Exception, ex:
        logging.warning('Unable to upload graph, err {}'.format(ex))

def unload():
    global initialised
    initialised = False

def init():
    py.sign_in(model_helper.get_param(constant.P_PLOTLY_USERNAME),model_helper.get_param(constant.P_PLOTLY_APIKEY))
    global initialised
    initialised = True
    tls.set_credentials_file(stream_ids=[
        "fmjbljkeot",
        "1piqv8ti6k",
        "24w1i6s6bs",
        "15ytl1hrhc"
    ])
    global stream_ids
    stream_ids = tls.get_credentials_file()['stream_ids']