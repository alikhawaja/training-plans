"""Microsoft-native agents, harness tools, delegation, and session persistence."""

import asyncio
import json

from agent_framework import (
    Agent, AgentSession, FileSystemAgentFileStore, FunctionMiddleware,
    MiddlewareFailure, create_harness_agent, tool,
)
from agent_framework.anthropic import AnthropicClient
from agent_framework.openai import OpenAIChatClient
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from settings import STATE, model_config
from tools import INSTRUCTIONS, RunControl, functions


class EnforceBudget(FunctionMiddleware):
    def __init__(self):
        self.calls = 0

    async def process(self, context, call_next):
        self.calls += 1
        if self.calls > 18:
            raise MiddlewareFailure("Tool budget exhausted; investigation is partial")
        try:
            await call_next()
        except RuntimeError as exc:
            raise MiddlewareFailure(str(exc)) from exc


def build(client, stage: str, control: RunControl):
    domain = functions(control)
    options = {"max_tokens": 1500}
    if isinstance(client, OpenAIChatClient):
        options["store"] = False
    selected = [] if stage == "first" else domain[:1] if stage == "tools" else domain
    native_tools = [tool(f) for f in selected]
    if stage == "delegate":
        specialist = Agent(
            client=client, name="OrderSpecialist",
            description="Bounded SQL order investigation with evidence references; no ticket writes.",
            instructions=INSTRUCTIONS,
            tools=[tool(domain[1], max_invocations=4)],
            middleware=[EnforceBudget()],
            default_options=options,
        )
        native_tools.append(specialist.as_tool())
    if stage in {"harness", "delegate"}:
        return create_harness_agent(
            client=client, name="SupportInvestigator", agent_instructions=INSTRUCTIONS,
            tools=native_tools, disable_web_search=True,
            disable_tool_auto_approval=True,
            file_memory_store=FileSystemAgentFileStore(STATE / "microsoft-memory"),
            # No shell executor, external skills or file-access provider is supplied.
            max_output_tokens=1500,
            default_options=options,
            middleware=[EnforceBudget()],
        )
    return Agent(
        client=client, name="SupportInvestigator", instructions=INSTRUCTIONS,
        tools=native_tools, middleware=[EnforceBudget()],
        default_options=options,
    )


async def run(prompt: str, run_id: str, stage: str, stream: bool) -> dict:
    provider, model, key = model_config()
    STATE.mkdir(exist_ok=True)
    control = RunControl()
    config = {
        "max_iterations": 12, "max_function_calls": 18,
        "max_duration_seconds": 85, "allow_concurrent_invocation": False,
        "max_consecutive_errors_per_request": 1,
    }
    session_file = STATE / f"microsoft-{run_id}-session.json"
    session = (
        AgentSession.from_dict(json.loads(session_file.read_text()))
        if session_file.exists() else AgentSession(session_id=run_id)
    )
    sdk = (
        AsyncOpenAI(api_key=key, timeout=30, max_retries=0)
        if provider == "openai" else AsyncAnthropic(api_key=key, timeout=30, max_retries=0)
    )
    try:
        async with sdk:
            client = (
                OpenAIChatClient(model=model, async_client=sdk, function_invocation_configuration=config)
                if provider == "openai"
                else AnthropicClient(model=model, anthropic_client=sdk, function_invocation_configuration=config)
            )
            agent = build(client, stage, control)
            async with asyncio.timeout(90):
                if stream:
                    response_stream = agent.run(prompt, session=session, stream=True)
                    async for update in response_stream:
                        if update.text:
                            print(update.text, end="", flush=True)
                    response = await response_stream.get_final_response()
                else:
                    response = await agent.run(prompt, session=session)
            return {
                "status": "returned", "text": response.text,
                "usage": str(response.usage_details),
                "note": "token usage is not an exact monetary spending cap",
                "state": str(session_file),
            }
    finally:
        session_file.write_text(json.dumps(session.to_dict(), indent=2), encoding="utf-8")
        control.save(f"microsoft-{run_id}")
