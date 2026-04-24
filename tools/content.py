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

from tools.section import Section

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

def parse_govuk_page(api_response: dict, source_url: str) -> dict:
    """
    Parses a GOV.UK Content API response into a dict.
    No HTTP calls — pure data transformation.
    """
    if api_response.get("withdrawn_notice"):
        return {
            "url": source_url,
            "page_title": api_response.get("title", ""),
            "public_updated_at": "",
            "is_withdrawn": True,
            "sections": [],
        }

    canonical_url = f"https://www.gov.uk{api_response.get('base_path', '')}"
    page_title = api_response.get("title", "")
    updated_at = api_response.get("public_updated_at", "")
    details = api_response.get("details", {})
    html_body = details.get("body", "")

    if html_body:
        sections = _parse_body(html_body, canonical_url)
    else:
        sections = _parse_parts(details.get("parts", []), canonical_url)

    return {
        "url": canonical_url,
        "page_title": page_title,
        "public_updated_at": updated_at,
        "is_withdrawn": False,
        "sections": sections,
    }


def _parse_parts(parts: list[dict], canonical_url: str) -> list[Section]:
    """
    Multi-part guide — each part parsed against its own tab URL
    so section direct_urls point to the tab, not the parent guide.
    """
    sections = []
    for part in parts:
        slug = part.get("slug", "")
        tab_url = f"{canonical_url}/{slug}"
        body = part.get("body", "")

        if DEBUG:
            print(
                f"     [part] '{part.get('title')}' "
                f"slug='{slug}' body_len={len(body)}"
            )

        if body:
            sections.extend(_parse_body(body, tab_url))
        else:
            sections.append(Section(
                heading=part.get("title", ""),
                anchor=slug,
                content_preview=f"Full content at {tab_url}",
                direct_url=tab_url,
                page_url=tab_url,
            ))
    return sections


def _parse_body(html_body: str, page_url: str) -> list[Section]:
    """
    Parses a single HTML body into sections by H2/H3 heading structure.
    Content before the first heading becomes an intro section
    with an empty anchor.
    """
    if len(html_body) > MAX_CONTENT_CHARS:
        html_body = html_body[:MAX_CONTENT_CHARS]

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


def _make_section(heading: str, anchor: str,
                  content: list[str], page_url: str) -> Section:
    preview = " ".join(content).strip()[:CONTENT_PREVIEW_CHARS]
    direct_url = f"{page_url}#{anchor}" if anchor else page_url
    return Section(
        heading=heading,
        content_preview=preview,
        page_url=page_url,
        anchor=anchor,
        direct_url=direct_url,
    )

def fetch_govuk_page(url: str) -> dict:
    """
    Fetches and parses a GOV.UK page.
    Returns a dict with page data and sections for tool use.
    """
    try:
        api_response = get_govuk_page(url)
    except requests.RequestException as e:
        return {
            "url": url,
            "page_title": "",
            "public_updated_at": "",
            "error": str(e),
            "sections": [],
        }

    parsed = parse_govuk_page(api_response, url)

    # Convert Section objects to dicts
    sections = [
        {
            "heading": s.heading,
            "anchor": s.anchor,
            "content_preview": s.content_preview,
            "page_url": s.page_url,
            "direct_url": s.direct_url,
        }
        for s in parsed.get("sections", [])
        if isinstance(s, Section)
    ]

    return {
        "url": parsed.get("url", ""),
        "page_title": parsed.get("page_title", ""),
        "public_updated_at": parsed.get("public_updated_at", ""),
        "is_withdrawn": parsed.get("is_withdrawn", False),
        "sections": sections,
        "section_count": len(sections),
    }
