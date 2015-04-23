import os
import platform

PACKAGE_NAME = 'SystemVerilog'
SRC = '..'
IGNORE_DIRS = ('.hg', '.idea', '__pycache__', 'aaa', 'test',)

my_sys = platform.system()
if my_sys == 'Windows':
    DST_ZIPPED = os.path.join(os.environ['APPDATA'],
                              'Sublime Text 3',
                              'Installed Packages',
                              '{}.sublime-package'.format(PACKAGE_NAME))

    DST_UNZIPPED = os.path.join(os.environ['APPDATA'],
                                'Sublime Text 3',
                                'Packages',
                                '{}'.format(PACKAGE_NAME))

    SUBLIME_SETTINGS_FILE = os.path.join(os.environ['APPDATA'],
                                         'Sublime Text 3',
                                         'Packages',
                                         'User',
                                         'Preferences.sublime-settings')

    PACKAGE_CONTROL_SETTINGS_FILE = os.path.join(os.environ['APPDATA'],
                                                 'Sublime Text 3',
                                                 'Packages',
                                                 'User',
                                                 'Package Control.sublime-settings')
else:
    print('[deployment] Unsupported system '+my_sys)