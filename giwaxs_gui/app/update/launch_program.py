# -*- coding: utf-8 -*-
import platform
import subprocess
import os


def launch_detached():
    try:
        if platform.system() == 'Windows':
            subprocess.Popen('giwaxs_gui', creationflags=subprocess.DETACHED_PROCESS)
        else:
            subprocess.Popen(['nohup', 'giwaxs_gui'], shell=False, stdout=None, stderr=None, preexec_fn=os.setpgrp)

    except subprocess.CalledProcessError:
        return -1
