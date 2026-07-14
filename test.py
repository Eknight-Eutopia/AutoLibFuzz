from langchain.agents import create_agent

from agents.llm import llm_base

test_agent = create_agent(
    model=llm_base.create_model(),
    tools=[],
    system_prompt="You are a useful agent"
)

test_agent.invoke({
    "messages": [
        {"role": "user", "content": "Hello, how are you?"}
    ]
})