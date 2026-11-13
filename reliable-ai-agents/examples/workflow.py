"""The same fixed evidence workflow using two native graph APIs, without an LLM."""

import argparse
import asyncio
import json
from typing import TypedDict

from tools import RunControl, functions


class Evidence(TypedDict):
    order_id: str
    order: str
    health: str


def langchain_workflow(order_id: str) -> dict:
    from langgraph.graph import END, START, StateGraph

    tools = functions(RunControl())
    graph = StateGraph(Evidence)
    graph.add_node("order", lambda state: {"order": tools[1](state["order_id"])})
    graph.add_node("health", lambda state: {"health": tools[0]()})
    graph.add_edge(START, "order")
    graph.add_edge("order", "health")
    graph.add_edge("health", END)
    return graph.compile().invoke({"order_id": order_id})


async def microsoft_workflow(order_id: str) -> list:
    from agent_framework import Executor, WorkflowBuilder, WorkflowContext, handler

    tools = functions(RunControl())

    class Order(Executor):
        @handler
        async def collect(self, message: str, ctx: WorkflowContext[dict]) -> None:
            await ctx.send_message({"order_id": message, "order": tools[1](message)})

    class Health(Executor):
        @handler
        async def collect(self, message: dict, ctx: WorkflowContext[dict]) -> None:
            await ctx.yield_output({**message, "health": tools[0]()})

    order, health = Order(id="order"), Health(id="health")
    workflow = WorkflowBuilder(start_executor=order).add_edge(order, health).build()
    result = await workflow.run(order_id)
    return result.get_outputs()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--track", choices=["langchain", "microsoft"], required=True)
    parser.add_argument("order_id")
    args = parser.parse_args()
    result = (
        langchain_workflow(args.order_id) if args.track == "langchain"
        else asyncio.run(microsoft_workflow(args.order_id))
    )
    print(json.dumps(result, indent=2))
