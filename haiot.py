__author__ = 'Dan Cristian<dan.cristian@gmail.com>'
import signal
import sys


# http://www.tutorialspoint.com/python/python_command_line_arguments.htm
def signal_handler(signal_name, frame):
    print('I got signal {} frame {}, exiting'.format(signal_name, frame))
    main.tinydb_app.unload()


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, signal_handler)

    import main.general_init
    main.general_init.init()

    import main.tinydb_app
    main.tinydb_app.init(sys.argv[1:])
    #main.run(sys.argv[1:])
