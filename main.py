"""
main.py

Test runner for the GOV.UK section retrieval prototype.
Add queries to TEST_QUERIES to test different scenarios.

Usage:
    export TAVILY_API_KEY=tvly-your-key
    export DEBUG=true
    python main.py
"""

import boto3
from config.settings import AWS_REGION
from retrieval.section_retrieval import find_section


TEST_QUERIES = [
    "Do I need to microchip my dog before travelling to Spain?",
    #"How long after a rabies vaccination before my dog can travel to the EU?",
    #"My dog's microchip cannot be read at the border — what happens?",
]


def print_result(query: str, result) -> None:
    divider = "─" * 60
    print(f"\n{divider}")
    print("RESULT")
    print(divider)

    if result.section_found:
        print(f"  Page:     {result.page_title}")
        print(f"  Section:  {result.section_heading}")
        print(f"  Anchor:   {result.anchor_id or '(intro — no anchor)'}")
        print(f"  URL:      {result.direct_url}")
        print(f"  Updated:  {result.public_updated_at[:10]}")

        if result.verbatim_content:
            content = result.verbatim_content
            preview = content[:400] + ("..." if len(content) > 400 else "")
            print(f"\n  Verbatim content (shown to user):")
            print(f"  {preview}")
        else:
            print("\n  ⚠️  Verbatim content empty — check anchor_id")
    else:
        print(f"  section_found: false")
        print(f"  reason: {result.reason}")

    print()


def main() -> None:
    bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)

    for query in TEST_QUERIES:
        print(f"\n{'─' * 60}")
        print(f"Query: {query[:80]}{'...' if len(query) > 80 else ''}")
        print(f"{'─' * 60}")

        result = find_section(query, bedrock)
        print_result(query, result)


if __name__ == "__main__":
    main()
