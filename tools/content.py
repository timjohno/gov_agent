"""
tools/content.py

GOV.UK Content API client.
Fetches pages and returns structured sections for the model to reason about.
Also provides fetch_section_verbatim() for retrieving the final display content —
this is called by the application after the model identifies an anchor,
and the model never sees or generates the text shown to the user.
"""

import requests
from bs4 import BeautifulSoup
from config.settings import (
    CONTENT_PREVIEW_CHARS,
    MAX_CONTENT_CHARS,
    REQUEST_TIMEOUT,
    VERIFY_SSL,
    DEBUG,
    CONTENT_API_BASE
)

from .utils import _to_path

def get_govuk_page(url: str) -> dict:
    path = (
        url
        .replace("https://www.gov.uk", "")
        .split("?")[0]
        .split("#")[0]
        .rstrip("/")
    )
    response = requests.get(
        f"{CONTENT_API_BASE}{path}",
        timeout=REQUEST_TIMEOUT,
        verify=VERIFY_SSL,
    )
    response.raise_for_status()
    return response.json()

def fetch_govuk_page(url: str) -> dict:
    """
    Fetches a GOV.UK page via the Content API and returns its sections.

    Handles two page types:
      - Simple pages: content in details.body
      - Guide pages: content split across details.parts (tabs),
        each part parsed with its own tab URL so direct_urls are
        correctly scoped to the tab, not the parent guide.
    """
    path = _to_path(url)

    try:
        data = get_govuk_page(url)
    except requests.RequestException as e:
        return {"error": f"fetch_failed: {e}", "url": url}

    if data.get("withdrawn_notice"):
        return {"error": "page_withdrawn", "url": url}

    canonical_url = f"https://www.gov.uk{data.get('base_path', path)}"
    page_title = data.get("title", "")
    updated_at = data.get("public_updated_at", "")
    details = data.get("details", {})
    html_body = details.get("body", "")

    # Guide pages: content is split across parts (tabs)
    if not html_body:
        parts = details.get("parts", [])
        if parts:
            sections = []
            for part in parts:
                part_slug = part.get("slug", "")
                part_url = f"{canonical_url}/{part_slug}"
                part_body = part.get("body", "")

                if DEBUG:
                    print(
                        f"     [part] '{part.get('title')}' "
                        f"slug='{part_slug}' body_len={len(part_body)}"
                    )

                if part_body:
                    # Parse using the tab URL so direct_urls are tab-scoped
                    for section in _parse_sections(part_body, part_url):
                        sections.append(section)
                else:
                    sections.append({
                        "heading": part.get("title", ""),
                        "anchor": part_slug,
                        "page_url": part_url,
                        "content_preview": f"Full content at {part_url}",
                    })

            return {
                "url": canonical_url,
                "page_title": page_title,
                "public_updated_at": updated_at,
                "section_count": len(sections),
                "sections": sections,
            }

        return {"error": "no_content_found", "url": url}

    # Simple pages: single HTML body
    if len(html_body) > MAX_CONTENT_CHARS:
        html_body = html_body[:MAX_CONTENT_CHARS]

    sections = _parse_sections(html_body, canonical_url)

    return {
        "url": canonical_url,
        "page_title": page_title,
        "public_updated_at": updated_at,
        "section_count": len(sections),
        "sections": sections,
    }

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_sections(html_body: str, page_url: str) -> list[dict]:
    """
    Parses HTML into sections using H2/H3 heading structure.
    Content before the first heading becomes an intro section.
    Each section includes page_url so the model can construct direct_url.
    """
    soup = BeautifulSoup(html_body, "lxml")
    sections = []
    current_heading = "Introduction"
    current_anchor = ""
    current_content: list[str] = []

    for element in soup.find_all(["h2", "h3", "p", "ul", "ol"]):
        if element.name in ("h2", "h3"):
            if current_content:
                sections.append(_make_section(
                    current_heading, current_anchor,
                    current_content, page_url,
                ))
            current_heading = element.get_text(strip=True)
            current_anchor = element.get("id", "")
            current_content = []
        else:
            text = element.get_text(strip=True)
            if text:
                current_content.append(text)

    if current_content:
        sections.append(_make_section(
            current_heading, current_anchor,
            current_content, page_url,
        ))

    return sections


def _make_section(
    heading: str,
    anchor: str,
    content: list[str],
    page_url: str,
) -> dict:
    return {
        "heading": heading,
        "anchor": anchor,
        "page_url": page_url,
        "content_preview": " ".join(content).strip()[:CONTENT_PREVIEW_CHARS],
    }

