# tietoolbox/scripts/demo.py
import importlib.resources
from tietoolbox.scripts import tie_viewer


def main():
    data_dir = importlib.resources.files("tietoolbox").joinpath("data")

    cfg_file_path = data_dir.joinpath("config.json")
    cache_dir = data_dir.joinpath("cache")

    predefined_args = ["--config", cfg_file_path, "-d", cache_dir]

    tie_viewer.main(predefined_args)


if __name__ == "__main__":
    main()
