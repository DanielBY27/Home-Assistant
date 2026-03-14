import pytest
import glob
import os
from ha_mock import load_blueprint_and_render_variables, load_scenario, assert_scenario_result

SCENARIO_PATH = 'tests/scenarios/go_echarger/*.json'
scenarios = glob.glob(SCENARIO_PATH)

@pytest.mark.parametrize("scenario_file", scenarios)
def test_goe_scenarios(scenario_file):
    """Dynamically run all go-eCharger scenarios."""
    mock_data, expected = load_scenario(scenario_file)
    variables = load_blueprint_and_render_variables('blueprints/automation/emhass_basic_trigger_go_echarger.yaml', mock_data)
    
    assert_scenario_result(variables, expected)
