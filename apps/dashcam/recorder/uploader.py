import subprocess
import threading
import prctl
from stat import S_ISREG, ST_CTIME, ST_MODE, ST_MTIME
import os, sys, time, datetime
import shutil
import utils
from collections import namedtuple
try:
    from main.logger_helper import L
except Exception:
    class L:
        class l:
            @staticmethod
            def info(msg): print msg
            @staticmethod
            def warning(msg): print msg
            @staticmethod
            def error(msg): print msg


disk_ntuple = namedtuple('partition',  'device mountpoint fstype')
usage_ntuple = namedtuple('usage',  'total used free percent')


class P():
    have_internet_file = '/tmp/haveinternet'
    have_wlan = '/tmp/havewlan'
    server = 'haiot@192.168.0.9'
    port = '22'
    dest_folder = '/mnt/motion/tmp/timelapse/dashcam/'  # need trailing /
    include_ext = '.mkv'
    root_mountpoint = None
    root_folder = None
    std_out_folder = None
    uploaded_folder = None
    exclude_time_delta = 120 # exclude files modified in the last x seconds
    days_to_keep = 30
    max_disk_used_percent = 80 #
    disk_usage_adjust = 4 # adjust usage percent (add to reported one)
    upload_batch = 2
    current_upload_file = None
    app_is_exiting = False
    folder_dict = set()


def disk_partitions(all_part=False):
    """Return all mountd partitions as a nameduple.
    If all == False return phyisical partitions only.
    """
    #https://stackoverflow.com/questions/4260116/find-size-and-free-space-of-the-filesystem-containing-a-given-file
    phydevs = []
    retlist = []
    fs = "/proc/filesystems"
    if os.path.isfile(fs):
        f = open(fs, "r")
        for line in f:
            if not line.startswith("nodev"):
                phydevs.append(line.strip())
        f = open('/etc/mtab', "r")
        for line in f:
            if not all_part and line.startswith('none'):
                continue
            fields = line.split()
            if len(fields) >= 3:
                device = fields[0]
                mountpoint = fields[1]
                fstype = fields[2]
                if not all_part and fstype not in phydevs:
                    continue
                if device == 'none':
                    device = ''
                ntuple = disk_ntuple(device, mountpoint, fstype)
                retlist.append(ntuple)
    else:
        L.l.error("Unable to read disk partitions due to missing file {}".format(fs))
    return retlist


def disk_usage(path):
    """Return disk usage associated with path."""
    st = os.statvfs(path)
    free = (st.f_bavail * st.f_frsize)
    total = (st.f_blocks * st.f_frsize)
    used = (st.f_blocks - st.f_bfree) * st.f_frsize
    try:
        percent = ret = (float(used) / total) * 100
    except ZeroDivisionError:
        percent = 0
    # NB: the percentage is -5% than what shown by df due to
    # reserved blocks that we are currently not considering:
    # http://goo.gl/sWGbH
    return usage_ntuple(total, used, free, round(percent, 1))


def _upload_file(file_path, file_date):
    start = time.time()
    fd = datetime.datetime.fromtimestamp(file_date)
    subfolder = str(fd.year) + '-' + str(fd.month) + '-' + str(fd.day) + '/'
    if subfolder not in P.folder_dict:
        #ssh -T -p 222 -c arcfour -o Compression=no $SSH_SERVER "mkdir -p $dest_parent"
        res = subprocess.check_output(['ssh -T -p ' + P.port + ' -c arcfour -o Compression=no ' +
                                       P.server + ' "mkdir -p "' + P.dest_folder + subfolder], shell=True)
        L.l.info('Created folder {}, res=[{}]'.format(subfolder, res))
        P.folder_dict.add(subfolder)
    L.l.info('Uploading file {}]'.format(file_path))
    P.current_upload_file = file_path
    # rsync -avrPe 'ssh -p 22 -T -c arcfour -o Compression=no -x ' 2017-12-25_13-26-08_pi.mp4 haiot@$192.168.0.9://mnt/motion/tmp/timelapse/dashcam
    res = subprocess.check_output(['rsync -avrPe "ssh -p ' + P.port + ' -T -c arcfour -o Compression=no -x" ' +
                                   '"' + file_path + '" ' + P.server + ':' + P.dest_folder + subfolder], shell=True)
    duration_min = (time.time() - start) / 60
    L.l.info('Uploaded file {}, res=[{}], duration in mins={}'.format(file_path, res, duration_min))
    P.current_upload_file = None


def _file_list(folder, exclude_delta=0):
    # https://stackoverflow.com/questions/168409/how-do-you-get-a-directory-listing-sorted-by-creation-date-in-python
    # get all entries in the directory w/ stats
    entries = (os.path.join(folder, fn) for fn in os.listdir(folder))
    entries = ((os.stat(path), path) for path in entries)

    # leave only regular files, insert creation date
    entries = ((stat[ST_MTIME], path) for stat, path in entries if S_ISREG(stat[ST_MODE]))
    # NOTE: on Windows `ST_CTIME` is a creation date
    #  but on Unix it could be something else
    # NOTE: use `ST_MTIME` to sort by a modification date

    result = []
    now = time.time()
    for cdate, path in sorted(entries, reverse=True):
        if P.include_ext in path:
            # print time.ctime(cdate), path
            delta_sec = (now - cdate)
            if delta_sec > exclude_delta:
                result.append([path, cdate])
                #Log.logger.info('Added {}'.format(path))
    return result


def _upload():
    # try to upload only if fast internet via wlan is available
    if os.path.isfile(P.have_internet_file) and os.path.isfile(P.have_wlan):
        files = _file_list(P.root_folder, exclude_delta=P.exclude_time_delta)
        count = 0
        for f in files:
            if P.app_is_exiting is True:
                break
            try:
                _upload_file(file_path=f[0], file_date=f[1])
                shutil.move(f[0], P.uploaded_folder)
                L.l.info('File {} moved to {}'.format(f[0], P.uploaded_folder))
                count += 1
                if count == P.upload_batch:
                    break
            except Exception as ex:
                L.l.info('Exception uploading file {}, ex={}'.format(f[0], ex))


def _clean_old(days_to_keep, folder):
    files = _file_list(folder)
    for file in files:
        now = time.time()
        try:
            delta_days = (now - file[1]) / (60*60*24)
            if delta_days > days_to_keep:
                os.remove(file[0])
                L.l.info('Old {} days file deleted {}'.format(delta_days, file[0]))
        except Exception as ex:
            pass


def _clean_space():
    days_keep = P.days_to_keep
    folder = P.uploaded_folder
    keep_try = True
    while keep_try:
        for parti in disk_partitions():
            if parti.mountpoint == P.root_mountpoint:
                usage = disk_usage(parti.mountpoint).percent + P.disk_usage_adjust
                if usage > P.max_disk_used_percent:
                    L.l.info('Disk usage is {}, removing files older than {} to stay at {}'.format(
                        usage, days_keep, P.max_disk_used_percent))
                    if days_keep > 0:
                        _clean_old(days_keep, folder)
                        days_keep -= 1
                    else:
                        L.l.warning('Warning, need to remove files from files not uploaded folder {}'.format(
                            P.root_folder))
                        if days_keep > 0:
                            days_keep = P.days_to_keep
                            if folder == P.root_folder:
                                # secondly clean this
                                folder = P.std_out_folder
                            else:
                                # first clean this
                                folder = P.root_folder
                        else:
                            L.l.info('Something is wrong, cannot free up more space!')
                            keep_try = False
                            break
                else:
                    #Log.logger.info('Disk usage is {}'.format(usage))
                    keep_try = False
                    break


def unload():
    P.app_is_exiting = True
    if P.current_upload_file is not None:
        while True:
            pid = utils.get_proc(P.current_upload_file)
            if pid is not None:
                L.l.info('Killing hanging rsync with pid {} on file {}'.format(pid, P.current_upload_file))
                os.kill(pid, 15)
                new_pid = utils.get_proc(P.current_upload_file)
                if new_pid == pid:
                    # force kill
                    os.kill(pid, 9)
            else:
                break


def thread_run():
    prctl.set_name("uploader")
    threading.current_thread().name = "uploader"
    _upload()
    _clean_space()


if __name__ == '__main__':
    #for part in disk_partitions():
    #    Log.logger.info(part)
    #    Log.logger.info("%s\n" % str(disk_usage(part.mountpoint)))
    P.root_folder = '/home/haiot/recordings/'
    P.uploaded_folder = '/home/haiot/recordings/uploaded/'
    P.root_mountpoint = '/'
    _clean_space()
    _upload()
