import pytest
import glob
from ha_mock import load_blueprint_and_render_variables, load_scenario, assert_scenario_result

SCENARIO_PATH = 'tests/scenarios/water_boiler/*.json'
scenarios = glob.glob(SCENARIO_PATH)

@pytest.mark.parametrize("scenario_file", scenarios)
def test_water_boiler_scenarios(scenario_file):
    """Dynamically run all water boiler (EMHASS-controlled interruptible load) scenarios."""
    mock_data, expected = load_scenario(scenario_file)
    variables = load_blueprint_and_render_variables('blueprints/automation/emhass_basic_trigger.yaml', mock_data)

    assert_scenario_result(variables, expected, scenario_file)
