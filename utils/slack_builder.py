class SlackBuilder:
    @staticmethod
    def build_news_blocks(data: dict, keyword: str) -> dict:
        """분석 데이터를 Slack Block Kit 포맷으로 변환합니다."""
        return {
            "response_type": "in_channel",
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": f"🤖 {data['summary_line']}", "emoji": True}},
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*키워드:* `{keyword or '최신 AI 트렌드'}`"}},
                {"type": "divider"},
                {"type": "section", "text": {"type": "mrkdwn", "text": f"{data['summary_detail']}"}},
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*신빙성:*\n{data['reliability']}"},
                        {"type": "mrkdwn", "text": f"*난이도:*\n{data['difficulty']}"},
                        {"type": "mrkdwn", "text": f"*비용 수준:*\n{data['cost_level']}"}
                    ]
                },
                {"type": "divider"},
                {"type": "section", "text": {"type": "mrkdwn", "text": f"💡 *AI 리뷰:*\n{data['ai_review']}"}}
            ]
        }
