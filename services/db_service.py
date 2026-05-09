import hashlib
import time
import boto3
from config import settings

class DBService:
    def _get_table(self):
        """
        [스레드 안전성(Thread-Safety) 보장 로직]
        BackgroundTasks(다른 스레드)에서 호출될 때마다 독립적인 세션을 생성하여 
        'Unable to locate credentials' 에러를 원천 차단합니다.
        """
        boto_kwargs = {'region_name': settings.aws_default_region}
        
        # 로컬 환경에서는 .env의 키를 주입하고, Lambda 환경에서는 권한을 자동 상속받음
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            boto_kwargs['aws_access_key_id'] = settings.aws_access_key_id
            boto_kwargs['aws_secret_access_key'] = settings.aws_secret_access_key
            
        session = boto3.Session(**boto_kwargs)
        return session.resource('dynamodb').Table(settings.dynamodb_table_name)  # type: ignore

    def generate_hash(self, url: str) -> str:
        """URL을 고유한 SHA-256 해시값으로 변환합니다."""
        return hashlib.sha256(url.encode('utf-8')).hexdigest()

    def is_duplicate(self, url: str) -> bool:
        """DynamoDB를 조회하여 이미 전송된 기사인지 확인합니다."""
        if not url: return True
            
        url_hash = self.generate_hash(url)
        try:
            response = self._get_table().get_item(Key={'url_hash': url_hash})
            return 'Item' in response
        except Exception as e:
            print(f"DB 조회 에러: {e}")
            return False # DB 에러 시 파이프라인 전체 중단 방지

    def save_news_url(self, url: str):
        """새로운 기사 URL을 DB에 저장합니다."""
        if not url: return
            
        try:
            self._get_table().put_item(
                Item={
                    'url_hash': self.generate_hash(url),
                    'url': url,
                    'created_at': int(time.time())
                }
            )
        except Exception as e:
            print(f"DB 저장 에러: {e}")

db_service = DBService()