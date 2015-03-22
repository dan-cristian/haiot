__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import logging
from plotly.graph_objs import *
import plotly.plotly as py
from plotly import graph_objs

def test1():
    py.sign_in("dancri77", "lw2w6fz9xk")

    trace0 = graph_objs.Scatter(
        x=[2],
        y=[3],
        name='cucu2'
    )
    trace1 = graph_objs.Scatter(
        x=[3],
        y=[2],
        name='cucu1'
    )
    data = graph_objs.Data([trace0, trace1])

    # Take 1: if there is no data in the plot, 'extend' will create new traces.
    plot_url = py.plot(data, filename='extend plot 1', fileopt='extend')

def test2():

    trace0 = Scatter(
        x=[7, 8],
        y=[2, 1]
    )

    trace1 = Scatter(
        x=[9, 10],
        y=[3, 2]
    )

    trace2 = Scatter(
        x=[11, 12],
        y=[4, 3]
    )

    data = Data([trace0, trace1, trace2])

    # Take 2: extend the traces on the plot with the data in the order supplied.
    plot_url = py.plot(data, filename='extend plot', fileopt='extend')


def thread_run():
    logging.info('Processing TEST_run')
    test1()
    #test2()
    return 'Processed TEST_run'