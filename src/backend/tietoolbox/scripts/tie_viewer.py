# Module level import not at top of file
# ruff: noqa: E402
# Comparison to `True` should be `cond is True` or `if cond:`
# ruff: noqa: E712
import sys
import os
import pickle
import click
from pathlib import PurePath

# ArcGis Pro is adding the paths of the default `conda`environement.
# Reset the path (remove all ArcGis stuff)
if ".exe" in sys.executable and any("ESRI" in pth for pth in sys.path):
    env_base = os.path.dirname(sys.executable)
    cur_dir = os.path.dirname(os.path.realpath(__file__))

    paths = [".", env_base, cur_dir]
    for dir in ["python39.zip", "DLLs", "lib", "site-packages"]:
        paths.append(os.path.join(env_base, dir))

    sys.path = paths

import matplotlib.pyplot as plt

import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from tietoolbox.scripts.utils import universalpath

from untie import TIE_visual as TIEvis
from tietoolbox.scripts.traces_export_utils import bed2cmap, export_traces
from tietoolbox.scripts.utils import universalpath
from tietoolbox.scripts.config import load_config_json

import logging

# Constants

DATA_DIR = universalpath(os.path.join("data/Widdergalm/2.0"))

cur_dir = os.path.dirname(os.path.realpath(__file__))

legendfile = universalpath(os.path.join(cur_dir, "symbols.tsv"))


@click.command()
@click.option(
    "-l",
    "--log-level",
    default="INFO",
    type=click.Choice(
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=True
    ),
    show_default=True,
    help="Log level",
)
@click.option(
    "-c",
    "--config",
    help="Specify a configuration file",
    metavar="FILE",
    default="config.json",
    show_default=True,
)
@click.option(
    "-d",
    "--data-dir",
    help="Directory where the .np and .pkl files are",
    default=DATA_DIR,
    show_default=True,
)
@click.option(
    "-p",
    "--plots",
    type=click.Choice(
        [
            "Overview3D",
            "3DTIE",
            "2DOverview",
            "SignalHeightDiagram",
            "SignalStereo",
            "IndividualSignals",
        ]
    ),
    default=["3DTIE"],
    multiple=True,
)
@click.option(
    "--save-figure", is_flag=True, show_default=True, default=False, help="Save figures"
)
def main(config, log_level, data_dir, save_figure, plots):
    # Loading data

    logger = logging.getLogger(__name__)
    logger.setLevel(log_level.upper())
    logger.addHandler(logging.StreamHandler(sys.stdout))

    cfg = load_config_json(config)

    project_name = cfg.name if cfg else "unknown"

    logger.info("Loading files for '{}'".format(project_name))
    logger.handlers[0].flush()
    sys.stdout.flush()

    with open(universalpath(os.path.join(data_dir, f"DEM.pkl")), "rb") as f:
        DEM = pickle.load(f)

    with open(universalpath(os.path.join(data_dir, f"faults.pkl")), "rb") as f:
        FTraces = pickle.load(f)

    try:
        with open(universalpath(os.path.join(data_dir, f"traces.pkl")), "rb") as f:
            BTraces = pickle.load(f)
    except FileNotFoundError:
        BTraces = []

    with open(PurePath(data_dir, f"BEDrst.npy"), "rb") as f:
        BEDrst = np.load(f)

    # TODO:
    cmap_fname = universalpath(os.path.join(data_dir, "cmap.pkl"))

    try:
        with open(cmap_fname, "rb") as f:
            cmap = pickle.load(f)
    except (FileNotFoundError, IOError) as e:
        cmap = []

    logger.info("Loading done")
    logger.handlers[0].flush()

    ## Visualisation

    mc, cmap = bed2cmap(BEDrst, legendfile)

    # define display variables
    mx, my = np.meshgrid(DEM["x"], DEM["y"])
    mz = np.flipud(DEM["z"].copy())
    mx = mx.astype(float)
    my = my.astype(float)

    cmap_plt = "Greens"

    # ['Unconsolidated Deposit', 'Intyamon-Formation', "Sciernes-d'Albeuve-Formation", 'Moléson-Formation', 'Torrent-de-Lessoc-Formation', '"Couches-Rouges der Klippen-Decke, undifferenziert"']

    # %% OVERVIEW MAP (3D)
    if "Overview3D" in plots:
        logger.info("Loading 3D plot")
        logger.handlers[0].flush()
        fig_OV3D = TIEvis.showOverview3D(
            mx,
            my,
            mz,
            mc,
            cmap=cmap,
            BTraces=BTraces,
            FTraces=FTraces,
            WithlabelsF=False,
        )

    # %% SIGNAL HEIGHT DIAGRAM
    if "SignalHeightDiagram" in plots:
        pth = [3, 9, 18, 90]
        fig_SH = TIEvis.sigHdiagram(BTraces, pth, scale="log")

    # %% INDIVIDUAL SIGNALS
    nt = 7
    if "IndividualSignals" in plots:
        fig_Signal = TIEvis.showSignal(BTraces[nt - 1])

    if "SignalStereo" in plots:
        fig_Stereo = TIEvis.showSigStereo(BTraces[nt - 1])

    # %% 3D PLOT with TIE ANALYSIS
    if "3DTIE" in plots:
        logger.info("Loading 3D plot with TIE Analysis")
        fig_3dTIE = TIEvis.showTIEmap(
            mx,
            my,
            mz,
            mc=mc,
            cmap=cmap,
            MainTrace_Set=BTraces,
            AuxTrace_Set=FTraces,
            ShowBars=True,
        )

    # 2D visualtions
    if "2DOverview" in plots:
        # %% OVERVIEW MAP (2D)
        logger.info("Loading overview map (2D)")
        logger.handlers[0].flush()

        formations = []
        fig_sidemap, ax = TIEvis.showOverviewMap(
            mx,
            my,
            mc,
            mz=mz,
            cmap=cmap,
            BTraces=BTraces,
            FTraces=FTraces,
            leg_labels=formations,
            WithSeg=True,
        )
        ax.set_title(project_name)

    plt.show()


if __name__ == "__main__":
    main()
