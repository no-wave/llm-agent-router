# 에이전트 워크플로우 설계로 똑똑한 AI 에이전트 만들기


<img src="https://beat-by-wire.gitbook.io/beat-by-wire/~gitbook/image?url=https%3A%2F%2F3055094660-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-x-prod.appspot.com%2Fo%2Fspaces%252FYzxz4QeW9UTrhrpWwKiQ%252Fuploads%252FeyqNTu8DIosQCukS9dyb%252FGroup%25202.png%3Falt%3Dmedia%26token%3Dd1075245-3e5a-43cd-b2f7-e0a85b0909e4&width=300&dpr=4&quality=100&sign=7c4305b0&sv=2" width="500" height="707"/>

## 책 소개

인공지능 기술의 발전은 우리가 시스템을 설계하고 구현하는 방식을 근본적으로 변화시키고 있다. 특히 대규모 언어 모델(LLM)의 등장은 자연어 처리를 넘어 복잡한 의사결정과 작업 수행이 가능한 AI 에이전트 시대를 열었다. 하지만 실제 프로덕션 환경에서 AI 에이전트를 구축할 때 우리는 중요한 질문들과 마주하게 된다. 모든 작업에 가장 강력한 모델을 사용해야 하는가? 비용과 성능 사이에서 어떻게 균형을 맞출 것인가? 사용자의 다양한 의도를 어떻게 정확하게 파악하고 적절한 처리 경로로 안내할 것인가?

이러한 질문들에 대한 해답이 바로 LLM 라우터(Router)다. 라우터는 단순히 요청을 전달하는 것을 넘어, 각 상황에 가장 적합한 모델, 데이터 소스, 처리 경로를 지능적으로 선택하는 핵심 메커니즘이다. 간단한 FAQ 응답에는 경량 모델을, 복잡한 추론이 필요한 작업에는 고성능 모델을, 특정 도메인 지식이 필요한 질문에는 RAG(Retrieval-Augmented Generation) 시스템을 활용하는 등 상황별 최적화를 가능하게 한다.

이 책은 네 가지 핵심 라우터 패턴을 통해 실용적이고 효율적인 AI 에이전트를 구축하는 방법을 다룬다. Router RAG Agent는 지식 베이스와 실시간 정보 검색을 지능적으로 조합하여 정확하고 맥락에 맞는 답변을 생성한다. Router LLM Model Agent는 작업의 복잡도를 평가하여 비용 효율적인 모델 선택을 자동화한다. Router Classify Agent는 사용자 의도를 정확히 분류하여 적절한 워크플로우로 요청을 분기시킨다. 마지막으로 Router LLM Serving Agent는 여러 모델 서빙 엔드포인트를 관리하며 안정적이고 유연한 인프라를 구축한다.

각 장에서는 이론적 배경과 아키텍처 설명에 그치지 않고, 실제 커피 키오스크 주문 시스템이라는 구체적인 예제를 통해 각 라우터 패턴이 어떻게 실전에 적용되는지 보여준다. 독자들은 단계별 튜토리얼을 따라가며 직접 코드를 작성하고 실행해볼 수 있으며, 마지막 장에서는 모든 개념을 통합한 완전한 프로젝트를 구현하게 된다.

AI 에이전트 개발은 더 이상 소수 전문가의 영역이 아니다. 적절한 가이드와 실용적인 패턴만 있다면 누구나 지능적이고 효율적인 시스템을 구축할 수 있다. 이 책이 여러분의 AI 에이전트 개발 여정에서 실질적인 길잡이가 되기를 바라며, 라우터라는 강력한 도구를 통해 더욱 똑똑하고 비용 효율적인 시스템을 만들어나가는 데 도움이 되기를 희망한다.


## 목 차

저자 소개

Table of Contents (목차)

서문: 들어가며

제1장: Router RAG Agent: 지능형 지식 탐색 및 합성

1.1. Router RAG 아키텍처

1.2. Router RAG 다이어그램

1.3. Router RAG Agent 기본 실습

1.4. Router RAG Agent: 커피 키오스크 주문 시스템

제2장: Router LLM Model Agent: 비용과 성능의 동적 최적화

2.1. Router LLM 아키텍처

2.2. Router LLM 다이어그램

2.3. Router LLM Model Agent 튜토리얼

2.4. Router LLM Model Agent: 커피 키오스크 주문 시스템

제3장: Router Classify Agent: 사용자 의도 기반 워크플로우 분기

3.1. Router Classify 아키텍처

3.2. Router Classify 분류기 다이어그램

3.3. Router Classify Agent 튜토리얼

3.4. Router Classify Agent: 커피 키오스크 주문 시스템

제4장: Router LLM Serving Agent: 유연하고 안정적인 서빙 인프라 관리

4.1. Router LLM Serving Agent 아키텍처

4.2. Router LLM Serving 다이어그램

4.3. Ollama 설치하기

4.4. Router LLM Serving Agent 튜토리얼

4.5. Router LLM Serving Agent: 커피 키오스크 주문 시스템

제5장: 실전 프로젝트: 카페 키오스크 주문 에이전트

5.1. 실전 프로젝트 개요

5.2. 설치 및 환경 설정

5.3. 에이전트 실행하기

제6장: 결론: 시나리오별 최적 라우터 설계 및 전망

References. 참고 문헌


## E-Book 구매

- Yes24: https://www.yes24.com/product/goods/162905689
- 교보문고: 
- 알라딘: https://www.aladin.co.kr/shop/wproduct.aspx?ItemId=375953484

## Github 코드: 

https://github.com/no-wave/llm-agent-router
