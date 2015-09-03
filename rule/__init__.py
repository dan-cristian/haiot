__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from inspect import getmembers, isfunction
from pydispatch import dispatcher
from main import logger
from main.admin import thread_pool
from main.admin import models
from common import constant
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = None
try:
    #this does not currently work on BusyBox routers
    #http://flexget.com/ticket/2741
    scheduler = BackgroundScheduler()
except Exception,ex:
    scheduler = None
    logger.warning('Cannot initialise apscheduler er={}'.format(ex))

if scheduler:
    import rules_run

initialised = False
__func_list = None

def parse_rules(obj, change):
    global __func_list
    #executed on all db value changes
    logger.debug('Received obj={} change={} for rule parsing'.format(obj, change))
    try:
        #extract only changed fields
        if hasattr(obj,'last_commit_field_changed_list'):
            field_changed_list = obj.last_commit_field_changed_list
        else:
            field_changed_list = []
        for func in __func_list:
            if func[1].func_defaults and len(func[1].func_defaults) > 0:
                first_param = func[1].func_defaults[0]
                #calling rule methods with first param type equal to passed object type
                if type(obj) == type(first_param):
                    result = getattr(rules_run, func[0])(obj=obj, field_changed_list=field_changed_list)
                    logger.debug('Rule returned {}'.format(result))
    except Exception, ex:
        logger.critical('Error parsing rules: {}', format(ex))

def thread_run():
    logger.debug('Processing rules thread_run')
    return 'Processed rules thread_run'

def unload():
    logger.info('Rules module unloading')
    #...
    thread_pool.remove_callable(rules_run.thread_run)
    global initialised
    initialised = False

def rule_record_update(record):
    logger.info("Rule definitions changed in db")
    __load_rules_from_db()
    pass

def __load_rules_from_db():
    logger.info("Loading rule definition from db")
    #keep host name default to '' rather than None (which does not work on filter in)
    '''
    rule_list = models.Rule.query.filter(models.Rule.host_name.in_([constant.HOST_NAME, ""])).all()
    scheduler.remove_all_jobs()
    for rule in rule_list:
        method_to_call = getattr(rules_run, rule.command)
        scheduler.add_job(method_to_call, 'cron', year=rule.year, month=rule.month, day=rule.day, week=rule.week,
                               day_of_week=rule.day_of_week, hour=rule.hour, minute=rule.minute, second=rule.second)
    '''

def init():
    global __func_list
    global scheduler
    logger.info('Rules module initialising')
    if scheduler:
        #load all function entries from hardcoded rule script
        __func_list = getmembers(rules_run, isfunction)
        __load_rules_from_db()
        scheduler.start()
        logger.info('Scheduler started')
    else:
        logger.warning('Rules not initialised as scheduler is not available')
    thread_pool.add_interval_callable(thread_run, run_interval_second=60)
    #connect rules processor for all db chages trigger
    dispatcher.connect(parse_rules, signal=constant.SIGNAL_DB_CHANGE_FOR_RULES, sender=dispatcher.Any)
    global initialised
    initialised = True

