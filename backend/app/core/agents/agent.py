from abc import ABC
from typing import List

from app.core.tool_executor.tools import (
    CreateCharacterTool,
    SetTitleTool,
    CreateAudioSegmentTool,
    SaveUrlAsFileTool,
    FileHandlingTool,
    GenerateSceneDialogueTool,
    CreateSoundEffectTool,
    CreateAudioOutlineTool,
)
from app.core.tool_executor.tools.agent_tool import AgentTool
from app.models.demo_configuration_model import DemoConfiguration


class Agent(ABC):
    workflow = None
    prompt = None
    models = None
    demo_configuration = None
    llm_max_tokens = 128000

    base_tools: List[AgentTool] = []
    tools: List[AgentTool] = []
    all_possible_tools = {
        "create_character": CreateCharacterTool,
        "set_title": SetTitleTool,
        "create_audio_segment": CreateAudioSegmentTool,
        "save_url_as_file": SaveUrlAsFileTool,
        "file_handling": FileHandlingTool,
        "generate_scene_dialogue": GenerateSceneDialogueTool,
        "create_sound_effect": CreateSoundEffectTool,
        "create_audio_outline": CreateAudioOutlineTool,
    }

    def __init__(self, demo_configuration: DemoConfiguration = None):
        self.demo_configuration = demo_configuration
        self.tools = self._build_tools(demo_configuration)

    def all_tools(self):
        tools = self.base_tools + self.tools
        for ancestor in Agent.mro():
            if issubclass(ancestor, Agent) and ancestor != Agent:
                tools += ancestor.tools
        return tools

    def tools_schema(self):
        functions = []
        function_names = set()

        for tool in self.all_tools():
            tool_variables_replacements = None
            if self.demo_configuration is not None:
                agent_configuration = self.demo_configuration['agent_configuration']
                tool_schema = agent_configuration.get(tool.schema()['name'])
                if tool_schema is None:
                    continue

                if tool_schema['is_enabled'] is False:
                    continue

                tool_variables_replacements = tool_schema.get('parameters_variables_values')

            schema = tool.schema(replacements=tool_variables_replacements)
            
            if schema['name'] not in function_names:
                functions.append(schema)
                function_names.add(schema['name'])

        return functions

    def _build_tools(self, demo_configuration: DemoConfiguration) -> List:
        if demo_configuration is None:
            return []

        tools = []
        for tool, tool_configuration in demo_configuration['agent_configuration'].items():
            tool_class = self.all_possible_tools.get(tool)
            if tool_class is None:
                continue

            if tool_configuration is None:
                continue

            if tool_configuration['is_enabled'] is False:
                continue

            tools.append(tool_class)

        return tools
