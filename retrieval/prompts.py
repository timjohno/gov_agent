"""
retrieval/prompts.py

System prompt and tool specifications for GOV.UK section retrieval.
"""

SYSTEM_PROMPT = """You find the most relevant GOV.UK guidance section for a British national's question.

STEPS:
1. Call search_govuk ONCE with your best search terms
2. Immediately call fetch_govuk_page on the 1-2 most relevant URLs
3. Read the section content_previews carefully — match content to the specific question, not just heading keywords
4. Once you find relevant sections, return your answer immediately
5. Only search again if fetched pages contain nothing relevant

Each section has: heading, anchor (HTML id attribute), page_url, content_preview.
Construct direct_url as: page_url + "#" + anchor (omit # if anchor is empty).

FINAL RESPONSE — output ONLY this JSON:
{"section_found": true, "page_title": "...", "section_heading": "...", "anchor_id": "...", "source_url": "...", "direct_url": "...", "public_updated_at": "..."}

If nothing found:
{"section_found": false, "reason": "..."}

IMPORTANT: Your final message must be ONLY the JSON object. No explanation."""


TOOL_SPECS = [
    {
        "toolSpec": {
            "name": "search_govuk",
            "description": (
                "Search GOV.UK for guidance pages relevant to the user's question. "
                "Call this ONCE first, then fetch the most relevant pages. "
                "Only search again if fetched pages contain nothing relevant."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Specific search terms for the user's question",
                        }
                    },
                    "required": ["query"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "fetch_govuk_page",
            "description": (
                "Fetch a GOV.UK page and return its sections with headings, "
                "anchor IDs, page_urls, and content previews. "
                "Use page_url + '#' + anchor to form direct_url in your response. "
                "Call this after search_govuk. You can call it multiple times."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "A GOV.UK URL to fetch",
                        }
                    },
                    "required": ["url"],
                }
            },
        }
    },
]
