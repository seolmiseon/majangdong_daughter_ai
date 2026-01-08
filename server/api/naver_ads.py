import time
import hmac
import hashlib
import base64
import requests
from server.llm_service.config.settings import settings

class NaverAdsAPI:
    def __init__(self):
        self.base_url = "https://api.searchad.naver.com"
        
        # 💡 혹시 모를 앞뒤 공백을 완벽히 제거합니다.
        self.api_key = str(settings.NAVER_AD_API_KEY).strip() if settings.NAVER_AD_API_KEY else ""
        self.secret_key = str(settings.NAVER_AD_SECRET_KEY).strip() if settings.NAVER_AD_SECRET_KEY else ""
        self.customer_id = str(settings.NAVER_AD_CUSTOMER_ID).strip() if settings.NAVER_AD_CUSTOMER_ID else ""
        
        # 키 유효성 검증
        if not self.api_key or not self.secret_key or not self.customer_id:
            raise ValueError("❌ 네이버 광고 API 키가 설정되지 않았습니다. .env 파일을 확인하세요.")
        
        # 키 형식 간단 검증 (디버깅용)
        print(f"✅ API Key 로드됨 (길이: {len(self.api_key)})")
        print(f"✅ Secret Key 로드됨 (길이: {len(self.secret_key)})")
        print(f"✅ Customer ID: {self.customer_id}")
        
        # ⚠️ 키가 너무 짧거나 형식이 이상하면 경고
        if len(self.api_key) < 20 or len(self.secret_key) < 20:
            print("⚠️ [경고] API 키 또는 시크릿 키가 너무 짧습니다. 키가 올바른지 확인하세요.")

    def _generate_signature(self, timestamp: str, method: str, uri: str):
        # 1. 메서드는 대문자로 (GET, POST 등)
        method_upper = method.upper()
        
        # 2. [핵심 수정] URI는 반드시 '/'로 시작해야 함!
        # 들어온 uri가 "ncc/campaigns"라면 "/ncc/campaigns"로 만들어줘야 합니다.
        if not uri.startswith("/"):
            uri = "/" + uri
            
        # 3. 메시지 조합 (예: 1767757297064.GET./ncc/campaigns)
        message = f"{timestamp}.{method_upper}.{uri}"
        
        # 4. 서명 생성 (나머지는 잘 작성하셨습니다)
        hash_obj = hmac.new(
            self.secret_key.encode('utf-8'), 
            message.encode('utf-8'), 
            hashlib.sha256
        )
        signature = base64.b64encode(hash_obj.digest()).decode('utf-8')
        
        # 디버깅: 이제 점(.) 뒤에 슬래시(/)가 보여야 정상입니다.
        print(f"🔍 [디버그] 메시지: {message}") 
        
        return signature
    def _get_headers(self, method: str, uri: str):
        timestamp = str(int(time.time() * 1000))
        signature = self._generate_signature(timestamp, method, uri)
        
        # 디버깅용 출력
        print(f"🔍 [디버그] 타임스탬프: {timestamp}")
        print(f"🔍 [디버그] 메서드: {method}")
        print(f"🔍 [디버그] URI: {uri}")
        print(f"🔍 [디버그] API Key: {self.api_key[:10]}...")
        print(f"🔍 [디버그] Customer ID: {self.customer_id}")
        
        return {
            "Content-Type": "application/json; charset=UTF-8",
            "X-Timestamp": timestamp,
            "X-API-KEY": self.api_key,
            "X-Customer": self.customer_id,
            "X-Signature": signature
        }

    def test_connection(self):
        uri = "/ncc/campaigns" 
        headers = self._get_headers("GET", uri)
        
        # 요청 URL 확인
        url = f"{self.base_url}{uri}"
        print(f"🔍 [디버그] 요청 URL: {url}")
        print(f"🔍 [디버그] 요청 헤더: {headers}")
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            print("✅ [성공] 드디어 네이버 문이 열렸습니다!")
            return response.json()
        else:
            print(f"❌ [실패] 코드: {response.status_code}")
            print(f"📝 서버 메시지: {response.text}")
            
            # 시크릿 키나 API 키가 비어있는지 확인
            if not self.secret_key or not self.api_key:
                print("⚠️ [경고] 시크릿 키 또는 API 키가 비어있을 수 있습니다!")
                print(f"   시크릿 키 존재: {bool(self.secret_key)}")
                print(f"   API 키 존재: {bool(self.api_key)}")
            
            return None
