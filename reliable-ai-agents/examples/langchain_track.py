"""LangChain agent, Deep Agents harness, and durable LangGraph state."""

import asyncio

from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from deepagents import create_deep_agent
from settings import STATE, model_config
from tools import INSTRUCTIONS, RunControl, functions


def build(model, stage: str, control: RunControl, checkpointer):
    domain = functions(control)
    if stage == "first":
        return create_agent(model, system_prompt=INSTRUCTIONS, checkpointer=checkpointer)
    selected = domain[:1] if stage == "tools" else domain
    limits = [
        ModelCallLimitMiddleware(run_limit=12, exit_behavior="error"),
        ToolCallLimitMiddleware(run_limit=18, exit_behavior="error"),
    ]
    if stage in {"harness", "delegate"}:
        specialists = []
        if stage == "delegate":
            specialists.append({
                "name": "order-specialist",
                "description": "Read SQL order/payment/shipment facts; cannot post notes.",
                "system_prompt": INSTRUCTIONS + "\nReturn SQL source references and uncertainty only.",
                "tools": [domain[1]],
                "middleware": [
                    ModelCallLimitMiddleware(run_limit=4, exit_behavior="error"),
                    ToolCallLimitMiddleware(run_limit=4, exit_behavior="error"),
                ],
            })
        return create_deep_agent(
            model=model,
            system_prompt=INSTRUCTIONS,
            tools=selected,
            subagents=specialists,
            middleware=limits,
            checkpointer=checkpointer,
        )
    return create_agent(
        model, system_prompt=INSTRUCTIONS, tools=selected,
        middleware=limits, checkpointer=checkpointer,
    )


async def run(prompt: str, run_id: str, stage: str, stream: bool) -> dict:
    provider, name, key = model_config()
    model = (
        ChatOpenAI(model=name, api_key=key, timeout=30, max_retries=0, max_tokens=1500)
        if provider == "openai"
        else ChatAnthropic(model_name=name, api_key=key, timeout=30, max_retries=0, max_tokens=1500)
    )
    STATE.mkdir(exist_ok=True)
    control = RunControl()
    try:
        async with AsyncSqliteSaver.from_conn_string(str(STATE / "langchain.sqlite")) as saver:
            agent = build(model, stage, control, saver)
            config = {"configurable": {"thread_id": run_id}, "recursion_limit": 40}
            inputs = {"messages": [{"role": "user", "content": prompt}]}
            async with asyncio.timeout(90):
                if stream:
                    async for update in agent.astream(inputs, config=config, stream_mode="updates"):
                        print(update)
                    result = (await agent.aget_state(config)).values
                else:
                    result = await agent.ainvoke(inputs, config=config)
            final = result["messages"][-1]
            return {
                "status": "returned",
                "text": final.content,
                "usage": getattr(final, "usage_metadata", None),
                "note": "usage is the final message only; not a whole-run bill",
                "state": str(STATE / "langchain.sqlite"),
            }
    finally:
        control.save(f"langchain-{run_id}")
