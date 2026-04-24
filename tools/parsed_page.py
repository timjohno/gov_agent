from dataclasses import dataclass, field

from tools.section import Section


@dataclass
class ParsedPage:
    url: str
    page_title: str
    public_updated_at: str
    sections: list[Section] = field(default_factory=list)
    is_withdrawn: bool = False
    error: str | None = None