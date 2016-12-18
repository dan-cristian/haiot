#!/bin/bash
# Dashing service
# Add this file to /etc/init.d/
# $ sudo cp dashboard /etc/init.d/
# Update variables the variables to suit your installation
# $ sudoedit /etc/init.d/dashboard
# Make executable
# $ sudo chmod 755 /etc/init.d/dashboard
# Update rc.d
# $ sudo update-rc.d dashboard defaults
# Dashboard will start at boot. Check out the boot log for trouble shooting "/var/log/boot.log"
# USAGE: start|stop|restart|status

### BEGIN INIT INFO
# Provides:          dashboard
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Start daemon at boot time
# Description:       Enable service provided by daemon.
### END INIT INFO

set -e
. /lib/lsb/init-functions

# Must be a valid filename
NAME=smashing
DASHING_DIR=/home/haiot/dashiot
PIDFILE="$DASHING_DIR/$NAME.pid"
DAEMON=/usr/local/bin/$NAME
GEM_HOME=/var/lib/gems/2.3.0

DASHING_PORT=8080
DAEMON_OPTS="start -d -p $DASHING_PORT -P $PIDFILE --tag $NAME -D"

RUNUSER=haiot
RUNGROUP=haiot

test -x $DAEMON || { log_failure_msg "$NAME not installed";exit 1; }

function checkuser() {
  if [[ $UID != 0 ]]; then
    if [[ `whoami` != "$RUNUSER" ]]; then
      log_failure_msg "$1 must be run as root or $RUNUSER"
      exit 1
    fi
  fi
}

function start_dashing() {
  log_action_msg "Starting daemon: $NAME" || true
  sleep 5
  start-stop-daemon --verbose --quiet --start --chuid $RUNUSER:$RUNGROUP --chdir $DASHING_DIR --exec $DAEMON -- $DAEMON_OPTS
  log_end_msg 0
}

function stop_dashing() {
  log_action_msg "Stopping daemon: $NAME" || true
  start-stop-daemon --quiet --stop --pidfile $PIDFILE --user $RUNUSER --retry 30 --oknodo
  log_end_msg 0
}


case "$1" in
  start)
    checkuser start
    start_dashing
  ;;
  stop)
    checkuser stop
    stop_dashing
  ;;
  restart)
    checkuser restart
    log_action_msg "Restarting daemon: $NAME"
    stop_dashing
    start_dashing
  ;;
  status)
    status_of_proc -p $DAEMON $NAME
  ;;
  logs)
    tail -F $DASHING_DIR/log/thin.log
  ;;
  *)
  echo "Usage: "$1" {start|stop|restart|status}"
  exit 1
esac

exit 0
