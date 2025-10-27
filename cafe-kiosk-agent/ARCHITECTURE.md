# 카페 키오스크 에이전트 - 아키텍처 Flowchart

## 1. 전체 시스템 아키텍처

```mermaid
flowchart TB
    subgraph User["👤 사용자 인터페이스"]
        UI[키오스크 터미널<br/>main.py]
    end
    
    subgraph Agents["🤖 에이전트 레이어"]
        OA[주문 에이전트<br/>OrderAgent]
        RA[추천 에이전트<br/>RecommendationAgent]
    end
    
    subgraph Routers["🔀 라우터 레이어"]
        CR[카테고리 라우터<br/>CategoryRouter]
        MR[모델 라우터<br/>ModelRouter]
        SR[서빙 라우터<br/>ServingRouter]
    end
    
    subgraph Services["⚙️ 서비스 레이어"]
        LS[LLM 서비스<br/>LLMService]
        OS[주문 서비스<br/>OrderService]
    end
    
    subgraph External["🌐 외부 서비스"]
        OPENAI[OpenAI API<br/>GPT-4o-mini]
        OLLAMA[Ollama<br/>로컬 모델]
    end
    
    subgraph Data["💾 데이터 레이어"]
        MENU[메뉴 DB<br/>menu_database.py]
        CONFIG[설정<br/>settings.py]
    end
    
    subgraph Utils["🛠️ 유틸리티"]
        LOG[로거<br/>logger.py]
        VAL[검증기<br/>validators.py]
    end
    
    UI --> OA
    UI --> RA
    
    OA --> CR
    OA --> MR
    OA --> SR
    OA --> OS
    
    RA --> OS
    RA --> MENU
    
    CR --> LS
    MR --> LS
    SR --> LS
    
    LS --> OPENAI
    LS --> OLLAMA
    
    OS --> MENU
    
    OA --> VAL
    OA --> LOG
    RA --> LOG
    
    CR -.->|참조| CONFIG
    MR -.->|참조| CONFIG
    SR -.->|참조| CONFIG
    
    style User fill:#e1f5ff
    style Agents fill:#fff4e1
    style Routers fill:#ffe1f5
    style Services fill:#e1ffe1
    style External fill:#ffe1e1
    style Data fill:#f5e1ff
    style Utils fill:#e1e1e1
```

## 2. 주문 처리 플로우

```mermaid
flowchart TD
    START([사용자 입력]) --> CHECK{입력 유형<br/>판단}
    
    CHECK -->|주문| ORDER[주문 처리<br/>OrderAgent]
    CHECK -->|추천| REC[추천 처리<br/>RecommendationAgent]
    CHECK -->|명령어| CMD[명령어 실행]
    
    ORDER --> VAL1[입력 검증<br/>& 살균]
    VAL1 --> ROUTE1[카테고리<br/>라우팅]
    
    ROUTE1 --> EXTRACT[메뉴 항목<br/>추출]
    EXTRACT --> CHECK_LLM{LLM<br/>성공?}
    
    CHECK_LLM -->|성공| VAL2[항목 검증]
    CHECK_LLM -->|실패| FALLBACK[폴백 추출<br/>키워드 매칭]
    FALLBACK --> VAL2
    
    VAL2 --> CHECK_VALID{검증<br/>통과?}
    
    CHECK_VALID -->|통과| CREATE[주문 생성]
    CHECK_VALID -->|실패| ERROR1[오류 메시지]
    
    CREATE --> CALC[금액 계산]
    CALC --> RECEIPT[영수증 생성]
    RECEIPT --> SUGGEST[보완 메뉴<br/>제안]
    SUGGEST --> END1([주문 완료])
    
    ERROR1 --> END2([처리 실패])
    
    REC --> TIME_CHECK{시간대/<br/>카테고리<br/>확인}
    TIME_CHECK --> GET_REC[추천 생성]
    GET_REC --> DISPLAY[추천 표시]
    DISPLAY --> END3([추천 완료])
    
    CMD --> EXEC[명령 실행]
    EXEC --> END4([실행 완료])
    
    style START fill:#e1f5ff
    style END1 fill:#e1ffe1
    style END2 fill:#ffe1e1
    style END3 fill:#fff4e1
    style END4 fill:#f5e1ff
```

## 3. 멀티 라우터 시스템

```mermaid
flowchart LR
    subgraph Input["입력"]
        QUERY[사용자 질문/<br/>주문]
    end
    
    subgraph CategoryRouter["1️⃣ 카테고리 라우터"]
        CR_START[카테고리 분류]
        CR_KEYWORD[키워드 매칭<br/>신뢰도 > 0.8]
        CR_LLM[LLM 분류]
        CR_RESULT{분류 결과}
        
        CR_START --> CR_KEYWORD
        CR_KEYWORD -->|실패| CR_LLM
        CR_KEYWORD -->|성공| CR_RESULT
        CR_LLM --> CR_RESULT
    end
    
    subgraph ModelRouter["2️⃣ 모델 라우터"]
        MR_START[복잡도 분석]
        MR_COMPLEX{복잡도}
        MR_LOW[gpt-4o-mini<br/>경량 모델]
        MR_MED[gpt-4o-mini<br/>표준 모델]
        MR_HIGH[gpt-4o-mini<br/>고급 모델]
        
        MR_START --> MR_COMPLEX
        MR_COMPLEX -->|Low| MR_LOW
        MR_COMPLEX -->|Medium| MR_MED
        MR_COMPLEX -->|High| MR_HIGH
    end
    
    subgraph ServingRouter["3️⃣ 서빙 라우터"]
        SR_START[민감도 분석]
        SR_CHECK{로컬<br/>사용 가능?}
        SR_SENS{민감도}
        SR_CLOUD[클라우드<br/>OpenAI]
        SR_LOCAL[로컬<br/>Ollama]
        
        SR_START --> SR_SENS
        SR_SENS -->|High| SR_CHECK
        SR_SENS -->|Low/Med| SR_CLOUD
        SR_CHECK -->|Yes| SR_LOCAL
        SR_CHECK -->|No| SR_CLOUD
    end
    
    subgraph Output["출력"]
        BEVERAGE[음료 처리]
        DESSERT[디저트 처리]
        MEAL[식사 처리]
    end
    
    QUERY --> CR_START
    CR_RESULT -->|음료| BEVERAGE
    CR_RESULT -->|디저트| DESSERT
    CR_RESULT -->|식사| MEAL
    
    QUERY -.-> MR_START
    QUERY -.-> SR_START
    
    style Input fill:#e1f5ff
    style CategoryRouter fill:#fff4e1
    style ModelRouter fill:#ffe1f5
    style ServingRouter fill:#e1ffe1
    style Output fill:#f5e1ff
```

## 4. 데이터 흐름

```mermaid
flowchart TD
    subgraph Client["클라이언트"]
        INPUT[사용자 입력]
    end
    
    subgraph Processing["처리 과정"]
        VALIDATE[검증 & 정규화]
        ROUTE[라우팅]
        EXTRACT[정보 추출]
        PROCESS[비즈니스 로직]
    end
    
    subgraph AI["AI 처리"]
        LLM_CLASSIFY[분류]
        LLM_EXTRACT[추출]
        LLM_GENERATE[생성]
    end
    
    subgraph Storage["저장소"]
        ORDERS[(주문 데이터)]
        MENU[(메뉴 DB)]
        HISTORY[(히스토리)]
    end
    
    subgraph Output["출력"]
        RECEIPT[영수증]
        RECOMMEND[추천]
        STATS[통계]
    end
    
    INPUT --> VALIDATE
    VALIDATE --> ROUTE
    ROUTE --> LLM_CLASSIFY
    LLM_CLASSIFY --> EXTRACT
    EXTRACT --> LLM_EXTRACT
    LLM_EXTRACT --> PROCESS
    
    PROCESS --> MENU
    MENU --> PROCESS
    
    PROCESS --> ORDERS
    ORDERS --> HISTORY
    
    PROCESS --> LLM_GENERATE
    LLM_GENERATE --> RECEIPT
    LLM_GENERATE --> RECOMMEND
    
    HISTORY --> STATS
    
    style Client fill:#e1f5ff
    style Processing fill:#fff4e1
    style AI fill:#ffe1f5
    style Storage fill:#e1ffe1
    style Output fill:#f5e1ff
```

## 5. 에러 처리 플로우

```mermaid
flowchart TD
    START[요청 시작] --> TRY{Try}
    
    TRY -->|정상| VALIDATE[입력 검증]
    TRY -->|예외| CATCH[Exception Catch]
    
    VALIDATE -->|통과| LLM_CALL[LLM 호출]
    VALIDATE -->|실패| VALID_ERROR[검증 오류]
    
    LLM_CALL -->|성공| PARSE[응답 파싱]
    LLM_CALL -->|실패| LLM_ERROR[LLM 오류]
    
    PARSE -->|성공| SUCCESS[성공 응답]
    PARSE -->|실패| PARSE_ERROR[파싱 오류]
    
    VALID_ERROR --> FALLBACK{폴백<br/>가능?}
    LLM_ERROR --> FALLBACK
    PARSE_ERROR --> FALLBACK
    
    FALLBACK -->|Yes| FALLBACK_LOGIC[폴백 로직<br/>키워드 매칭]
    FALLBACK -->|No| ERROR_RESPONSE[오류 응답]
    
    FALLBACK_LOGIC --> RETRY_SUCCESS[부분 성공]
    
    CATCH --> LOG[로그 기록]
    LOG --> ERROR_RESPONSE
    
    SUCCESS --> END1([정상 종료])
    RETRY_SUCCESS --> END2([폴백 성공])
    ERROR_RESPONSE --> END3([오류 종료])
    
    style START fill:#e1f5ff
    style SUCCESS fill:#e1ffe1
    style RETRY_SUCCESS fill:#fff4e1
    style ERROR_RESPONSE fill:#ffe1e1
    style END1 fill:#e1ffe1
    style END2 fill:#fff4e1
    style END3 fill:#ffe1e1
```

## 6. 비동기 처리 구조

```mermaid
flowchart LR
    subgraph Main["메인 스레드"]
        MAIN_LOOP[이벤트 루프]
    end
    
    subgraph Tasks["비동기 태스크"]
        TASK1[주문 처리 1]
        TASK2[주문 처리 2]
        TASK3[주문 처리 3]
        TASK4[추천 생성]
        TASK5[통계 계산]
    end
    
    subgraph IO["I/O 작업"]
        API1[OpenAI API]
        API2[Ollama API]
        DB[데이터베이스]
        FILE[파일 I/O]
    end
    
    subgraph Results["결과 수집"]
        GATHER[asyncio.gather]
        RESULT[통합 결과]
    end
    
    MAIN_LOOP -->|spawn| TASK1
    MAIN_LOOP -->|spawn| TASK2
    MAIN_LOOP -->|spawn| TASK3
    MAIN_LOOP -->|spawn| TASK4
    MAIN_LOOP -->|spawn| TASK5
    
    TASK1 -->|await| API1
    TASK2 -->|await| API2
    TASK3 -->|await| DB
    TASK4 -->|await| API1
    TASK5 -->|await| FILE
    
    API1 --> GATHER
    API2 --> GATHER
    DB --> GATHER
    FILE --> GATHER
    
    GATHER --> RESULT
    RESULT --> MAIN_LOOP
    
    style Main fill:#e1f5ff
    style Tasks fill:#fff4e1
    style IO fill:#ffe1f5
    style Results fill:#e1ffe1
```

## 7. 모듈 의존성 그래프

```mermaid
flowchart TB
    subgraph Core["핵심 모듈"]
        MAIN[main.py]
        CONFIG[config/]
    end
    
    subgraph Agents["agents/"]
        ORDER_AGENT[order_agent.py]
        REC_AGENT[recommendation_agent.py]
    end
    
    subgraph Routers["routers/"]
        CAT_ROUTER[category_router.py]
        MODEL_ROUTER[model_router.py]
        SERVE_ROUTER[serving_router.py]
    end
    
    subgraph Services["services/"]
        LLM_SERVICE[llm_service.py]
        ORDER_SERVICE[order_service.py]
    end
    
    subgraph Utils["utils/"]
        LOGGER[logger.py]
        VALIDATOR[validators.py]
    end
    
    MAIN --> ORDER_AGENT
    MAIN --> REC_AGENT
    
    ORDER_AGENT --> CAT_ROUTER
    ORDER_AGENT --> MODEL_ROUTER
    ORDER_AGENT --> SERVE_ROUTER
    ORDER_AGENT --> LLM_SERVICE
    ORDER_AGENT --> ORDER_SERVICE
    ORDER_AGENT --> VALIDATOR
    
    REC_AGENT --> LLM_SERVICE
    REC_AGENT --> ORDER_SERVICE
    
    CAT_ROUTER --> LLM_SERVICE
    MODEL_ROUTER --> LLM_SERVICE
    SERVE_ROUTER --> LLM_SERVICE
    
    ORDER_AGENT --> LOGGER
    REC_AGENT --> LOGGER
    CAT_ROUTER --> LOGGER
    MODEL_ROUTER --> LOGGER
    SERVE_ROUTER --> LOGGER
    LLM_SERVICE --> LOGGER
    
    CONFIG --> ORDER_AGENT
    CONFIG --> REC_AGENT
    CONFIG --> LLM_SERVICE
    
    style Core fill:#e1f5ff
    style Agents fill:#fff4e1
    style Routers fill:#ffe1f5
    style Services fill:#e1ffe1
    style Utils fill:#f5e1ff
```

## 8. 배치 주문 처리

```mermaid
sequenceDiagram
    participant User as 👤 사용자
    participant Agent as OrderAgent
    participant Router as CategoryRouter
    participant LLM as LLMService
    participant Service as OrderService
    
    User->>Agent: 배치 주문 요청<br/>[주문1, 주문2, 주문3]
    
    activate Agent
    
    par 병렬 처리
        Agent->>Router: 주문1 분류
        Router->>LLM: LLM 호출
        LLM-->>Router: 카테고리: 음료
        Router-->>Agent: 음료
        Agent->>Service: 주문1 생성
    and
        Agent->>Router: 주문2 분류
        Router->>LLM: LLM 호출
        LLM-->>Router: 카테고리: 디저트
        Router-->>Agent: 디저트
        Agent->>Service: 주문2 생성
    and
        Agent->>Router: 주문3 분류
        Router->>LLM: LLM 호출
        LLM-->>Router: 카테고리: 식사
        Router-->>Agent: 식사
        Agent->>Service: 주문3 생성
    end
    
    Service-->>Agent: 주문 결과 리스트
    deactivate Agent
    
    Agent-->>User: 통합 결과<br/>[결과1, 결과2, 결과3]
```

## 범례

- 🟦 **파란색**: 사용자 인터페이스 / 입력
- 🟨 **노란색**: 에이전트 레이어 / 처리 과정
- 🟪 **보라색**: 라우터 레이어 / 분류
- 🟩 **초록색**: 서비스 레이어 / 비즈니스 로직
- 🟥 **빨간색**: 외부 서비스 / 에러
- 🟫 **회색**: 유틸리티 / 지원 기능
