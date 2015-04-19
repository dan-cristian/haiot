import concurrent.futures
import logging, time
from datetime import datetime

callable_list=[]
callable_progress_list={}
exec_interval_list={}
exec_last_date_list={}
thread_pool_enabled = True

dict_future_func={}

def add_callable(func, run_interval_second=60):
    print_name = func.func_globals['__name__']+'.'+ func.func_name
    logging.info('Added for processing callable ' + print_name)
    callable_list.append(func)
    exec_last_date_list[func]=datetime.now()
    exec_interval_list[func]=run_interval_second

def add_callable_progress(func, run_interval_second=60, progress_func=None):
    add_callable(func, run_interval_second=run_interval_second)
    callable_progress_list[func] = progress_func

def remove_callable(func):
    pass

def unload():
    global thread_pool_enabled
    thread_pool_enabled = False

def get_thread_status():
    global dict_future_func
    return dict_future_func

def main():
    global thread_pool_enabled
    thread_pool_enabled = True
    #https://docs.python.org/3.3/library/concurrent.futures.html
    global dict_future_func
    dict_future_func={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        while thread_pool_enabled:
            if len(callable_list) != len(dict_future_func):
                logging.info('Initialising thread processing with {} functions'.format(len(callable_list)))
                dict_future_func = {executor.submit(call_obj): call_obj for call_obj in callable_list}
            for future_obj in dict_future_func :
                func=dict_future_func [future_obj]
                print_name = func.func_globals['__name__']+'.'+ func.func_name
                exec_interval = exec_interval_list.get(func, None)
                if not exec_interval:
                    logging.warning('No exec interval set for thread function ' + print_name)
                last_exec_date = exec_last_date_list.get(func, None)
                elapsed_seconds = (datetime.now() - last_exec_date).total_seconds()
                if future_obj.done():
                    try:
                        result = future_obj.result()
                        logging.debug('Thread result={}'.format(result))
                    except Exception, exc:
                        logging.critical('Exception [{}] in {}'.format(exc, print_name))
                    #print('%s=%s' % (print_name, future_obj.result()))
                    if elapsed_seconds and elapsed_seconds > exec_interval:
                        del dict_future_func[future_obj]
                        dict_future_func[executor.submit(func)] = func
                        exec_last_date_list[func] = datetime.now()
                elif future_obj.running():
                    if elapsed_seconds>1*30:
                        logging.warning('Threaded function {} is long running for {} seconds'.format(
                            print_name,elapsed_seconds))
                        if callable_progress_list.has_key(func):
                            progress_status=callable_progress_list[func].func_globals['progress_status']
                            logging.warning('Progress Status is {}'.format(progress_status))
            time.sleep(2)
        executor.shutdown()
        logging.info('Thread pool processor exit')
