# 🤖 마장동딸 완전 자동화 시스템

## 📋 개요

네이버 플레이스 검색 순위를 자동으로 올리는 **완전 자동화 + 3단계 안전장치** 시스템입니다.

**핵심 특징:**
- ✅ S3 + CloudFront CDN 기반 이미지 저장소
- ✅ boto3 비동기 지원 (FastAPI 호환)
- ✅ Gemini 2.0 Flash AI 콘텐츠 생성
- ✅ 자동 금지어 필터링 및 재생성
- ✅ 크론잡 기반 완전 자동화

---

## 🎯 핵심 기능

### 1️⃣ 사진 창고 시스템 (`photo_manager.py`) - S3 기반

#### 주요 기능
- 📸 **랜덤 사진 선택**: S3에서 무작위로 사진 선택
- 🔄 **중복 방지**: 모든 사진을 사용하면 자동으로 리셋
- 📊 **사용 이력 추적**: JSON 파일로 기록 관리
- ☁️ **CloudFront CDN**: 빠른 이미지 로딩 (SEO 최적화)
- ⚡ **비동기 지원**: FastAPI에서 안전하게 사용 가능

#### 기술 스택
- **저장소**: AWS S3 + CloudFront CDN
- **다운로드**: boto3 (동기/비동기 모두 지원)
- **이벤트 루프**: run_in_executor로 블로킹 방지

#### 사용법
```bash
# 1. 사진을 S3에 업로드
python scripts/upload_to_s3.py /path/to/photos/

# 2. 테스트
python server/automation/photo_manager.py

# 3. 통계 확인
python -c "from server.automation.photo_manager import get_photo_manager; pm = get_photo_manager(); print(pm.get_stats())"
```

#### API 사용법
```python
# 동기 버전 (크론잡용)
photo_manager = get_photo_manager()
result = photo_manager.get_random_photo()  # (filename, bytes)

# 비동기 버전 (FastAPI용)
result = await photo_manager.get_random_photo_async()  # (filename, bytes)
```

---

### 2️⃣ 날씨/요일 컨텍스트 (`context_provider.py`)

#### 주요 기능
- 📅 **요일별 메시지**: 월요일 블루 → 불금까지 자동 변경
- 🌤️ **시간대별 메시지**: 아침/점심/저녁 자동 감지
- 🎯 **AI 프롬프트 자동 삽입**: 상황에 맞는 글 생성

#### 예시
```
금요일 저녁 → "불금! 오늘 저녁 계획은 마장동딸"
비 오는 월요일 → "월요일 블루를 따뜻한 고기로 날려버리세요"
```

---

### 3️⃣ 스마트 콘텐츠 생성기 (`smart_content_generator.py`)

#### 🔒 안전장치 1: 금지어 필터
다음 단어들을 **절대 사용하지 않음**:
```python
할인, 무료, 이벤트, 쿠폰, 증정, 프로모션, 특가, 세일, %, 원, 만원
```

#### 🔄 안전장치 2: 자동 재생성
- AI가 금지어를 사용하면 **자동으로 3번까지 재생성**
- 안전한 콘텐츠만 통과

#### ✅ 생성되는 콘텐츠
- 음식의 맛, 신선도, 품질 묘사
- 가게 분위기, 청결함 강조
- 날씨/요일에 맞는 자연스러운 표현
- 키워드 최적화: '마장동 소고기', '마장동 한우' 자동 포함

#### API 사용법
```python
# 동기 버전 (크론잡용)
generator = get_content_generator()
content = generator.generate_post_content()

# 비동기 버전 (FastAPI용)
content = await generator.generate_post_content_async()
```

**테스트:**
```bash
python server/automation/smart_content_generator.py
```

---

### 4️⃣ 자동 게시 시스템 (`auto_poster.py`)

#### 📤 자동 업로드 플로우
1. 사진 창고에서 랜덤 선택 (S3 boto3)
2. 날씨/요일 컨텍스트 생성
3. AI로 안전한 설명 생성 (금지어 체크)
4. 네이버 플레이스 '새 소식' 자동 등록
5. 로그 기록

#### 🧪 테스트 모드 (안전)
```bash
# 실제 업로드 없이 테스트만
python server/automation/auto_poster.py --test
```

#### 🚀 실제 게시
```bash
# 네이버 플레이스에 실제로 업로드
python server/automation/auto_poster.py --place-id YOUR_PLACE_ID --post

# 할인/이벤트 언급 허용 모드
python server/automation/auto_poster.py --place-id YOUR_PLACE_ID --post --allow-promotions
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

### 1단계: AWS S3 설정

#### 환경 변수 설정 (`.env`)
```env
# AWS S3 설정
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_S3_BUCKET=majangdong-photos
AWS_REGION=ap-northeast-2
CLOUDFRONT_URL=https://your-cloudfront-url.cloudfront.net  # 선택사항
```

#### S3 버킷 설정
1. AWS 콘솔에서 S3 버킷 생성
2. IAM 사용자 생성 및 권한 부여 (S3 읽기/쓰기)
3. CloudFront 배포 설정 (선택사항, SEO 최적화)

### 2단계: 사진 준비 및 S3 업로드

```bash
# 1. 핸드폰에서 사진을 로컬로 전송 (USB/클라우드)

# 2. S3에 업로드
python scripts/upload_to_s3.py /path/to/photos/

# 또는 개별 파일
python scripts/upload_to_s3.py photo1.jpg photo2.jpg
```

**권장 사진:**
- 신선한 고기 (손질 전후)
- 고기 굽는 모습
- 완성된 요리
- 가게 내부/외부
- 손님들 식사 모습 (얼굴 모자이크)

### 3단계: Gemini API 설정 (유료화)

#### 환경 변수 설정 (`.env`)
```env
# 유료 API 키 사용 권장 (Google Cloud Console에서 발급)
GOOGLE_AI_API_KEY=your_gemini_api_key

# Gemini Vision 모델 선택 (선택사항)
# 기본값: models/gemini-2.0-flash
# 유료 모델 옵션:
#   - models/gemini-1.5-pro (고품질, 유료)
#   - models/gemini-1.5-flash (빠른 응답, 유료)
#   - models/gemini-2.0-flash-exp (실험적, 최신 기능)
GEMINI_MODEL=models/gemini-2.0-flash
```

#### 모델 설정 및 비용 비교

| 모델 | 비용 효율 | 정확도 | 추천도 | 월 예상 비용 (60회) |
|------|----------|--------|--------|-------------------|
| **gemini-2.0-flash** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ **최고 추천** | **1-2원** (무료 티어 15회 포함) |
| gemini-1.5-flash | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⚠️ 비추천 | 2-3원 |
| gemini-1.5-pro | ⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ 비추천 | 5-10원 |

**💰 비용 절감 추천: `models/gemini-2.0-flash` (기본값)**
- ✅ 무료 티어 지원: 월 15회 무료
- ✅ 유료 사용 시: 입력 $0.075/1M 토큰, 출력 $0.30/1M 토큰
- ✅ 정확도: 이미지 분석 및 콘텐츠 생성에 충분
- ✅ 속도: 빠름 (Flash 시리즈)
- ✅ 월 60회 사용 시 예상 비용: 약 1-2원

**💡 비용 절감 팁:**
1. **무료 티어 활용**: 월 15회는 무료이므로, 하루 1회로 줄이면 거의 무료
2. **프롬프트 최적화**: 불필요한 설명 제거로 토큰 수 절감
3. **재시도 최소화**: 금지어 체크를 정확하게 해서 재시도 줄이기
4. **사진 다양성**: 같은 사진 재사용 시 캐싱 고려 (향후 개선)

#### 🔄 무료 → 유료 전환 방법 (중요!)

**핵심 정리:**
- ✅ **모델 이름은 그대로**: `models/gemini-2.0-flash` 유지 (변경 불필요!)
- ✅ **무료 티어**: 월 15회 무료 (자동 적용)
- ✅ **유료 전환**: 무료 티어 15회를 다 쓰면 **자동으로 유료로 전환됨**
- ✅ **결제 계정 연결**: Google Cloud Console에서 결제 계정만 연결하면 됨

**단계별 가이드:**

1. **Google Cloud Console 접속**
   - [Google Cloud Console](https://console.cloud.google.com/) 접속
   - 프로젝트 생성 또는 선택

2. **API 활성화**
   - "API 및 서비스" > "라이브러리"에서 "Generative Language API" 활성화

3. **결제 계정 연결 (유료화 핵심!)**
   
   **왜 프로젝트 선택이 필요한가?**
   - Google Cloud는 **프로젝트별로 결제 계정을 연결**하는 구조입니다
   - 각 프로젝트마다 다른 결제 계정을 사용할 수 있습니다
   - 따라서 결제 계정을 연결하려면 **먼저 프로젝트를 선택**해야 합니다
   
   **단계별 진행:**
   
   a) **프로젝트 선택**
   - 상단의 프로젝트 선택 드롭다운에서 프로젝트 선택
   - 프로젝트가 없으면 "새 프로젝트" 생성
   
   b) **결제 계정 생성/연결**
   - 왼쪽 메뉴에서 "결제" 클릭
   - "결제 계정 연결" 또는 "결제 계정 만들기" 클릭
   - 신용카드 정보 입력 및 등록
   
   c) **프로젝트에 결제 계정 연결**
   - 결제 계정 생성 후, 해당 프로젝트에 결제 계정 연결
   - ⚠️ **주의**: 결제 계정을 연결하면 무료 티어 15회를 다 쓰면 자동으로 유료 과금됨
   
   **💡 팁:**
   - 프로젝트 이름은 자유롭게 설정 가능 (예: "majangdong-ai")
   - 결제 계정은 한 번만 만들면 여러 프로젝트에 재사용 가능

4. **API 키 생성**
   - "API 및 서비스" > "사용자 인증 정보"에서 API 키 생성
   - 생성된 API 키를 `.env` 파일의 `GOOGLE_AI_API_KEY`에 설정

5. **모델 설정 (변경 불필요!)**
   ```env
   # 모델 이름은 그대로 유지 (변경 안 해도 됨!)
   GEMINI_MODEL=models/gemini-2.0-flash
   ```

**💡 작동 방식:**
- **무료 티어**: 월 15회까지 무료 (결제 계정 연결 안 해도 됨)
- **유료 전환**: 무료 티어 15회를 다 쓰면 → 자동으로 유료 과금 시작
- **과금 방식**: 사용한 만큼만 과금 (입력 $0.075/1M 토큰, 출력 $0.30/1M 토큰)
- **예상 비용**: 월 60회 사용 시 약 1-2원 (무료 15회 포함)

**⚠️ 주의사항:**
- 결제 계정을 연결하지 않으면: 무료 티어 15회만 사용 가능, 그 이후는 API 호출 실패
- 결제 계정을 연결하면: 무료 티어 15회 사용 후 자동으로 유료 과금 시작
- 모델 이름 변경 불필요: `models/gemini-2.0-flash` 그대로 사용

### 4단계: 네이버 플레이스 ID 확인

네이버 플레이스 관리자 페이지에서 가게 ID를 확인하세요.

**예시:**
```
URL: https://place.naver.com/place/1234567890
→ Place ID: 1234567890
```

### 5단계: 테스트 실행

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

### 6단계: 크론잡 등록

위의 "크론잡 설정" 섹션 참조

---

## 📊 효과 및 성과 측정

### 검색 순위 상승 요인

1. **정기적인 새 소식 발행** (네이버 알고리즘 선호)
   - 주 2~3회 자동 발행
   - 신선한 콘텐츠로 인식

2. **키워드 최적화**
   - '마장동 소고기' (현재 22위, 상위권 진입 목표)
   - '마장동 한우' (현재 34위)
   - '마장동딸', '신선' 자동 포함
   - 자연스러운 문맥 삽입

3. **고품질 콘텐츠**
   - AI 생성 설명 + 실제 사진
   - 스팸 필터 회피 (금지어 없음)

4. **상황별 맞춤 글**
   - 날씨/요일 반영
   - 사람이 쓴 것처럼 자연스러움

### 성과 추적 방법

```bash
# 순위 히스토리 확인
cat data/rank_history.csv

# 자동 게시 로그 확인
tail -f server/automation/auto_post_log.txt

# 사진 사용 통계
python -c "from server.automation.photo_manager import get_photo_manager; print(get_photo_manager().get_stats())"
```

---

## 🛡️ 안전장치 요약

| 안전장치 | 설명 | 효과 |
|---------|------|------|
| 금지어 필터 | 할인/이벤트 등 15개 단어 차단 | 네이버 정책 위반 방지 |
| 자동 재생성 | 금지어 포함 시 3번 재시도 | 안전한 콘텐츠만 게시 |
| 컨텍스트 삽입 | 날씨/요일 자동 반영 | 스팸으로 보이지 않음 |
| 중복 방지 | 사진 사용 이력 추적 | 매번 다른 사진 |
| Dry Run 모드 | 테스트 모드 제공 | 실수 방지 |
| 비동기 지원 | FastAPI 이벤트 루프 블로킹 방지 | 안정적인 서비스 운영 |

---

## 🔄 비동기 지원 (FastAPI 호환)

### 문제점
- FastAPI는 비동기(async/await) 사용
- boto3는 동기 라이브러리
- 동기 코드가 이벤트 루프를 블로킹할 수 있음

### 해결 방법
- `run_in_executor`로 동기 코드를 스레드에서 실행
- 이벤트 루프 블로킹 방지

### 사용 예시
```python
# 크론잡 (동기)
photo_manager = get_photo_manager()
result = photo_manager.get_random_photo()

# FastAPI (비동기)
result = await photo_manager.get_random_photo_async()
```

---

## 📝 로그 확인

```bash
# 자동 게시 로그
tail -f server/automation/auto_post_log.txt

# 크론잡 로그
tail -f /tmp/auto_post.log

# 사진 사용 이력
cat server/automation/photo_usage_history.json
```

---

## 🚨 문제 해결

### 사진이 없다고 나올 때
```bash
# S3에 사진이 업로드되어 있는지 확인
python server/automation/photo_manager.py

# 사진이 없으면 업로드
python scripts/upload_to_s3.py /path/to/photos/
```

### Gemini API 오류
```bash
# .env 파일 확인
cat .env | grep GOOGLE_AI_API_KEY

# 할당량 확인
# https://ai.dev/rate-limit 에서 확인

# 모델 확인
python check_models.py
```

### 네이버 플레이스 업로드 실패
- 네이버 플레이스 API 키 확인
- Place ID 확인
- 네트워크 연결 확인
- Playwright 브라우저 업데이트: `playwright install chromium`

### S3 접근 오류
```bash
# AWS 자격 증명 확인
cat .env | grep AWS

# S3 버킷 권한 확인
# AWS 콘솔에서 버킷 정책 확인
```

---

## 💰 비용 절감 가이드 (취준생 친화적)

### 현재 비용 구조
- **Gemini API**: 월 60회 사용 시 약 1-2원 (gemini-2.0-flash 기준)
- **AWS S3**: 월 약 3원
- **CloudFront CDN**: 월 약 13원
- **총 예상 비용**: 월 약 17-18원

### 🔄 무료 vs 유료 FAQ

**Q: 무료 버전을 유료로 바꾸려면 모델 이름을 바꿔야 하나요?**
- ❌ **아니요!** 모델 이름은 그대로 `models/gemini-2.0-flash` 사용
- ✅ **결제 계정만 연결**하면 자동으로 유료화됨

**Q: 무료 티어를 다 쓰면 자동으로 유료로 전환되나요?**
- ✅ **네!** 무료 티어 15회를 다 쓰면 자동으로 유료 과금 시작
- ⚠️ 단, 결제 계정이 연결되어 있어야 함 (연결 안 하면 API 호출 실패)

**Q: 결제 계정을 연결하지 않으면?**
- 무료 티어 15회만 사용 가능
- 15회 초과 시 API 호출 실패 (에러 발생)

**Q: 결제 계정을 연결하면?**
- 무료 티어 15회 사용 가능
- 15회 초과 시 자동으로 유료 과금 시작
- 사용한 만큼만 과금 (매우 저렴)

### 비용 절감 전략

#### 1. 무료 티어 최대 활용
```env
# Gemini 무료 티어: 월 15회 무료
# 하루 1회로 줄이면 거의 무료로 운영 가능
# 크론잡을 하루 1회로 변경:
# 0 10 * * * ... (오전 10시만 실행)
```

#### 2. 모델 선택 최적화
- ✅ **추천**: `models/gemini-2.0-flash` (기본값 유지)
  - 무료 티어 지원
  - 비용 효율 최고
  - 정확도 충분
- ❌ **비추천**: `gemini-1.5-pro` (비용 5-10배 높음)

#### 3. 프롬프트 최적화
- 불필요한 설명 제거
- 키워드만 간결하게 포함
- 토큰 수 절감으로 비용 절감

#### 4. 재시도 최소화
- 금지어 체크를 정확하게 해서 재시도 줄이기
- 현재 3회 재시도 → 필요시 2회로 조정 가능

#### 5. 사용량 모니터링
```bash
# Google Cloud Console에서 사용량 확인
# https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas
```

### 예산 관리 팁
1. **Google Cloud 결제 알림 설정**: 예상치 못한 비용 방지
2. **월별 사용량 추적**: 로그로 사용 횟수 확인
3. **무료 티어 한도 확인**: 월 15회 무료 활용

---

## 💡 추가 개선 아이디어

1. **실제 날씨 API 연동** (현재는 시간대만 사용)
2. **리뷰 답글 자동화** 연동
3. **A/B 테스팅**: 여러 프롬프트 비교
4. **성과 분석**: 조회수/클릭수 추적
5. **이미지 최적화**: 자동 리사이징 및 압축

---

## 📞 지원

문제가 발생하면 로그를 확인하고, 이슈를 등록하세요.

**Happy Auto-Posting! 🚀**
