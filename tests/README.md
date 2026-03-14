# Home Assistant Blueprint Testing System

This directory contains the testing infrastructure for Home Assistant blueprints using a mock environment.

## Directory Structure

- `ha_mock.py`: Core logic for mocking the Home Assistant environment (Jinja2, states, inputs, etc.).
- `mocks/`: Base mock configuration files in JSON format.
- `scenarios/`: Data-driven test scenarios.
    - `dishwasher/`: Scenarios for the dishwasher blueprint.
    - `go_echarger/`: Scenarios for the go-eCharger blueprint.
- `test_*.py`: Pytest scripts that load and execute scenarios.
- `run_tests.ps1`: PowerShell script to run tests inside a Docker container.

## How it Works

The testing system separates **test logic** from **test data**.

1.  **Test Logic**: Defined in `test_*.py`. These scripts use `pytest` to find scenario files and call helper functions in `ha_mock.py` to render blueprint variables and assert results.
2.  **Test Data (Scenarios)**: Defined in JSON files within `tests/scenarios/[component]/*.json`. Each scenario file defines:
    - `base_mock`: The baseline state of the system.
    - `example_inputs`: Blueprint configuration to use.
    - `overrides`: Specific sensor states or inputs to change for this test case.
    - `trigger`: The event that triggers the automation.
    - `expected`: The expected results (variables or context states) after rendering.

## Adding a New Test Scenario

To add a new test, creating a JSON file in the appropriate subdirectory of `tests/scenarios/`.

Example scenario (`tests/scenarios/dishwasher/my_new_test.json`):

```json
{
    "base_mock": "tests/mocks/emhass_basic_trigger_mock.json",
    "example_inputs": "examples/blueprints/emhass_basic_trigger_dishwasher.yaml",
    "overrides": {
        "sensor.geschirrspuler_leistung": "500"
    },
    "trigger": {
        "id": "cron",
        "platform": "time_pattern"
    },
    "expected": {
        "context": {
            "action_needed": true,
            "target_status": "running"
        }
    }
}
```

- **Inputs/Overrides**: These are defined in the `overrides` section.
- **Expected Results**: These are defined in the `expected` section and compared in `ha_mock.py:assert_scenario_result`.

## Running Tests

Execute the PowerShell script from the repository root:

```powershell
.\tests\run_tests.ps1
```

This will build a Docker image and run `pytest` inside a container, mapping the current directory to `/app`.
