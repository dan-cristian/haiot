try:
    import picamera
    __has_picamera = True
except Exception, ex:
    __has_picamera = False
import subprocess
import os
import time
import datetime as dt
from nbstreamreader import NonBlockingStreamReader as NBSR
try:
    from common import Constant
except Exception:
    pass

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'
initialised = False

class Params:
    ffmpeg_pi = None
    ffmpeg_pi_out = None
    ffmpeg_usb = None
    ffmpeg_usb_out = None
    segment_duration = 3600  # in seconds
    is_recording_pi = False
    is_recording_usb = False
    recordings_root = '/home/haiot/recordings/'
    pi_out_filename = recordings_root + 'pi_%Y-%m-%d_%H-%M-%S.mp4'
    usb_out_filename = recordings_root + 'usb_%Y-%m-%d_%H-%M-%S.mp4'
    usb_camera_keywords = 'HD Webcam C525'
    usb_camera_dev_name = '/dev/video0'
    usb_record_hw_card = 1
    usb_record_hw_dev = 0
    usb_max_resolution = '1280x720'
    pi_max_resolution = (1296, 972)
    win_camera_dev_name = "Integrated Camera"
    pi_thread = None
    usb_thread = None
    pi_framerate = 8
    usb_framerate = 8
    pi_camera = None
    pi_bitrate = 2000000


def _get_win_cams():
    pass

# card 1: C525 [HD Webcam C525], device 0: USB Audio [USB Audio]
def _get_usb_params():
    rec = subprocess.check_output(['arecord', '-l']).split('\n')
    for line in rec:
        if len(line) > 1:
            atoms = line.split(',')
            if len(atoms) > 1:
                if Params.usb_camera_keywords in atoms[0]:
                    Params.usb_record_hw_card = atoms[0].split(':')[0].split('card ')[1]
                    Params.usb_record_hw_dev = atoms[1].split(':')[0].split(' device ')[1]
                    print "Found audio card {}:{}".format(Params.usb_record_hw_card, Params.usb_record_hw_dev)


def _run_ffmpeg_pi():
    print "Recording on {}".format(Params.pi_out_filename)
    if Params.ffmpeg_pi is None:
        Params.ffmpeg_pi = subprocess.Popen([
            'ffmpeg', '-y', '-r', str(Params.pi_framerate), '-i', '-', '-vcodec', 'copy',
            '-f', 'segment', '-segment_time', str(Params.segment_duration), '-segment_format', 'mp4',
            '-reset_timestamps', '1', '-force_key_frames', '"expr:gte(t,n_forced*10)"',
            '-frag_duration', '1000', '-strftime', '1', '-an', Params.pi_out_filename],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _run_ffmpeg_usb_win(no_sound=True):
    if no_sound:
        sound_param = "-an"
    else:
        sound_param = ""
    if Params.ffmpeg_usb is None:
        Params.ffmpeg_usb = subprocess.Popen([
            'ffmpeg', '-y', '-f', 'dshow', '-i', 'video={}'.format(Params.win_camera_dev_name),
            sound_param, '-c:v', 'libx264', '-b:v', '3000k', '-r', Params.usb_framerate,
            '-f', 'segment', '-segment_time', Params.segment_duration, '-segment_format', 'mp4',
            '-reset_timestamps', '1',
            '-force_key_frames', 'expr:gte(t,n_forced*10)',
            #'-vf', '"drawtext=fontfile=/Windows/Fonts/arial.ttf: text=\'%{localtime\:%c}\': fontcolor=white@0.8: fontsize=32: x=10: y=10"',
            '-s', '800x600', '-frag_duration', '1000',
            '-strftime', '1',
            Params.usb_out_filename])
        #, stdin=subprocess.PIPE)
        #print Params.ffmpeg_usb.returncode


# fmpeg -y -f alsa -thread_queue_size 16384 -ac 1 -i hw:1 -r 8 -f video4linux2 -thread_queue_size 8192 -i /dev/video0 -vf "drawtext=text='%{localtime\:%c}': fontcolor=white@0.8: fontsize=32: x=10: y=10" -s 1280x720 -c:v h264_omx -b:v 3000k -frag_duration 1000 -f segment -segment_time 3600 -reset_timestamps 1  -force_key_frames "expr:gte(t,n_forced*2)" -strftime 1 /home/haiot/recordings/usb_%Y-%m-%d_%H-%M-%S.mp4
def _run_ffmpeg_usb(no_sound=True):
    if no_sound:
        sound_param = "-an"
    else:
        sound_param = ""
    if Params.ffmpeg_usb is None:
        overlay = '%{localtime\:%c}'
        #cmd_line = 'ffmpeg -y -f alsa -thread_queue_size 16384 -ac 1 -i hw:{} -r 8 -f video4linux2 ' \
        #           '-thread_queue_size 8192 -i {} ' \
        #           '-vf "drawtext=text=\'{}\': fontcolor=white@0.8: fontsize=32: x=10: y=10" ' \
        #           '-s {} {} -c:v h264_omx -b:v 3000k -frag_duration 1000 -f segment -segment_time 3600 ' \
        #           '-reset_timestamps 1 -force_key_frames \"expr:gte(t,n_forced*2)\" -strftime 1 {}'.format(
        #    Params.usb_record_hw_card, Params.usb_camera_dev_name, overlay, Params.usb_max_resolution, sound_param,
        #    Params.usb_out_filename)
        #print "Executing: {}".format(cmd_line)
        #Params.ffmpeg_usb = subprocess.Popen([cmd_line], shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        #                                     stderr=subprocess.PIPE)

        Params.ffmpeg_usb = subprocess.Popen(
            ['ffmpeg', '-y', '-f', 'alsa', '-thread_queue_size', '16384', '-ac', '1',
             '-i', 'hw:{}'.format(Params.usb_record_hw_card), '-r', str(Params.usb_framerate),
             '-f', 'video4linux2', '-thread_queue_size', '16384', '-i', Params.usb_camera_dev_name,
             '-reset_timestamps', '1', '-force_key_frames', 'expr:gte(t,n_forced*10)',
             '-vf', 'drawtext=text=\'%{localtime\:%c}\': fontcolor=white@0.8: fontsize=32: x=10: y=10',
             '-s', Params.usb_max_resolution, sound_param, "-c:v", "h264_omx", "-b:v", "3000k",
             '-frag_duration', '1000', '-strftime', '1', Params.usb_out_filename],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)



def _usb_init():
    print "Recording USB"
    try:
        if Constant.IS_OS_WINDOWS():
            _run_ffmpeg_usb_win(no_sound=True)
        else:
            _run_ffmpeg_usb(no_sound=True)
            print "Recording started"
        if Params.ffmpeg_usb._child_created:
            Params.is_recording_usb = True
            Params.ffmpeg_usb_out = NBSR(Params.ffmpeg_usb.stdout)
        else:
            print "Recording process not created"
    except Exception, ex:
        print "Unable to initialise USB camera, ex={}".format(ex)


def _usb_record_loop():
    if Params.is_recording_usb:
        Params.ffmpeg_usb.poll()
        if Params.ffmpeg_usb.returncode is not None:
            Params.is_recording_usb = False
            print "usb record exit with code {}".format(Params.ffmpeg_usb.returncode)
            if Params.ffmpeg_usb.returncode != 0:
                stdout, stderr = Params.ffmpeg_usb.communicate()
                print "USB recording stopped with error"
                print stderr
        else:
            # print "USB recording ongoing"
            line = Params.ffmpeg_usb_out.readline(0.5)
            if line is not None:
                print line
    else:
        print "USB not recording"


def _pi_record_loop():
    if Params.is_recording_pi:
        Params.pi_camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Params.pi_camera.wait_recording(0.4)
        Params.ffmpeg_pi.poll()
        if Params.ffmpeg_pi.returncode is not None:
            Params.is_recording_pi = False
            print "PI record exit with code {}".format(Params.ffmpeg_pi.returncode)
            if Params.ffmpeg_pi.returncode != 0:
                stdout, stderr = Params.ffmpeg_pi.communicate()
                print "PI recording stopped with error"
                print stderr
        else:
            # print "PI is recording\n"
            line = Params.ffmpeg_pi_out.readline(0.5)
            if line is not None:
                print line
    else:
        print "PI not recording"


def _pi_init():
    if __has_picamera:
        try:
            Params.pi_camera = picamera.PiCamera()
            Params.pi_camera.resolution = Params.pi_max_resolution
            Params.pi_camera.framerate = Params.pi_framerate
            Params.pi_camera.annotate_background = picamera.Color('black')
            print "Recording PI"
            _run_ffmpeg_pi()
            Params.pi_camera.start_recording(Params.ffmpeg_pi.stdin, format='h264', bitrate=Params.pi_bitrate)
            if Params.ffmpeg_pi._child_created:
                Params.is_recording_pi = True
                Params.ffmpeg_pi_out = NBSR(Params.ffmpeg_pi.stdout)
        except Exception, ex:
            print "Unable to initialise picamera, ex={}".format(ex)
    else:
        print "No picamera module"


def _pi_stop():
    Params.pi_camera.stop_recording()
    Params.pi_camera.close()
    Params.is_recording_pi = False
    Params.ffmpeg_pi.terminate()


def _usb_stop():
    Params.ffmpeg_usb.terminate()


def unload():
    global initialised
    _pi_stop()
    _usb_stop()
    initialised = False

def init():
    global initialised
    if not os.path.exists(Params.recordings_root):
        os.makedirs(Params.recordings_root)
    _get_usb_params()
    _pi_init()
    _usb_init()
    initialised = True

def thread_run():
    if Params.is_recording_pi:
        _pi_record_loop()
    if Params.is_recording_usb:
        _usb_record_loop()


if __name__ == '__main__':
    _get_usb_params()
    _run_ffmpeg_usb(no_sound=True)
    if Params.ffmpeg_usb._child_created:
        Params.is_recording_usb = True
        print "Recording started"
        Params.ffmpeg_usb_out = NBSR(Params.ffmpeg_usb.stdout)
    else:
        print "Recording process not created"
    _pi_init()
    while True:
        _usb_record_loop()
        _pi_record_loop()
        time.sleep(2)
