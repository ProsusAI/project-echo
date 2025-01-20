from typing import Optional, Dict
from pydantic import BaseModel

class ToolConfiguration(BaseModel):
    is_enabled: bool
    system_prompt_guidelines: str
    parameters_variables_values: Optional[Dict] = None

class AgentConfiguration(BaseModel):
    create_character: ToolConfiguration
    set_title: ToolConfiguration
    create_audio_segment: ToolConfiguration
    save_url_as_file: ToolConfiguration
    file_handling: ToolConfiguration
    generate_scene_dialogue: ToolConfiguration
    create_sound_effect: ToolConfiguration
    create_audio_outline: ToolConfiguration

class DemoConfiguration(BaseModel):
    demo_name: str
    agent_configuration: AgentConfiguration
