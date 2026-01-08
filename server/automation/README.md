# 🤖 마장동딸 완전 자동화 시스템

## 📋 개요

네이버 플레이스 검색 순위를 자동으로 올리는 **완전 자동화 + 3단계 안전장치** 시스템입니다.

---

## 🎯 핵심 기능

### 1️⃣ 사진 창고 시스템 (`photo_manager.py`)
- 📸 **랜덤 사진 선택**: 폴더에서 무작위로 사진 선택
- 🔄 **중복 방지**: 모든 사진을 사용하면 자동으로 리셋
- 📊 **사용 이력 추적**: JSON 파일로 기록 관리

**사용법:**
```bash
# 1. 사진 추가
mkdir -p server/photo_storage
cp /path/to/photos/*.jpg server/photo_storage/

# 2. 테스트
python server/automation/photo_manager.py
```

---

### 2️⃣ 날씨/요일 컨텍스트 (`context_provider.py`)
- 📅 **요일별 메시지**: 월요일 블루 → 불금까지 자동 변경
- 🌤️ **시간대별 메시지**: 아침/점심/저녁 자동 감지
- 🎯 **AI 프롬프트 자동 삽입**: 상황에 맞는 글 생성

**예시:**
```
금요일 저녁 → "불금! 오늘 저녁 계획은 마장동딸"
비 오는 월요일 → "월요일 블루를 따뜻한 고기로 날려버리세요"
```

---

### 3️⃣ 스마트 콘텐츠 생성기 (`smart_content_generator.py`)

#### 🔒 **안전장치 1: 금지어 필터**
다음 단어들을 **절대 사용하지 않음**:
```python
할인, 무료, 이벤트, 쿠폰, 증정, 프로모션, 특가, 세일, %, 원, 만원
```

#### 🔄 **안전장치 2: 자동 재생성**
- AI가 금지어를 사용하면 **자동으로 3번까지 재생성**
- 안전한 콘텐츠만 통과

#### ✅ **생성되는 콘텐츠**
- 음식의 맛, 신선도, 품질 묘사
- 가게 분위기, 청결함 강조
- 날씨/요일에 맞는 자연스러운 표현

**테스트:**
```bash
python server/automation/smart_content_generator.py
```

---

### 4️⃣ 자동 게시 시스템 (`auto_poster.py`)

#### 📤 **자동 업로드 플로우**
1. 사진 창고에서 랜덤 선택
2. 날씨/요일 컨텍스트 생성
3. AI로 안전한 설명 생성 (금지어 체크)
4. 네이버 플레이스 '새 소식' 자동 등록
5. 로그 기록

#### 🧪 **테스트 모드 (안전)**
```bash
# 실제 업로드 없이 테스트만
python server/automation/auto_poster.py --test
```

#### 🚀 **실제 게시**
```bash
# 네이버 플레이스에 실제로 업로드
python server/automation/auto_poster.py --place-id YOUR_PLACE_ID --post
```

---

## 📅 크론잡 설정 (자동 실행)

### 매일 오전 10시, 오후 6시 자동 게시

```bash
# 크론탭 편집
crontab -e

# 다음 라인 추가
0 10 * * * cd /home/seolmiseon/majangdong-daughter-ai && source venv/bin/activate && python server/automation/auto_poster.py --place-id YOUR_PLACE_ID --post >> /tmp/auto_post.log 2>&1

0 18 * * * cd /home/seolmiseon/majangdong-daughter-ai && source venv/bin/activate && python server/automation/auto_poster.py --place-id YOUR_PLACE_ID --post >> /tmp/auto_post.log 2>&1
```

**주의:**
- `YOUR_PLACE_ID`를 실제 네이버 플레이스 ID로 변경하세요
- 경로(`/home/seolmiseon/...`)를 실제 프로젝트 경로로 수정하세요

---

## 🔧 초기 설정 가이드

### 1단계: 사진 준비
```bash
# 1. 사진 폴더 생성
mkdir -p server/photo_storage

# 2. 고기 사진 20~30장 복사
cp ~/고기사진/*.jpg server/photo_storage/
```

**권장 사진:**
- 신선한 고기 (손질 전후)
- 고기 굽는 모습
- 완성된 요리
- 가게 내부/외부
- 손님들 식사 모습 (얼굴 모자이크)

---

### 2단계: 네이버 플레이스 ID 확인

네이버 플레이스 관리자 페이지에서 가게 ID를 확인하세요.

**예시:**
```
URL: https://place.naver.com/place/1234567890
→ Place ID: 1234567890
```

---

### 3단계: 테스트 실행

```bash
# 1. 가상환경 활성화
source venv/bin/activate

# 2. 시스템 전체 테스트
python server/automation/auto_poster.py --test

# 3. Dry run (실제 업로드 없이 테스트)
python server/automation/auto_poster.py --place-id YOUR_PLACE_ID

# 4. 실제 게시 (한 번만)
python server/automation/auto_poster.py --place-id YOUR_PLACE_ID --post
```

---

### 4단계: 크론잡 등록

위의 "크론잡 설정" 섹션 참조

---

## 📊 효과

### 검색 순위 상승 요인

1. **정기적인 새 소식 발행** (네이버 알고리즘 선호)
   - 주 2~3회 자동 발행
   - 신선한 콘텐츠로 인식

2. **키워드 최적화**
   - '마장동딸', '한우', '신선', '마장동' 자동 포함
   - 자연스러운 문맥 삽입

3. **고품질 콘텐츠**
   - AI 생성 설명 + 실제 사진
   - 스팸 필터 회피 (금지어 없음)

4. **상황별 맞춤 글**
   - 날씨/요일 반영
   - 사람이 쓴 것처럼 자연스러움

---

## 🛡️ 안전장치 요약

| 안전장치 | 설명 | 효과 |
|---------|------|------|
| 금지어 필터 | 할인/이벤트 등 15개 단어 차단 | 네이버 정책 위반 방지 |
| 자동 재생성 | 금지어 포함 시 3번 재시도 | 안전한 콘텐츠만 게시 |
| 컨텍스트 삽입 | 날씨/요일 자동 반영 | 스팸으로 보이지 않음 |
| 중복 방지 | 사진 사용 이력 추적 | 매번 다른 사진 |
| Dry Run 모드 | 테스트 모드 제공 | 실수 방지 |

---

## 📝 로그 확인

```bash
# 자동 게시 로그
tail -f server/automation/auto_post_log.txt

# 크론잡 로그
tail -f /tmp/auto_post.log
```

---

## 🚨 문제 해결

### 사진이 없다고 나올 때
```bash
ls -la server/photo_storage/
# → 사진 파일이 없으면 추가
```

### Gemini API 오류
```bash
# .env 파일 확인
cat .env | grep GOOGLE_AI_API_KEY
```

### 네이버 플레이스 업로드 실패
- 네이버 플레이스 API 키 확인
- Place ID 확인
- 네트워크 연결 확인

---

## 💡 추가 개선 아이디어

1. **실제 날씨 API 연동** (현재는 시간대만 사용)
2. **리뷰 답글 자동화** 연동
3. **A/B 테스팅**: 여러 프롬프트 비교
4. **성과 분석**: 조회수/클릭수 추적

---

## 📞 지원

문제가 발생하면 로그를 확인하고, 이슈를 등록하세요.

**Happy Auto-Posting! 🚀**
