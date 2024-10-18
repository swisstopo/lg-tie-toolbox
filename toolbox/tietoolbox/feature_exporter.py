# ruff: noqa: E501, UP032, UP004
# UP032 Use f-string instead of `format` call (python2!)
# UP004 [*] Class `...` inherits from `object` (python2!)

import arcpy
import os
import six

from tietoolbox.utils import get_valid_filename

MAX_AREA = 1000 * 1000 * 10  # 10 km2

MAX_SCALE = 40000.0


def get_project(path=None):
    if path is None:
        path = "CURRENT"
    if six.PY2:
        # an mxd
        return arcpy.mapping.MapDocument(path)
    else:
        # a project
        return arcpy.mp.ArcGISProject(path)


def get_layers(mxd, df=None, pattern="*"):
    if six.PY2:
        # dataframes
        if df is not None:
            return arcpy.mapping.ListLayers(mxd, pattern, df)
        else:
            return arcpy.mapping.ListLayers(mxd, pattern)

    else:
        m = get_dataframes(mxd)
        return m.listLayers()


def get_dataframes(mxd, pattern="*"):
    if six.PY2:
        return arcpy.mapping.ListDataFrames(mxd, pattern)[0]
    else:
        return mxd.listMaps(pattern)[0]


def get_map_extent(df):
    if six.PY2:
        return df.extent
    else:
        return df.defaultCamera.getExtent()


def AddMsg(msg, severity=0):
    # Adds a Message (in case this is run as a tool)
    # and also prints the message to the screen (standard output)
    print(msg)
    # Split the message on \n first, so that if it's multiple lines,
    #  a GPMessage will be added for each line
    try:
        for string in msg.split("\n"):
            if severity == 0:
                arcpy.AddMessage(string)
            elif severity == 1:
                arcpy.AddWarning(string)
            elif severity == 2:
                arcpy.AddError(string)
    except:
        pass


class FeaturesExporter:
    def __init__(self, mxd_path, output_gdb):
        self.mxd_path = mxd_path  # 'CURRNET'
        self._mxd = None
        self.output_gdb = output_gdb
        self._extent = None
        self._df = None
        self.extent_lyrname = "TieAnalysisExtent"
        self.extent_lyr = None
        self.polygon = None
        self.out_path = None

        self._create_workspace()

    @property
    def mxd(self):
        if self._mxd is None:
            try:
                self._mxd = get_project(path=self.mxd_path)
            except OSError:
                pass

        return self._mxd

    @property
    def df(self):
        if self._df is None:
            self._df = get_dataframes(self.mxd, pattern="*")
        return self._df

    def _create_workspace(self):
        out_path = os.path.dirname(self.output_gdb)
        if not os.path.isdir(out_path):
            os.makedirs(out_path)
        self.out_path = out_path
        out_gdb = os.path.basename(self.output_gdb)

        # TODO: really weak test for GDB
        if not arcpy.Exists(self.output_gdb):
            AddMsg("Creating workspace {}".format(self.output_gdb))
            try:
                # Same in py2/3
                arcpy.management.CreateFileGDB(out_path, out_gdb)
            except arcpy.ExecuteError as e:
                AddMsg(arcpy.GetMessages(2), severity=2)
        return

    def get_layer(self, layername):
        for i, lyr in enumerate(get_layers(self.mxd)):
            if lyr.name == layername:
                return lyr
        return None

    def _delete_featclass(self, feat_name):
        fc_path = os.path.join(self.output_gdb, feat_name)

        if arcpy.Exists(fc_path):
            AddMsg("Deleting feature class: {}".format(fc_path))
            arcpy.Delete_management(fc_path)
            return True
        return False

    def _refresh_extent(self):
        if self.extent_lyr is None or self.extent is None:
            AddMsg("Cannot compare extent")
            return True
        else:
            ds = self.extent_lyr.dataSource
            try:
                desc = arcpy.Describe(ds)
            except IOError as e:
                AddMsg("No datasource for {}: {}".format(self.extent_lyrname, e))
                return True
            if desc:
                extent = desc.extent
                minx, miny, maxx, maxy = (
                    extent.XMin,
                    extent.YMin,
                    extent.XMax,
                    extent.YMax,
                )
                new_extent = (minx, miny, maxx, maxy)
                AddMsg(map(int, new_extent))
                AddMsg(map(int, self.extent))
                refresh_needed = not map(int, new_extent) == map(int, self.extent)
                AddMsg("Refresh needed: {}".format(refresh_needed))
                return refresh_needed
        return True

    @property
    def workspace(self):
        AddMsg("Creating Workspace")
        self._create_extent()

    # TODO:  check if layer.minScale < MAX_SCALE
    def _create_extent(self, delete=True):
        extent_lyr = None
        in_features = self.extent_lyrname
        arcpy.env.workspace = self.output_gdb
        arcpy.env.overwriteOutput = True
        extent_fc = os.path.normpath(os.path.join(self.output_gdb, self.extent_lyrname))
        # True if new extent, check if extent and polyon match
        # if not self._extent_too_large():

        target_lyrs = get_layers(self.mxd, pattern=in_features, df=self.df)
        if len(target_lyrs) > 0:
            extent_lyr = target_lyrs[0]
            self.extent_lyr = extent_lyr
            AddMsg("Found a layer extent")
        AddMsg("Extent lyr: {}".format(extent_lyr))
        if self._refresh_extent():
            arcpy.AddMessage("Extent layer and feature need to be updated")

            # Remove the layer, not the featureclass

            if extent_lyr is not None:
                AddMsg("Removing the layer extent")
                arcpy.Delete_management(extent_lyr)
                extent_lyr = None
                self.extent_lyr = None

            self._delete_featclass(in_features)

        if extent_lyr is None:
            # TODO: error in loaded for the fisrt time (or wrong type)
            AddMsg("Creating the extent from the polygon: {}".format(self.extent))
            arcpy.CopyFeatures_management(self.polygon, extent_fc)
            # Create a layer
            AddMsg(
                "Adding new extent layer {} ({})".format(self.extent_lyrname, extent_fc)
            )
            # TODO: why it's not add the layer!
            AddMsg(
                "arcpy.MakeFeatureLayer_management('{}' , '{}')".format(
                    extent_fc, self.extent_lyrname
                )
            )
            try:
                #

                # Create mapping layer
                # TODO: py23
                if six.PY2:
                    arcpy.MakeFeatureLayer_management(extent_fc, self.extent_lyrname)
                    extent_lyr = arcpy.mapping.Layer(self.extent_lyrname)
                    # Add mapping layer to map
                    arcpy.mapping.AddLayer(self.df, extent_lyr, "TOP")

                else:
                    try:
                        # Add the layer to the map
                        layer_name = (
                            self.extent_lyrname
                        )  # Change this to the name of the layer in your Geodatabase
                        layer_path = self.output_gdb + "\\" + layer_name

                        # Add the layer to the map
                        extent_lyr = self.df.addDataFromPath(layer_path)
                        arcpy.AddMessage(type(extent_lyr))
                        """arcpy.AddMessage(extent_fc)
                        arcpy.AddMessage(self.extent_lyrname)
                        extent_lyr = arcpy.management.MakeFeatureLayer(
                            extent_fc, self.extent_lyrname
                        )
                        arcpy.AddMessage("New layer: {}".format(extent_lyr))
                        toto = os.path.join(self.out_path, self.extent_lyrname)
                        arcpy.SaveToLayerFile_management(self.extent_lyrname, toto)
                        lyrx = arcpy.mp.LayerFile(toto + ".lyrx")
                        self.df.addLayer(lyrx, "TOP")"""
                    except Exception as e:
                        arcpy.AddError(e)

                arcpy.AddMessage(
                    "Setting self.extent_lyr to {}".format(extent_lyr.name)
                )
                self.extent_lyr = extent_lyr

                # delete layer in memory to prevent confusion
                # arcpy.Delete_management(extent_fc)

                # res = arcpy.MakeFeatureLayer_management(extent_fc, self.extent_lyrname)
                """if arcpy.Exists(res):
                    addLayer = arcpy.mapping.Layer(res)
                    arcpy.mapping.AddLayer(self.df, addLayer, "TOP")
                    AddMsg("-> Added {0} to map.".format(addLayer))"""
                AddMsg("Result form adding: {}".format(extent_lyr))

                return extent_lyr
            except arcpy.ExecuteError as e:
                AddMsg("Cannot add layer: {}".format(e), severity=2)
            AddMsg(arcpy.mapping.ListLayers(self.mxd, in_features, self.df))
            # if len(target_lyrs) > 0:
            #    self.extent_lyr = target_lyrs[0]
        else:
            AddMsg("Won't create/update an extent layer")
            return self.extent_lyr

        # TODO

        lyrs = get_layers(self.mxd, self.extent_lyrname, self.df)
        AddMsg("List... {}".format(lyrs))

        if len(lyrs) > 0:
            extent_lyr = lyrs[0]
            self.extent_lyr = extent_lyr
            AddMsg("Found one... {}".format(extent_lyr))

        return extent_lyr

    @property
    def extent(self):
        return self._get_extent()

    def _get_extent(self):
        old_extent = self._extent
        # df = arcpy.mapping.ListDataFrames(self.mxd, "*")[0]
        df = get_dataframes(self.mxd, pattern="*")

        #   Get data frame extent
        frameExtent = get_map_extent(df)

        minx, miny, maxx, maxy = (
            frameExtent.XMin,
            frameExtent.YMin,
            frameExtent.XMax,
            frameExtent.YMax,
        )

        polygon = frameExtent.polygon  # arcpy.Polygon(array) #creates polygon object
        new_extent = (minx, miny, maxx, maxy)

        self.polygon = polygon
        self._extent = (minx, miny, maxx, maxy)

        return new_extent

    def merge_layers(self):
        feat_class_to_merge = []
        arcpy.env.workspace = self.output_gdb
        merged_feat_class_path = os.path.join(self.output_gdb, "Linear_Objects")
        featureclasses = arcpy.ListFeatureClasses("Linear_Objects_*", "Line")

        for fc in featureclasses:
            arcpy.AddMessage("FC to merge {}: {}".format(len(featureclasses), fc))
            feat_class_to_merge.append(
                os.path.join(arcpy.env.workspace, os.path.splitext(fc)[0])
            )

        if len(feat_class_to_merge) > 1:
            AddMsg("Merging line feature class to {}".format(merged_feat_class_path))
            arcpy.Merge_management(feat_class_to_merge, merged_feat_class_path)

        elif len(feat_class_to_merge) == 1:
            try:
                feat_class = feat_class_to_merge[0]
                AddMsg(
                    "Only one feature class: copy {} to  class to 'Linear_Objects'".format(
                        feat_class
                    ),
                    severity=1,
                )
                arcpy.CopyFeatures_management(feat_class, merged_feat_class_path)
            except arcpy.ExecuteError as e:
                AddMsg("Cannot copy feature file: {}".format(e), severity=2)
        else:
            AddMsg("No feature classes to merge", severity=2)

        return "Linear_Objects"

    def export_from(self, lyr, field_name=None):
        # Linear Objects_Bruch  KIND IN (14901002,14901004,14901005,14901006,14901007,14901008)
        # Linear Objects_Ueberschiebung KIND = 14901001
        arcpy.AddMessage(type(lyr))
        if six.PY2:
            layer_types = (arcpy._mapping.Layer,)
        else:
            layer_types = (
                arcpy._mp.Layer,
                arcpy._mp.LayerFile,
            )
        if not isinstance(lyr, layer_types):
            lyr = self.get_layer(lyr)

        if lyr is None:
            AddMsg("layerfile for {} is None".format(lyr))
            return
        AddMsg("==== Export for {} ====\n".format(lyr.name))
        # TODO: check if fields are present
        FIELD_NAME = "FmAt_Litstrat_Int".upper()
        fld = "TOPGIS_GC_GC_BED_FORM_ATT_FMAT_LITSTRAT"

        # check if requested field is in layer

        if field_name is not None and lyr.supports("dataSource"):
            fields = arcpy.ListFields(lyr.dataSource)
            fields_name = [f.name for f in fields]
            if field_name not in fields_name:
                AddMsg(
                    "  Requested field {} not found. Existing fields: {}".format(
                        field_name, fields_name
                    ),
                    severity=2,
                )
                raise arcpy.ExecuteError(
                    "Requested field {} not found in layer.".format(field_name)
                )

        # TODO: check if extent is too large
        arcpy.AddMessage("===OK==")
        if self.polygon is None or self.extent is None:
            self._get_extent()

        # Clear visible scale range
        # TODO: do the same for PY3
        if six.PY2:
            if lyr.minScale < self.df.scale:
                AddMsg(
                    "  Removing minScale for layer {} (was {})".format(
                        lyr.name, lyr.minScale
                    ),
                    severity=1,
                )
                lyr.minScale = 2.0e6
                lyr.maxScale = 0

        # TODO: Layer vs LayerFile
        if not isinstance(self.extent_lyr, layer_types):
            # self._create_extent()
            AddMsg("  No extent layer found.", severity=2)
            raise arcpy.ExecuteError("  No extent layer found.")

        arcpy.env.workspace = self.output_gdb

        # delete fc
        layername = get_valid_filename(lyr.name)
        out_fc = os.path.join(self.output_gdb, "{}_Extract".format(layername))

        if arcpy.Exists(out_fc):
            arcpy.Delete_management(out_fc)
            AddMsg("Deleting {}".format(out_fc))

        # TODO: warn if extent_lyr is not set
        AddMsg("  Selecting features within: {}".format(self.extent_lyr))
        arcpy.SelectLayerByLocation_management(lyr, "intersect", self.extent_lyr)
        matchcount = int(arcpy.GetCount_management(lyr)[0])
        AddMsg("  Match: {}".format(matchcount))

        if matchcount == 0:
            AddMsg("  No features found within extent")
            return None
        else:
            arcpy.CopyFeatures_management(lyr, out_fc)

            AddMsg("  {} features with extent written to {}".format(matchcount, out_fc))
        return layername

    def __repr__(self):
        class_name = self.__class__.__name__
        return "{}(extent={}, gdb={})".format(class_name, self.extent, self.output_gdb)


def main():
    fe = FeaturesExporter("CURRENT", r"D:\temp\dummy\dummy.gdb")
    fe._get_extent()
    AddMsg(fe)
    polygon = fe.polygon
    fe._create_extent()

    AddMsg(fe.extent, fe.extent_lyr, fe.polygon)
    fe._refresh_extent()

    # TODO: arcpy.RefreshActiveView() and arcpy.RefreshTOC()


if __name__ == "__main__":
    print("toto")
