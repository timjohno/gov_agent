# GOV.UK Section Retrieval Prototype

Prototype for the FCDO Consular Digital Triage agentic section retrieval feature.
Given a user query, finds the most relevant GOV.UK guidance section and returns
its verbatim content with a direct URL.

## Architecture

```
main.py                         # test runner
config/
  settings.py                   # all configuration
tools/
  search.py                     # Tavily GOV.UK search
  content.py                    # GOV.UK Content API fetch + section parser
llm/
  tool_loop.py                  # generic Bedrock Converse tool use loop
retrieval/
  section_retrieval.py          # main retrieval logic, prompts, tool wiring
```

## How it works

1. Model calls `search_govuk` to find relevant GOV.UK pages via Tavily
2. Model calls `fetch_govuk_page` to read page sections via GOV.UK Content API
3. Model identifies the best section and returns structured JSON
4. Application calls `fetch_section_verbatim` to retrieve the actual content
   — the model never sees or generates the text shown to the user

## Setup

```bash
pip install boto3 requests beautifulsoup4 lxml

export TAVILY_API_KEY=tvly-your-key-here
export DEBUG=true   # set false to suppress debug output

# AWS credentials must be configured
export AWS_PROFILE=your-profile   # or use env vars / IAM role
```

## Run

```bash
python main.py
```

Add queries to `TEST_QUERIES` in `main.py` to test additional scenarios.

## Key design decisions

- **Tavily for search** — GOV.UK's own v1 search API returns poor results
  for specific guidance queries. Tavily restricted to `gov.uk` works well.
- **Verbatim content fetched by application** — model identifies where to look,
  application fetches the text. Model never generates displayed content.
- **Generic tool loop** — `llm/tool_loop.py` is reusable for any Bedrock
  Converse tool use pattern, not specific to this feature.
- **Hard search cap** — `MAX_SEARCH_CALLS` in settings prevents the model
  from searching repeatedly before fetching pages.

## Configuration

All settings in `config/settings.py`. Key values:

| Setting | Default | Description |
|---|---|---|
| `MAX_ITERATIONS` | 8 | Hard cap on total tool call iterations |
| `MAX_SEARCH_CALLS` | 2 | Hard cap on search calls per query |
| `CONTENT_PREVIEW_CHARS` | 400 | Section preview length sent to model |
| `MAX_CONTENT_CHARS` | 8000 | Page content truncation limit |
| `VERIFY_SSL` | False | Set True in production with correct cert bundle |
| `DEBUG` | True | Print tool call trace to stdout |

## Known limitations

- SSL verification disabled for local development — set `VERIFY_SSL=True`
  in production with the correct certificate bundle
- GOV.UK v1 search API is not used — Tavily is required
- Anchor IDs for intro sections (content before first heading) are derived
  from page slug and may not match real HTML id attributes
