"""Windows installer

Blatantly stollen from https://github.com/geoadmin/tool-topgis/blob/master/topgis/src/topgis/installer/install_topgis.py
"""

import ctypes
import glob
import itertools
import os
import platform
import shutil
import socket
import string
import subprocess
import sys
import tarfile
import logging

from six import BytesIO
from six.moves import configparser, input

HOME = os.getenv("HOMEDRIVE") + os.getenv("HOMEPATH")

CONDA_EXE = os.path.expandvars(
    r"C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\conda.exe"
)

CONDA_BASE_DIR = r"D:\conda\envs"

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


def get_available_drives():
    if "Windows" not in platform.system():
        return []
    drive_bitmask = ctypes.cdll.kernel32.GetLogicalDrives()
    return list(
        itertools.compress(
            string.ascii_uppercase,
            map(lambda x: ord(x) - ord("0"), bin(drive_bitmask)[:1:-1]),
        )
    )


def mapDrive(drive, networkPath):
    if not drive.endswith(":"):
        drive + ":"
    drive_letter = drive.replace(":", "")
    if drive_letter in get_available_drives():
        logging.warning(" Drive {} in use, trying to unmap...".format(drive))
        return -1
    else:
        logging.info(" Drive {} is free".format(drive))

    if os.path.exists(networkPath):
        logging.info("{} is found...".format(networkPath))
        logging.info("Trying to map {} to drive {}".format(networkPath, drive))
        winCMD = ["NET", "USE", drive, networkPath]
        try:
            cmdOutPut = subprocess.Popen(
                winCMD, stdout=subprocess.PIPE, shell=True
            ).communicate()
            return drive_letter in get_available_drives()
        except:
            logging.error("Unexpected error...")
            return -1
        logging.info("Mapping to {} successful".format(drive))
        return 1
    else:
        logging.info("Network path {} unreachable...".format(networkPath))
        return -1


def quote(str):
    return '"{}"'.format(str)


class Installer:
    dirname = os.path.dirname(os.path.abspath(__file__))

    conda_base_dir = r"\\v0t0020a.adr.admin.ch\prod\lgX\TOPGIS\conda"

    @classmethod
    def clone_conda(cls, envname):
        dest_env = r"D:\conda\envs\{}".format(envname)
        src_env = r"TIE"

        yaml_file = os.path.join(cls.dirname, "environment_from_yaml_list_explicit.txt")

        # cmd = """"C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\conda.exe" create --clone "T:\TIE" -p  "D:\conda\envs\TIE_TEST" - vv - -no - shortcuts --pinned 1"""

        cmd = """"C:/Program Files/ArcGIS/Pro/bin/Python/scripts/conda.exe"  create   -p {}  --file  {}""".format(
            dest_env, yaml_file
        )
        args = [
            quote(CONDA_EXE),
            "create",
            "--clone",
            quote(src_env),
            "-p",
            quote(dest_env),
            "-vv",
            "--no-shortcuts",
            "--pinned",
            "1",
        ]

        logging.info(cmd)

        proc = subprocess.Popen(cmd)

        logging.info(proc.communicate())

        return dest_env

    @classmethod
    def create_from_scratch(cls, envname):
        dest_env = r"D:\conda\envs\{}".format(envname)
        PYTHON_VERSION="3.9.18"

        pkgs_list = [ 'conda', 'pip', 'setuptools',  'geopandas', 'scikit-image',  'scipy',  'rasterio', 'shapely',  'mayavi', 'geocube', 'tqdm', 'requests', 'gdal', 'pyproj', 'geojson', 'pyyaml', 'pyogrio', 'dask', 'ipycytoscape' ]



        # cmd = """"C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\conda.exe" create --clone "T:\TIE" -p  "D:\conda\envs\TIE_TEST" - vv - -no - shortcuts --pinned 1"""

        cmd = """"C:/Program Files/ArcGIS/Pro/bin/Python/scripts/conda.exe"  create   -p {}  -v --override-channels -c conda-forge -y --show-channel-urls python={} {} """.format(
            dest_env, PYTHON_VERSION, " ".join(pkgs_list)
        )

        logging.info(cmd)

        proc = subprocess.Popen(cmd)

        logging.info(proc.communicate())

        return dest_env

    @classmethod
    def download_conda_env(cls, envname='TIE'):
        conda_env_path = r"D:\conda\envs"

        archive_name = "conda-TIE-win10.tar.gz"

        if not os.path.isdir(conda_env_path):
            os.makedirs(conda_env_path)

        tar_archive_path = os.path.join(base_dir, archive_name)

        logging.info("  Copy tar archive {} to {}".format(tar_archive_path, conda_env_path))
        shutil.copy(tar_archive_path, conda_env_path)

        os.chdir(conda_env_path)

        logging.info("  Gunziping archive")
        with tarfile.open(archive_name, "r:gz") as tar:
            print(os.path.commonprefix(tar.getnames()))
            tar.extractall()
            tar.close()

        return conda_env_path

    @classmethod
    def update_env(cls, conda_env_path):
        python_exe = os.path.join(conda_env_path, 'python.exe')

        for pkg in ("https://bitbucket.org/procrastinatio/lg-tie-lib/get/packaging.zip",
                    "https://bitbucket.org/procrastinatio/geocover-utils/get/master.zip"):
            proc = subprocess.call(
            [python_exe, "-m", "pip", "install", "--trusted", "bitbucket.org", pkg]
            )

        conda_exe = os.path.join(conda_env_path, 'condabin',  'conda.bat')

        for pkg in ("swisstopo::tietoolbox", ):
            proc = subprocess.call(
                [conda_exe,  "install", "--yes",  pkg]
            )

        logging.info(r"Toolbox installed in '{}\Lib\site-packages\tietoolbox\esri\toolboxes'".format(conda_env_path))



    @classmethod
    def map_drive(cls, drive, unc_path):
        logging.info("=====  Mapping Drive for conda env =====")

        mapDrive(drive, unc_path)

        return os.path.join(os.sep, drive + os.sep, os.path.basename(unc_path))

    @classmethod
    def ini_file(cls, conda_env_path):
        logging.info("=====  geocover.ini =====")
        base_dir = cls.conda_base_dir

        user_config_dir = os.path.join(HOME, r"config\geocover")

        user_config_path = os.path.join(user_config_dir, "geocover.ini")

        if os.path.isfile(user_config_path):
            logging.info(
                "geocover.ini file already exists in {}. Will not overwrite it!".format(
                    user_config_dir
                )
            )
            return 2

        if not os.path.isdir(user_config_dir):
            os.makedirs(user_config_dir)

        data = {
            "hostname": socket.gethostname(),
            "username": os.environ.get("USERNAME"),
            "conda_env_path": conda_env_path,
        }
        try:
            with open(os.path.join(base_dir, "geocover.ini.in"), "r") as f:
                tpl = f.read()

                ini_str = tpl.format(**data)
        except (IOError, KeyError, ValueError) as e:
            logging.info("Cannot read or create the ini file: {}".format(e))

        try:
            config = configparser.RawConfigParser(allow_no_value=True)
            config.readfp(BytesIO(ini_str))

            with open(user_config_path, "wb") as configfile:
                config.write(configfile)
                logging.info("Config written to {}".format(user_config_path))
        except Exception as e:
            logging.error("Error: {}".format(e))

    @classmethod
    def condarc_file(cls):
        logging.info("=====  .condarc =====")
        base_dir = cls.conda_base_dir

        user_config_dir = HOME

        user_config_path = os.path.join(user_config_dir, ".condarc")

        if os.path.isfile(user_config_path):
            logging.warning("File {} already exists. Will not overwrite".format(user_config_path))
            return 2

        if not os.path.isdir(user_config_dir):
            os.makedir(user_config_dir)

        try:
            shutil.copy2(os.path.join(base_dir, "_condarc"), user_config_path)
        except (IOError, KeyError, ValueError) as e:
            logging.error("Cannot write file to {}: {}".format(user_config_path, e))

    @classmethod
    def install_from_setup(cls):
        curdir = os.path.dirname(os.path.abspath(__file__))

        os.chdir(curdir)

        for python_exe in glob.glob(
            r"C:\Python27" + os.sep + "**" + os.sep + "python.exe"
        ):
            logging.info("===== Installing for {} =====".format(python_exe))

            # TODO: proper install for python2
            subprocess.call(
                [python_exe, "-m", "pip", "install", "-r", "requirements.txt"]
            )

    @classmethod
    def main(cls):
        envname = "TIE"


        try:
            logging.info("=== Preparing conda env ===")
            cls.condarc_file()

            if not os.path.isdir(CONDA_BASE_DIR):
                try:
                    os.makedirs(CONDA_BASE_DIR)
                except Exception as e:
                    logging.error("Cannot create dir {}. Exit".format(CONDA_BASE_DIR))
                    sys.exit(2)



            # Use one of them
            # conda_env_unc_path = os.path.join(cls.conda_base_dir, "envs\TIE")
            conda_env_path = r"D:\conda\envs\EMPTY_FROM_YAML"

            # Download and unzipped an archive containing the conda en
            # conda_env_path = cls.download_conda_env(envname=envname)
            # Map a network drive containing the conda env
            # conda_env_path = cls.map_drive("T:", conda_env_unc_path)

            conda_env_path = cls.clone_conda(envname)

            # Create the env from scratch (very long)
            #conda_env_path = cls.create_from_scratch(envname)


            cls.update_env(conda_env_path)

            logging.info(conda_env_path)

            cls.ini_file(conda_env_path)

            logging.info("Installing geocover and dependencies from setup.py")

            cls.install_from_setup()
            logging.info("\nPython geocover successfully installed")
            input("Press enter...")
        except Exception as e:
            print(
                "\nCould not install required python modules. Please contact GeoCover support geocover@swisstopo.ch"
            )
            logging.error(e)
            input("Press enter...")


if __name__ == "__main__":
    i = Installer()
    i.main()
