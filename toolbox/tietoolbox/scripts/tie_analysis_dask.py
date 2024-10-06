# import dask_geopandas as dask_gpd
import argparse
import logging
import os
import sys
import pickle
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

import geopandas as gpd
import matplotlib.pyplot as plt
import rasterio as rst
import pyogrio
import click
import dask
import numpy as np
from dask.delayed import delayed

from shapely.geometry import box as shapely_box

from tietoolbox.scripts.utils import universalpath

from untie import TIE_core as TIEcr
from untie import TIE_load as TIEld

from tietoolbox.scripts.utils import array_to_tif, dem_to_array, cropDEMextent
from tietoolbox.scripts.config import load_config_json


class FlushHandler(logging.Handler):
    def __init__(self, level=logging.INFO) -> None:
        super().__init__(level=level)

    def emit(self, record) -> None:
        msg = self.format(record)
        print(f"{msg}", flush=True)


h = FlushHandler()
formatter = logging.Formatter("%(asctime)s :: %(levelname)s ::  %(message)s")
h.setFormatter(formatter)

logger = logging.getLogger()

logger.addHandler(h)

class DataException(Exception):
    pass

class TIEDataProcessor:
    def __init__(self, config):
        # TODO:
        config.geodata_dir = config.project_dir
        if config.geodata_dir:
            os.environ["geodata_dir"] = config.geodata_dir
        self.cfg = config
        self.project_dir = config.project_dir
        self.dem_source = (
            config.DEM.source
        )  # "../tie/data/Widdergalm/swissalti3d-2.0-mosaic.tif"
        self.bounds = None
        self.minx, self.miny, self.maxx, self.maxy = self.cfg.bbox
        self.x, self.y = (self.minx, self.maxx), (self.miny, self.maxy)
        self.bedrock_path = None
        self.tec_path = config.Lines.source.format(geodata_dir=config.geodata_dir)
        self.tec_name = config.Lines.layer
        self.transform = None
        self.crs = None
        self.cache_dir = os.path.join(
            self.project_dir, "cache"
        )  # should load from cfg?
        if not os.path.isdir(self.cache_dir):
            os.makedirs(self.cache_dir)

    @delayed
    def load_dem(self):
        # Load DEM
        dem_data = rst.open(self.dem_source)

        return dem_data  # Replace with actual loading logic

    @delayed
    def load_big_shp(self, tec_name, use_crs=False):
        TECbig = None
        logger.info(f"Loading from GDB: {tec_name}")
        bbox = tuple(self.cfg.bbox)

        try:
            TECbig = gpd.read_file(
                self.tec_path,
                driver="OpenFileGDB",
                bbox=bbox,
                engine="pyogrio",
                layer=tec_name,
            )
        except (pyogrio.errors.DataSourceError, pyogrio.errors.DataLayerError) as py_e:
            logging.error(f"Error while loading '{tec_name}' at '{self.tec_path}': {py_e}")
        except Exception as e:
            logging.error(f"Unknown error while loading {tec_name}: {e}")

        if TECbig is None:
            raise DataException

        if use_crs:
            self.crs = TECbig.crs
        if TECbig is not None or not TECbig.empty:
            try:
                json_path = os.path.join(self.cache_dir, f"{tec_name}.geojson")
                TECbig.to_file(json_path, driver="GeoJSON")
            except (FileNotFoundError, PermissionError, OSError, IOError) as e:
                logging.error(f"Error while writing '{json_path}': {e}")

        return TECbig

    @delayed
    def create_extent_alt(self, TECbig, save_to_file=True):
        bounds = self.cfg.bbox
        logger.info(f"Creating extent (NEW): {bounds}")
        extent_df = gpd.GeoDataFrame({"id": 1, "geometry": [shapely_box(*bounds)]})
        extent_df.set_crs("epsg:2056")

        if save_to_file:
            json_path = os.path.join(self.cache_dir, "extent.geojson")
            extent_df.to_file(json_path, driver="GeoJSON")
            logger.info(f"Saving extent as {json_path}")

            pickle_path = os.path.join(self.cache_dir, "extent.pkl")
            logger.info(f"Saving extent as {pickle_path}")
            with open(pickle_path, "wb") as f:
                pickle.dump(extent_df, f)

        return extent_df

    # Origina,l not working
    @delayed
    def create_extent(self, TECbig, save_to_file=True):
        logger.info(f"Creating extent (ORI): {self.x}, {self.y}")
        extent = TIEld.createExtentPLG(self.x, self.y, TECbig.crs)
        if save_to_file:
            json_path = os.path.join(self.cache_dir, "extent.geojson")
            extent.to_file(json_path, driver="GeoJSON")
            logger.info(f"Saving extent as {json_path}")

            pickle_path = os.path.join(self.cache_dir, "extent.pkl")
            logger.info(f"Saving extent as {pickle_path}")
            with open(pickle_path, "wb") as f:
                pickle.dump(extent, f)

        return extent

    @delayed
    def crop_dem(self, DEMbig, extent):
        # Crop DEM
        logger.info("Crop DEM")
        # from test_extent import simple_crop
        # cropped_dem = simple_crop(DEMbig, bbox=self.cfg.bbox)
        # Ori
        cropped_dem = TIEld.cropDEMextent(DEMbig, extent)
        # custom
        # cropped_dem =  cropDEMextent(DEMbig, extent)
        self.transform = cropped_dem["meta"]["transform"]
        return cropped_dem  # Replace with actual cropping logic

    @delayed
    def adapt_shp_to_dem(self, big_shp, cropped_dem):
        logger.info("Adapt SHP to DEM")
        return TIEld.adaptSHAPE2DEM(big_shp, cropped_dem)

    @delayed
    def rasterize_shp(self, TECshp, attr_TEC, DEM, layername):
        logger.info(f"Rasterizing {layername} with {attr_TEC}")
        raster_shp = None
        if attr_TEC not in TECshp.columns:
            logging.error(
                f"Dataframe '{attr_TEC}' is not in {TECshp.columns} ('{layername}')"
            )
        try:
            raster_shp = TIEld.rasterizeSHP(TECshp, attr_TEC, DEM)
        except IndexError as idx_err:
            logging.error(f"Rasterizing error ({layername}): {idx_err}")
        except Exception as e:
            logging.error(f"Unknown error while rasterizing '{layername}': {e}")
        if raster_shp is None or raster_shp.size == 0:
            logging.error(f"Rasterized geodataframe for '{layername}' is empty")
        return raster_shp

    @delayed
    def tie_analysis(self, traces, DEM, seg=True):
        logger.info(" === TIE Analysis ===")
        traces = TIEcr.tie(traces, DEM["x"], DEM["y"], np.flipud(DEM["z"]), seg=seg)

        return traces

    @delayed
    def shortcircuit_faults(self, TECrst, BEDrst, DEM):
        logger.info("Short-circuiting fault analysis (TECrst)")
        faults = TIEld.extractTraces(TECrst, "L")

        logger.info(f"TECrst, found  faults: {len(faults)}")

        #  TIE-ANALYSIS

        # logger.info(" === TIE Analysis ===")

        # faults = TIEcr.tie(faults, DEM["x"], DEM["y"], np.flipud(DEM["z"]), seg=True)

        return faults

    @delayed
    def extract_traces(self, TECrst, geom_type="L"):
        logger.info(f"Extracting trace of type '{geom_type}'")
        faults = TIEld.extractTraces(TECrst, geom_type)
        return faults

    @delayed
    def identify_traces_toto(self, BEDrst, faults):
        logger.info("Identifying traces")
        BTRrst = TIEld.identifyTRACE(BEDrst, faults)

        return BEDrst

    @delayed
    def find_neight_type(self, traces, BEDrst):
        logger.info("Identifying neightbours")
        traces = TIEld.findNeighType(traces, BEDrst)
        return traces

    # @delayed
    # def shortcircuit_traces(self, TECrst, BEDrst, DEM, faults):
    #     logger.info("Short-circuiting traces analysis")
    #     # faults = TIEld.extractTraces(TECrst, "L")
    #     # logger.info(f"faults={len(faults)}")
    #
    #     BTRrst = TIEld.identifyTRACE(BEDrst, faults)
    #
    #     logger.info("BTRrst identified")
    #     logger.info("Starting traces extraction from BTRrst")  # lent, add feedback
    #     traces = TIEld.extractTraces(BTRrst, "PLG")
    #
    #     logger.info(f"BTRrst: extracted traces={len(traces)}")
    #     traces = TIEld.findNeighType(traces, BEDrst)
    #
    #     logger.info(f"BTRrst found traces: {len(traces)}")
    #
    #     #  TIE-ANALYSIS
    #
    #     # logger.info(" === TIE Analysis ===")
    #
    #     # traces = TIEcr.tie(traces, DEM["x"], DEM["y"], np.flipud(DEM["z"]), seg=True)
    #
    #     return traces

    @delayed
    def identify_traces(self, BEDrst, faults):
        logger.info("Short-circuiting traces analysis")
        # faults = TIEld.extractTraces(TECrst, "L")
        # logger.info(f"faults={len(faults)}")

        BTRrst = TIEld.identifyTRACE(BEDrst, faults)

        return BTRrst

    @delayed
    def save_tie_analysis(self, traces, faults, dem):
        logger.info("Saving TIE Analysis")
        if faults is not None:
            with open(PurePath(self.cache_dir, "faults.pkl"), "wb") as f:
                pickle.dump(faults, f)

        if traces is not None:
            logger.info("Saving traces")
            with open(PurePath(self.cache_dir, "traces.pkl"), "wb") as f:
                pickle.dump(traces, f)
        if dem is not None:
            with open(PurePath(self.cache_dir, "DEM.pkl"), "wb") as f:
                pickle.dump(dem, f)

    @delayed
    def save_rst(self, rst, outname, save_as_tiff=True):
        rst_both = np.flip(rst, (0, 1))

        np.save(PurePath(self.cache_dir, f"{outname}.npy"), rst)
        logger.info(f"Saved Rst {outname} to {self.cache_dir}")

        if save_as_tiff:
            array_to_tif(
                rst_both,
                PurePath(self.cache_dir, f"{outname}.tif"),
                self.crs,
                self.transform,
            )
            logger.info(f"Saved Rst {outname} to {self.cache_dir} as GeoTiff")

    @delayed
    def save_gdf_to_json(self, geo_frm, outname):
        json_path = os.path.join(self.cache_dir, outname)
        # TODO: keep failing because of schema
        """
        col_name = 'KIND_NUM'
        if col_name in geo_frm.columns:
            geo_frm['KIND_NUM'] = geo_frm['KIND'].astype(int)

        schema = gpd.io.file.infer_schema(geo_frm)
        for p in schema['properties']:
           print(p)
        null_mask = geo_frm.isnull().any(axis=1)
        null_rows = geo_frm[null_mask]"""
        # print(null_rows)
        # TODO: reactivate
        """col_name = 'KIND_NUM'
        if col_name in geo_frm.columns:
            geo_frm.drop('KIND_NUM', axis=1, inplace=True)"""
        try:
            pass
            # geo_frm.to_file(json_path, driver="GeoJSON", schema=None)
        except IndexError as idx:
            logging.error(f"Error while writing GeoJSON to {json_path}: {idx}")
        except ValueError as e:
            logging.error(f"Error while writing GeoJSON to {json_path}: {e}")

    @delayed
    def save_data(self, DEM, output_path):
        DEMarr = dem_to_array(DEM)

        array_to_tif(
            DEMarr, PurePath(self.cache_dir, output_path), self.crs, self.transform
        )
        logger.info(f"DEM saved as GeoTIFF to {output_path}")

    @delayed
    def finalizing_tie(self, *args):
        pass

    def process_geodata(self):
        # Create dask graph

        # Loading data
        load_big_dem_task = self.load_dem()
        load_big_bed_task = self.load_big_shp(self.cfg.Bedrock.layer, use_crs=True)
        load_big_tec_task = self.load_big_shp(self.cfg.Lines.layer, use_crs=False)

        # preaparing data
        create_extent_taks = self.create_extent(load_big_bed_task)
        crop_dem_task = self.crop_dem(load_big_dem_task, create_extent_taks)

        bed_shp_task = self.adapt_shp_to_dem(load_big_bed_task, crop_dem_task)
        tec_shp_task = self.adapt_shp_to_dem(load_big_tec_task, crop_dem_task)

        # TODO: cannot save to geojson (scham issue)
        save_bed_shp_task = self.save_gdf_to_json(
            bed_shp_task, "bedrock_clipped.geojson"
        )
        tec_shp_task_task = self.save_gdf_to_json(
            tec_shp_task, "tecto_lines_clipped.geojson"
        )

        # Rasterizing data
        bed_rast_task = self.rasterize_shp(
            bed_shp_task, self.cfg.Bedrock.attribute, crop_dem_task, "bedrock"
        )

        tec_rast_task = self.rasterize_shp(
            tec_shp_task, self.cfg.Lines.attribute, crop_dem_task, "tecto lines"
        )

        # Extracting traces
        """faults_from_shortcircuit_task = self.shortcircuit_faults(
            tec_rast_task, bed_rast_task, crop_dem_task
        )"""

        # extract_faults_task = self.extract_traces(tec_rast_task, geom_type="L")

        faults_extract_task = self.extract_traces(tec_rast_task, geom_type="L")
        # ---------------------

        # traces_from_shortcircuit_task = self.shortcircuit_traces(
        #     tec_rast_task, bed_rast_task, crop_dem_task, faults_from_shortcircuit_task
        # )

        btrst_task = self.identify_traces(bed_rast_task, faults_extract_task)

        traces_extract_plg_task = self.extract_traces(btrst_task, geom_type="PLG")

        traces_neight_type_task = self.find_neight_type(
            traces_extract_plg_task, bed_rast_task
        )

        # TIE Analysis

        faults_task = self.tie_analysis(faults_extract_task, crop_dem_task, seg=True)

        traces_task = self.tie_analysis(
            traces_neight_type_task, crop_dem_task, seg=True
        )

        # if traces_task:
        save_tie_task = self.save_tie_analysis(traces_task, faults_task, crop_dem_task)

        save_rst_task = self.save_rst(bed_rast_task, "BEDrst")
        save_tec_task = self.save_rst(tec_rast_task, "TECrst")

        save_data_task = self.save_data(crop_dem_task, "cropped.tif")

        final_task = self.finalizing_tie(
            save_tie_task,
            save_data_task,
            save_rst_task,
            save_tec_task,
            save_bed_shp_task,
            tec_shp_task_task,
        )

        # Visualize the graph

        pipeline_file = os.path.join(self.project_dir, "tie_pipeline")
        try:
            dask.visualize(
                final_task,
                engine="cytoscape",
                filename=pipeline_file,
                optimize_graph=True,
            )
            plt.show()
        except Exception as e:
            # No write access or missing lib 'cytoscape'
            logger.error(f"Error while saving Dask Task Graph to file:  {e}")

        # Compute the dask graph
        dask.compute(final_task)


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
    default=PurePath(__file__).stem + ".json",
    show_default=True,
)
def main(config, log_level):
    import time

    cfg = load_config_json(config)

    logger.setLevel(log_level.upper())

    start = time.time()
    logger.info("== Starting pipeline ===")
    processor = TIEDataProcessor(cfg)
    processor.process_geodata()

    logger.info(f"== Ending pipeline {time.time() - start}s===")


if __name__ == "__main__":
    main()
