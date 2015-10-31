#!/bin/bash
### BEGIN INIT INFO
# Provides:          pigpiod
# Required-Start:    $network $remote_fs $syslog
# Required-Stop:     $network $remote_fs $syslog
# Should-Start:      $all
# Should-Stop:       $all
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: pigpiod services launcher
# Description:       Launches pigpiod daemon.
### END INIT INFO

# Author: dan.cristian@gmail.com


# PATH should only include /usr/* if it runs after the mountnfs.sh script
PATH=/sbin:/usr/sbin:/bin:/usr/bin:/usr/local/bin
DESC="pigpiod services launcher"
NAME="pigpiod"
SCRIPTNAME=/etc/init.d/$NAME
LOCKFILE=/var/run/$NAME.lock
DAEMON=/usr/local/bin/pigpiod
PIDFILE=/var/run/pigpiod.pid
PIGPIOD_OPTS="-s 10"

# Load the VERBOSE setting and other rcS variables
. /lib/init/vars.sh

# Define LSB log_* functions.
# Depend on lsb-base (>= 3.2-14) to ensure that this file is present
# and status_of_proc is working.
. /lib/lsb/init-functions

test -x $DAEMON || exit 5


case "$1" in
  start)
	log_daemon_msg "Starting $DESC" "$NAME"
	start-stop-daemon --start --quiet --oknodo --pidfile $PIDFILE --startas $DAEMON -- -p $PIDFILE $PIGPIOD_OPTS
	status=$?
	log_end_msg $status
	;;
  stop)
	log_daemon_msg "Stopping $DESC" "$NAME"	
	start-stop-daemon --stop --quiet --oknodo --pidfile $PIDFILE
	log_end_msg $?
	rm -f $PIDFILE
	;;
  status)
	status_of_proc $DAEMON "pigpiod"
	;;
  restart|force-reload)
	$0 stop && sleep 2 && $0 start
	;;
  *)
	echo "Usage: $SCRIPTNAME {start|stop|status|restart|force-reload}" >&2
	exit 3
	;;
esac

exit 0

