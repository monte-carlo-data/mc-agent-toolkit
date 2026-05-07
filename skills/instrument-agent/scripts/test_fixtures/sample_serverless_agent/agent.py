"""Lambda-shaped LangGraph agent fixture for instrument-agent smoke testing.

Same agent shape as sample_agent/agent.py but exposed via a Lambda
handler. Used to validate that detect_libraries.py flips runtime to
serverless and surfaces the lambda_handler signal — which drives the
workflow toward the SimpleSpanProcessor template variant.
"""

import json
from typing import TypedDict

from langchain.chat_models import ChatOpenAI
from langgraph.graph import StateGraph


class AgentState(TypedDict):
    messages: list[dict]
    iterations: int


def call_model(state: AgentState) -> AgentState:
    model = ChatOpenAI(model="gpt-4o-mini")
    response = model.invoke(state["messages"])
    state["messages"].append({"role": "assistant", "content": response.content})
    state["iterations"] += 1
    return state


def should_continue(state: AgentState) -> str:
    return "END" if state["iterations"] >= 3 else "CONTINUE"


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("call_model", call_model)
    graph.set_entry_point("call_model")
    graph.add_conditional_edges(
        "call_model", should_continue, {"CONTINUE": "call_model", "END": "__end__"}
    )
    return graph.compile()


def lambda_handler(event, context):
    prompt = event.get("prompt", "Hello, agent.")
    graph = build_graph()
    result = graph.invoke({"messages": [{"role": "user", "content": prompt}], "iterations": 0})
    return {"statusCode": 200, "body": json.dumps({"response": result["messages"][-1]["content"]})}
