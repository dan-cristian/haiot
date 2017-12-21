try:
    import picamera
    __has_picamera = True
except Exception, ex:
    __has_picamera = False

import subprocess
import time
import datetime as dt
import re

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


_ffmpeg_pi = None
_ffmpeg_usb = None
_segment_duration = 3600  # in seconds
_is_recording_pi = False
_is_recording_usb = False
_pi_out_filename = '/mnt/tmp/pi_%Y-%m-%d_%H-%M-%S.mp4'
_usb_out_filename = '/mnt/tmp/usb_%Y-%m-%d_%H-%M-%S.mp4'
_usb_camera_dev_name = '/dev/video0'
_usb_max_resolution = '1280x720'
_pi_max_resolution = (1296, 972)
_win_camera_dev_name = "Integrated Camera"


def _get_win_cams():
    pass


def _run_ffmpeg_pi(out_filename):
    global _ffmpeg_pi
    print "Recording on {}".format(out_filename)
    if _ffmpeg_pi is None:
        _ffmpeg_pi = subprocess.Popen([
            'ffmpeg', '-y', '-r', '8', '-i', '-', '-vcodec', 'copy',
            '-f', 'segment', '-segment_time', _segment_duration, '-segment_format', 'mp4', '-reset_timestamps', '1',
            '-force_key_frames', '"expr:gte(t,n_forced*10)"',
            '-frag_duration', '1000', '-strftime', '1',
            '-an', out_filename
        ], stdin=subprocess.PIPE)


def _run_ffmpeg_usb_win(resolution, no_sound=True):
    global _ffmpeg_usb
    if no_sound:
        sound_param = "-an"
    else:
        sound_param = ""
    if _ffmpeg_usb is None:
        _ffmpeg_usb = subprocess.Popen([
            'ffmpeg', '-y', '-f', 'dshow', '-i', 'video=%s' % _win_camera_dev_name,
            sound_param, '-c:v', 'libx264', '-b:v', '3000k',
            '-frag_duration', '1000', '-r', '8',
            '-f', 'segment', '-segment_time', _segment_duration, '-segment_format', 'mp4', '-reset_timestamps', '1',
            '-vf', 'drawtext=fontfile=/Windows/Fonts/arial.ttf: text=\'%{localtime\:%c}\': fontcolor=white@0.8: fontsize=32: x=10: y=10',
            '-strftime', '1',
            _usb_out_filename
        ], stdin=subprocess.PIPE)
    else:
        # check if done
        pass


def _run_ffmpeg_usb(resolution, no_sound=True):
    global _ffmpeg_usb
    if no_sound:
        sound_param = "-an"
    else:
        sound_param = ""
    if _ffmpeg_usb is None:
        _ffmpeg_usb = subprocess.Popen([
            'ffmpeg', '-y',
            '-f', 'alsa', '-thread_queue_size', '16384', '-ac', '1', '-i', 'hw:1'
            '-r', '8', '-f', 'video4linux2', '-i', _usb_camera_dev_name, '-thread_queue_size', '16384'
            '-vf', '"drawtext=text=\'%{localtime\:%c}\': fontcolor=white@0.8: fontsize=32: x=10: y=10"',
            '-s', _usb_max_resolution, sound_param, "-c:v", "h264_omx", "-b:v", "3000k",
            '-frag_duration', '1000', '-strftime', '1',
            _usb_out_filename,
        ])
            #, stdin=subprocess.PIPE)


def usb_record_loop():
    global _ffmpeg_usb, _is_recording_usb
    _is_recording_usb = True
    print "Recording USB"
    while _is_recording_usb:
        _run_ffmpeg_usb_win(no_sound=True)
        _ffmpeg_usb.wait()
        if _ffmpeg_usb.returncode is not None:
            _ffmpeg_usb.poll()
            pass
    _is_recording_usb = False


def pi_record_loop():
    global _ffmpeg_pi, _is_recording_pi
    _is_recording_pi = True
    camera = picamera.PiCamera()
    camera.resolution = _pi_max_resolution
    camera.framerate = 8
    camera.annotate_background = picamera.Color('black')
    print "Recording PI"
    _run_ffmpeg_pi(_pi_out_filename)
    camera.start_recording(_ffmpeg_pi.stdin, format='h264', bitrate=2000000)
    start = dt.datetime.now()
    while _is_recording_pi:
        camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        camera.wait_recording(0.4)
    camera.stop_recording()
    camera.close()
    _is_recording_pi = False


def thread_run():
    usb_record_loop()
    pi_record_loop()


if __name__ == '__main__':
    usb_record_loop()
