"""
retrieval/section_retrieval.py

GOV.UK section retrieval using Bedrock Converse tool use.
Combines the search and content tools with the generic tool loop
to find and return the most relevant GOV.UK section for a query.
"""

import json
import re
from dataclasses import dataclass

from config.settings import MAX_ITERATIONS, MAX_SEARCH_CALLS, DEBUG
from tools.search import search_govuk
from tools.content import fetch_govuk_page
from tools.verbatim import fetch_section_verbatim
from llm.tool_loop import run_tool_loop


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


@dataclass
class SectionResult:
    section_found: bool
    page_title: str = ""
    section_heading: str = ""
    anchor_id: str = ""
    source_url: str = ""
    direct_url: str = ""
    public_updated_at: str = ""
    verbatim_content: str = ""
    reason: str = ""

def make_tools(search_cap: int = 2) -> dict:
    """
    Returns the tools dict with state (visited urls, search count)
    captured in closures. Called once per query.
    """
    search_count = [0]
    visited_urls: set[str] = set()

    def handle_search(input_data: dict) -> dict:
        if search_count[0] >= search_cap:
            if DEBUG:
                print(f"\n  🚫 search blocked (limit {search_cap} reached)")
            return {
                "error": "search_limit_reached",
                "message": "Search limit reached. Use results from previous searches.",
            }
        query_str = input_data.get("query", "")
        search_count[0] += 1
        if DEBUG:
            print(f"\n  🔍 search_govuk(\"{query_str}\") [{search_count[0]}/{search_cap}]")
        return search_govuk(query_str)

    def handle_fetch(input_data: dict) -> dict:
        url = input_data.get("url", "")
        if url in visited_urls:
            if DEBUG:
                print(f"\n  ⚠️  Already fetched: {url}")
            return {
                "error": "already_fetched",
                "message": "Already fetched. Use the sections you already have.",
            }
        visited_urls.add(url)
        if DEBUG:
            print(f"\n  📄 fetch_govuk_page(\"{url}\")")
        result = fetch_govuk_page(url)
        if DEBUG:
            count = result.get("section_count", 0)
            title = result.get("page_title", "")
            print(f"     → \"{title}\" — {count} sections")
            for s in result.get("sections", [])[:5]:
                anchor_str = f"[{s.get('anchor', '')}] " if s.get("anchor") else ""
                print(f"       {anchor_str}{s.get('heading', '')}")
        return result

    tools = {
        "search_govuk": handle_search,
        "fetch_govuk_page": handle_fetch,
    }
    return tools


def find_section(query: str, bedrock_client) -> SectionResult:
    """
    Main entry point. Finds the most relevant GOV.UK section for a query.
    Returns a SectionResult with verbatim_content populated if section found.
    """


    raw_response = run_tool_loop(
        system=SYSTEM_PROMPT,
        initial_message=(
            f"Find the most relevant GOV.UK section for this question "
            f"from a British national: {query}"
        ),
        tools=make_tools(search_cap=2),
        tool_specs=TOOL_SPECS,
        bedrock_client=bedrock_client,
        max_iterations=MAX_ITERATIONS,
    )

    if DEBUG:
        print(f"\n  [DEBUG] Raw model response:\n  {repr(raw_response[:300])}")

    parsed = _parse_response(raw_response)

    if not parsed.get("section_found"):
        return SectionResult(
            section_found=False,
            reason=parsed.get("reason", "max_iterations_reached"),
        )

    verbatim = fetch_section_verbatim(parsed.get("direct_url", ""))

    return SectionResult(
        section_found=True,
        page_title=parsed.get("page_title", ""),
        section_heading=parsed.get("section_heading", ""),
        anchor_id=parsed.get("anchor_id", ""),
        source_url=parsed.get("source_url", ""),
        direct_url=parsed.get("direct_url", ""),
        public_updated_at=parsed.get("public_updated_at", ""),
        verbatim_content=verbatim,
    )


def _parse_response(text: str) -> dict:
    """Parses the model's JSON response, handling markdown fences and prose."""
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # JSON embedded in prose
    match = re.search(r'\{[^{}]*"section_found"[^{}]*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return {"section_found": False, "reason": "unparseable_response"}
