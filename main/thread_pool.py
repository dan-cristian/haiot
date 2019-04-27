import time
from datetime import datetime
import threading
import prctl
import concurrent.futures

from main.logger_helper import L


class P:
    thread_func_list = {}
    cl = []  # list with callables
    # cpl = {} # list with callables progress
    eil = {}  # exec_interval_list
    eldl = {}  # exec_last_date_list
    tpool = True  # thread pool is enabled?
    ff = {}  # dict_future_func
    executor = None


class ThreadFunc:

    def __init__(self):
        self.name = None
        self.func = None
        self.interval = None
        self.last_exec = datetime.min
        self.long_running = False


def __get_print_name_callable(func):
    return func.__globals__['__name__'] + '.' + func.__name__


def add_interval_callable(func, run_interval_second, long_running=False):  # , *args):
    print_name = __get_print_name_callable(func)
    #if func not in P.cl:

    if print_name not in P.thread_func_list:
        f = ThreadFunc()
        f.name = print_name
        f.func = func
        f.interval = run_interval_second
        f.last_exec = datetime.now()
        f.long_running = long_running
        P.thread_func_list[print_name] = f

        #P.cl.append(func)
        #P.eldl[func] = datetime.now()
        #P.eil[func] = run_interval_second

        if len(P.ff) > 0 and P.executor is not None:  # run the function already if thread pool is started
            P.ff[P.executor.submit(func)] = func
    else:
        L.l.warning('Callable {} not added, already there'.format(print_name))


def remove_callable(func):
    print_name = __get_print_name_callable(func)
    if print_name in P.thread_func_list:
        P.thread_func_list.pop(print_name, None)
    #if func in P.cl:
        #P.cl.remove(func)
        L.l.info('Removed from processing callable ' + print_name)


def unload():
    P.tpool = False


def get_thread_status():
    return P.ff


def run_thread_pool():
    prctl.set_name("thread_pool")
    threading.current_thread().name = "thread_pool"
    P.tpool = True
    # https://docs.python.org/3.3/library/concurrent.futures.html
    P.ff = {}
    P.executor = concurrent.futures.ThreadPoolExecutor(max_workers=20)
    # with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    while P.tpool:
        #if len(P.cl) != len(P.ff):
        #    P.ff = {P.executor.submit(call_obj): call_obj
        #            for call_obj in P.cl}
        if len(P.thread_func_list) != len(P.ff):
            for tf in P.thread_func_list.values():
                P.ff[P.executor.submit(tf.func)] = tf.func

        for future_obj in dict(P.ff):
            func = P.ff[future_obj]
            print_name = __get_print_name_callable(func)
            tf = P.thread_func_list[print_name]
            #exec_interval = P.eil.get(func, None)
            exec_interval = tf.interval
            if exec_interval is None:
                L.l.error('No exec interval set for thread function ' + print_name)
                exec_interval = 60  # set a default exec interval
            #last_exec_date = P.eldl.get(func, None)
            last_exec_date = tf.last_exec
            elapsed_seconds = (datetime.now() - last_exec_date).total_seconds()
            # when function is done check if needs to run again or if is running for too long
            if future_obj.done():
                try:
                    result = future_obj.result()
                except Exception as exc:
                    L.l.error('Exception {} in {}'.format(exc, print_name), exc_info=True)
                # run the function again at given interval
                if elapsed_seconds and elapsed_seconds > exec_interval:
                    del P.ff[future_obj]
                    P.ff[P.executor.submit(func)] = func
                    tf.last_exec = datetime.now()
                    #P.eldl[func] = datetime.now()
            elif future_obj.running():
                if elapsed_seconds > 1*20 and not tf.long_running:
                    L.l.info('Threaded func{} is long running for {} seconds'.format(print_name, elapsed_seconds))
                    if 'P' in func.__globals__ and hasattr(func.__globals__['P'], 'thread_pool_status'):
                        progress_status = func.__globals__['P'].thread_pool_status
                        L.l.warning('Progress Status since {} sec is [{}]'.format(elapsed_seconds, progress_status))
        time.sleep(1)
    P.executor.shutdown()
    L.l.info('Interval thread pool processor exit')
