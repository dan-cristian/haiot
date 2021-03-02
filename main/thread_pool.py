import time
from datetime import datetime
import threading
import concurrent.futures

from main.logger_helper import L

from common import fix_module
while True:
    try:
        import prctl
        break
    except ImportError as iex:
        if not fix_module(iex):
            break

class P:
    thread_func_list = {}
    cl = []  # list with callables
    eil = {}  # exec_interval_list
    eldl = {}  # exec_last_date_list
    tpool = True  # thread pool is enabled?
    ff = {}  # dict_future_func
    executor = None
    _event = threading.Event()


class ThreadFunc:

    def __init__(self):
        self.name = None
        self.func = None
        self.interval = None
        self.last_exec = datetime.min
        self.long_running = False

    def done_callback(self, obj):
        # L.l.info('I am done {}={}'.format(self.name, obj))
        # P._event.set()
        pass


def __get_print_name_callable(func):
    return func.__globals__['__name__'] + '.' + func.__name__


def add_interval_callable(func, run_interval_second, long_running=False):  # , *args):
    print_name = __get_print_name_callable(func)
    if func not in P.thread_func_list:
        f = ThreadFunc()
        f.name = print_name
        f.func = func
        f.interval = run_interval_second
        f.last_exec = datetime.now()
        f.long_running = long_running
        P.thread_func_list[func] = f
        if len(P.ff) > 0 and P.executor is not None:  # run the function already if thread pool is started
            P.ff[P.executor.submit(func)] = func
    else:
        L.l.warning('Callable {} not added, already there'.format(print_name))


def remove_callable(func):
    print_name = __get_print_name_callable(func)
    if func in P.thread_func_list:
        P.thread_func_list.pop(func, None)
        L.l.info('Removed from processing callable ' + print_name)
    else:
        L.l.info('Cannot find callable {} to remove'.format(print_name))


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
        prctl.set_name("thread_pool")
        threading.current_thread().name = "thread_pool"
        try:
            if len(P.thread_func_list) != len(P.ff):
                P.ff.clear()
                # copy list as can change
                for tf in dict(P.thread_func_list):
                    P.ff[P.executor.submit(tf)] = P.thread_func_list[tf].func

            for future_obj in dict(P.ff):
                prctl.set_name("thread_pool_loop")
                threading.current_thread().name = "thread_pool_loop"
                func = P.ff[future_obj]
                print_name = __get_print_name_callable(func)
                if func in P.thread_func_list:
                    tf = P.thread_func_list[func]
                else:
                    L.l.warning('Skip processing func {}, was removed?'.format(print_name))
                    P.ff.pop(future_obj, None)
                    break
                exec_interval = tf.interval
                if exec_interval is None:
                    L.l.error('No exec interval set for thread function ' + print_name)
                    exec_interval = 60  # set a default exec interval
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
                        future = P.executor.submit(func)
                        future.add_done_callback(tf.done_callback)
                        P.ff[future] = func
                        tf.last_exec = datetime.now()
                elif future_obj.running():
                    if elapsed_seconds > 1*20 and not tf.long_running:
                        L.l.info('Threaded func{} is running for {} sec'.format(print_name, elapsed_seconds))
                        if 'P' in func.__globals__ and hasattr(func.__globals__['P'], 'thread_pool_status'):
                            progress_status = func.__globals__['P'].thread_pool_status
                            L.l.warning('Progress Status since {} sec is [{}]'.format(elapsed_seconds, progress_status))
            # fixme: replace sleep with thread signal to reduce CPU usage
            time.sleep(0.6)
            # https://stackoverflow.com/questions/44551728/pause-and-resume-thread-in-python
            # P._event.wait()
            # P._event.clear()

        except Exception as ex:
            L.l.error('Error in threadpool run, ex={}'.format(ex), exc_info=True)
    P.executor.shutdown()
    L.l.info('Interval thread pool processor exit')
