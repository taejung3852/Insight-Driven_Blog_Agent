# Multi-Agent Blog Generator

> **LangGraph 기반의 지능형 멀티 에이전트 블로그 작성 시스템**
> 이전 글의 맥락과 문체를 기억하여 일관성 있는 시리즈 포스팅을 생성합니다.

---

## 프로젝트 개요
단순한 텍스트 생성을 넘어, 사용자의 기존 집필 스타일을 분석하고 지식의 연속성을 유지하는 블로그 에이전트 시스템입니다. **Supervisor 아키텍처**를 활용하여 콘텐츠 생성, 비평, 맥락 주입 과정을 자동화합니다.

## 핵심 기능
- **Context Engineering**: VectorDB를 활용해 이전 포스트의 핵심 메타데이터(용어, 결론, 문체 지문)를 추출 및 주입합니다.
- **Multi-Agent Orchestration**: Supervisor 에이전트가 작업 흐름을 제어하며 적절한 작업 노드에 할당합니다.
- **Style Consistency**: 전략 패턴을 통해 사용자 맞춤형 말투와 톤앤매너를 유지합니다.
- **LLM-as-a-judge**: Critic 에이전트가 사전에 정의된 체크리스트를 바탕으로 글의 완성도를 엄격히 검토합니다.

## 시스템 아키텍처
본 프로젝트는 LangGraph를 사용하여 상태 중심의 순환 그래프 구조로 설계되었습니다.

1. **Hierarchical**: 계층형 구조 도입
    1.1. Main Supervisor
    전체 워크플로우의 거시적인 방향을 결정합니다.
    - **Context Injection**: 이전 포스트 메타데이터 주입 지시
    - **Critic & Final**: 최종 검토 및 VectorDB 업데이트 지시

    1.2. Sub-Graphs (하위 작업 그룹)
    실제 콘텐츠 생성을 담당하며, 내부적으로 Sub-Supervisor가 세부 작업을 조율합니다.
    - **Intro Graph**: 첫 포스팅 전용 작성 파이프라인 (작성 → 자체 리뷰)
    - **Continuation Graph**: 2편 이상 연속 포스팅 파이프라인 (맥락 분석 → 작성 → 자체 리뷰)
2. **Context Injection**: 이전 포스트 맥락 불러오기
3. **Intro/Continuation Graph**: 포스트 순서에 따른 맞춤형 집필
4. **Critic**: 일관성 및 품질 검토 (반려 시 재작업 루프)
5. **Final**: 최종 결과물 정제 및 출력

## 프로젝트 구조
```text
blog_agent_project/
├── docs/               # 설계 및 규약 문서
├── src/
│   ├── nodes/          # 에이전트 노드 로직
│   ├── state.py        # 그래프 상태 정의
│   ├── graph.py        # LangGraph 회로 구성
│   └── strategies.py   # 문체/스타일 전략 클래스
├── main.py             # 시스템 실행 엔트리 포인트
├── requirements.txt    # 사용된 라이브러리 패키지
└── README.md
```
## 개발 규약
본 프로젝트는 아래 규약을 따라 개발되었습니다.
- (docs/02_git_branch_strategy.md)
- (docs/03_commit_message_guide.md)

## 문서
- [프로젝트 마일스톤] (docs/01_project_milestone.md)