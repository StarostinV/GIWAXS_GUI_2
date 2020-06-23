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
        #
        # elif platform.system() == 'Darwin':
        #     return -1
            # subprocess.Popen(['/usr/bin/open',
            #                   '-n', '-a', 'Terminal', '/usr/local/bin/node', 'index.js'],
            #                  shell=False)
            # with open("start_node.command", "w") as f:
            #     f.write("#!/bin/sh\nnode index.js\n")
            #     os.chmod('myfile', stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH)
            # subprocess.Popen(['/usr/bin/open', '-n', '-a', 'Terminal', 'start_node.command'], shell=False)

    except subprocess.CalledProcessError:
        return -1
