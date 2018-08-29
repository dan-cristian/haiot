from inspect import getmembers, isfunction
import imp
import os
from pydispatch import dispatcher
from apscheduler.schedulers.background import BackgroundScheduler
from main.logger_helper import L
from main import thread_pool
from main.admin import models
from common import Constant

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

scheduler = None
try:
    # fixme: this does not currently work on BusyBox/openwrt routers
    # http://flexget.com/ticket/2741
    scheduler = BackgroundScheduler()
except Exception as ex:
    scheduler = None
    L.l.warning('Cannot initialise apscheduler er={}'.format(ex))

if scheduler:
    import rules_run, rule_common

initialised = False
__func_list = None
__rules_timestamp = None


class P:
    event_list = []


class Obj:
    pass


def parse_rules(obj, change):
    """ running rule method corresponding with obj type """
    global __func_list
    global __event_list
    # executed on all db value changes
    L.l.debug('Received obj={} change={} for rule parsing'.format(obj, change))
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
                        record = Obj()
                        for attr, value in obj.__dict__.iteritems():
                            setattr(record, attr, value)
                        P.event_list.append([record, func[0], field_changed_list])
                        # optimises CPU, but ensure each function name is unique in rule file
                        break
    except Exception as ex:
        L.l.exception('Error parsing rules, ex={}'.format(ex))


def process_events():
    for obj in list(P.event_list):
        try:
            result = getattr(rules_run, obj[1])(obj=obj[0], field_changed_list=obj[2])
            L.l.debug('Rule returned {}'.format(result))
            P.event_list.remove(obj)
        except Exception as ex:
            L.l.critical("Error processing rule event err={}".format(ex), exc_info=1)


def thread_run():
    process_events()
    return 'Processed rules thread_run'


def unload():
    L.l.info('Rules module unloading')
    # ...
    thread_pool.remove_callable(thread_run)
    global initialised
    initialised = False


def record_update(record):
    L.l.info("Rule definitions changed in db, ignoring for now")
    # __load_rules_from_db()
    pass


# load rules definition from database into the scheduler object list
# NOT USED ANYMORE!
def __load_rules_from_db():
    L.l.info("Loading scheduled rules definition from db")
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
                L.l.info("Rule {} is marked as inactive, skipping".format(rule.command))
    except Exception as ex1:
        L.l.error("Unable to load rules from db, err={}".format(ex1, exc_info=True))


def get_alexawemo_rules():
    ALEXA_RULE_PREFIX = 'alexawemo_'
    alexa_rules = {}
    # parse rules to find alexawemo specific ones
    __func_list = getmembers(rules_run, isfunction)
    if __func_list:
        for func in __func_list:
            if not func[1].func_defaults and not func[1].func_name.startswith('_'):
                # add this to DB
                func_name = func[0]
                if func_name.startswith(ALEXA_RULE_PREFIX):
                    # cmd = func_name.split(ALEXA_RULE_PREFIX)[1]
                    name_list = func_name.split('_on')
                    if len(name_list) == 2:
                        dev_name = name_list[0].split(ALEXA_RULE_PREFIX)[1]
                        if dev_name in alexa_rules.keys():
                            # alexa_rules[dev_name][0] = func[1]
                            alexa_rules[dev_name][0] = func_name
                        else:
                            # alexa_rules[dev_name] = [func[1], 0]
                            alexa_rules[dev_name] = [func_name, None]
                    else:
                        name_list = func_name.split('_off')
                        if len(name_list) == 2:
                            dev_name = name_list[0].split(ALEXA_RULE_PREFIX)[1]
                            if dev_name in alexa_rules.keys():
                                # alexa_rules[dev_name][1] = func[1]
                                alexa_rules[dev_name][1] = func_name
                            else:
                                # alexa_rules[dev_name] = [None, func[1]]
                                alexa_rules[dev_name] = [None, func_name]
    return alexa_rules


def execute_rule(rule_name):
    rule = models.Rule().query_filter_first(models.Rule.command.in_([rule_name]))
    if rule is not None:
        return rules_run.execute_macro(rule, force_exec=True)
    else:
        L.l.warning("No rule found in db with name {}".format(rule_name))
        return False


# add dynamic rules into db and sceduler to allow execution via web interface or API
def __add_rules_into_db():
    try:
        global __func_list
        # load all function entries from hardcoded rule script
        __func_list = getmembers(rules_run, isfunction)
        scheduler.remove_all_jobs()
        models.Rule().delete()
        if __func_list:
            for func in __func_list:
                if not func[1].func_defaults and not func[1].func_name.startswith('_'):
                    # add this to DB
                    record = models.Rule()
                    record.name = func[1].func_name
                    record.command = func[1].func_name
                    record.host_name = Constant.HOST_NAME
                    comment = func[1].__doc__
                    if comment:
                        pairs = dict(u.split("=") for u in comment.split(";"))
                        if "year" in pairs.keys():
                            record.year = pairs["year"]
                        else:
                            record.year = "*"
                        if "month" in pairs.keys():
                            record.month = pairs["month"]
                        else:
                            record.month = "*"
                        if "week" in pairs.keys():
                            record.week = pairs["week"]
                        else:
                            record.week = "*"
                        if "day_of_week" in pairs.keys():
                            record.day_of_week = pairs["day_of_week"]
                        else:
                            record.day_of_week = "*"
                        if "day" in pairs.keys():
                            record.day = pairs["day"]
                        else:
                            record.day = "*"
                        if "hour" in pairs.keys():
                            record.hour = pairs["hour"]
                        else:
                            record.hour = "*"
                        if "minute" in pairs.keys():
                            record.minute = pairs["minute"]
                        else:
                            record.minute = "*"
                        if "second" in pairs.keys():
                            record.second = pairs["second"]
                        else:
                            record.second = "0"
                        if "is_active" in pairs.keys():
                            record.is_active = pairs["is_active"]
                        if "is_async" in pairs.keys():
                            record.is_async= pairs["is_async"]
                        if record.is_active is "1":
                            scheduler.add_job(func[1], trigger='cron', year=record.year, month=record.month,
                                              day=record.day, week=record.week, day_of_week=record.day_of_week,
                                              second=record.second, hour=record.hour, minute=record.minute,
                                              max_instances=1, misfire_grace_time=None)
                            L.l.info("Adding rule {}:{} to scheduler ".format(record.name, record.command))
                    record.add_commit_record_to_db()
    except Exception as ex:
        L.l.exception('Error adding rules into db {}'.format(ex), exc_info=1)


def _get_stamp():
    path = rules_run.__file__
    path = path.replace(".pyc", ".py")
    return os.path.getmtime(path)


def reload_rules():
    global __rules_timestamp
    new_stamp = _get_stamp()
    if new_stamp != __rules_timestamp:
        L.l.info('Reloading rules as timestamp changed, {} != {}'.format(__rules_timestamp, new_stamp))
        imp.reload(rules_run)
        __add_rules_into_db()
        __rules_timestamp = new_stamp
        rules_run.test_code()
    # else:
    #    Log.logger.info('Reloading {} skip timestamp {} != {}'.format(path, __rules_timestamp, new_stamp))


def init():
    global scheduler
    L.l.debug('Rules module initialising')
    if scheduler:
        __add_rules_into_db()
        # __load_rules_from_db()
        scheduler.start()
        L.l.info('Scheduler started')
        global __rules_timestamp
        __rules_timestamp = _get_stamp()
        rule_common.init()
    else:
        L.l.warning('Rules not initialised as scheduler is not available')
    thread_pool.add_interval_callable(thread_run, run_interval_second=1)
    thread_pool.add_interval_callable(reload_rules, run_interval_second=10)
    # connect rules processor for all db chages trigger
    dispatcher.connect(parse_rules, signal=Constant.SIGNAL_DB_CHANGE_FOR_RULES, sender=dispatcher.Any)
    global initialised
    initialised = True
