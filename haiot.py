#!/usr/bin/env python
__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import sys
import main
import os

#http://www.tutorialspoint.com/python/python_command_line_arguments.htm

if __name__ == '__main__':
    os.system('/bin/bash  --rcfile /home/dcristian/PYC/venv/bin/activate')
    main.run(sys.argv[1:])