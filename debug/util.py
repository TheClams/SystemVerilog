import shutil
import os
import platform
import logger

alog = logger.getLogger('sv_console_debug')


def deployment(action='install'):
    my_sys = platform.system()

    if my_sys == 'Windows':
        src = os.path.join('..', '..', 'sublimesystemverilog')
        dst = os.path.expandvars(os.path.join('%APPDATA%', 'Sublime Text 3', 'Packages', 'SystemVerilog'))

        if os.path.exists(dst):
            shutil.rmtree(dst)

        if action == 'install':
            shutil.copytree(src=src, dst=dst, ignore=shutil.ignore_patterns(".hg", ".idea"))
            alog.warning('Deployment DONE')
        elif action == 'uninstall':
            alog.warning('Undeployment DONE')
        else:
            alog.warning('Unknown command')
    else:
        alog.warning('Unsupported system ' + my_sys)