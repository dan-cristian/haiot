__author__ = 'dcristian'
import threading
import utils
import prctl
from main.logger_helper import L
from main import thread_pool
import psutil
import os
from common import Constant

class P:
    query_count = None
    query_cumulative_time_miliseconds = None
    min_query_time_miliseconds = None
    max_query_time_miliseconds = None
    log_file = None


def add_query(start_time, query_details=None):
        elapsed = int((utils.get_base_location_now_date() - start_time).total_seconds()*1000)

        if not P.query_count:
            P.query_count = 0
            P.query_cumulative_time_miliseconds = 0
            P.max_query_time_miliseconds = elapsed
            P.min_query_time_miliseconds = elapsed

        if P.max_query_time_miliseconds < elapsed:
            P.max_query_time_miliseconds = elapsed
            L.l.debug("Longest query details:{}".format(str(query_details)[:50]))
            L.l.debug("Count={} avg={} min={} max={}".format(
                P.query_count, P.query_cumulative_time_miliseconds / P.query_count, P.min_query_time_miliseconds,
                P.max_query_time_miliseconds))

        if P.min_query_time_miliseconds > elapsed:
            P.min_query_time_miliseconds = elapsed

        P.query_count += 1
        P.query_cumulative_time_miliseconds += elapsed
        L.l.debug("Count={} avg={} min={} max={}".format(P.query_count,
                                                         P.query_cumulative_time_miliseconds / P.query_count,
                                                         P.min_query_time_miliseconds, P.max_query_time_miliseconds))
        return elapsed


# https://stackoverflow.com/questions/34361035/python-thread-name-doesnt-show-up-on-ps-or-htop
def _thread_for_ident(ident):
    return threading._active.get(ident)


def _save_threads_cpu_percent(p, interval=0.1):
    total_percent = p.cpu_percent(interval)
    total_time = sum(p.cpu_times())
    list = []
    with open(P.log_file, "w") as log:
        total = 0
        for t in p.threads():
            load = round(total_percent * ((t.system_time + t.user_time)/total_time), 2)
            total += load
            th = _thread_for_ident(t.id)
            if th is None:
                tname = "None"
            else:
                tname = th.name
            log.write("{} % \t {} \t\t\t\t {}\n".format(load, tname, t))
        log.write("Total={} %\n".format(total))

def _cpu_profiling():
    p = psutil.Process(os.getpid())
    #mem = p.get_memory_info()[0] / float(2 ** 20)
    # treads_list = p.threads()
    _save_threads_cpu_percent(p)
    #li = get_threads_cpu_percent(p)
    #with open(P.log_file, "w") as log:
        #log.write(mem)
        #log.write("PID={}\n".format(os.getpid()))
        #log.write("Threads: {}\n".format(li))


def thread_run():
    prctl.set_name("performance")
    threading.current_thread().name = "performance"
    _cpu_profiling()
    prctl.set_name("idle")
    threading.current_thread().name = "idle"


def init(log_file):
    P.log_file = log_file
    thread_pool.add_interval_callable_progress(thread_run, run_interval_second=5)
