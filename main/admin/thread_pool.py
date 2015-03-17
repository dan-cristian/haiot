import concurrent.futures
import logging, time
from datetime import datetime

callable_list=[]
exec_interval_list={}
exec_last_date_list={}

def add_callable(func):
    print_name = func.func_globals['__name__']+'.'+ func.func_name
    logging.info('Added for processing callable ' + print_name)
    callable_list.append(func)
    exec_last_date_list[func]=datetime.now()

def set_exec_interval(func, seconds):
    exec_interval_list[func]=seconds

def main():
    #https://docs.python.org/3.3/library/concurrent.futures.html
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:

        # Start the load operations and mark each future with its id
        dict_future_func = {executor.submit(call_obj): call_obj for call_obj in callable_list}

        while True:
            for future_obj in dict_future_func :
                func=dict_future_func [future_obj]
                print_name = func.func_globals['__name__']+'.'+ func.func_name
                exec_interval = exec_interval_list.get(func, None)
                if not exec_interval:
                    logging.warning('No exec interval set for thread function ' + print_name)
                    elapsed_seconds=None
                else:
                    last_exec_date = exec_last_date_list.get(func, None)
                    elapsed_seconds = (datetime.now() - last_exec_date).total_seconds()
                if future_obj.done():
                    #print('%s=%s' % (print_name, future_obj.result()))
                    if elapsed_seconds and elapsed_seconds > exec_interval:
                        del dict_future_func[future_obj]
                        dict_future_func[executor.submit(func)] = func
                        exec_last_date_list[func] = datetime.now()
                elif future_obj.running():
                    if elapsed_seconds and elapsed_seconds > 300:
                        logging.warning('Very long running {} elapsed {} sec'.format(print_name, elapsed_seconds))
                    pass
                    #print('running ' + print_name)
            time.sleep(5)


        logging.info('Thread pool processor exit')

def main2():
    #https://docs.python.org/3.3/library/concurrent.futures.html
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        while True:
            # Start the load operations and mark each future with its id
            future_to_obj = {executor.submit(call_obj): call_obj for call_obj in callable_list}

            for future in concurrent.futures.as_completed(future_to_obj):
                call_obj = future_to_obj[future]
                try:
                    data = future.result()
                except Exception as exc:
                    print('%r generated an exception: %s' % (call_obj, exc))
                else:
                    print('%r result is %s' % (call_obj, data))
        #logging.info('Thread Pool Done')
        time.sleep(1)