import logging
import os
import socket
import logging.handlers
import subprocess
import logging.config as lc
import sys
import time

try:
    from SystemVerilog.debug.log_config import CONFIG, COMMAND_STOP_SERVER
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
    from log_config import CONFIG, COMMAND_STOP_SERVER

lc.dictConfig(CONFIG)
alog = logging.getLogger("sv_console_debug")


def getLogger(name=''):
    return logging.getLogger(name)


def server_start():
    s = socket.socket()  # socket.AF_INET, socket.SOCK_STREAM
    # check if logging server down and run
    for attempt in range(5):
        if s.connect_ex(('localhost', CONFIG['handlers']['socket']['port'])):
            apath = os.path.join(os.path.dirname(__file__), 'log_server.py')
            # only for windows CREATE_NEW_CONSOLE
            subprocess.Popen('py {}'.format(apath), creationflags=subprocess.CREATE_NEW_CONSOLE)
            alog.warning('Trying to run logging server')
            time.sleep(1)
        else:
            alog.warning("Logging server up")
            return
    alog.error('Cannot start logging server')


def server_stop():
    s = socket.socket()
    for attempt in range(10):
        if not s.connect_ex(('localhost', CONFIG['handlers']['socket']['port'])):
            alog.warning(COMMAND_STOP_SERVER)
            time.sleep(1)
        else:
            alog.warning('Logging server stopped')
            return
    alog.error('Cannot stop logging server')


def test(aalog, s=''):
    aalog.debug("debug "+s)
    aalog.info("info "+s)
    aalog.warning("warn "+s)
    aalog.error("err "+s)


if __name__ == "__main__":
    server_start()
    test(alog, 'wazzzzzup2')
    server_stop()