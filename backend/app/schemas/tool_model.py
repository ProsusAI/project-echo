import re
from typing import Optional, Dict

from pydantic import BaseModel


class ToolInput(BaseModel):
    @classmethod
    def get_schema(cls, replacements: Optional[Dict[str, str]] = None) -> Dict[str, any]:
        schema = cls.schema()

        # Retrieve the properties with potential description replacements
        properties = cls._get_properties(schema, replacements)

        parameters = {
            "type": "object",
            "properties": properties,
            "required": cls._get_required_properties(schema),
        }

        schema_description = (
            cls._get_parent_description()
            if "description" not in schema
            else schema["description"]
        )

        # Apply replacements if provided
        if replacements:
            schema_description = schema_description.format(**replacements)

        return {
            "name": cls._camel_to_snake(schema["title"]),
            "description": schema_description,
            "parameters": parameters,
        }

    @classmethod
    def _get_properties(cls, schema: Dict[str, any], replacements: Optional[Dict[str, str]] = None) -> Dict[str, any]:
        properties = {
            key: {k: v for k, v in value.items() if k not in ("title", "default")}
            for key, value in schema["properties"].items()
        }

        # Dynamically update descriptions in the properties if replacements are provided
        if replacements:
            for key, prop_attrs in properties.items():
                if 'description' in prop_attrs:
                    prop_attrs['description'] = prop_attrs['description'].format(**replacements)

        return properties

    @classmethod
    def _get_required_properties(cls, schema):
        return sorted(
            key for key, value in schema["properties"].items() if "default" not in value
        )

    @classmethod
    def _get_parent_description(cls):
        parent = cls.__bases__[0]
        parent_description = parent.model_json_schema().get("description")
        if not parent_description:
            raise ValueError(
                f"Please provide a description for {cls.__name__} or its parent class"
            )
        return parent_description

    @classmethod
    def _camel_to_snake(cls, name):
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
        return s2.lower()
