def _to_path(url: str) -> str:
    """Converts a GOV.UK URL to a Content API path."""
    return (
        url.replace("https://www.gov.uk", "")
           .split("?")[0]
           .split("#")[0]
           .rstrip("/")
    )