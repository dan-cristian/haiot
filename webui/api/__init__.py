__author__ = 'Dan Cristian <dan.cristian@gmail.com>'


from main.logger_helper import L
from webui.api import api_v1

initialised = False


def unload():
    L.l.info('API module unloading')
    global initialised
    initialised = False


def init():
    L.l.debug('API module initialising')
    global initialised
    initialised = True
