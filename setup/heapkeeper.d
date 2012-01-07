#! /bin/sh

### BEGIN INIT INFO
# Provides:          Heapkeeper Django FastCGI server
# Required-Start:    networking
# Required-Stop:     networking
# Default-Start:     2 3 4 5
# Default-Stop:      S 0 1 6
# Short-Description: Start Heapkeeper Django FastCGI server
### END INIT INFO

# This is a simplified version of a script found at
# http://code.djangoproject.com/wiki/InitdScriptForDebian

set -e

# path to the directory for socket and pid files
RUNFILES_PATH=/var/run/heapkeeper
SITE_PATH=/home/hcs/Heapkeeper
RUN_AS=hcs
SITE=Heapkeeper
PYTHON=`which python`

# http://stackoverflow.com/questions/393629/what-values-to-use-for-fastcgi-maxrequests-maxspare-minspare-maxchildren/393636#393636
MAXREQUESTS=1000

PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
DESC="Heapkeeper Django FastCGI server"
NAME=$0
SCRIPTNAME=/etc/init.d/$NAME
mkdir -p $RUNFILES_PATH
chown -R $RUN_AS:$RUN_AS $RUNFILES_PATH

#
#       Function that starts the daemon/service.
#
d_start()
{
    if [ -f $RUNFILES_PATH/$SITE.pid ]; then
        echo -n " already running"
    else
        start-stop-daemon --start --quiet \
                   --pidfile $RUNFILES_PATH/$SITE.pid \
                   --chuid $RUN_AS --exec $PYTHON -- \
                   $SITE_PATH/manage.py runfcgi \
                   method=threaded maxrequests=$MAXREQUESTS \
                   host=127.0.0.1 port=8001 \
                   pidfile=$RUNFILES_PATH/$SITE.pid
        chmod 400 $RUNFILES_PATH/$SITE.pid
                 #  protocol=fcgi
                 #  socket=$RUNFILES_PATH/$SITE.socket
    fi
}

#
#       Function that stops the daemon/service.
#
d_stop() {
    # Killing all Django FastCGI processes running
    start-stop-daemon --stop --quiet --pidfile $RUNFILES_PATH/$SITE.pid \
                      || echo -n " not running"
    if [ -f $RUNFILES_PATH/$SITE.pid ]; then
       rm -f $RUNFILES_PATH/$SITE.pid
    fi
}

ACTION="$1"
case "$ACTION" in
    start)
        echo -n "Starting $DESC:"
        d_start
        echo "."
        ;;

    stop)
        echo -n "Stopping $DESC:"
        d_stop
        echo "."
        ;;

    status)
        echo "Status of $DESC:"
        if [ -f $RUNFILES_PATH/$SITE.pid ]; then
            echo " running ($(cat $RUNFILES_PATH/$SITE.pid))"
        else
            echo " not running"
        fi
        ;;

    restart|force-reload)
        echo -n "Restarting $DESC: $NAME"
        d_stop
        sleep 1
        d_start
        echo "."
        ;;

    *)
        echo "Usage: $NAME {start|stop|restart|force-reload|status} [site]" >&2
        exit 3
        ;;
esac

exit 0

