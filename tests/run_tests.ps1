Write-Host "Building Docker image for Home Assistant Testing..."
docker build -t home-assistant-tests ./tests/

if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker build failed."
    exit $LASTEXITCODE
}

Write-Host "Running tests..."
# Run the docker container, mapping our current project directory to /app inside the container
docker run --rm -v "${PWD}:/app" -w /app home-assistant-tests pytest -sv $args

if ($LASTEXITCODE -ne 0) {
    Write-Error "Tests failed!"
    exit $LASTEXITCODE
}

Write-Host "All tests executed successfully!" -ForegroundColor Green
