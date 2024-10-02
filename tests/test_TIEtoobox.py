import os
import shutil
import unittest
import arcpy


def prepare_project(temp_dir):
    # Path to a blank MXD template
    template_mxd_path = os.path.join(temp_dir, "blank.mxd")

    # Path where you want to save the new MXD
    new_mxd_path =os.path.join(temp_dir, "new_project.mxd")
    if os.path.exists(new_mxd_path):
        os.remove(new_mxd_path)

    # Shapefile paths and their names for TOC
    shapefiles = [
    {"path": "data/Linear_Objects_Ueberschiebung.shp", "name": "Linear Objects_Ueberschiebung"},
    {"path": "data/Linear_Objects_Bruch.shp", "name": "Linear Objects_Bruch"},
        {"path": "data/Bedrock_HARMOS.shp", "name": "Bedrock_HARMOS_<40000"}
    ]

    # Copy the template MXD to create a new MXD
    arcpy.management.Copy(template_mxd_path, new_mxd_path)

    # Load the new MXD
    mxd = arcpy.mapping.MapDocument(new_mxd_path)

    # Get the first data frame in the MXD
    data_frame = arcpy.mapping.ListDataFrames(mxd)[0]

    # Add each shapefile to the MXD
    for shp in shapefiles:
        layer = arcpy.mapping.Layer(shp["path"])
        arcpy.mapping.AddLayer(data_frame, layer, "BOTTOM")
        # Rename the layer in the TOC
        for lyr in arcpy.mapping.ListLayers(mxd, "", data_frame):

            if os.path.basename(shp["path"].lower())  in lyr.dataSource.lower():
                print('Renaming to {}'.format(shp["name"]))
                lyr.name = shp["name"]
                break

    # Save the MXD
    mxd.save()

    return new_mxd_path




class TestTIEToolbox(unittest.TestCase):
    def setUp(self):
        # Set up environment variable
        temp_dir = os.path.dirname(os.path.abspath(__file__))
        aprx_path = prepare_project(temp_dir)

        os.environ["MXD_PROJECT_PATH"] = aprx_path

        temp_dir = os.path.join("D:\Projects", "Toto")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

    def tearDown(self):
        # Clean up environment variable
        del os.environ["MXD_PROJECT_PATH"]
        temp_dir = os.path.join("D:\Projects", "Toto")

        if os.path.exists(temp_dir):
            arcpy.env.workspace = temp_dir

            shutil.rmtree(temp_dir, ignore_errors=True)
            arcpy.management.Delete("geocover.gdb")

    def test_exporter(self):
        path = os.path.dirname(os.path.realpath(__file__))
        path = os.path.dirname(os.path.abspath(__file__))
        tbx_path = os.path.join(path, "TIEtoolbox.pyt")
        tbx_path = r"h:\code\arcmap-tie-toolbox\toolbox\tietoolbox\esri\toolboxes\TIEtoolbox.pyt"
        aprx_path = os.environ.get("MXD_PROJECT_PATH")
        print(os.path.exists(tbx_path))
        if os.path.exists(tbx_path):
            # Set the project environment
            arcpy.env.workspace = aprx_path

            # Open the specified ArcGIS Pro project
            mxd = arcpy.mapping.MapDocument(aprx_path)
            arcpy.ImportToolbox(tbx_path)

            try:
                result = arcpy.Exporter(r"D:\Projects", "Toto")

                self.assertEqual(4, result.status)  # 4 == succeed
                self.assertTrue(result.getOutput(0))
            except arcpy.ExecuteError:
                print(arcpy.GetMessages(2))
            finally:
                del mxd
                arcpy.RemoveToolbox(tbx_path)


if __name__ == "__main__":
    unittest.main()
