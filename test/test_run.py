__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from main import L
import plotly.plotly as py
from plotly.graph_objs import *
import plotly.tools as tls
import plotly
from plotly.grid_objs import Column, Grid
import datetime
from common import utils

def test1():
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

def test3():
    column_1 = Column([1, 2, 3], 'column 1')
    column_2 = Column(['a', 'b', utils.get_base_location_now_date()], 'column 2')
    grid = Grid([column_1, column_2])

    unique_url = py.grid_ops.upload(grid, 'grid1', world_readable=True)
    print unique_url

def test4():
    row = [4, 5]
    url=py.grid_ops.append_rows([row], grid_url="https://plot.ly/~dancri77/816") #shortcut
    print url

def test5():
    column_1 = Column([1, 2, 3], 'column 1')
    column_2 = Column(['a', 'b', datetime.datetime.now()], 'column 2') # Tabular data can be numbers, strings, or dates
    grid = Grid([column_1, column_2])
    url = py.grid_ops.upload(grid,
                         'grid example',      # name of the grid in your plotly account
                         world_readable=True, # public or private
                         auto_open=True)      # open the grid in the browser
def thread_run():
    L.l.info('Processing TEST_run')
    #py.sign_in("dancri77", "lw2w6fz9xk")
    #test5()
    #test2()
    return 'Processed TEST_run'