from dataclasses import dataclass

@dataclass
class Section:
    heading: str
    content_preview: str
    page_url: str
    anchor: str
    direct_url: str