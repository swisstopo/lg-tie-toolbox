"""
Provides generic Config class useful for passing around parameters
Also provides basic saving/loading functionality to and from json/yaml

https://gist.github.com/Hanwant/9875d35ee22b50fe815778af75e20e5d
"""

import json
from pathlib import Path

import yaml


class Config(dict):
    """
    Wraps a dictionary to have its keys accesible like attributes
    I.e can do both config['steps'] and config.steps to get/set items

    Note - Recursively applies this class wrapper to each dict inside dict
    I.e:
    >>> config = Config({'filepath': '/path/to/file',
                         'settings': {'a': 1, 'b': 2}})
    >>> print(config.filepath)
    /path/to/file
    >>> config.settings.c = 3
    >>> print(config.settings.c, config.settings['c'])
    3 3
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for k, v in self.items():
            if isinstance(v, dict):
                self[k] = Config(v)

    def __getattr__(self, key):
        if key not in self:
            raise KeyError(f"key doesn't exist: {key}")
        return self[key]

    def __setattr__(self, key, val):
        self[key] = val

    def __delattr__(self, name):
        if name in self:
            del self[name]
        raise AttributeError("No such attribute: " + name)

    @classmethod
    def from_path(cls, filepath):
        """Loads config from given filepath"""
        filepath = Path(filepath)
        if filepath.suffix == ".json":
            return cls(load_config_json(filepath))
        if filepath.suffix == ".yaml":
            return cls(load_config_yaml(filepath))
        raise NotImplementedError("Only .json or .yaml extensions supported")

    def save(self, savepath):
        """
        Saves config as either json or yaml depending on suffix
        of savepath provided.
        """
        savepath = Path(savepath)
        if savepath.suffix == ".json":
            save_config_json(self, savepath)
        elif savepath.suffix == ".yaml":
            save_config_yaml(self, savepath)
        raise NotImplementedError("Only .json or .yaml extensions supported")

    def as_dict(self):
        return config_to_dict(self)


def config_to_dict(config: Config):
    """
    Recursively converts config objects to dict
    """
    config = dict(config)
    for k, v in config.items():
        if isinstance(v, Config):
            config[k] = config_to_dict(v)
    return config


def load_config_json(path):
    with open(path, "r") as f:
        out = json.load(f)
    return Config(out)


def save_config_json(config, path, write_mode="w"):
    with open(path, write_mode) as f:
        json.dump(dict(config), f)


def load_config_yaml(path):
    with open(path, "r") as f:
        conf = yaml.load(f, Loader=yaml.FullLoader)
    return Config(conf)


def save_config_yaml(config, path, write_mode="w"):
    config = config_to_dict(config)
    with open(path, write_mode) as f:
        yaml.dump(config, f)


def main():
    cfg = load_config_json("config.json")

    print(cfg.Widdergalm.bbox)

    save_config_yaml(cfg, "config.yaml")


if __name__ == "__main__":
    main()
