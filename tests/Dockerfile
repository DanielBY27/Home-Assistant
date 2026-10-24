FROM python:3.12-alpine

WORKDIR /app

ENV PYTHONPATH=/app

# Install dependencies for Home Assistant testing and Google Drive/Sheets MCP server
RUN pip install --no-cache-dir \
    pytest \
    jinja2 \
    pyyaml \
    tzdata \
    google-api-python-client \
    google-auth \
    google-auth-oauthlib \
    google-auth-httplib2 \
    mcp

# Command to run tests when container starts.
# We map the root project directory to /app
CMD ["pytest", "-sv", "tests/"]
