# 멀티 에이전트 기반 블로그 자동 작성 시스템 (MAS)

## 프로젝트 개요
이전 포스팅의 맥락과 문제를 기억하고 일관성있는 블로그를 자동으로 작성/검토하는 LangGraph 기반 AI 에이전트 시스템 구축.

## 마일스톤

- [✔️] **Phase 0: 설계 및 아키텍처 확정**
    - Supervisor 아키텍처 기반 설계
    - 처음 포스팅하는 내용인지 이전에 작성하고 있던 내용인지 파악 후 적절한 Sub 그래프로 경로 설정
    - Context Injection 노드를 통해서 VectorDB에 저장된 이전 포스팅의 내용을 들고와서 맥락을 유지
    - Critic 노드를 통해서 글이 잘 작성되었는지 판단

- [✔️] **Phase 1: 상태(State) 정의 및 더미 노드 구축 (현재 진행 중)**
    - `BlogGraphState`에 스키마 작성
    - 에이전트 연동 전, 로직 테스트용 `dummy_nodes` 생성
        - 로직을 자세히 구현하지 않고  연결이 잘 되었는지만 확인하는 용도

- [ ] **Phase 2: LangGraph기반 workflow 뼈대 조립 및 라우팅 테스트**
  - `graph.py`에서 노드 간 Edge 연결
  - 루프 및 Edge, Conditional Edge 동작 검증

- [ ] **Phase 3: LLM 및 프롬프트 주입**
  - `actual_nodes.py`로 전환 -> `dummy`로 작성된거 실제로 구체화해서 실제 기능을 하도록 만드는 것
  - Critic 에이전트에 평가 체크리스트 프롬프트 적용

- [ ] **Phase 4: VectorDB 연동 (Context Injection)**
  - 이전 포스팅들의 '핵심 메타데이터 3요소' 추출 및 저장 로직 구현