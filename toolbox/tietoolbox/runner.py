from __future__ import print_function

import sys
import platform
import os

import threading
import queue

import arcpy

from subprocess import CalledProcessError, Popen, PIPE, STDOUT

sys.dont_write_bytecode = True


running_windows = platform.system() == "Windows"

if running_windows:
    from subprocess import STARTUPINFO, STARTF_USESHOWWINDOW


def default_callback(value):
    """
    A simple default callback that outputs using the print function. When
    tools are called without providing a custom callback, this function
    will be used to print to standard output.
    """
    print(value)
    sys.stdout.flush()


class Runner(object):
    """
    An object for interfacing with the WhiteboxTools executable.
    """

    def __init__(self, start_minimized=False):
        self.work_dir = ""
        self.verbose = True
        self.start_minimized = start_minimized

        self.cancel_op = False
        self.default_callback = default_callback

    def running(
        self, cmd, working_dir=None, timeout_sec=5, callback=None, minimized=False
    ):
        def t_read_stdout(process, queue):
            """Read from stdout"""

            for output in iter(process.stdout.readline, b""):
                queue.put(output)

            return

        if working_dir is None:
            working_dir = os.path.dirname(os.path.realpath(__file__))
        if callback is None:
            callback = self.default_callback

        try:
            if minimized:
                si = STARTUPINFO()
                si.dwFlags = STARTF_USESHOWWINDOW
                si.wShowWindow = 7  # Set window minimized and not activated

                process = Popen(
                    cmd,
                    stdout=PIPE,
                    stderr=STDOUT,
                    bufsize=0,
                    cwd=working_dir,
                    close_fds=False,
                    shell=True,
                    startupinfo=si,
                )
            else:
                process = Popen(
                    cmd,
                    stdout=PIPE,
                    stderr=STDOUT,
                    bufsize=0,
                    cwd=working_dir,
                    close_fds=False,
                    shell=True,
                )

            q = queue.Queue()
            t_stdout = threading.Thread(target=t_read_stdout, args=(process, q))
            t_stdout.daemon = True
            t_stdout.start()

            while process.poll() is None or not q.empty():
                try:
                    output = q.get(timeout=timeout_sec)

                except queue.Empty:
                    continue

                if not output:
                    continue

                (callback(">>> {}".format(output.rstrip())),)

            t_stdout.join()
            return 0

        except (OSError, ValueError, CalledProcessError) as err:
            callback(err)
            return 1
        output, error = process.communicate()
        if process.returncode != 0:
            callback("Command failed %d %s %s" % (process.returncode, output, error))

            raise arcpy.ExecuteError(
                "Command failed %d %s %s" % (process.returncode, output, error)
            )
        else:
            callback(output)
            return output

    def run_tool(self, args, callback=None, working_dir=None):
        """
          Runs a tool and specifies tool arguments.
        Returns 0 if completes without error.
        Returns 1 if error encountered (details are sent to callback).
        Returns 2 if process is cancelled by user.
        """
        if working_dir is None:
            working_dir = os.path.dirname(os.path.realpath(__file__))
        print(working_dir)
        try:
            if callback is None:
                callback = self.default_callback

            proc = None

            if self.start_minimized == True:
                si = STARTUPINFO()
                si.dwFlags = STARTF_USESHOWWINDOW
                si.wShowWindow = 7  # Set window minimized and not activated
                proc = Popen(
                    args,
                    shell=False,
                    stdout=PIPE,
                    stderr=STDOUT,
                    bufsize=1,
                    universal_newlines=True,
                    startupinfo=si,
                    cwd=working_dir,
                )
            else:
                proc = Popen(
                    args,
                    shell=False,
                    stdout=PIPE,
                    stderr=STDOUT,
                    bufsize=1,
                    universal_newlines=True,
                )

            while proc is not None:
                line = proc.stdout.readline()
                sys.stdout.flush()
                if line != "":
                    if not self.cancel_op:
                        if self.verbose:
                            callback(line.strip())
                    else:
                        self.cancel_op = False
                        proc.terminate()
                        return 2
                else:
                    break

            return 0
        except (OSError, ValueError, CalledProcessError) as err:
            callback(str(err))
            return 1
