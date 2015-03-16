import concurrent.futures
import logging, time

URLS = ['http://www.foxnews.com/',
        'http://www.cnn.com/',
        'http://europe.wsj.com/',
        'http://www.bbc.co.uk/',
        'http://some-made-up-domain.com/']

callable_list=[]

# Retrieve a single page and report the url and contents
def load_url(url, timeout):
    return url

def add_callable(callable_obj):
    logging.info('Added for processing callable ' + str(callable_obj))
    callable_list.append(callable_obj)

def main():
    #https://docs.python.org/3.3/library/concurrent.futures.html
    while True:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Start the load operations and mark each future with its URL
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

    # We can use a with statement to ensure threads are cleaned up promptly
    # with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Start the load operations and mark each future with its URL
    #    future_to_url = {executor.submit(load_url, url, 60): url for url in URLS}
    #    for future in concurrent.futures.as_completed(future_to_url):
    #        url = future_to_url[future]
    #        try:
    #            data = future.result()
    #        except Exception as exc:
    #            print('%r generated an exception: %s' % (url, exc))
    #        else:
    #            print('%r page is %d bytes' % (url, len(data)))