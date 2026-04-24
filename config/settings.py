"""
Set TAVILY_API_KEY as an environment variable before running.
"""

import os

# AWS Bedrock
AWS_REGION = "eu-west-2"
MODEL_ID = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"
MAX_TOKENS = 600
TEMPERATURE = 0

# Tool use
MAX_ITERATIONS = 8
MAX_SEARCH_CALLS = 2        # hard cap on search calls per query
MAX_CONTENT_CHARS = 8000    # truncation limit for GOV.UK page HTML
CONTENT_PREVIEW_CHARS = 400 # characters of each section sent to model

# HTTP
REQUEST_TIMEOUT = 5         # seconds for GOV.UK API calls
VERIFY_SSL = True          # set True in production with correct cert bundle
CONTENT_API_BASE = "https://www.gov.uk/api/content"

# Tavily
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
TAVILY_MAX_RESULTS = 5

# Debug
DEBUG = os.environ.get("DEBUG", "true").lower() == "true"
