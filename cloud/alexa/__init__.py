from main.logger_helper import L
import wemo_run


__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

initialised = False


def unload():
    L.l.info('Alexa module unloading')
    wemo_run.unload()
    global initialised
    initialised = False


def init():
    L.l.info('Alexa module initialising')
    wemo_run.init()
    global initialised
    initialised = True
