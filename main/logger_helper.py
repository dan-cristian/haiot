import socket

__author__ = 'Dan Cristian <dan.cristian@gmail.com>'


class L:
    def __init__(self):
        pass

    l = None
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
        L.l = logging.getLogger('haiot-' + socket.gethostname())
        L.remote_logger = logging.getLogger('haiot-remote-' + socket.gethostname())
        L.l.setLevel(L.LOGGING_LEVEL)
        L.remote_logger.setLevel(L.LOGGING_LEVEL)

        # init logger to cloud papertrail services
        if (L.SYSLOG_ADDRESS is not None) and (L.SYSLOG_PORT is not None):
            filter_log = ContextFilter()
            L.l.addFilter(filter_log)
            L.remote_logger.addFilter(filter_log)
            syslog_papertrail = logging.handlers.SysLogHandler(address=(L.SYSLOG_ADDRESS, int(L.SYSLOG_PORT)))
            pap_formatter = logging.Formatter(
                '%(asctime)s %(hostname)s haiot %(levelname)s %(module)s:%(funcName)s %(message)s',
                datefmt='%Y-%m-%dT%H:%M:%S')
            syslog_papertrail.setFormatter(pap_formatter)
            L.l.addHandler(syslog_papertrail)
            remote_syslog_papertrail = logging.handlers.SysLogHandler(
                address=(L.SYSLOG_ADDRESS, int(L.SYSLOG_PORT)))
            remote_pap_formatter = logging.Formatter('')
            remote_syslog_papertrail.setFormatter(remote_pap_formatter)
            L.remote_logger.addHandler(remote_syslog_papertrail)
            L.l.info('Initialised syslog with {}:{}'.format(L.SYSLOG_ADDRESS, L.SYSLOG_PORT))

        # log to syslog standard file
        if L.LOG_TO_SYSLOG:
            try:
                handler = logging.handlers.SysLogHandler(address='/dev/log')
                L.l.addHandler(handler)
                L.l.info('Syslog program started at {}'.format(socket.gethostname()))
            except Exception as ex:
                try:
                    ntl = logging.handlers.NTEventLogHandler(appname='haiot')
                    L.l.addHandler(ntl)
                except Exception as ex:
                    print 'Unable to init syslog handler err={}'.format(ex)
        else:
            if L.LOG_FILE is not None:
                file_handler = logging.handlers.RotatingFileHandler(L.LOG_FILE, maxBytes=1024 * 1024 * 1, backupCount=3)
                L.l.addHandler(file_handler)

        L.l.info('Logging level is {}'.format(L.LOGGING_LEVEL))

        # todo: remove annoying info messages, but only for few cases, efect unclear
        logging.getLogger("requests").setLevel(logging.INFO)

        # propagate False stops log writes to standard output. Set to True to show log in Pycharm
        if L.RUN_IN_LIVE:
            L.l.info('Logger is set to live mode, disabling log propagation')
        L.l.propagate = not L.RUN_IN_LIVE
    

