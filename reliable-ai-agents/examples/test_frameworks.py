"""Native adapter contracts using fake HTTP transports, not live model calls."""

import asyncio
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx


class NativeFrameworkTests(unittest.IsolatedAsyncioTestCase):
    @unittest.skipUnless(importlib.util.find_spec("deepagents"), "LangChain track not installed")
    async def test_langchain_both_provider_adapters_execute_tool_loop(self):
        import httpx2
        import langchain_track
        from anthropic import AsyncAnthropic
        from openai import AsyncOpenAI
        from langchain_anthropic import ChatAnthropic
        from langchain_openai import ChatOpenAI
        from langgraph.checkpoint.memory import InMemorySaver
        from tools import RunControl

        for provider in ("openai", "anthropic"):
            requests, calls = [], []
            transport_module = httpx if provider == "openai" else httpx2

            def handler(request):
                requests.append(request)
                first = len(requests) == 1
                if provider == "openai":
                    message = {"role": "assistant", "content": None if first else "Health observed: test:health."}
                    if first:
                        message["tool_calls"] = [{
                            "id": "call_test", "type": "function",
                            "function": {"name": "health", "arguments": "{}"},
                        }]
                    body = {
                        "id": "test", "object": "chat.completion", "created": 1, "model": "test",
                        "choices": [{"index": 0, "finish_reason": "tool_calls" if first else "stop", "message": message}],
                        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                    }
                else:
                    body = {
                        "id": "test", "type": "message", "role": "assistant", "model": "test",
                        "content": (
                            [{"type": "tool_use", "id": "tool_test", "name": "health", "input": {}}]
                            if first else [{"type": "text", "text": "Health observed: test:health."}]
                        ),
                        "stop_reason": "tool_use" if first else "end_turn",
                        "usage": {"input_tokens": 1, "output_tokens": 1},
                    }
                return transport_module.Response(200, json=body)

            http = transport_module.AsyncClient(transport=transport_module.MockTransport(handler))
            sdk = AsyncOpenAI(api_key="test", http_client=http) if provider == "openai" else AsyncAnthropic(api_key="test", http_client=http)
            if provider == "openai":
                model = ChatOpenAI(
                    model="test", api_key="test", root_async_client=sdk,
                    async_client=sdk.chat.completions, max_retries=0,
                )
            else:
                model = ChatAnthropic(model_name="test", api_key="test", max_retries=0)
                # Inject the SDK's fake transport into the adapter's cached client.
                model.__dict__["_async_client"] = sdk

            def health() -> str:
                """Return a synthetic health observation."""
                calls.append(1)
                return '{"status":"healthy","source":"test:health"}'

            try:
                with patch.object(langchain_track, "functions", lambda control: [health]):
                    agent = langchain_track.build(model, "tools", RunControl(), InMemorySaver())
                result = await agent.ainvoke(
                    {"messages": [{"role": "user", "content": "Check health"}]},
                    {"configurable": {"thread_id": provider}},
                )
                self.assertIn("test:health", str(result["messages"][-1].content))
                self.assertEqual(len(requests), 2)
                self.assertEqual(len(calls), 1)
            finally:
                await sdk.close()

    @unittest.skipUnless(importlib.util.find_spec("agent_framework"), "Microsoft track not installed")
    async def test_microsoft_both_provider_adapters_and_session_roundtrip(self):
        import microsoft_track
        from agent_framework import AgentSession
        from agent_framework.anthropic import AnthropicClient
        from agent_framework.openai import OpenAIChatClient
        from anthropic import AsyncAnthropic
        from openai import AsyncOpenAI
        import httpx2
        from tools import RunControl

        for provider in ("openai", "anthropic"):
            requests = []
            tool_calls = []
            transport_module = httpx if provider == "openai" else httpx2
            def handler(request):
                requests.append(request)
                first = len(requests) == 1
                if provider == "openai" and request.url.path.endswith("/responses"):
                    body = {
                        "id": "test", "object": "response", "created_at": 1,
                        "model": "test", "status": "completed",
                        "output": [{
                            "id": "msg_test", "type": "message", "role": "assistant", "status": "completed",
                            "content": [{"type": "output_text", "text": "Unknown; no evidence supplied.", "annotations": []}],
                        }],
                        "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
                    }
                    if first:
                        body["output"] = [{
                            "id": "fc_test", "type": "function_call", "call_id": "call_test",
                            "name": "health", "arguments": "{}", "status": "completed",
                        }]
                elif provider == "openai":
                    body = {
                        "id": "test", "object": "chat.completion", "created": 1, "model": "test",
                        "choices": [{"index": 0, "finish_reason": "stop",
                                     "message": {"role": "assistant", "content": "Unknown; no evidence supplied."}}],
                        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                    }
                else:
                    body = {
                        "id": "test", "type": "message", "role": "assistant", "model": "test",
                        "content": [{"type": "text", "text": "Unknown; no evidence supplied."}],
                        "stop_reason": "end_turn", "usage": {"input_tokens": 1, "output_tokens": 1},
                    }
                    if first:
                        body["content"] = [{"type": "tool_use", "id": "tool_test", "name": "health", "input": {}}]
                        body["stop_reason"] = "tool_use"
                return transport_module.Response(200, json=body)
            http = transport_module.AsyncClient(transport=transport_module.MockTransport(handler))
            sdk = AsyncOpenAI(api_key="test", http_client=http) if provider == "openai" else AsyncAnthropic(api_key="test", http_client=http)
            client = OpenAIChatClient(model="test", async_client=sdk) if provider == "openai" else AnthropicClient(model="test", anthropic_client=sdk)
            try:
                def health() -> str:
                    """Return a synthetic health observation."""
                    tool_calls.append(1)
                    return '{"status":"healthy","source":"test:health"}'
                with tempfile.TemporaryDirectory() as folder, patch.object(
                    microsoft_track, "STATE", Path(folder),
                ), patch.object(microsoft_track, "functions", lambda control: [health]):
                    agent = microsoft_track.build(client, "harness", RunControl())
                    session = agent.create_session()
                    response = await agent.run("What is known?", session=session)
                    self.assertIn("Unknown", response.text)
                    restored = AgentSession.from_dict(json.loads(json.dumps(session.to_dict())))
                    self.assertEqual(restored.session_id, session.session_id)
                    self.assertEqual(len(requests), 2)
                    self.assertEqual(len(tool_calls), 1)
            finally:
                await sdk.close()

    @unittest.skipUnless(importlib.util.find_spec("deepagents"), "LangChain track not installed")
    async def test_langchain_harness_real_graph_with_fake_model_and_durable_state(self):
        from langchain_core.language_models.chat_models import BaseChatModel
        from langchain_core.messages import AIMessage
        from langchain_core.outputs import ChatGeneration, ChatResult
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        import langchain_track
        from tools import RunControl

        class FakeModel(BaseChatModel):
            @property
            def _llm_type(self):
                return "test"

            def bind_tools(self, tools, **kwargs):
                return self

            def _generate(self, messages, stop=None, run_manager=None, **kwargs):
                return ChatResult(generations=[
                    ChatGeneration(message=AIMessage(content="Unknown; no evidence supplied."))
                ])

        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "state.sqlite")
            async with AsyncSqliteSaver.from_conn_string(path) as saver:
                agent = langchain_track.build(FakeModel(), "harness", RunControl(), saver)
                config = {"configurable": {"thread_id": "test"}}
                result = await agent.ainvoke({"messages": [{"role": "user", "content": "Assess"}]}, config)
                self.assertIn("Unknown", result["messages"][-1].content)
            async with AsyncSqliteSaver.from_conn_string(path) as saver:
                agent = langchain_track.build(FakeModel(), "harness", RunControl(), saver)
                restored = await agent.aget_state(config)
                self.assertEqual(len(restored.values["messages"]), 2)

    @unittest.skipUnless(importlib.util.find_spec("agent_framework") and importlib.util.find_spec("deepagents"), "Both tracks not installed")
    async def test_both_native_workflow_graphs(self):
        import workflow
        fake = lambda control: [lambda: '{"status":"healthy"}', lambda order_id: '{"order":"captured"}']
        with patch.object(workflow, "functions", fake):
            self.assertIn("health", workflow.langchain_workflow("ORD-1001"))
            result = await workflow.microsoft_workflow("ORD-1001")
            self.assertEqual(result[0]["order_id"], "ORD-1001")


if __name__ == "__main__":
    unittest.main()
