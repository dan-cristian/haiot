import time
from datetime import datetime

import concurrent.futures

from main.logger_helper import L


class P:
    cl = []  # list with callables
    # cpl = {} # list with callables progress
    eil = {}  # exec_interval_list
    eldl = {}  # exec_last_date_list
    tpool = True  # thread pool is enabled?
    ff = {}  # dict_future_func
    executor = None


def __get_print_name_callable(func):
    return func.__globals__['__name__'] + '.' + func.__name__


def add_interval_callable(func, run_interval_second, progress_func=None):  # , *args):
    print_name = __get_print_name_callable(func)
    if func not in P.cl:
        P.cl.append(func)
        P.eldl[func] = datetime.now()
        P.eil[func] = run_interval_second
        if len(P.ff) > 0 and P.executor is not None:  # run the function already is thread pool is started
            P.ff[P.executor.submit(func)] = func
    else:
        L.l.warning('Callable {} not added, already there'.format(print_name))


def remove_callable(func):
    print_name = __get_print_name_callable(func)
    if func in P.cl:
        P.cl.remove(func)
        L.l.info('Removed from processing callable ' + print_name)


def unload():
    P.tpool = False


def get_thread_status():
    return P.ff


def run_thread_pool():
    P.tpool = True
    # https://docs.python.org/3.3/library/concurrent.futures.html
    P.ff = {}
    P.executor = concurrent.futures.ThreadPoolExecutor(max_workers=20)
    # with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    while P.tpool:
        if len(P.cl) != len(P.ff):
            P.ff = {P.executor.submit(call_obj): call_obj for call_obj in P.cl}
        for future_obj in dict(P.ff):
            func = P.ff[future_obj]
            print_name = __get_print_name_callable(func)
            exec_interval = P.eil.get(func, None)
            if not exec_interval:
                L.l.error('No exec interval set for thread function ' + print_name)
                exec_interval = 60  # set a default exec interval
            last_exec_date = P.eldl.get(func, None)
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
                    P.eldl[func] = datetime.now()
            elif future_obj.running():
                if elapsed_seconds > 1*20:
                    # L.l.info('Threaded func{} is long running for {} seconds'.format(print_name, elapsed_seconds))
                    if 'P' in func.__globals__ and hasattr(func.__globals__['P'], 'thread_pool_status'):
                        progress_status = func.__globals__['P'].thread_pool_status
                        # L.l.warning('Progress Status since {} sec is [{}]'.format(elapsed_seconds, progress_status))
        time.sleep(0.1)
    P.executor.shutdown()
    L.l.info('Interval thread pool processor exit')
