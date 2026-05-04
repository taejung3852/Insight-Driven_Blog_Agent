from langgraph.graph import StateGraph, START, END
from src.state import BlogState
from src.nodes.llm_nodes import (
    supervisor_agent,
    context_injection_agent,
    intro_graph_agent,
    continuation_graph_agent,
    critic_agent,
    final_agent
)

workflow = StateGraph(BlogState)

workflow.add_node('supervisor', supervisor_agent)
workflow.add_node('context_injection', context_injection_agent)
workflow.add_node('intro_graph', intro_graph_agent)
workflow.add_node('continuation_graph', continuation_graph_agent)
workflow.add_node('critic', critic_agent)
workflow.add_node('final', final_agent)

workflow.add_edge(START, 'supervisor')

def route_from_supervisor(state: BlogState) -> str:
    # 아직은 supervisor_agent가 state의 'next_step'을 업데이트 했다고 가정
    return state.get('next_step')

workflow.add_conditional_edges('supervisor', route_from_supervisor,
                               {'context_injection' : 'context_injection',
                                'intro_graph' : 'intro_graph',
                                'continuation_graph': 'continuation_graph',
                                'critic' : 'critic',
                                'final' : 'final'
                                   })

workflow.add_edge('context_injection', 'supervisor')
workflow.add_edge('intro_graph', 'supervisor')
workflow.add_edge('continuation_graph', 'supervisor')
workflow.add_edge('critic', 'supervisor')
workflow.add_edge('final', END)

app = workflow.compile()