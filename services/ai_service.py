import json
from tavily import TavilyClient
from google import genai
from google.genai import types
from config import settings
from services.db_service import db_service

class AIService:
    def __init__(self):
        self.tavily = TavilyClient(api_key=settings.tavily_api_key)
        self.gemini = genai.Client(api_key=settings.gemini_api_key)

    def search_news(self, query: str) -> list:
        """Tavily 최신 뉴스 검색 및 DynamoDB 중복 필터링"""
        search_query = query if query else "최신 AI 기술 트렌드"
        response = self.tavily.search(query=search_query, search_depth="advanced", max_results=5)
        
        fresh_news = []
        for result in response.get('results', []):
            url = result.get('url', '')
            
            # DB 중복 검사
            if not db_service.is_duplicate(url):
                fresh_news.append(result)
                db_service.save_news_url(url)
                
                if len(fresh_news) == 3: # 3개 찾으면 종료
                    break
        return fresh_news

    def analyze_content(self, news_results: list) -> dict:
        """Gemini를 사용하여 뉴스 내용을 분석하고 JSON으로 반환"""
        if not news_results:
            return {
                "summary_line": "새로운 뉴스가 없습니다.",
                "summary_detail": "이미 모든 최신 뉴스를 확인하셨거나 검색 결과가 없습니다.",
                "reliability": "하", "difficulty": "최하", "cost_level": "하",
                "ai_review": "나중에 다시 시도해 주세요."
            }

        context = "\n".join([f"- 제목: {r['title']}\n  내용: {r['content']}" for r in news_results])
        
        prompt = f"""
        당신은 전문 AI 뉴스 큐레이터입니다. 다음 뉴스 데이터를 분석하여 JSON 포맷으로 요약하세요.
        [데이터]
        {context}
        [필수 포함 항목]
        - summary_line: 한 줄 평
        - summary_detail: 상세 요약
        - reliability: 신빙성 (상/중/하)
        - difficulty: 난이도 (최상/상/중/하/최하)
        - cost_level: 비용 (상/중/하)
        - ai_review: 실현 가능성 및 후기
        """

        # 하드코딩 대신 config.py에서 모델명을 동적으로 불러옴
        response = self.gemini.models.generate_content(
            model=settings.gemini_model, 
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2
            ),
        )

        if not response.text:
            raise ValueError("Gemini 응답이 비어있습니다.")
            
        return json.loads(response.text)

ai_service = AIService()