from main.logger_helper import Log
from common import Constant
from main.admin import model_helper
from main import thread_pool
import smtplib
import json
from pydispatch import dispatcher

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

initialised = False


def _get_pass(email=None):
    config_file = model_helper.get_param(Constant.P_GMAIL_CREDENTIAL_FILE)
    try:
        with open(config_file , 'r') as f:
            config_list = json.load(f)
            if email in config_list.keys():
                record = config_list[email]
                return record['password']
    except Exception, ex:
        Log.logger.warning("Could not read credential email file {}".format(config_file ))
    return None


def send_notification(subject=None, body=None):
    sent_from = model_helper.get_param(Constant.P_GMAIL_NOTIFY_FROM_EMAIL)
    notify_recipient = model_helper.get_param(Constant.P_NOTIFY_EMAIL_RECIPIENT)
    gmail_password = _get_pass(sent_from)
    if gmail_password is not None:
        to = [notify_recipient]
        email_text = "\r\n".join([
            "From: %s" % sent_from,
            "To: %s" % ", ".join(to),
            "Subject: %s" % subject,
            "",
            "%s" % body
        ])
        try:
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.ehlo()
            server.login(sent_from, gmail_password)
            server.sendmail(sent_from, to, email_text)
            server.close()
            return True
        except Exception, ex:
            Log.logger.warning("Email not sent, err={}".format(ex))
    else:
        Log.logger.warning("Could not get credential for email {}".format(sent_from))
    return False


def unload():
    Log.logger.info('Email module unloading')
    # ...
    global initialised
    initialised = False


def init():
    Log.logger.info('Email module initialising')
    dispatcher.connect(send_notification, signal=Constant.SIGNAL_EMAIL_NOTIFICATION, sender=dispatcher.Any)
    if send_notification("Starting haiot", "Host is {}".format(Constant.HOST_NAME)):
        Log.logger.info("Init email sent OK")
    global initialised
    initialised = True

