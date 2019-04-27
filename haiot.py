__author__ = 'Dan Cristian<dan.cristian@gmail.com>'
import signal
import sys
import time
import threading


# http://www.tutorialspoint.com/python/python_command_line_arguments.htm
def signal_handler(signal_name, frame):
    print('I got signal {} frame {}, exiting'.format(signal_name, frame))
    main.general_init.unload()


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, signal_handler)

    from main.logger_helper import L
    L.init_logging()

    import common
    common.init()

    import main.general_init
    main.general_init.init(sys.argv[1:])

    global initialised
    initialised = True

    from main.logger_helper import L
    L.l.info('Feeding dogs with grass until app will exit')
    #if common.Constant.HOST_NAME == 'netbook':
    #    common.Constant.HOST_NAME = 'pi-face'
    #    common.Constant.debug_dummy = True

    try:
        while not main.general_init.P.shutting_down:
            time.sleep(1)
    except KeyboardInterrupt:
        print('CTRL+C was pressed, exiting')
        exit_code = 1
    except Exception as ex:
        print('Main exit with exception {}'.format(ex))
    main.general_init.unload()
    print('App EXIT')
    for thread in threading.enumerate():
        print(thread.name)
