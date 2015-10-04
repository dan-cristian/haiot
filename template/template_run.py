__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from main.logger_helper import Log

def thread_run():
    Log.logger.debug('Processing template_run')
    return 'Processed template_run'