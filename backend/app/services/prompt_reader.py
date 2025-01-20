import json
import logging
import os

from app.utils.resources import ResourcesBase

logger = logging.getLogger("prompt_reader")


class PromptReader(ResourcesBase):
    _relative_path = os.path.join("data", "prompts")

    @classmethod
    def get_prompts_path(cls):
        return cls.get_resources_path()

    @classmethod
    def set_prompts_path(cls, fp: str = None):
        logger.info(f"Setting prompts path to: {fp}")
        return cls.set_resources_path(fp)

    @classmethod
    def get_prompt(cls, fn: str):
        logger.info(f"Reading prompt from file: {fn}")
        return cls.get_resource(fn)

    @classmethod
    def get_prompt_list(cls, fn: str):
        return json.loads(cls.get_prompt(fn))
