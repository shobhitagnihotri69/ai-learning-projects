"""
Shared utilities for LangGraph projects.
"""

from langgraph.graph import StateGraph, END
from typing import TypedDict


def build_graph(state_schema: type, nodes: dict, edges: list, entry: str):
    graph = StateGraph(state_schema)
    for name, fn in nodes.items():
        graph.add_node(name, fn)
    graph.set_entry_point(entry)
    for src, dst in edges:
        if dst == "end":
            graph.add_edge(src, END)
        else:
            graph.add_edge(src, dst)
    return graph.compile()


def pretty_print_state(state: dict):
    for k, v in state.items():
        print(f"  {k}: {v}")
