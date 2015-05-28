__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

import httplib
import httplib2
import os
import random
import time

from apiclient import discovery, errors, http
#from apiclient.discovery import build
#from apiclient.errors import HttpError
#from apiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

from pydispatch import dispatcher

from main import logger
from common import constant, utils
from main.admin import model_helper, thread_pool

initialised = False
__file_list_last_change = {}
__uploaded_file_list_date = {}
# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, httplib.NotConnected,
  httplib.IncompleteRead, httplib.ImproperConnectionState,
  httplib.CannotSendRequest, httplib.CannotSendHeader,
  httplib.ResponseNotReady, httplib.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the Google Developers Console at
# https://console.developers.google.com/.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
__CLIENT_SECRETS_FILE = 'text.txt'

# This OAuth 2.0 access scope allows an application to upload files to the
# authenticated user's YouTube channel, but doesn't allow other types of access.
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# This variable defines a message to display if the CLIENT_SECRETS_FILE is
# missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the Developers Console
https://console.developers.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__), __CLIENT_SECRETS_FILE))

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")

class Args:
    privacyStatus = 'private'
    title = 'Default video title'
    description = 'Default video description'
    category = 22
    keywords = ''
    file = None

__args = Args()
__youtube = None



def get_authenticated_service(args):
  flow = flow_from_clientsecrets(__CLIENT_SECRETS_FILE,
    scope=YOUTUBE_UPLOAD_SCOPE,
    message=MISSING_CLIENT_SECRETS_MESSAGE)

  storage = Storage("%s-oauth2.json" % __name__)
  credentials = storage.get()

  if credentials is None or credentials.invalid:
    credentials = run_flow(flow, storage, args)

  return discovery.build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
    http=credentials.authorize(httplib2.Http()))

def initialize_upload(youtube, options):
  tags = None
  if options.keywords:
    tags = options.keywords.split(",")

  body=dict(
    snippet=dict(
      title=options.title,
      description=options.description,
      tags=tags,
      categoryId=options.category
    ),
    status=dict(
      privacyStatus=options.privacyStatus
    )
  )

  # Call the API's videos.insert method to create and upload the video.
  insert_request = youtube.videos().insert(
    part=",".join(body.keys()),
    body=body,
    # The chunksize parameter specifies the size of each chunk of data, in
    # bytes, that will be uploaded at a time. Set a higher value for
    # reliable connections as fewer chunks lead to faster uploads. Set a lower
    # value for better recovery on less reliable connections.
    #
    # Setting "chunksize" equal to -1 in the code below means that the entire
    # file will be uploaded in a single HTTP request. (If the upload fails,
    # it will still be retried where it left off.) This is usually a best
    # practice, but if you're using Python older than 2.6 or if you're
    # running on App Engine, you should set the chunksize to something like
    # 1024 * 1024 (1 megabyte).
    media_body= http.MediaFileUpload(options.file, chunksize=-1, resumable=True)
  )

  resumable_upload(insert_request)

# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_upload(insert_request):
  response = None
  error = None
  retry = 0
  while response is None:
    try:
      file = insert_request.resumable._filename
      logger.debug('Uploading file {}'.format(file))
      status, response = insert_request.next_chunk()
      if 'id' in response:
        logger.info('Video id {} file {} was successfully uploaded.'.format(response['id'], file))
      else:
        logger.warning('The upload for {} failed with an unexpected response {}'.format(file, response))
    except errors.HttpError, e:
      if e.resp.status in RETRIABLE_STATUS_CODES:
        error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status, e.content)
      else:
        raise
    except RETRIABLE_EXCEPTIONS, e:
      error = "A retriable error occurred: %s" % e

    if error is not None:
      print error
      retry += 1
      if retry > MAX_RETRIES:
        logger.warning('No longer attempting to retry upload for file {}'.format(file))
      max_sleep = 2 ** retry
      sleep_seconds = random.random() * max_sleep
      logger.info('Sleeping {} seconds and then retrying upload for {}'.format(sleep_seconds, file))
      time.sleep(sleep_seconds)

def upload_file(file):
    global initialised, __args, __uploaded_file_list_date
    if initialised:
        if not os.path.exists(file):
            logger.warning('Not existent file={} to be uploaded to youtube'.format(file))
        else:
            __args.file = file
            __args.title = os.path.basename(file)
            time.sleep(1)

            if not os.access(file, os.R_OK):
                logger.warning('Cannot access for upload file {}'.format(file))
            else:
                try:
                    test_open = open(file, 'r')
                    test_open.close()
                    try:
                        initialize_upload(__youtube, __args)
                        __uploaded_file_list_date[file] = utils.get_base_location_now_date()
                        del __file_list_last_change[file]
                    except errors.HttpError, ex:
                        logger.warning('Error while uploading file={}, err={}'.format(file, ex))
                    except Exception, ex:
                        logger.info('Unexpected error on upload, file {}, err={}'.format(file, ex))
                except Exception, ex:
                    logger.info('Locked file {}, err={}'.format(file, ex))

    else:
        logger.warning('Trying to upload youtube file={} when not connected to youtube'.format(file))


def file_watcher_event(event, file, is_directory):
    logger.debug('Received file watch event={} file={}'.format(event, file))
    if event == 'modified' and not is_directory:
        __file_list_last_change[file] = utils.get_base_location_now_date()
        #upload_file(file)

#https://developers.google.com/youtube/v3/guides/uploading_a_video
if __name__ == '__main__':
  argparser.add_argument("--file", required=True, help="Video file to upload")
  argparser.add_argument("--title", help="Video title", default="Test Title")
  argparser.add_argument("--description", help="Video description",
    default="Test Description")
  argparser.add_argument("--category", default="22",
    help="Numeric video category. " +
      "See https://developers.google.com/youtube/v3/docs/videoCategories/list")
  argparser.add_argument("--keywords", help="Video keywords, comma separated",
    default="")
  argparser.add_argument("--privacyStatus", choices=VALID_PRIVACY_STATUSES,
    default=VALID_PRIVACY_STATUSES[0], help="Video privacy status.")
  args = argparser.parse_args()

  if not os.path.exists(args.file):
    exit("Please specify a valid file using the --file= parameter.")

  youtube = get_authenticated_service(args)
  try:
    initialize_upload(youtube, args)
  except errors.HttpError, e:
    print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)

def thread_run():
    global __file_list_last_change, __uploaded_file_list_date
    try:
        for file in __file_list_last_change.keys():
            lapsed = (utils.get_base_location_now_date() - __file_list_last_change[file]).total_seconds()
            if lapsed > 30:
                if file in __uploaded_file_list_date.keys():
                    logger.warning('Skip duplicate video upload for file {}'.format(file))
                else:
                    upload_file(file)
                    if len(__uploaded_file_list_date) > 100:
                        __uploaded_file_list_date.clear()
    except Exception, ex:
        logger.warning('Exception on youtube thread run, err={}'.format(ex))

def init():
    global initialised, __CLIENT_SECRETS_FILE, __youtube
    try:
        __CLIENT_SECRETS_FILE = os.getcwd() + '/' + model_helper.get_param(constant.P_YOUTUBE_CREDENTIAL_FILE)
        logger.info('Initialising youtube with credential from {}'.format(__CLIENT_SECRETS_FILE))
        __youtube = get_authenticated_service([])
        dispatcher.connect(file_watcher_event, signal=constant.SIGNAL_FILE_WATCH, sender=dispatcher.Any)
        thread_pool.add_callable(thread_run, run_interval_second=10)
        initialised = True
        #upload_file('c:\\temp\\01-20150512215655-alert.avi')
    except Exception, ex:
        logger.warning('Unable to initialise youtube uploader, err={}'.format(ex))

