import shutil
import os
import json
import zipfile


def in_installed_packages(src, dst, action="install", ignore_dirs=""):
    if os.path.exists(dst):
        os.remove(dst)
    if action == "install":
        zipf = zipfile.ZipFile(dst, 'w', compression=zipfile.ZIP_DEFLATED)
        abs_path = os.path.abspath(src)
        os.chdir(abs_path)
        for root, dirs, files in os.walk("."):
            [dirs.remove(d) for d in dirs if d in ignore_dirs]
            for file in files:
                zipf.write(os.path.join(root, file))
        zipf.close()


def in_packages(src, dst, action='install', ignore_dirs=""):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    if action == 'install':
        shutil.copytree(src=src, dst=dst, ignore=shutil.ignore_patterns(*ignore_dirs))


def change_settings(fn_settings, par_name, value, action="add"):
    if os.path.exists(fn_settings):
        with open(fn_settings) as f:
            csublime_settings = json.load(f)
            old_value = csublime_settings.get(par_name, [])
            if action == "add" and value not in old_value:
                csublime_settings[par_name] = old_value + [value]
            elif action == "del" and value in old_value:
                csublime_settings[par_name].remove(value)
            with open(fn_settings, "w") as wf:
                json.dump(obj=csublime_settings, fp=wf, indent=4, sort_keys=True)
    elif action == "add":
        with open(fn_settings, 'w') as f:
            json.dump('{"{par_name}": [{value}]}'.format(par_name=par_name, value=value), fp=f, indent=4, sort_keys=True)
