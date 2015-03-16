import concurrent.futures
import logging, time

callable_list=[]

def add_callable(callable_obj):
    print_name = callable_obj.func_globals['__name__']+'.'+ callable_obj.func_name
    logging.info('Added for processing callable ' + print_name)
    callable_list.append(callable_obj)

def main():
    #https://docs.python.org/3.3/library/concurrent.futures.html
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:

        # Start the load operations and mark each future with its id
        dict_future_func = {executor.submit(call_obj): call_obj for call_obj in callable_list}

        while True:
            for future_obj in dict_future_func :
                func=dict_future_func [future_obj]
                print_name = func.func_globals['__name__']+'.'+ func.func_name
                if future_obj.done():
                    print('%s=%s' % (print_name, future_obj.result()))
                    del dict_future_func[future_obj]
                    dict_future_func[executor.submit(func)]=func
                elif future_obj.running():
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