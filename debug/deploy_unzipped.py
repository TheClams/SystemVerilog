import util
from deploy_config import PACKAGE_CONTROL_SETTINGS_FILE, SUBLIME_SETTINGS_FILE, PACKAGE_NAME, SRC, DST_UNZIPPED, IGNORE_DIRS
import time

print('[deploy] Deployment to Packages ...')

util.change_settings(PACKAGE_CONTROL_SETTINGS_FILE,
                     "auto_upgrade_ignore", PACKAGE_NAME, action='add')
util.change_settings(PACKAGE_CONTROL_SETTINGS_FILE,
                     "in_process_packages", PACKAGE_NAME, action='add')
util.change_settings(SUBLIME_SETTINGS_FILE,
                     "ignored_packages", PACKAGE_NAME, action='add')

time.sleep(2)
util.in_packages(src=SRC, dst=DST_UNZIPPED, action='install', ignore_dirs=IGNORE_DIRS)
time.sleep(1)

util.change_settings(SUBLIME_SETTINGS_FILE,
                     "ignored_packages", PACKAGE_NAME, action='del')
util.change_settings(PACKAGE_CONTROL_SETTINGS_FILE,
                     "in_process_packages", PACKAGE_NAME, action='del')

print('[deploy] Deployment to Packages DONE')