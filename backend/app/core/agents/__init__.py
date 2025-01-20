from app.core.agents.agent import Agent
from app.core.agents.voice_director import VoiceDirector

agents = [
    VoiceDirector,
]

agent_router = {agent.workflow: agent for agent in agents}