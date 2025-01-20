import logging
import asyncio
from typing import Dict, Any, List
from asyncio import Queue

from pydantic import ValidationError

from app.core.tool_executor.utils import flatten_parallel
from app.models.session_model import Session
from app.core.tool_executor.tools.agent_tool import AgentTool

logger = logging.getLogger(__name__)

class ToolExecutor:
    @staticmethod
    def initialise_tools(agent):
        return list(set(tool for tool in agent.all_tools()))

    def __init__(self, agent):
        self.tools = ToolExecutor.initialise_tools(agent)
        self.tools_router = {
            tool.schema().get("name"): tool for tool in self.tools
        }

    async def execute_tool(
            self,
            tool_to_call: dict,
            agent_session: Session,
            workflow: str,
            queue: Queue
    ):

        tool_name = tool_to_call["tool_name"]
        tool_args = tool_to_call["tool_args"]
        tool_call_id = tool_to_call.get("tool_call_id")
        tool_class = self.tools_router.get(tool_name)

        logging.info(f"Executing tool", extra={"tool_name": tool_name, "tool_args": tool_args, "tool_call_id": tool_call_id})

        if tool_class is None:
            raise ValueError(f"Function {tool_name} is not supported, please select one of the following: {self.tools_router.keys()}")

        tool: AgentTool = tool_class(
            tool_name=tool_name,
            tool_args=tool_args,
            tool_call_id=tool_call_id,
            agent_session=agent_session,
            workflow=workflow
        )

        async for update in tool.execute():
            await queue.put(update)

    async def execute_tools_concurrently(self, tools_to_call: List[Dict[str, Any]], agent_session: Session, workflow: str):
        queue = Queue(maxsize=1000)

        calls = []
        for tool_to_call in tools_to_call:
            flattened = flatten_parallel(tool_to_call["tool_name"], tool_to_call["tool_args"])
            calls.extend(flattened)

        async def execute_and_enqueue(tool_to_call):
            try:
                await self.execute_tool(tool_to_call, agent_session, workflow, queue)
            except ValidationError as e:
                error_message = f"Validation error in {tool_to_call['tool_name']}: {str(e)}"
                logging.error(error_message)
                await queue.put({
                    "message_type": "validation_error",
                    "content": error_message,
                    "tool_name": tool_to_call['tool_name']
                })

        semaphore = asyncio.Semaphore(10)  # Limit concurrent executions to 10

        async def sem_task(coro):
            async with semaphore:
                await coro

        tasks = [asyncio.create_task(sem_task(execute_and_enqueue(tool_to_call)))
                 for tool_to_call in calls]

        async def process_queue():
            while True:
                try:
                    update = queue.get_nowait()
                    yield update
                    queue.task_done()
                except asyncio.QueueEmpty:
                    if all(task.done() for task in tasks):
                        break
                    await asyncio.sleep(0.1)  # Small delay to prevent busy waiting

        async for update in process_queue():
            yield update

        await asyncio.gather(*tasks)  # Ensure all tasks are completed