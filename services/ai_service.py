import json
from tavily import TavilyClient
from google import genai
from google.genai import types
from config import settings

class AIService:
    def __init__(self):
        self.tavily = TavilyClient(api_key=settings.tavily_api_key)
        self.gemini = genai.Client(api_key=settings.gemini_api_key)

    def search_news(self, query: str) -> list:
        """Tavily를 통해 최신 뉴스를 검색합니다."""
        search_query = query if query else "최신 AI 기술 트렌드"
        response = self.tavily.search(query=search_query, search_depth="advanced", max_results=3)
        return response.get('results', [])

    def analyze_content(self, news_results: list) -> dict:
        """Gemini를 사용하여 뉴스 내용을 분석하고 JSON으로 반환합니다."""
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

        response = self.gemini.models.generate_content(
            model='gemini-2.0-flash', # 혹은 사용 가능한 최신 모델
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
