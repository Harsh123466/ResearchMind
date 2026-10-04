from langgraph.graph import StateGraph, START, END

from graph.state import ResearchState
from graph.nodes import search_node, reader_node, critic_node, writer_node
from langgraph.types import RetryPolicy


retry = RetryPolicy(
    max_attempts=6,
    initial_interval=10.0,
    backoff_factor=2.0,
    max_interval=90.0,
    retry_on=Exception,
)


# conditional decision
def should_continue(state: ResearchState):

    if state['score'] >= 7:
        return "end"

    if state.get("revision_count", 0) >= 3:
        return "end"

    return "rewrite"


# Build Graph

graph = StateGraph(ResearchState)


# Add Nodes
graph.add_node("search", search_node, retry_policy=retry)
graph.add_node("reader", reader_node, retry_policy=retry)
graph.add_node("writer", writer_node, retry_policy=retry)
graph.add_node("critic", critic_node, retry_policy=retry)


# Connect Nodes
graph.add_edge(START, 'search')
graph.add_edge('search', 'reader')
graph.add_edge('reader','writer')
graph.add_edge('writer','critic')



# Conditional Edge
graph.add_conditional_edges(
    'critic',
    should_continue,
    {
        'rewrite': 'writer',
        'end': END
    }
)


graph = graph.compile()