from main.logger_helper import L
from common import Constant
from main.admin import model_helper
from main import thread_pool
import smtplib
import json
from pydispatch import dispatcher

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

initialised = False
__notif_from = None
__notif_pass = None
__notif_dest = None


def _get_pass(email=None):
    config_file = model_helper.get_param(Constant.P_GMAIL_CREDENTIAL_FILE)
    try:
        with open(config_file , 'r') as f:
            config_list = json.load(f)
            if email in config_list.keys():
                record = config_list[email]
                return record['password']
    except Exception, ex:
        L.l.warning("Could not read credential email file {}".format(config_file))
    return None


def send_notification(subject=None, body=None):
    global __notif_from, __notif_pass, __notif_dest
    sent_from = __notif_from
    notify_recipient = __notif_dest

    if __notif_pass is not None:
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
            server.login(sent_from, __notif_pass)
            server.sendmail(sent_from, to, email_text)
            server.close()
            return True
        except Exception, ex:
            L.l.warning("Email not sent, err={}".format(ex))
    else:
        L.l.warning("Could not get credential for email {}".format(sent_from))
    return False


def unload():
    L.l.info('Email module unloading')
    # ...
    global initialised
    initialised = False


def init():
    L.l.debug('Email module initialising')
    dispatcher.connect(send_notification, signal=Constant.SIGNAL_EMAIL_NOTIFICATION, sender=dispatcher.Any)
    global __notif_from, __notif_pass, __notif_dest
    __notif_from = model_helper.get_param(Constant.P_GMAIL_NOTIFY_FROM_EMAIL)
    __notif_dest = model_helper.get_param(Constant.P_NOTIFY_EMAIL_RECIPIENT)
    __notif_pass = _get_pass(__notif_from)

    #if send_notification("Starting haiot", "Host is {}".format(Constant.HOST_NAME)):
    #    Log.logger.info("Init email sent OK")
    global initialised
    initialised = True

