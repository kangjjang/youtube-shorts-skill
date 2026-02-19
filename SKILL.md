---
name: youtube-shorts
description: "인포그랩 AI/DevOps 유튜브 숏츠 자동 생성. HN/Reddit 트렌드 수집 → Gemini 스크립트 → 이미지 → Veo 영상 → TTS 나레이션 → Remotion 합성 → YouTube 업로드"
version: "2.0.0"
metadata:
  openclaw:
    requires:
      tools:
        - bash
        - exec
      env:
        - GEMINI_API_KEY
---

# YouTube Shorts 자동화 스킬 — 인포그랩

## 사용법

```
숏츠 만들어줘
숏츠 주제 뽑아줘
[주제명] 숏츠 만들어줘      (예: "Kubernetes Gateway API 숏츠 만들어줘")
트렌드만 수집해줘
```

---

## 사전 준비

### 1. 의존성 설치
```bash
cd <SKILL_DIR>
pip install -r requirements.txt
```

### 2. 환경변수
`.env.example`을 `.env`로 복사 후 API 키 입력:
```
GEMINI_API_KEY=AIza...
```
Gemini API 키 하나로 텍스트(스크립트/SEO) + 이미지 + 영상 + TTS 전체 처리.

### 3. Node.js + Remotion
Remotion으로 Veo 클립 + 한글 자막 + 나레이션을 합성:
```bash
brew install node
cd <SKILL_DIR>/remotion && npm install
```

### 4. YouTube 업로드 (선택)
- Google Cloud Console → OAuth 2.0 클라이언트 ID (데스크톱 앱) 생성
- YouTube Data API v3 활성화
- JSON 다운로드 → `credentials/client_secret.json`에 저장

### 5. FFmpeg (폴백)
Remotion 실패 시 폴백으로 사용:
```bash
brew install ffmpeg
```

---

## 실행 흐름 (Pipeline)

```
트렌드 → 주제 → 스크립트 → 이미지 → Veo 클립 ─┐
                                                 ├→ Remotion 합성 → SEO → 업로드
                          스크립트 → Gemini TTS ──┘
```

### STEP 1 — 트렌드 수집
Hacker News API + Reddit (r/devops, r/MachineLearning, r/kubernetes, r/LocalLLaMA, r/programming, r/aws) 에서 AI/DevOps 관련 포스트 수집 후 숏츠 적합도 점수로 정렬.

```bash
python main.py trends
```

### STEP 2 — 주제 선정
Gemini 2.5 Flash로 트렌드 분석, 상위 3개 후보 추출. 사용자에게 선택 요청 (--auto 시 자동 선택).

### STEP 3 — 스크립트 작성
Gemini 2.5 Flash로 60초 한국어 숏츠 스크립트 생성. 훅(5초) + 핵심 설명(40초) + CTA(15초) 구조. 장면별 이미지/영상 프롬프트 포함 JSON 출력.

```bash
python main.py generate --topic "Kubernetes Gateway API"
```

### STEP 4 — 이미지 생성
각 장면별 키프레임을 Gemini 2.5 Flash Image로 생성. 9:16 세로, 다크 테크 스타일.

### STEP 5 — 영상 생성
키프레임 이미지를 첫 프레임으로 Veo 3.1으로 8초 클립 생성. Veo 클립은 배경 영상으로 사용.

### STEP 6 — TTS 나레이션
Gemini `gemini-2.5-flash-preview-tts`로 스크립트 나레이션(hook + main + cta)을 한국어 음성으로 생성. 별도 API 키 불필요 (기존 GEMINI_API_KEY 사용).

### STEP 7 — Remotion 합성
Veo 클립(배경) + 한글 자막(Noto Sans KR) + 나레이션 오디오를 Remotion으로 합성. 1080×1920, 30fps. Remotion 실패 시 FFmpeg로 폴백.

### STEP 8 — SEO 패키지
Gemini로 제목(A/B/C), 설명, 태그 20개, 해시태그 생성.

### STEP 9 — 업로드
YouTube Data API v3로 업로드 (기본 비공개).

```bash
python main.py --auto --upload          # 비공개 업로드
python main.py --auto --upload --public # 공개 업로드
```

---

## CLI 명령어

| 명령어 | 설명 |
|--------|------|
| `python main.py` | 전체 파이프라인 (대화형 주제 선택) |
| `python main.py --auto --upload` | 자동 선택 + 비공개 업로드 |
| `python main.py --upload --public` | 공개 업로드 |
| `python main.py --quality full` | 고품질 Veo ($0.30/s) |
| `python main.py trends` | 트렌드 수집만 |
| `python main.py generate --topic "K8s"` | 특정 주제로 생성 |
| `python main.py upload --dir outputs/...` | 기존 영상 업로드 |

---

## 파일 구조

```
youtube-shorts/
├── SKILL.md                 ← 이 파일
├── requirements.txt         ← Python 의존성
├── .env.example             ← 환경변수 템플릿
├── config.py                ← 설정 관리 (.env 로딩, 검증)
├── main.py                  ← CLI 진입점 (오케스트레이터)
├── modules/
│   ├── __init__.py
│   ├── trends.py            ← HN + Reddit 트렌드 수집
│   ├── topic_selector.py    ← Gemini — 주제 선정
│   ├── script_writer.py     ← Gemini — 60초 한국어 스크립트
│   ├── tts_generator.py     ← Gemini TTS — 한국어 나레이션
│   ├── compositor.py        ← Remotion — 영상 합성
│   ├── seo_packager.py      ← Gemini — SEO 메타데이터
│   ├── image_generator.py   ← Gemini 2.5 Flash Image — 키프레임
│   ├── video_generator.py   ← Veo 3.1 — 8초 클립 + FFmpeg 폴백
│   └── youtube_uploader.py  ← YouTube Data API v3 — OAuth2 업로드
├── remotion/                ← Remotion 합성 프로젝트
│   ├── package.json         ← Node.js 의존성
│   ├── tsconfig.json        ← TypeScript 설정
│   └── src/
│       ├── Root.tsx          ← Remotion 진입점
│       └── ShortsVideo.tsx   ← 메인 합성 컴포넌트
├── prompts/
│   ├── topic_research.md    ← 주제 큐레이션 프롬프트
│   ├── script_writer.md     ← 스크립트 작성 프롬프트
│   └── seo_packager.md      ← SEO 패키징 프롬프트
├── credentials/             ← OAuth2 인증 (gitignore)
└── outputs/                 ← 생성 결과물
    └── YYYY-MM-DD-[slug]/
        ├── trends.json
        ├── script.json
        ├── seo.json
        ├── narration.wav    ← TTS 나레이션
        ├── composition-props.json ← Remotion 입력
        ├── frames/          ← 키프레임 이미지
        ├── clips/           ← Veo 영상 클립
        └── final_shorts.mp4
```

---

## 비용 참고

| 항목 | 단가 | 숏츠 1편 기준 |
|------|------|---------------|
| Gemini 2.5 Flash (텍스트) | ~$0.001 | ~$0.003 (3회 호출) |
| Gemini 2.5 Flash Image | ~$0.001/장 | ~$0.003 (3장) |
| Veo 3.1 Fast | $0.10/초 | ~$2.40 (3클립 × 8초) |
| Veo 3.1 Full | $0.30/초 | ~$7.20 (3클립 × 8초) |
| Gemini TTS | ~$0.001 | ~$0.001 (1회 호출) |
| **합계 (Fast)** | | **~$2.40** |
| **합계 (Full)** | | **~$7.20** |

영상 생성 전 비용 체크포인트에서 예상 비용을 표시하고 확인을 받습니다 (--auto 시 생략).

---

## 에러 처리

- Reddit API 실패 → Hacker News만으로 폴백
- 개별 이미지/클립 생성 실패 → 건너뛰고 나머지 계속 진행
- TTS 생성 실패 → 나레이션 없이 계속 진행
- Remotion 렌더링 실패 → FFmpeg 단순 결합으로 폴백
- YouTube 업로드 실패 → 지수 백오프로 최대 5회 재시도

---

## 사용 모델

- **Gemini 2.5 Flash** — 텍스트 (주제 선정, 스크립트, SEO)
- **Gemini 2.5 Flash Image** — 키프레임 이미지 생성
- **Gemini 2.5 Flash Preview TTS** — 한국어 나레이션 음성 합성
- **Veo 3.1 Fast/Full** — 8초 영상 클립 생성
