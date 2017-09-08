from main.logger_helper import Log
import wemo_run


__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

initialised = False


def unload():
    Log.logger.info('Alexa module unloading')
    wemo_run.unload()
    global initialised
    initialised = False


def init():
    Log.logger.info('Alexa module initialising')
    wemo_run.init()
    global initialised
    initialised = True
