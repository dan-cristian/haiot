#!/usr/bin/env python

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import sys
import os

#http://www.tutorialspoint.com/python/python_command_line_arguments.htm

if __name__ == '__main__':
    print 'Executing venv'
    os.system('/bin/bash  --rcfile /home/dcristian/PYC/venv/bin/activate')
    print 'Executing main'
    import main
    main.run(sys.argv[1:])