import requests
from bs4 import BeautifulSoup

from config.settings import (
    REQUEST_TIMEOUT,
    VERIFY_SSL,
    CONTENT_API_BASE,
)

from .utils import _to_path

def fetch_section_verbatim(direct_url: str) -> str:
    """
    Fetches the current live verbatim content of a section.
    Called by the application after the model returns an anchor —
    the model never sees or generates this text.

    Handles:
      1. Simple pages: anchor found in details.body
      2. Guide pages: anchor searched across all parts' bodies
      3. No anchor: returns intro content of the matching part by slug
    """
    if "#" in direct_url:
        page_url, anchor = direct_url.split("#", 1)
    else:
        page_url, anchor = direct_url, ""

    path = _to_path(page_url)

    try:
        response = requests.get(
            f"{CONTENT_API_BASE}{path}",
            timeout=REQUEST_TIMEOUT,
            verify=VERIFY_SSL,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return ""

    details = data.get("details", {})

    # Collect all HTML bodies to search
    all_bodies = []
    if details.get("body"):
        all_bodies.append(details["body"])
    for part in details.get("parts", []):
        if part.get("body"):
            all_bodies.append(part["body"])

    # Search all bodies for the anchor
    if anchor:
        for body in all_bodies:
            content = _extract_section_by_anchor(body, anchor)
            if content:
                return content

    # No anchor or anchor not found — return intro of the matching part
    slug = path.split("/")[-1]
    for part in details.get("parts", []):
        if part.get("slug") == slug and part.get("body"):
            return _extract_intro(part["body"])

    return ""


def _extract_section_by_anchor(html_body: str, anchor: str) -> str:
    soup = BeautifulSoup(html_body, "lxml")
    heading = soup.find(id=anchor)
    if not heading:
        return ""

    level = int(heading.name[1]) if heading.name in ("h2", "h3", "h4") else 2
    parts = []

    for sibling in heading.find_next_siblings():
        if sibling.name in ("h2", "h3", "h4"):
            if int(sibling.name[1]) <= level:
                break
        text = sibling.get_text(separator=" ", strip=True)
        if text:
            parts.append(text)

    return " ".join(parts)


def _extract_intro(html_body: str) -> str:
    """Returns content before the first H2/H3 in a body."""
    soup = BeautifulSoup(html_body, "lxml")
    intro = []
    for el in soup.find_all(["p", "ul", "ol", "h2", "h3"]):
        if el.name in ("h2", "h3"):
            break
        text = el.get_text(separator=" ", strip=True)
        if text:
            intro.append(text)
    if intro:
        return " ".join(intro)
    return soup.get_text(separator=" ", strip=True)[:800]