import time
from datetime import datetime

import concurrent.futures

from main.logger_helper import Log

__callable_list=[]
__callable_progress_list={}
__exec_interval_list={}
__exec_last_date_list={}
__thread_pool_enabled = True
__dict_future_func={}

__immediate_executor = None

def add_interval_callable(func, run_interval_second=60):
    print_name = func.func_globals['__name__']+'.'+ func.func_name
    Log.logger.info('Added for processing callable ' + print_name)
    __callable_list.append(func)
    __exec_last_date_list[func]=datetime.now()
    __exec_interval_list[func]=run_interval_second

def add_interval_callable_progress(func, run_interval_second=60, progress_func=None):
    add_interval_callable(func, run_interval_second=run_interval_second)
    __callable_progress_list[func] = progress_func

def remove_callable(func):
    pass

def unload():
    global __thread_pool_enabled
    __thread_pool_enabled = False

def get_thread_status():
    global __dict_future_func
    return __dict_future_func

def run_thread_pool():
    global __thread_pool_enabled
    __thread_pool_enabled = True
    #init immediate jobs thread pool
    global __immediate_executor
    __immediate_executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
    #https://docs.python.org/3.3/library/concurrent.futures.html
    global __dict_future_func
    __dict_future_func={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        while __thread_pool_enabled:
            if len(__callable_list) != len(__dict_future_func):
                Log.logger.info('Initialising interval thread processing with {} functions'.format(len(__callable_list)))
                __dict_future_func = {executor.submit(call_obj): call_obj for call_obj in __callable_list}
            for future_obj in __dict_future_func :
                func=__dict_future_func [future_obj]
                print_name = func.func_globals['__name__']+'.'+ func.func_name
                exec_interval = __exec_interval_list.get(func, None)
                if not exec_interval:
                    Log.logger.warning('No exec interval set for thread function ' + print_name)
                last_exec_date = __exec_last_date_list.get(func, None)
                elapsed_seconds = (datetime.now() - last_exec_date).total_seconds()
                #when function is done check if needs to run again or if is running for too long
                if future_obj.done():
                    try:
                        result = future_obj.result()
                        Log.logger.debug('Thread result={}'.format(result))
                    except Exception, exc:
                        Log.logger.error('Exception {} in {}'.format(exc, print_name, exc_info=True))
                    #print('%s=%s' % (print_name, future_obj.result()))
                    #run the function again at given interval
                    if elapsed_seconds and elapsed_seconds > exec_interval:
                        del __dict_future_func[future_obj]
                        __dict_future_func[executor.submit(func)] = func
                        __exec_last_date_list[func] = datetime.now()
                elif future_obj.running():
                    if elapsed_seconds>1*30:
                        Log.logger.debug('Threaded function {} is long running for {} seconds'.format(
                            print_name,elapsed_seconds))
                        if __callable_progress_list.has_key(func):
                            progress_status=__callable_progress_list[func].func_globals['progress_status']
                            Log.logger.warning('Progress Status is {}'.format(progress_status))
            time.sleep(2)
        executor.shutdown()
        Log.logger.info('Interval thread pool processor exit')

#immediately runs submitted job using a thread pool
def do_job(function):
    global __immediate_executor
    __immediate_executor.submit(function)
