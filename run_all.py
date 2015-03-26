__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import sys

#http://www.tutorialspoint.com/python/python_command_line_arguments.htm
def main(argv):
    if 'disk' in argv:
        return 'disk'
    else:
        if 'mem' in argv:
            return 'mem'
        else:
            print 'usage: run_all.py disk OR mem'
            sys.exit(1)

if __name__ == '__main__':
    location = main(sys.argv[1:])
    print('DB Location is {}'.format(location))
    import main
    main.set_db_location(location)
    main.init()
    print 'App EXIT'

