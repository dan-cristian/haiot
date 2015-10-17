__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from inspect import getmembers, isfunction

from pydispatch import dispatcher
from apscheduler.schedulers.background import BackgroundScheduler

from main.logger_helper import Log
from main import thread_pool
from main.admin import models
from common import Constant

scheduler = None
try:
    #this does not currently work on BusyBox routers
    #http://flexget.com/ticket/2741
    scheduler = BackgroundScheduler()
except Exception,ex:
    scheduler = None
    Log.logger.warning('Cannot initialise apscheduler er={}'.format(ex))

if scheduler:
    import rules_run

initialised = False
__func_list = None


def parse_rules(obj, change):
    global __func_list
    # executed on all db value changes
    Log.logger.debug('Received obj={} change={} for rule parsing'.format(obj, change))
    try:
        # extract only changed fields
        if hasattr(obj, 'last_commit_field_changed_list'):
            field_changed_list = obj.last_commit_field_changed_list
        else:
            field_changed_list = []
        if __func_list:
            for func in __func_list:
                if func[1].func_defaults and len(func[1].func_defaults) > 0:
                    first_param = func[1].func_defaults[0]
                    #calling rule methods with first param type equal to passed object type
                    if type(obj) == type(first_param):
                        result = getattr(rules_run, func[0])(obj=obj, field_changed_list=field_changed_list)
                        Log.logger.debug('Rule returned {}'.format(result))
    except Exception:
        Log.logger.exception('Error parsing rules')

def thread_run():
    Log.logger.debug('Processing rules thread_run')
    return 'Processed rules thread_run'

def unload():
    Log.logger.info('Rules module unloading')
    #...
    thread_pool.remove_callable(thread_run)
    global initialised
    initialised = False

def rule_record_update(record):
    Log.logger.info("Rule definitions changed in db")
    __load_rules_from_db()
    pass

def __load_rules_from_db():
    Log.logger.info("Loading rule definition from db")
    #keep host name default to '' rather than None (which does not work on filter in_)
    try:
        #rule_list = models.Rule.query.filter(models.Rule.host_name.in_([constant.HOST_NAME, ""])).all()
        rule_list = models.Rule().query_filter_all(models.Rule.host_name.in_([Constant.HOST_NAME, ""]))
        scheduler.remove_all_jobs()
        for rule in rule_list:
            method_to_call = getattr(rules_run, rule.command)
            if rule.is_active:
                year = rule.year if rule.year != '' else None
                month = rule.month if rule.month != '' else None
                day = rule.day if rule.day != '' else None
                week = rule.week if rule.week != '' else None
                day_of_week = rule.day_of_week if rule.day_of_week != '' else None
                hour = rule.hour if rule.hour != '' else None
                minute = rule.minute if rule.minute != '' else None
                second = rule.second if rule.second != '' else None
                scheduler.add_job(method_to_call, 'cron', year=year, month=month, day=day, week=week,
                                  day_of_week=day_of_week, hour=hour, minute=minute, second=second)
            else:
                Log.logger.info("Rule {} is marked as inactive, skipping".format(rule.command))
    except Exception, ex:
        Log.logger.error("Unable to load rules from db, err={}".format(ex, exc_info=True))

def init():
    global __func_list
    global scheduler
    Log.logger.info('Rules module initialising')
    if scheduler:
        #load all function entries from hardcoded rule script
        __func_list = getmembers(rules_run, isfunction)
        __load_rules_from_db()
        scheduler.start()
        Log.logger.info('Scheduler started')
    else:
        Log.logger.warning('Rules not initialised as scheduler is not available')
    thread_pool.add_interval_callable(thread_run, run_interval_second=60)
    #connect rules processor for all db chages trigger
    dispatcher.connect(parse_rules, signal=Constant.SIGNAL_DB_CHANGE_FOR_RULES, sender=dispatcher.Any)
    global initialised
    initialised = True

