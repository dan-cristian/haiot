import socket

__author__ = 'Dan Cristian <dan.cristian@gmail.com>'


class Log:
    def __init__(self):
        pass

    logger = None
    # KEY setting, this filters out message priority from being logged
    LOGGING_LEVEL = None
    LOG_FILE = None
    # logging output will go to syslog
    LOG_TO_SYSLOG = False
    # on systems without remote logging access like openshift use transport to perform logging by a proxy node
    LOG_TO_TRANSPORT = False
    # this logger is used to log remote logs messages using a different formatter
    remote_logger = None
    # this is to enable remote syslog like papertrail
    SYSLOG_ADDRESS = None
    SYSLOG_PORT = None
    # reduce amount of logging when running in LIVE prod
    RUN_IN_LIVE = False

    @staticmethod
    def init_logging():
        import logging
        import logging.handlers

        class ContextFilter(logging.Filter):
            hostname = socket.gethostname()

            def filter(self, record):
                record.hostname = ContextFilter.hostname
                return True

        # global LOGGING_LEVEL, LOG_FILE, LOG_TO_SYSLOG, SYSLOG_ADDRESS, SYSLOG_PORT, RUN_IN_LIVE
        # global logger, remote_logger
        # set logging general formatting
        logging.basicConfig(format='%(asctime)s haiot %(levelname)s %(module)s:%(funcName)s %(message)s')
        # %(threadName)s
        Log.logger = logging.getLogger('haiot-' + socket.gethostname())
        Log.remote_logger = logging.getLogger('haiot-remote-' + socket.gethostname())
        Log.logger.setLevel(Log.LOGGING_LEVEL)
        Log.remote_logger.setLevel(Log.LOGGING_LEVEL)

        # init logger to cloud papertrail services
        if (Log.SYSLOG_ADDRESS is not None) and (Log.SYSLOG_PORT is not None):
            filter_log = ContextFilter()
            Log.logger.addFilter(filter_log)
            Log.remote_logger.addFilter(filter_log)
            syslog_papertrail = logging.handlers.SysLogHandler(address=(Log.SYSLOG_ADDRESS, int(Log.SYSLOG_PORT)))
            pap_formatter = logging.Formatter(
                '%(asctime)s %(hostname)s haiot %(levelname)s %(module)s:%(funcName)s %(message)s',
                datefmt='%Y-%m-%dT%H:%M:%S')
            syslog_papertrail.setFormatter(pap_formatter)
            Log.logger.addHandler(syslog_papertrail)
            remote_syslog_papertrail = logging.handlers.SysLogHandler(
                address=(Log.SYSLOG_ADDRESS, int(Log.SYSLOG_PORT)))
            remote_pap_formatter = logging.Formatter('')
            remote_syslog_papertrail.setFormatter(remote_pap_formatter)
            Log.remote_logger.addHandler(remote_syslog_papertrail)
            Log.logger.info('Initialised syslog with {}:{}'.format(Log.SYSLOG_ADDRESS, Log.SYSLOG_PORT))

        # log to syslog standard file
        if Log.LOG_TO_SYSLOG:
            try:
                handler = logging.handlers.SysLogHandler(address='/dev/log')
                Log.logger.addHandler(handler)
                Log.logger.info('Syslog program started at {}'.format(socket.gethostname()))
            except Exception, ex:
                try:
                    ntl = logging.handlers.NTEventLogHandler(appname='haiot')
                    Log.logger.addHandler(ntl)
                except Exception, ex:
                    print 'Unable to init syslog handler err={}'.format(ex)
        else:
            if Log.LOG_FILE is not None:
                file_handler = logging.handlers.RotatingFileHandler(Log.LOG_FILE, maxBytes=1024*1024*1, backupCount=3)
                Log.logger.addHandler(file_handler)

        Log.logger.info('Logging level is {}'.format(Log.LOGGING_LEVEL))

        # todo: remove annoying info messages, but only for few cases, efect unclear
        logging.getLogger("requests").setLevel(logging.INFO)

        # propagate False stops log writes to standard output. Set to True to show log in Pycharm
        if Log.RUN_IN_LIVE:
            Log.logger.info('Logger is set to live mode, disabling log propagation')
        Log.logger.propagate = not Log.RUN_IN_LIVE


