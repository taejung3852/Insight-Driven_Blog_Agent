from langgraph.graph import StateGraph, START, END
from src.state import BlogState
from src.nodes.main_node import (
    supervisor_agent,
    context_injection_agent,
    critic_agent,
    final_agent,
    image_analysis_agent,
    image_placement_agent
)
from src.nodes.sub_graph_nodes.intro_graph_node import (
    intro_supervisor_agent,
    intro_outline_agent,
    intro_draft_agent,
    internal_editor_agent
)
from src.nodes.sub_graph_nodes.continuation_graph_node import (
    continuation_supervisor_agent,
    continuation_outline_agent,
    continuation_draft_agent,
    continuation_internal_editor_agent
)


# ==============================================
# 첫 포스팅을 처리할 Sub-graph
intro_workflow = StateGraph(BlogState)

# intro_워크플로우 node 추가
intro_workflow.add_node("intro_supervisor", intro_supervisor_agent)
intro_workflow.add_node('outline', intro_outline_agent)
intro_workflow.add_node("image_analysis", image_analysis_agent)
intro_workflow.add_node("draft", intro_draft_agent)
intro_workflow.add_node("internal_editor", internal_editor_agent)
intro_workflow.add_node('image_placement', image_placement_agent)

def route_intro_graph(state: BlogState):
    step = state.get('sub_next_step')
    if step == 'finish':
        return END
    return step

# intro_워크플로우 순서
intro_workflow.add_edge(START, "intro_supervisor")

intro_workflow.add_conditional_edges("intro_supervisor", route_intro_graph,
                                     {
                                        'outline': 'outline',
                                        'image_analysis': 'image_analysis',
                                        "draft": "draft",
                                        "internal_editor": "internal_editor",
                                        END: END
                                     }
                                    )

intro_workflow.add_edge("outline", "intro_supervisor")
intro_workflow.add_edge("image_analysis", "image_placement") # 분석 끝나면 삽입으로
intro_workflow.add_edge("image_placement", "intro_supervisor")
intro_workflow.add_edge("draft", "intro_supervisor")
intro_workflow.add_edge("internal_editor", "intro_supervisor")

intro_app = intro_workflow.compile()
# ==============================================

# ==============================================
# 연재 중인 블로그 포스팅을 처리할 Sub-graph
continuation_workflow = StateGraph(BlogState)

# continuation_workflow node 추가
continuation_workflow.add_node("continuation_supervisor", continuation_supervisor_agent)
continuation_workflow.add_node("outline", continuation_outline_agent)
continuation_workflow.add_node("image_analysis", image_analysis_agent) # 공통 사용
continuation_workflow.add_node("draft", continuation_draft_agent)
continuation_workflow.add_node("internal_editor", continuation_internal_editor_agent)
continuation_workflow.add_node('image_placement', image_placement_agent)


def route_continuation_graph(state: BlogState):
    step = state.get('sub_next_step')
    if step == 'finish':
        return END # 사실상 안쓰임
    return step

# continuation_workflow 순서
continuation_workflow.add_edge(START, "continuation_supervisor")

continuation_workflow.add_conditional_edges('continuation_supervisor', route_continuation_graph,
                                            {
                                                "outline": "outline",
                                                "image_analysis": "image_analysis",
                                                "draft": "draft",
                                                "internal_editor": "internal_editor",
                                                END:END
                                            }
                                        )

continuation_workflow.add_edge("outline", "continuation_supervisor")
continuation_workflow.add_edge("image_analysis", "image_placement")
continuation_workflow.add_edge("image_placement", "continuation_supervisor")
continuation_workflow.add_edge("draft", "continuation_supervisor")
continuation_workflow.add_edge("internal_editor", "continuation_supervisor")

continuation_app = continuation_workflow.compile()
# ==============================================


workflow = StateGraph(BlogState)

workflow.add_node('supervisor', supervisor_agent)
workflow.add_node('context_injection', context_injection_agent)
workflow.add_node('intro_graph', intro_app) # 서브 그래프를 노드로 넣는다.
workflow.add_node('continuation_graph', continuation_app) # 서브 그래프를 노드로 넣는다.
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

# # 컴파일된 app 객체 사용
# https://mermaid.live 이 사이트에 출력된 결롸를 넣으면 시각화 그래프를 얻을 수 잇다.
# mermaid_code = app.get_graph().draw_mermaid()
# print(mermaid_code)