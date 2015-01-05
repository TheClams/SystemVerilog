import shutil
import os
import platform
import logger

def deployment(action='install'):
    my_sys = platform.system()

    if my_sys == 'Windows':
        src = os.path.join('..', '..', 'sublimesystemverilog')
        dst = os.path.expandvars(os.path.join('%APPDATA%', 'Sublime Text 3', 'Packages', 'SystemVerilog'))

        if os.path.exists(dst):
            shutil.rmtree(dst)

        if action == 'install':
            shutil.copytree(src=src, dst=dst, ignore=shutil.ignore_patterns(".hg", ".idea"))
            print('[deployment] Deployment DONE')
        elif action == 'uninstall':
            print('[deployment] Undeployment DONE')
        else:
            print('[deployment] Unknown command')
    else:
        print('[deployment] Unsupported system ' + my_sys)