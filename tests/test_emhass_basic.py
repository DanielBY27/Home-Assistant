import pytest
import json
from ha_mock import load_example_inputs, load_blueprint_and_render_variables, HomeAssistantMockEnv

def setup_basic_mock(overrides=None, trigger=None):
    """
    Helper function to load the base emhass_basic configuration
    and apply specific state / trigger overrides for concise testing.
    """
    with open('tests/mocks/emhass_basic_mock.json', 'r') as f:
        mock_data = json.load(f)

    # Apply base emhass_basic example overrides First
    example_inputs = load_example_inputs('examples/blueprints/emhass_basic_blueprint.yaml')
    mock_data["inputs"].update(example_inputs)
    
    # Apply specific state overrides
    if overrides:
        for entity_id, state_val in overrides.items():
            if entity_id not in mock_data["states"] or not isinstance(mock_data["states"][entity_id], dict):
                prev_state = mock_data["states"].get(entity_id, "unknown")
                mock_data["states"][entity_id] = {"state": str(prev_state), "attributes": {}}
                
            if isinstance(state_val, dict):
                if "state" in state_val:
                    mock_data["states"][entity_id]["state"] = state_val["state"]
                if "attributes" in state_val:
                    mock_data["states"][entity_id]["attributes"].update(state_val["attributes"])
            else:
                mock_data["states"][entity_id]["state"] = str(state_val)

    if trigger:
        mock_data["trigger"] = trigger

    return mock_data

@pytest.mark.parametrize("scenario, overrides, trigger, check_type", [
    ("publish_config", None, None, "publish"),
    ("optim_structure", None, None, "optim_base"),
    ("emhass_v017_reset_done", None, None, "done_reset"),
])
def test_emhass_basic_scenarios(scenario, overrides, trigger, check_type):
    """
    Consolidated test function for various emhass_basic scenarios using parametrization.
    """
    mock_data = setup_basic_mock(overrides, trigger)
    variables = load_blueprint_and_render_variables('blueprints/automation/emhass_basic.yaml', mock_data)
    
    assert "context" in variables, f"Context missing in rendered variables for scenario: {scenario}"
    context_raw = variables["context"]
    context_json = json.loads(context_raw) if isinstance(context_raw, str) else context_raw
    
    if check_type == "publish":
        # Validates that the publish payload is correctly constructed
        publish_payload = context_json["result"]["publish"]
        assert publish_payload["force_update_data"] == True
        assert publish_payload["get_data_from_home_assistant"] == True

    elif check_type == "optim_base":
        # Validates the basic structure of the optim payload
        optim_payload = context_json["result"]["optim"]
        assert optim_payload["number_of_deferrable_loads"] == 6
        assert len(optim_payload["nominal_power_of_deferrable_loads"]) == 6
        # Dishwasher (0) and Wallbox (4) are 'done' in mock defaults.
        # Previously they were reset to 0, but now they retain their nominal power.
        assert optim_payload["nominal_power_of_deferrable_loads"][0] == 2500
        assert optim_payload["nominal_power_of_deferrable_loads"][4] == 11000

    elif check_type == "done_reset":
        # Verifies that for 'done' status loads, all technical parameters are reset to 0 (EMHASS v0.17)
        optim_payload = context_json["result"]["optim"]
        
        # Index 0 is Dishwasher (status: 'done' in emhass_basic_mock.json)
        idx = 0
        assert optim_payload["operating_hours_of_each_deferrable_load"][idx] == 0
        assert optim_payload["start_timesteps_of_each_deferrable_load"][idx] == 0
        # assert optim_payload["end_timesteps_of_each_deferrable_load"][idx] == 0 # User intentional change: et is no longer reset to 0
        assert optim_payload["nominal_power_of_deferrable_loads"][idx] == 2500
        assert optim_payload["minimum_power_of_deferrable_loads"][idx] == 0
        assert optim_payload["set_deferrable_startup_penalty"][idx] == 0
        
        # Index 1 is Tumble Dryer (status: 'wait') - should NOT be 0
        idx_wait = 1
        assert optim_payload["nominal_power_of_deferrable_loads"][idx_wait] > 0


@pytest.mark.parametrize("status_code, notify_enabled, expected_notification", [
    (200, True, False),   # EMHASS v0.17.7+ success returns 200 -> no failure notification
    (201, True, False),   # Legacy EMHASS v0.17.6 success returns 201 -> no failure notification
    (400, True, True),    # Bad request / failure -> notification triggered
    (500, True, True),    # Internal server error -> notification triggered
    (200, False, False),  # Notifications disabled -> no notification
    (400, False, False),  # Notifications disabled -> no notification
])
def test_emhass_basic_notification_status_codes(status_code, notify_enabled, expected_notification):
    """
    Verifies that the blueprint notification condition does not trigger on HTTP 200 or 201,
    but does trigger on HTTP errors (400, 500) when notify_enabled is True.
    """
    mock_data = setup_basic_mock()
    env = HomeAssistantMockEnv(mock_data)
    
    context_str = json.dumps({
        "automation": {
            "notify_enabled": notify_enabled,
            "notify_group": "persistent_notification"
        }
    })
    
    template_str = "{{ (context | from_json).automation.notify_enabled | bool and response.status not in [200, 201] }}"
    template = env.env.from_string(template_str)
    result = template.render(context=context_str, response={"status": status_code})
    
    assert (result.strip().lower() == "true") == expected_notification


@pytest.mark.parametrize("now_iso, battery_soc, expected_soc_final", [
    ("2026-10-23T22:00:00+02:00", "20", 0.3),   # Night (20-10h), current < min (0.20 < 0.30) -> 0.3
    ("2026-10-23T08:00:00+02:00", "45", 0.45),  # Night/Morning (20-10h), current > min (0.45 > 0.30) -> 0.45
    ("2026-10-23T12:00:00+02:00", "35", 0.5),   # First half day (10-16h), current < min (0.35 < 0.50) -> 0.5
    ("2026-10-23T14:00:00+02:00", "65", 0.65),  # First half day (10-16h), current > min (0.65 > 0.50) -> 0.65
    ("2026-10-23T18:00:00+02:00", "25", 0.4),   # Second half day (16-20h), current < min (0.25 < 0.40) -> 0.4
    ("2026-10-23T19:00:00+02:00", "55", 0.55),  # Second half day (16-20h), current > min (0.55 > 0.40) -> 0.55
])
def test_emhass_basic_soc_final_calculation(now_iso, battery_soc, expected_soc_final):
    """
    Verifies that emhass_config_soc_final applies the time-based minimum SoC
    (20-10h: 0.3, 10-16h: 0.5, 16-20h: 0.4) and preserves current_soc if higher.
    """
    mock_data = setup_basic_mock(overrides={"sensor.scb_battery_soc": battery_soc})
    mock_data["now"] = now_iso
    variables = load_blueprint_and_render_variables('blueprints/automation/emhass_basic.yaml', mock_data)
    context_raw = variables["context"]
    context_json = json.loads(context_raw) if isinstance(context_raw, str) else context_raw
    optim_payload = context_json["result"]["optim"]
    assert float(optim_payload["soc_final"]) == pytest.approx(expected_soc_final, 0.001)


