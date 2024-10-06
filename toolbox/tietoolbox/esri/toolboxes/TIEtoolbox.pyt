# ruff: noqa: E501, UP032, UP004

# UP032 Use f-string instead of `format` call (python2!)
# UP004 [*] Class `...` inherits from `object` (python2!)

from six.moves import configparser
import imp
import json
import logging
import os
import shlex
import socket
import subprocess
import sys
import threading
import time
import traceback
from math import ceil, floor
from subprocess import Popen, PIPE
from threading import Timer
import errno
import six
import traceback

import arcpy

try:
    from tietoolbox import utils
except ImportError:
    current_dir = os.path.dirname(os.path.realpath(__file__))
    module_dir = os.path.abspath(os.path.join(current_dir, "../../.."))
    sys.path.append(module_dir)
    arcpy.AddError(sys.path)

try:
    from queue import Queue, Empty
except ImportError:
    from Queue import Queue, Empty  # python 2.x
import subprocess, threading

# Windows only
from subprocess import (
    PIPE,
    STARTF_USESHOWWINDOW,
    STARTUPINFO,
    STDOUT,
    CalledProcessError,
    Popen,
)
from threading import Timer

from tietoolbox import commonlogger, feature_exporter, utils, runner as tie_runner
from tietoolbox.runner import Runner

# TODO: disabling
DEBUG = True
MAX_LINES = 1000
DEM_DATASET_NAME = "ch.swisstopo.swissalti3d"

if DEBUG:
    sys.dont_write_bytecode = True
    imp.reload(tie_runner)

# Python2,3

# Global variable to store the config path
project_config_path = None
tool_data = dict()


class PythonNotFound(Exception):
    pass


class GeoprocessingCancelException(Exception):
    pass


def is_running_in_arcgis():
    try:
        mxd = arcpy.mapping.MapDocument("CURRENT")
        return True
    except RuntimeError:
        print("Not using ArcMap")

    return False


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "TIE Analysis Toolbox"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [Exporter, Downloader, Analysis, Viewer]


class Tool(object):
    def __init__(self):
        self.config_path = r"H:\config\geocover\geocover.ini"  # Class variable shared by all subclasses
        self._config = None
        self.hostname = socket.gethostname()
        self.proxy = False

        self._get_proxy()
        self.cancel_op = False
        self._cache_dir = None
        self._python_exe = None
        self._conda_env_path = None
        self.conda_env_name = None
        self.output = Queue()
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.stop_event = threading.Event()
        if not os.path.isdir(self.cache_dir):
            try:
                os.makedirs(self.cache_dir)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise

    @property
    def cache_dir(self):
        if self._cache_dir is None:
            self._cache_dir = os.path.expandvars("%TEMP%")
        return self._cache_dir

    @property
    def config(self):
        if self._config:
            return self._config
        return self._load_config()

    @property
    def conda_env_path(self):
        if self._conda_env_path is None:
            self._conda_env_path = self.config.get(
                self.hostname, "tie_conda_env"
            ).strip()
        return self._conda_env_path

    def _load_config(self):
        # geocover.ini
        self._config = configparser.ConfigParser()
        try:
            self._config.read(self.config_path)
            sections = self._config.sections()
            for section in sections:
                if not section == section.lower():
                    self._config.add_section(section.lower())
                    for key, val in self._config.items(section):
                        self._config.set(section.lower(), key, val)
                    self._config.remove_section(section)

            # arcpy.AddMessage(self._config)
            return self._config

        except IOError as e:
            arcpy.AddError("Cannot load config {}: {}".format(self.config_path, e))
            sys.exit(2)

    def get_path(self, name):
        # H:\code\arcmap-tie-toolbox\toolbox\tietoolbox\esri\toolboxes
        path = os.path.abspath(os.path.join(self.current_dir, "../../.."))
        arcpy.AddMessage(path)
        for root, dirs, files in os.walk(path):
            if name in files:
                script_path = os.path.join(root, name)
                arcpy.AddMessage("Found script at {}".format(script_path))
                return script_path
        return None

    @property
    def python_exe(self, exe_name="python.exe"):
        if self._python_exe is not None:
            return self._python_exe
        if six.PY3:
            if sys.platform != "win32":
                return sys.executable
            for path in sys.path:
                assumed_path = os.path.join(path, exe_name)
                if os.path.isfile(assumed_path):
                    return assumed_path
            raise arcpy.ExecuteError("Python executable not found")

        else:
            try:
                python_exe = os.path.join(self.conda_env_path, exe_name)
                arcpy.AddMessage("Python exe: {}".format(python_exe))

                self.conda_env_name = os.path.basename(self.conda_env_path)

                # TODO: absolute path
                """os.environ["GDAL_DATA"] = os.path.join(
                    conda_env_path, r"\Library\share\gdal"
                )"""

                out = subprocess.check_output([python_exe, "--version"])
                arcpy.AddMessage(type(out))
                if "Python 3.9." in out:
                    arcpy.AddMessage(out)
                    self._python_exe = python_exe
                    return python_exe
                else:
                    raise arcpy.ExecuteError
                    arcpy.AddError("Python 3 not found or wrong version")

            except Exception as e:
                tb = sys.exc_info()[2]
                tbinfo = traceback.format_tb(tb)[0]

                # Concatenate information together concerning the error into a message string
                pymsg = (
                    "PYTHON ERRORS:\nTraceback info:\n"
                    + tbinfo
                    + "\nError Info:\n"
                    + str(sys.exc_info()[1])
                )
                msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages(2) + "\n"

                # Return Python error messages for use in script tool or Python window
                arcpy.AddError(pymsg)
                arcpy.AddError(msgs)
                arcpy.AddError("Problem with '{}': {}".format(python_exe, e))
                raise arcpy.ExecuteError

    def _get_proxy(self):
        if self.proxy == False:
            self.proxy = self.config.get(self.hostname, "proxy")

    def default_callback(self, value):
        """
        A simple default callback that outputs using the print function. When
        tools are called without providing a custom callback, this function
        will be used to print to standard output.
        """
        arcpy.AddMessage(value)


class Exporter(Tool):
    def __init__(self, **kwds):
        """Define the tool (tool name is the name of the class)."""
        self.label = "A - Exporter"
        self.description = ""
        self.canRunInBackground = False
        super(Exporter, self).__init__(**kwds)

    def getParameterInfo(self):
        # Define parameter definitions

        # First parameter
        param0 = arcpy.Parameter(
            displayName="Output directory",
            name="out_directory",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input",
        )

        # Set the filter to accept only local (personal or file) geodatabases
        # param0.filter.list = ["Local Database"]

        param0.value = r"D:\Projects"

        param1 = arcpy.Parameter(
            displayName="Project name",
            name="project_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )

        param2 = arcpy.Parameter(
            displayName="Output",
            name="out_param",
            datatype="GPString",
            parameterType="Derived",
            direction="Output",
        )
        param1.value = "Guggisberg"

        params = [param0, param1, param2]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        global tool_data
        start = time.time()

        # TODO: to be removed once debugged
        imp.reload(feature_exporter)

        # TODO: what to do with GDB
        base_directory = parameters[0].valueAsText
        project_name = parameters[1].valueAsText

        out_directory = os.path.join(base_directory, project_name)

        output_gdb = os.path.join(out_directory, "geocover.gdb")

        if not os.path.isdir(out_directory):
            os.makedirs(out_directory)
            # TODO: check if GDB alreday exist (update)

        # TODO
        if is_running_in_arcgis:
            project_path = "CURRENT"
        else:
            pass

        project_path = os.environ.get("MXD_PROJECT_PATH", "CURRENT")

        # cur_dir = os.path.dirname(os.path.abspath(__file__))
        # project_path = os.path.join(cur_dir, "test.mxd")

        # raise Exception(project_path)

        fe = feature_exporter.FeaturesExporter(project_path, output_gdb)

        fe._get_extent()

        config_path = os.path.join(out_directory, "config.json")
        cfg = {}
        if os.path.isfile(config_path):
            try:
                with open(config_path, "rb") as f:
                    cfg = json.load(f)
            except (IOError, json.JSONDecodeError) as e:
                arcpy.AddError("Cannot open config file {}: {}".format(config_path, e))

        project_config_path = config_path
        tool_data["project_config_path"] = config_path
        minx, miny, maxx, maxy = fe.extent
        cfg["gdb"] = output_gdb
        cfg["bbox"] = [ceil(minx), ceil(miny), floor(maxx), floor(maxy)]
        cfg["name"] = project_name
        cfg["project_dir"] = out_directory

        fe._create_extent()

        # TODO: should be a config
        lyrs_to_export = [
            ("Bedrock", "Bedrock_HARMOS_<40000"),
            ("Lines", "Linear Objects_Bruch"),
            ("Lines", "Linear Objects_Ueberschiebung"),
        ]

        for grp, lyr_name in lyrs_to_export:
            arcpy.AddMessage("=== Export layer: {} ===".format(lyr_name))
            # Linear Objects_Bruch  KIND IN (14901002,14901004,14901005,14901006,14901007,14901008)
            # Linear Objects_Ueberschiebung KIND = 14901001
            lyr = fe.get_layer(lyr_name)
            if lyr is None:
                arcpy.AddError("Cannot find layer: {}".format(lyr_name))
                continue
            # TODO
            lyr.visible = True
            # arcpy.RefreshTOC()
            # arcpy.RefreshActiveView()
            layername = fe.export_from(lyr)
            # TODO: rethink the all thing
            # Lines may be inexisting
            if layername is not None and grp != "Bedrock":
                lyr_cfg = {"source": output_gdb, "layer": layername}
                try:
                    if grp in cfg:
                        cfg[grp].append(lyr_cfg)
                    else:
                        cfg[grp] = [lyr_cfg]
                except Exception as e:
                    arcpy.AddError(cfg)

        # Merge exported layers
        merged_layername = fe.merge_layers()

        cfg["Lines"] = {
            "source": output_gdb,
            "layer": merged_layername,
            "attribute": "KIND",
        }
        cfg["Bedrock"] = {
            "source": output_gdb,
            "layer": "Bedrock_HARMOS_lt40000_Extract",
            "attribute": "TOPGIS_GC_GC_BED_FORM_ATT_FMAT_LITSTRAT",
        }
        # DEM
        cfg["DEM"] = {
            "source": os.path.join(out_directory, "swissalti3d-2.0-mosaic.tif"),
            "resolution": "2.0",
        }
        # TypeError: a bytes-like object is required, not 'str'

        try:
            if six.PY2:
                with open(config_path, "wb") as f:
                    f.write(json.dumps(cfg, indent=4))
            else:
                with open(config_path, "w") as f:
                    f.write(json.dumps(cfg, indent=4))
            arcpy.AddMessage("Config written to: {}".format(config_path))
            arcpy.SetParameter(2, "Hello")
        except IOError as e:
            arcpy.AddError("Cannot write to {}".format(config_path))

        arcpy.AddMessage("Elapsed: {}s".format(time.time() - start))

        # Cleanup
        try:
            del fe
        except Exception as e:
            arcpy.AddError("Error while cleaning up: {}".format(e))

        return True


class Downloader(Tool):
    def __init__(self, **kwds):
        """Define the tool (tool name is the name of the class)."""
        self.label = "B - Downloader (DEM)"
        self.description = ""
        self.canRunInBackground = False
        super(Downloader, self).__init__(**kwds)

    def getParameterInfo(self):
        global tool_data
        # Define parameter definitions

        # First parameter
        param0 = arcpy.Parameter(
            displayName="Config file",
            name="in_config",
            datatype="DEFile",
            parameterType="Required",
            direction="Input",
        )

        param0.value = tool_data.get("project_config_path")

        param1 = arcpy.Parameter(
            displayName="Extent layer",
            name="layer_extent",
            datatype="GPLayer",
            parameterType="Optional",
            direction="Input",
        )

        params = [param0, param1]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        project_cfg_path = tool_data.get("project_config_path")
        if project_cfg_path and os.path.isfile(project_cfg_path):
            parameters[0].value = project_cfg_path
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        config_file = parameters[0].valueAsText
        # TODO DEM source (mosaic_path)

        (
            os.path.join(
                self.conda_env_path,
                "Lib",
                "site-packages",
                "geocover_utils",
                "swissalti.py",
            ),
        )

        script_path = os.path.join(self.conda_env_path, "Scripts", "swissalti")
        if script_path is None:
            arcpy.AddError("Cannot find script path: 'swissalti'")
            raise arcpy.ExecuteError

        cmd_args = [
            self.python_exe,
            # TODO: absolute path
            script_path,
            "--dataset",
            DEM_DATASET_NAME,
            "--yes",
            "--cache-directory",
            self.cache_dir,
            "--cache-delete",
            "--log-level",
            "INFO",
            "--resolution",
            "2.0",
            "--proxy",
            self.proxy,
            "-c",
            config_file,
        ]

        extent_lyr = parameters[1]
        OFFSET = 1000
        if extent_lyr.valueAsText is not None:
            desc = arcpy.Describe(extent_lyr)
            ext = desc.extent
            extent = (
                ext.XMin - OFFSET,
                ext.YMin - OFFSET,
                ext.XMax + OFFSET,
                ext.YMax + OFFSET,
            )

            cmd_args.append("--bbox")
            cmd_args.append(",".join(map(str, extent)))
        try:
            cmd = " ".join(cmd_args)
        except (TypeError, ValueError) as e:
            arcpy.AddError(e)
            arcpy.AddError(cmd_args)

        arcpy.AddMessage("Please wait... Downloader is starting")
        arcpy.AddMessage(cmd)

        runner = Runner()

        # TODO: how to remove ArcGis path pollution?
        cmd = 'cmd "/c activate {} && {}  && deactivate && exit 0"'.format(
            self.conda_env_path, cmd
        )

        ret = runner.running(
            cmd,
            callback=arcpy.AddMessage,
            working_dir=self.conda_env_path,
            minimized=True,
        )

        if ret == 0:
            arcpy.AddMessage("Success")

        return


class Analysis(Tool):
    def __init__(self, **kwds):
        """Define the tool (tool name is the name of the class)."""
        self.label = "C - Analysis"
        self.description = ""
        self.canRunInBackground = False
        super(Analysis, self).__init__(**kwds)

    def getParameterInfo(self):
        # Define parameter definitions
        global tool_data

        # First parameter
        param0 = arcpy.Parameter(
            displayName="Config file",
            name="in_config",
            datatype="DEFile",
            parameterType="Required",
            direction="Input",
        )

        project_cfg_path = tool_data.get("project_config_path")
        if project_cfg_path and os.path.isfile(project_cfg_path):
            param0.value = project_cfg_path

        params = [param0]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        global tool_data
        project_cfg_path = tool_data.get("project_config_path")
        if project_cfg_path and os.path.isfile(project_cfg_path):
            parameters[0].value = project_cfg_path
            tool_data["project_config_path"] = project_cfg_path
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        # python_exe = self.find_python()
        config_file = parameters[0].valueAsText

        # script_path = self.get_path("tie_analysis_dask.py")
        script_path = os.path.join(self.conda_env_path, "Scripts", "tie_analysis.exe")
        if script_path is None:
            arcpy.AddError("Cannot find script path: anaylysis.py")
            raise arcpy.ExecuteError

        cmd_args = [
            # self.python_exe,
            script_path,
            "--log-level",
            "DEBUG",
            "--config",
            config_file,
        ]
        cmd = " ".join(cmd_args)

        arcpy.AddMessage(cmd)

        arcpy.AddMessage("Please wait... TIE analysis is starting")

        runner = Runner()

        cmd = 'cmd "/c activate {} && {}  && deactivate && exit 0"'.format(
            self.conda_env_path, cmd
        )

        ret = runner.running(
            cmd,
            callback=arcpy.AddMessage,
            working_dir=self.conda_env_path,
            minimized=True,
        )

        if ret == 0:
            arcpy.AddMessage("Success")

        return ret


class Viewer(Tool):
    def __init__(self, **kwds):
        """Define the tool (tool name is the name of the class)."""
        self.label = "D - Viewer"
        self.description = ""
        self.canRunInBackground = False
        super(Viewer, self).__init__(**kwds)

    def getParameterInfo(self):
        # Define parameter definitions
        global tool_data

        # First parameter
        param0 = arcpy.Parameter(
            displayName="Config file",
            name="in_config",
            datatype="DEFile",
            parameterType="Required",
            direction="Input",
        )

        param0.value = tool_data.get("project_config_path")

        param1 = arcpy.Parameter(
            displayName="Plot typ",
            name="in_plot",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )

        # Set a value list of 1, 10 and 100
        param1.filter.type = "ValueList"
        param1.filter.list = [
            "Overview3D",
            "3DTIE",
            "2DOverview",
            "SignalHeightDiagram",
            "SignalStereo",
            "IndividualSignals",
        ]
        param1.multiValue = True

        param1.value = "3DTIE"

        params = [param0, param1]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        global tool_data
        project_cfg_path = tool_data.get("project_config_path")
        if project_cfg_path and os.path.isfile(project_cfg_path):
            parameters[0].value = project_cfg_path
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        # python_exe = self.find_python()
        config_file = parameters[0].valueAsText

        try:
            with open(config_file, "r") as f:
                cfg = json.load(f)
                project_dir = cfg.get("project_dir")
        except (IOError, RuntimeError, ValueError) as e:
            arcpy.AddError(
                "Cannot read/parse config file {}: {}".format(config_file, e)
            )
            raise arcpy.ExecuteError

        data_dir = os.path.join(project_dir, "cache")

        try:
            plots = parameters[1].valueAsText.split(";")
        except Exception as e:
            raise arcpy.ExecuteError
        # TODO: py23
        plot_cmd = " ".join(map(lambda x: "-p {}".format(x), plots))

        # TODO: sometime spelled 'tie_viewver.exe'
        script_path = os.path.join(self.conda_env_path, "Scripts", "tie_viewer.exe")
        script_dir = os.path.dirname(script_path)
        if script_path is None:
            arcpy.AddError("Cannot find script path: 'tie_viewer.exe'")
            raise arcpy.ExecuteError

        cmd_args = [
            script_path,
            # TODO_ rename to cache_dir?
            "--data-dir",
            data_dir,
            "--log-level",
            "DEBUG",
            "--config",
            config_file,
            plot_cmd,
        ]
        cmd = " ".join(cmd_args)

        arcpy.AddMessage("Please wait... Mayavi is starting")
        arcpy.AddMessage(cmd)

        runner = Runner()
        cmd = 'cmd "/c activate {} && {}  && deactivate && exit 0"'.format(
            self.conda_env_path, cmd
        )

        return runner.running(
            cmd,
            callback=arcpy.AddMessage,
            working_dir=script_dir,
            minimized=True,
        )
