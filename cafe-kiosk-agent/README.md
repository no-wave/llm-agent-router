# 🤖 카페 키오스크 에이전트 시스템

> LLM 기반 비동기 Router Agent 패턴을 활용한 지능형 카페 주문 시스템

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 📖 목차

- [프로젝트 소개](#-프로젝트-소개)
- [주요 기능](#-주요-기능)
- [프로젝트 구조](#-프로젝트-구조)
- [설치 방법](#-설치-방법)
- [사용 방법](#-사용-방법)
- [아키텍처](#-아키텍처)
- [문제 해결](#-문제-해결)
- [향후 계획](#-향후-계획)

## 🎯 프로젝트 소개

고객의 자연어 주문을 이해하고 적절한 카테고리로 분류하여 최적의 모델로 처리하는 멀티 라우터 에이전트 아키텍처를 구현한 카페 주문 시스템입니다.

### 핵심 특징

- **자연어 주문 처리**: "아메리카노 2잔이랑 케이크 주세요" 같은 자연스러운 표현 지원
- **지능형 라우팅**: 주문 복잡도와 카테고리에 따른 최적 모델 자동 선택
- **비동기 처리**: 다중 주문 동시 처리로 빠른 응답 시간 보장
- **로컬/클라우드 하이브리드**: 상황에 따른 유연한 모델 선택

## ✨ 주요 기능

### 1️⃣ 멀티 라우터 아키텍처

| 라우터 | 역할 | 분류 기준 |
|--------|------|-----------|
| **카테고리 라우터** | 음료/디저트/식사 분류 | 메뉴 데이터베이스 매칭 |
| **모델 라우터** | 최적 LLM 선택 | 질문 복잡도 분석 |
| **서빙 라우터** | 클라우드/로컬 선택 | 민감도 및 시스템 상태 |

### 2️⃣ 지능형 주문 처리

```python
# 다양한 자연어 표현 지원
"아메리카노 두 잔 주세요"           # ✅
"ice 아메리카노 톨 사이즈로"       # ✅
"커피 2개랑 케이크 하나"           # ✅
```

### 3️⃣ 메뉴 추천 시스템

- **시간대별 추천**: 아침 메뉴, 브런치, 디저트
- **날씨별 추천**: 따뜻한/시원한 음료
- **조합 추천**: 음료 + 디저트 세트

### 4️⃣ 주문 커스터마이징

- 사이즈: Tall, Grande, Venti
- 온도: Hot, Ice
- 추가 옵션: 샷, 시럽, 휘핑 등

## 📁 프로젝트 구조

```
cafe-kiosk-agent/
├── 📄 README.md
├── 📄 ARCHITECTURE.md
├── 📄 requirements.txt
├── 📄 .env.example
├── 📂 config/
│   ├── settings.py              # 전역 설정
│   └── menu_database.py         # 메뉴 데이터베이스
├── 📂 src/
│   ├── 📂 routers/
│   │   ├── category_router.py   # 카테고리 분류
│   │   ├── model_router.py      # 모델 선택
│   │   └── serving_router.py    # 서빙 전략
│   ├── 📂 agents/
│   │   ├── order_agent.py       # 주문 처리
│   │   └── recommendation_agent.py  # 추천
│   ├── 📂 services/
│   │   ├── llm_service.py       # LLM 통합
│   │   └── order_service.py     # 주문 관리
│   └── 📂 utils/
│       ├── logger.py            # 로깅
│       └── validators.py        # 검증
└── 📄 main.py                    # 실행 파일
```

## 🚀 설치 방법

### 1. 필수 요구사항

- Python 3.11 이상
- OpenAI API Key
- (선택) Ollama 로컬 모델

### 2. 설치 단계

```bash
# 1. 저장소 클론
git clone https://github.com/yourusername/cafe-kiosk-agent.git
cd cafe-kiosk-agent

# 2. 가상환경 생성 및 활성화
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

# 3. 패키지 설치
pip install -r requirements.txt

# 4. 환경변수 설정
cp .env.example .env
# .env 파일을 열어 API 키 입력
```

### 3. 환경변수 설정

`.env` 파일에 다음 내용을 입력하세요:

```env
# 필수
OPENAI_API_KEY=sk-proj-your_api_key_here

# 선택 (로컬 모델 사용 시)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=exaone3.5:7.8b
ENABLE_LOCAL_MODEL=false

# 시스템 설정
LOG_LEVEL=INFO
DEFAULT_LANGUAGE=ko
```

## 💻 사용 방법

### 기본 실행

```bash
python main.py
```

### 코드로 사용하기

```python
from src.agents.order_agent import OrderAgent
import asyncio

async def main():
    agent = OrderAgent()
    
    # 단일 주문 처리
    result = await agent.process_order("아메리카노 2잔이랑 케이크 1개 주세요")
    print(result)
    
    # 배치 주문 처리
    orders = [
        "카페라떼 3잔",
        "와플이랑 아이스티",
        "파스타 2인분"
    ]
    results = await agent.process_batch_orders(orders)

asyncio.run(main())
```

### 테스트 실행

```bash
# 전체 테스트
pytest tests/

# 특정 테스트
pytest tests/test_order_flow.py -v

# 커버리지 확인
pytest --cov=src tests/
```

## 🏗 아키텍처

### 1. 카테고리 라우터

주문 내용을 분석하여 카테고리로 분류합니다.

```
사용자 입력 → LLM 분석 → 메뉴 DB 매칭 → 카테고리 결정
                                          ↓
                              [음료 | 디저트 | 식사]
```

### 2. 모델 라우터

질문 복잡도에 따라 최적 모델을 선택합니다.

| 복잡도 | 모델 | 사용 케이스 |
|--------|------|-------------|
| Low | gpt-5-nano | 간단한 주문 |
| Medium | gpt-5-mini | 일반 주문 + 추천 |
| High | gpt-5 | 복잡한 커스터마이징 |

### 3. 서빙 라우터

시스템 상태와 민감도에 따라 모델을 선택합니다.

```
[일반 주문] → 클라우드 모델 (높은 정확도)
[개인정보] → 로컬 모델 (보안)
[네트워크 불안정] → 로컬 모델 (안정성)
```

### 성능 지표

- **평균 응답 시간**: ~2초
- **배치 처리** (10개 주문): ~3-5초
- **정확도**: 95%+

## 🔧 문제 해결

### Windows UTF-8 인코딩 오류

**오류 메시지:**
```
'utf-8' codec can't decode bytes in position 2-3
```

**해결 방법:**

#### 방법 1: 배치 파일 사용 (권장)
```bash
run.bat
```

#### 방법 2: 환경변수 설정
```powershell
$env:PYTHONIOENCODING="utf-8"
python main.py
```

#### 방법 3: 코드 페이지 변경
```cmd
chcp 65001
python main.py
```

### API 키 오류

**오류 메시지:**
```
⚠️ 경고: OpenAI API 키가 설정되지 않았습니다!
```

**해결 방법:**
1. `.env` 파일 존재 확인
2. API 키 형식 확인 (따옴표나 공백 없이)
3. 환경변수 재로드

### ModuleNotFoundError

**해결 방법:**
```bash
# 가상환경 활성화 확인
pip install -r requirements.txt --force-reinstall
```

### 더 많은 문제 해결

자세한 문제 해결 가이드는 [Troubleshooting Guide](docs/TROUBLESHOOTING.md)를 참조하세요.

## 🔍 로컬 모델 설정 (선택)

Ollama를 사용하여 로컬에서 LLM을 실행할 수 있습니다.

```bash
# 1. Ollama 설치
# https://ollama.ai에서 다운로드

# 2. 모델 다운로드
ollama pull exaone3.5:7.8b

# 3. 서버 실행
ollama serve

# 4. .env에서 활성화
ENABLE_LOCAL_MODEL=true
```

## 📋 향후 계획

- [ ] 다국어 지원 (영어, 일본어)
- [ ] 음성 주문 인터페이스
- [ ] 결제 시스템 통합
- [ ] 고객 선호도 학습 시스템
- [ ] 재고 관리 시스템
- [ ] 모바일 앱 연동
- [ ] 멤버십 및 포인트 시스템
- [ ] A/B 테스팅 프레임워크

## 🤝 기여 방법

프로젝트 기여를 환영합니다!

1. Fork the repository
2. Feature 브랜치 생성 (`git checkout -b feature/AmazingFeature`)
3. 변경사항 커밋 (`git commit -m 'Add some AmazingFeature'`)
4. 브랜치에 Push (`git push origin feature/AmazingFeature`)
5. Pull Request 생성

## 📄 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 📞 문의 및 지원

- **Issues**: [GitHub Issues](https://github.com/yourusername/cafe-kiosk-agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/cafe-kiosk-agent/discussions)
- **Email**: your.email@example.com

## 📚 참고 자료

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
- [Ollama Documentation](https://github.com/ollama/ollama)
- [Python Best Practices](https://docs.python-guide.org/)

---

<div align="center">

**Made with ❤️ for Better Cafe Experience**

⭐ 이 프로젝트가 도움이 되었다면 Star를 눌러주세요!

</div>
