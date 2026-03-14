import pytest
import glob
import os
from ha_mock import load_blueprint_and_render_variables, load_scenario, assert_scenario_result

SCENARIO_PATH = 'tests/scenarios/dishwasher/*.json'
scenarios = glob.glob(SCENARIO_PATH)

@pytest.mark.parametrize("scenario_file", scenarios)
def test_dishwasher_scenarios(scenario_file):
    """Dynamically run all dishwasher scenarios."""
    mock_data, expected = load_scenario(scenario_file)
    variables = load_blueprint_and_render_variables('blueprints/automation/emhass_basic_trigger.yaml', mock_data)
    
    assert_scenario_result(variables, expected)

# Keeping specific tests for complex checks if needed, but they should also use load_scenario
def test_dishwasher_initial_snapshot():
    """Specific check for snapshot loading."""
    mock_data, expected = load_scenario('tests/scenarios/dishwasher/wait_snapshot.json')
    variables = load_blueprint_and_render_variables('blueprints/automation/emhass_basic_trigger.yaml', mock_data)
    
    assert_scenario_result(variables, expected)
