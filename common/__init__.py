__author__ = 'dcristian'
import os,logging
import constant

def init():
    logging.info('Running on OS '+ os.name)
    constant.OS=os.name
