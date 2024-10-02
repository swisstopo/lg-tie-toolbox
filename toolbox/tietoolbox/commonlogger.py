import os
import sys

import time
import glob
import tempfile

import logging
import logging.handlers


try:
    import arcpy

    has_arcpy = True
    temp_dir = arcpy.env.scratchFolder
except ImportError:
    has_arcpy = False
    temp_dir = tempfile.mkdtemp()
    if not os.path.isdir(temp_dir):
        os.makedirs(temp_dir)


# See https://community.esri.com/t5/python-questions/use-of-logging-module-in-python-toolbox/td-p/1248620


# Log handler that forwards messages to ArcGIlog
class ArcGisHandler(logging.Handler):
    is_run_from_cmd_line = sys.stdin is not None and sys.stdin.isatty()

    terminator = ""

    def __init__(self, level=10):
        # throw logical error if arcpy not available
        if not has_arcpy:
            raise EnvironmentError(
                "The ArcPy handler requires an environment with ArcPy, a Python environment with "
                "ArcGIS Pro or ArcGIS Enterprise."
            )

        # call the parent to cover rest of any potential setup
        super(ArcGisHandler).__init__(level=level)

    def emit(self, record):
        if not self.is_run_from_cmd_line:
            msg = self.format(record)

            # route anything NOTSET (0), DEBUG (10) or INFO (20) through AddMessage
            if record.levelno <= 20:
                arcpy.AddMessage(msg)

            # route all WARN (30) messages through AddWarning
            elif record.levelno == 30:
                arcpy.AddWarning(msg)

            # everything else; ERROR (40), FATAL (50) and CRITICAL (50), route through AddError
            else:
                arcpy.AddError(msg)


# Set up logging
def get(log_name, log_to_file=True):
    if log_to_file:
        # Something like \\v0t0020a.adr.admin.ch\vdiuser$\U80795753\data\Documents\ArcGIS\scratch\logs
        LOG_FILE = os.path.join(
            temp_dir, "logs", log_name, log_name + "_%i.log" % os.getpid()
        )

        # Compute the full path for this process and make sure the directory exists
        if not os.path.exists(os.path.dirname(LOG_FILE)):
            os.makedirs(os.path.dirname(LOG_FILE))

        # Clean up old log files
        if not os.path.exists(LOG_FILE):
            for file in glob.glob(
                os.path.join(temp_dir, "logs", log_name, log_name + "_*.log")
            ):
                if time.time() - os.path.getmtime(file) > 2 * 60 * 60 * 24:
                    try:
                        os.remove(file)
                    except BaseException:
                        pass

    logger = logging.getLogger(log_name)
    logger.disabled = False
    logger.setLevel(logging.DEBUG)

    if len(logger.handlers) == 0:
        # File handler for detailed tracing
        if log_to_file:
            try:
                file_formatter = logging.Formatter(
                    "%(asctime)s -  %(levelname)s - %(module)s - %(message)s"
                )
                file_handler = logging.FileHandler(LOG_FILE)
                file_handler.setFormatter(file_formatter)
                file_handler.setLevel(logging.DEBUG)
                logger.addHandler(file_handler)
            except BaseException as e:
                logger.exception("Cannot configure the 'Fileandler: {}'".format(e))
        # Standard out handler
        try:
            stream_formatter = logging.Formatter("%(levelname)s - %(message)s")
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setFormatter(stream_formatter)
            stream_handler.setLevel(logging.INFO)
            logger.addHandler(stream_handler)
        except BaseException as e:
            logger.exception("Cannot configure the 'StreamHandler': {}".format(e))
        # Custom handler to send messages to ArcGIS
        try:
            if sys.version_info.major >= 2 and has_arcpy:
                arc_formatter = logging.Formatter(
                    "%(asctime)s - %(message)s", "%H:%M:%S"
                )
                arc_handler = ArcGisHandler()
                arc_handler.setFormatter(arc_formatter)
                arc_handler.setLevel(logging.INFO)
                logger.addHandler(arc_handler)
        except BaseException as e:
            logger.exception("Cannot configure the 'ArcGisHandler': {}".format(e))

    return logger
