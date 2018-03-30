import subprocess

#   PID TTY      STAT   TIME COMMAND
# 4222 pts/1    Ss     0:00 -bash
# 4555 pts/1    R      8:49 ffmpeg -y -f alsa -thread_queue_size 8192 -ac 1 -i hw:1,0 -r 8 -f video4linux2 -thread_queue_size 8192 -i /dev/v4l/by-id/usb-046d_HD_
def get_proc(keywords):
    res = None
    try:
        out = subprocess.check_output(['ps', 'aww']).split('\n')
        for line in out:
            if keywords in line:
                atoms = line.strip().split(' ')
                if atoms[0].isdigit():
                    res = int(atoms[0])
    except Exception, ex:
        print("Got exception on proc find, err={}".format(ex))
    return res


if __name__ == '__main__':
    print get_proc('/home/haiot/recordings/' + '%Y-%m-%d_%H-%M-%S_usb.mp4')
