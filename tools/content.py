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
from tools.parsed_page import ParsedPage

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

def parse_govuk_page(api_response: dict, source_url: str) -> ParsedPage:
    """
    Parses a GOV.UK Content API response into a ParsedPage.
    No HTTP calls — pure data transformation.
    """
    if api_response.get("withdrawn_notice"):
        return ParsedPage(
            url=source_url,
            page_title=api_response.get("title", ""),
            public_updated_at="",
            is_withdrawn=True,
        )

    canonical_url = f"https://www.gov.uk{api_response.get('base_path', '')}"
    page_title = api_response.get("title", "")
    updated_at = api_response.get("public_updated_at", "")
    details = api_response.get("details", {})
    html_body = details.get("body", "")

    if html_body:
        sections = _parse_body(html_body, canonical_url)
    else:
        sections = _parse_parts(details.get("parts", []), canonical_url)

    return ParsedPage(
        url=canonical_url,
        page_title=page_title,
        public_updated_at=updated_at,
        sections=sections,
    )


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
        anchor=anchor,
        content_preview=preview,
        direct_url=direct_url,
        page_url=page_url,
    )

def fetch_govuk_page(url: str, verify_ssl: bool = True) -> ParsedPage:
    """
    Fetches and parses a GOV.UK page.
    Errors are captured in ParsedPage.error — never raises.
    """
    try:
        api_response = get_govuk_page(url)
    except requests.RequestException as e:
        return ParsedPage(url=url, page_title="",
                         public_updated_at="", error=str(e))

    return parse_govuk_page(api_response, url)