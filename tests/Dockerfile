FROM python:3.12-alpine

WORKDIR /app

# Install standard dependencies
RUN pip install --no-cache-dir pytest jinja2 pyyaml

# Command to run tests when container starts.
# We map the root project directory to /app
CMD ["pytest", "-sv", "tests/"]
