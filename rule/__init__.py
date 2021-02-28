from inspect import getmembers, isfunction
import imp
import os
import threading
import prctl
from pydispatch import dispatcher
from main.logger_helper import L
from main import thread_pool
from main import sqlitedb
from common import Constant
from storage.model import m

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from common import fix_module
while True:
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        break
    except ImportError as iex:
        if not fix_module(iex):
            break


scheduler = None
try:
    # fixme: this does not currently work on BusyBox/openwrt routers
    # http://flexget.com/ticket/2741
    scheduler = BackgroundScheduler()
except Exception as ex:
    scheduler = None
    L.l.warning('Cannot initialise apscheduler er={}'.format(ex))

if scheduler:
    from rule import rules_run, rule_common


class P:
    event_list = []
    initialised = False
    func = {}
    timestamp = None
    rules_modules = []
    sub_modules = {}


class Obj:
    pass


# executed on all DB changes
def parse_rules(obj, change):
    """ running rule method corresponding with obj type """
    # executed on all db value changes
    L.l.debug('Received obj={} change={} for rule parsing'.format(obj, change))
    try:
        # extract only changed fields
        if hasattr(obj, Constant.JSON_PUBLISH_FIELDS_CHANGED):
            field_changed_list = obj.last_commit_field_changed_list
        else:
            # fixme: not sure if above is still needed
            field_changed_list = change
        # iterate all functions in each rule module and queue for execution what matches
        # fixme: improve performance by using dictionary search
        for func_list in P.func.values():
            if func_list:
                for func in func_list:
                    if func[1].__defaults__ and len(func[1].__defaults__) > 0:
                        first_param = func[1].__defaults__[0]
                        # find rule methods for queued execution with first param type equal to passed object type
                        if type(obj) == type(first_param):
                            # record = Obj()
                            # for attr, value in obj.__dict__.items():
                            #    setattr(record, attr, value)
                            # P.event_list.append([record, func[0], field_changed_list])
                            P.event_list.append([obj, func[0], field_changed_list])
                            # optimises CPU, but ensure each function name is unique in rule file
                            # fixme: optimisation does not work, does not allow multiple functions?
                            break
    except Exception as ex:
        L.l.exception('Error parsing rules, ex={}'.format(ex))


# async run of rules
def _process_events():
    for obj in list(P.event_list):
        try:
            for rule_mod in P.rules_modules:
                # result = getattr(rules_run, obj[1])(obj=obj[0], field_changed_list=obj[2])
                if hasattr(rule_mod, obj[1]):
                    result = getattr(rule_mod, obj[1])(obj=obj[0], change=obj[2])
                    L.l.debug('Rule returned {}'.format(result))
                    # set remove at the end to allow for all rules with same object to execute
                    P.event_list.remove(obj)
        except Exception as ex:
            L.l.critical("Error processing rule event err={}".format(ex), exc_info=1)


def thread_run():
    prctl.set_name("rule_run")
    threading.current_thread().name = "rule_run"
    _process_events()
    prctl.set_name("idle_rule_run")
    threading.current_thread().name = "idle_rule_run"
    return 'Processed rules thread_run'


def unload():
    L.l.info('Rules module unloading')
    thread_pool.remove_callable(thread_run)
    thread_pool.remove_callable(reload_rules)
    P.initialised = False


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
        rule_list = m.Rule.find({m.Rule.host_name: Constant.HOST_NAME})
        scheduler.remove_all_jobs()
        for rule in rule_list:
            method_to_call = getattr(rules_run, rule.command)
            if rule.is_active:
                L.l.info("Adding job {} to scheduler, active=".format(method_to_call, rule.is_active))
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


# add dynamic rules into db and sceduler to allow execution via web interface or API
def add_rules_into_db(module):
    try:
        # load all function entries from hardcoded rule script
        P.func[module] = getmembers(module, isfunction)
        if P.func[module]:
            for func in P.func[module]:
                if not func[1].__defaults__ and not func[1].__name__.startswith('_'):
                    # add this to DB
                    record = m.Rule()
                    record.name = func[1].__name__
                    record.command = func[1].__name__
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
                            record.is_active = (pairs["is_active"].lower() == "true")
                        if "is_async" in pairs.keys():
                            record.is_async = (pairs["is_async"].lower() == "true")
                        if record.is_active is True:
                            scheduler.add_job(func[1], trigger='cron', year=record.year, month=record.month,
                                              day=record.day, week=record.week, day_of_week=record.day_of_week,
                                              second=record.second, hour=record.hour, minute=record.minute,
                                              max_instances=1, misfire_grace_time=None)
                            L.l.info("Adding rule {}:{} to scheduler {}".format(record.name, record.command,
                                                                                record.is_active))
    except Exception as ex:
        L.l.exception('Error adding rules into db {}'.format(ex), exc_info=1)


def _get_stamp():
    path = rules_run.__file__
    path = path.replace(".pyc", ".py")
    return os.path.getmtime(path)


def reload_rules():
    prctl.set_name("rule_reload")
    threading.current_thread().name = "rule_reload"
    new_stamp = _get_stamp()
    if new_stamp != P.timestamp:
        L.l.info('Reloading rules as timestamp changed, {} != {}'.format(P.timestamp, new_stamp))
        imp.reload(rules_run)
        add_rules_into_db(module=rules_run)
        P.timestamp = new_stamp
        rules_run.test_code()
    # else:
    #    Log.logger.info('Reloading {} skip timestamp {} != {}'.format(path, P.timestamp, new_stamp))
    prctl.set_name("idle_rule_reload")
    threading.current_thread().name = "idle_rule_reload"


def _process_sub_rules():
    prctl.set_name("subrule_run")
    threading.current_thread().name = "subrule_run"

    for thread_func in P.sub_modules.values():
        thread_func()

    prctl.set_name("idle_subrule_run")
    threading.current_thread().name = "idle_subrule_run"


def init_sub_rule(thread_run_func, rule_module):
    add_rules_into_db(module=rule_module)
    P.sub_modules[rule_module] = thread_run_func
    # if len(P.sub_modules) == 1:
    #    thread_pool.add_interval_callable(_process_sub_rules, run_interval_second=10)


def init():
    global scheduler
    L.l.info('Rules module initialising')
    if scheduler:
        from rule import electricity
        P.rules_modules.append(rules_run)
        P.rules_modules.append(electricity)
        scheduler.remove_all_jobs()
        add_rules_into_db(module=rules_run)
        # __load_rules_from_db()
        scheduler.start()
        P.timestamp = _get_stamp()
        rule_common.init()
    else:
        L.l.warning('Rules not initialised as scheduler is not available')
    thread_pool.add_interval_callable(thread_run, run_interval_second=1)
    thread_pool.add_interval_callable(reload_rules, run_interval_second=30)
    # connect rules processor for all db chages trigger
    dispatcher.connect(parse_rules, signal=Constant.SIGNAL_DB_CHANGE_FOR_RULES, sender=dispatcher.Any)
    P.initialised = True
