from langchain.tools import tool, ToolRuntime
from langchain.messages import ToolMessage
from langchain.agents import create_agent, AgentState
from langgraph.types import Command

from agents.llm import llm_base
from agents.harness import harness_agent
from agents.instrument import instrument_agent
from agents.api import api_agent
from tools.target_analysis import build_harness_context

from utils.logger import get_logger
logger = get_logger()

SYSTEM_MAIN_PROMPT = """You corrdinate specialized sub-agents
Available agents:
- instrument: construct libafl_cc and use it to instrument target library source code.
- api: analyze the target library and generate a list of public APIs that can be fuzzed.
- harness: compose harness.c(cc) and compile it with libafl_cc and target library
Use the task tool to delegate work.
First, use the `set_state` tool to set the state with target library path and libafl_cc path .
Then, use the instrument agent to instrument the target library with libafl_cc. If instrument agent fails, you need to give possible solutions to instrument agent and retry. Max retry times is 5. If it still failes, exit directly and report problem.
Lastly, use the api agent to analyze the target library and generate a list of public APIs that can be fuzzed. Make sure all APIs are provided and written to `harness_path/api_<function_name>/api.txt` file. If api agent has found any new api, you need to ask it to update. Continue this loop for max 5 times. Make sure api agent achieved maxmium coverage of the target library apis.
Then, use the harness agent to compose harness.c(cc) and compile it with libafl_cc and target library for all APIs. Make sure all APIs provided by the api agent are successfully built and compiled. If harness agent fails, you need to give possible solutions to harness agent and retry. Max retry times is 5. If it still failes, exit directly and report problem.
Notice that you need to complete instrument work first, then you can call harness agent.
"""

class CustomState(AgentState):
    target_library_path: str = ""
    libafl_cc_path: str = ""
    harness_path: str = ""
    # is_instrumented: bool = False
    # is_harnessed: bool = False

SUBAGENTS = {
    "harness": harness_agent,
    "api": api_agent,
    "instrument": instrument_agent
}

@tool
def task(
    agent_name: str,
    description: str,
    runtime: ToolRuntime[None, CustomState]
) -> str:
    """Launch an ephemeral subagent for a task

    Available agents:
    - instrument: construct libafl_cc and use it to instrument target library source code. 
    - api: analyze the target library and generate a list of public APIs that can be fuzzed.
    - harness: compose harness.c(cc) and compile it with libafl_cc and target library.
    """
    logger.info(f"\n========================================")
    logger.info(f"Launching subagent {agent_name} for task: {description}")
    description += (
        "\nExecution context:"
        f"\n- target_library_path: {runtime.state['target_library_path']}"
        f"\n- libafl_cc_path: {runtime.state['libafl_cc_path']}"
        f"\n- harness_path: {runtime.state['harness_path']}"
    )
    if agent_name == "harness":
        description += "\n\nPrecomputed harness context:\n"
        description += build_harness_context(runtime.state["target_library_path"])
    agent = SUBAGENTS[agent_name]
    result = agent.invoke({
        "messages": [
            {"role": "user", "content": description}
        ]
    })
    logger.info(f"Subagent {agent_name} completed : {result['messages'][-1].content}")
    logger.info(f"\n========================================\n")
    return result["messages"][-1].content

@tool
def set_state(
    target_library_path: str,
    libafl_cc_path: str,
    harness_path: str,
    runtime: ToolRuntime[None, CustomState]
) -> str:
    """Set the state of the main agent"""
    logger.debug(f"Setting state: target_library_path={target_library_path}, libafl_cc_path={libafl_cc_path}, harness_path={harness_path}")
    return Command(
        update={
            "target_library_path": target_library_path,
            "libafl_cc_path": libafl_cc_path,
            "harness_path": harness_path,
            "messages": [
                ToolMessage(
                    content=f"State updated: target_library_path={target_library_path}, libafl_cc_path={libafl_cc_path}, harness_path={harness_path}",
                    tool_call_id=runtime.tool_call_id
                )
            ]
        }
    )

main_agent = create_agent(
    llm_base.create_model(),
    tools=[task, set_state],
    system_prompt=SYSTEM_MAIN_PROMPT,
    state_schema=CustomState,
)
