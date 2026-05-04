# 멀티 에이전트 기반 개인화 블로그 작성 시스템 (MAS)

## 프로젝트 개요
사용자의 학습 인사이트와 멀티모달(캡처 이미지) 데이터를 바탕으로, 기계적인 느낌 없이 '직접 공부하며 쓴 느낌'의 개인화된 블로그 포스팅을 작성/검토하는 LangGraph 기반 AI 에이전트 시스템 구축.

## 마일스톤

- [x] **Phase 0: 설계 및 아키텍처 확정**
  - Supervisor 아키텍처 기반 설계
  - 처음 포스팅하는 내용인지 이전에 작성하고 있던 내용인지 파악 후 적절한 Sub 그래프로 경로 설정
  - Context Injection 노드를 통해서 VectorDB에 저장된 이전 포스팅의 내용을 들고와서 맥락을 유지
  - Critic 노드를 통해서 글이 잘 작성되었는지 판단

- [x] **Phase 1: 상태(State) 정의 및 더미 노드 구축**
  - `BlogState` 스키마 작성 (TypedDict 기반으로 업데이트 완료)
  - 에이전트 연동 전, 로직 테스트용 `dummy_nodes` 생성
    - 로직을 자세히 구현하지 않고 연결이 잘 되었는지만 확인하는 용도

- [x] **Phase 2: LangGraph기반 workflow 뼈대 조립 및 라우팅 테스트**
  - `graph.py`에서 노드 간 Edge 연결
  - 루프 및 Edge, Conditional Edge 동작 검증 완료

- [x] **Phase 3: LLM 기본 연동 및 시스템 프롬프트 가이드라인 확립**
  - `llm_nodes.py` 생성 및 OpenAI 연동
  - CARE 프레임워크(역할-목표-규칙-출력형식) 기반 프롬프트 템플릿 문서화(`docs/04_prompt_guide.md`)
  
- [ ] **Phase 4: 사용자 맞춤형 서브 그래프(Sub-graph) 구축 및 멀티모달 연동**
  - 학습 인사이트 기반 아웃라인 설계 (`content_structure_agent`)
  - 캡처 이미지(Base64) 분석 및 최적 배치 가이드 (`image_analysis_agent`)
  - 기계적 냄새를 지운 휴먼라이징 초안 작성 (`humanized_draft_agent`)
  - 메인 그래프(`supervisor`)와 서브 그래프(계층형 라우팅) 통합

- [ ] **Phase 5: VectorDB 연동 (Context Injection) 및 최종 테스트**
  - 이전 포스팅들의 '핵심 메타데이터 3요소' 추출 및 저장 로직 구현
  - RAG 기반 맥락 주입 테스트