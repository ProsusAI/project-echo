
import os
import logging

from threading import RLock


class ResourcesBase:
    resources_path = None
    _lock = RLock()
    _relative_path = "data"

    @classmethod
    def get_resources_path(cls):
        with cls._lock:
            if cls.resources_path is None:
                cls.set_resources_path()
            return cls.resources_path

    @classmethod
    def set_resources_path(cls, fp: str = None):
        fp = fp or os.path.join(os.path.abspath(os.path.curdir), cls._relative_path)
        with cls._lock:
            fp = os.path.abspath(fp)
            if cls.resources_path is not None and cls.resources_path != fp:
                raise RuntimeError(
                    f"Invoked set_resources_path multiple times with different arguments:\n"
                    f"current: {cls.resources_path}\n"
                    f"new: {fp}"
                )

            if not os.path.isdir(fp):
                raise NotADirectoryError(f"Not a directory: {fp}")
            logging.info(f"Setting the resources path to {fp}")
            cls.resources_path = fp

    @classmethod
    def get_resource(cls, fn: str):
        pth = cls.get_resources_path()
        if os.path.isabs(fn):
            raise ValueError(f"fn={fn} must be a relative path")
        fp = os.path.join(pth, fn)
        if not os.path.abspath(fp).startswith(pth):
            raise ValueError(f"The absolute path of fn={fn} must be a sub-directory of {pth}")

        with open(os.path.join(pth, fp)) as inf:
            return inf.read()


class Resources(ResourcesBase):
    pass
