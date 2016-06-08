from inspect import getmembers, isfunction
from pydispatch import dispatcher
from apscheduler.schedulers.background import BackgroundScheduler
from main.logger_helper import Log
from main import thread_pool
from main.admin import models
from common import Constant

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

scheduler = None
try:
    # fixme: this does not currently work on BusyBox/openwrt routers
    # http://flexget.com/ticket/2741
    scheduler = BackgroundScheduler()
except Exception, ex:
    scheduler = None
    Log.logger.warning('Cannot initialise apscheduler er={}'.format(ex))

if scheduler:
    import rules_run

initialised = False
__func_list = None
__event_list = []


def parse_rules(obj, change):
    global __func_list
    global __event_list
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
                    # calling rule methods with first param type equal to passed object type
                    if type(obj) == type(first_param):
                        # fixme: implement processing queue for rules to avoid sql session errors
                        # __event_list.append([obj, func[0], field_changed_list])
                        result = getattr(rules_run, func[0])(obj=obj, field_changed_list=field_changed_list)
                        Log.logger.debug('Rule returned {}'.format(result))
    except Exception:
        Log.logger.exception('Error parsing rules')

# unused yet
def process_events():
    global __event_list
    for obj_array in __event_list:
        try:
            __event_list.remove(obj_array)
            result = getattr(rules_run, obj_array[1])(obj=obj_array[0], field_changed_list=obj_array[2])
            Log.logger.debug('Rule returned {}'.format(result))
        except Exception, ex:
            Log.logger.critical("Error processing rule event err={}".format(ex), exc_info=1)


def thread_run():
    Log.logger.debug('Processing rules thread_run')
    process_events()
    return 'Processed rules thread_run'


def unload():
    Log.logger.info('Rules module unloading')
    # ...
    thread_pool.remove_callable(thread_run)
    global initialised
    initialised = False


def rule_record_update(record):
    Log.logger.info("Rule definitions changed in db")
    __load_rules_from_db()
    pass


# load rules definition from database into the scheduler object list
def __load_rules_from_db():
    Log.logger.info("Loading scheduled rules definition from db")
    # keep host name default to '' rather than None (which does not work on filter in_)
    try:
        # rule_list = models.Rule.query.filter(models.Rule.host_name.in_([constant.HOST_NAME, ""])).all()
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
    except Exception, ex1:
        Log.logger.error("Unable to load rules from db, err={}".format(ex1, exc_info=True))


# add dynamic rules into db to allow execution via web interface or API
def __add_rules_into_db():
    try:
        if __func_list:
            for func in __func_list:
                if not func[1].func_defaults and not func[1].func_name.startswith('_'):
                    # add this to DB
                    record = models.Rule()
                    record.name = func[1].func_name
                    record.command = func[1].func_name
                    record.host_name = Constant.HOST_NAME
                    record.add_commit_record_to_db()
    except Exception:
        Log.logger.exception('Error adding rules into db')


def init():
    global __func_list
    global scheduler
    Log.logger.info('Rules module initialising')
    if scheduler:
        # load all function entries from hardcoded rule script
        __func_list = getmembers(rules_run, isfunction)
        __add_rules_into_db()
        __load_rules_from_db()
        scheduler.start()
        Log.logger.info('Scheduler started')
    else:
        Log.logger.warning('Rules not initialised as scheduler is not available')
    thread_pool.add_interval_callable(thread_run, run_interval_second=1)
    # connect rules processor for all db chages trigger
    dispatcher.connect(parse_rules, signal=Constant.SIGNAL_DB_CHANGE_FOR_RULES, sender=dispatcher.Any)
    global initialised
    initialised = True
