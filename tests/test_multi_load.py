import pytest
import json
import datetime
from ha_mock import load_blueprint_and_render_variables, load_example_inputs

def test_multi_load_aggregation():
    """
    Integration test checking if the Controller correctly aggregates:
    1. A 'running' load (Wallbox) that has already progressed (ho decreased).
    2. A 'waiting' load (Dishwasher) that just started.
    """
    # 1. Load Base Mock
    with open('tests/mocks/emhass_basic_mock.json', 'r') as f:
        mock_data = json.load(f)

    # Apply base emhass_basic example inputs
    example_inputs = load_example_inputs('examples/blueprints/emhass_basic_blueprint.yaml')
    mock_data["inputs"].update(example_inputs)

    # 2. Setup Scenarios
    # Base Time: 2026-03-14T10:00:00+01:00 (1773046800.0)
    # Step: 15 min (0.25h)
    
    # --- Load 4: Wallbox (Running, 30 min elapsed) ---
    # ss = 30 min ago
    wb_ss = 1773045000.0 
    wb_json = {
        "us": "running",
        "ss": wb_ss,
        "ho": 4.0,   # Initial HO
        "st": 0,
        "et": 96,
        "po": 11000,
        "mp": 0,
        "se": False,
        "si": True,
        "pe": 0,
        "needs_optim": False,
        "emhass_step_value": 15,
        "emhass_step_value_hour": 0.25,
        "emhass_deferrable_count": 1 # To enable recalculation
    }
    
    # --- Load 0: Dishwasher (Wait, just started) ---
    dw_json = {
        "us": "wait",
        "ss": 0,
        "ho": 1.5,
        "st": 12,
        "et": 48,
        "po": 2500,
        "mp": 0,
        "se": False,
        "si": True,
        "pe": 0,
        "needs_optim": True, # Signal that we need an optimization run
        "emhass_step_value": 15,
        "emhass_step_value_hour": 0.25,
        "emhass_deferrable_count": 0
    }

    mock_data["states"]["input_text.wallbox_emhass_json"] = {
        "state": json.dumps(wb_json),
        "attributes": {"friendly_name": "Wallbox"}
    }
    mock_data["states"]["input_text.dishwasher_emhass_json"] = {
        "state": json.dumps(dw_json),
        "attributes": {"friendly_name": "Dishwasher"}
    }
    # Ensure status sensors match
    mock_data["states"]["input_select.wallbox_emhass_status"] = "running"
    mock_data["states"]["input_select.dishwasher_emhass_status"] = "wait"

    # 3. Render Controller
    # The controller should aggregate these values into the 'optim' payload.
    variables = load_blueprint_and_render_variables('blueprints/automation/emhass_basic.yaml', mock_data)
    
    assert "context" in variables
    context_raw = variables["context"]
    context_json = json.loads(context_raw) if isinstance(context_raw, str) else context_raw
    optim_payload = context_json["result"]["optim"]

    # --- Verification ---
    
    # Index 0: Dishwasher
    assert optim_payload["operating_hours_of_each_deferrable_load"][0] == 1.5
    assert optim_payload["start_timesteps_of_each_deferrable_load"][0] == 12
    
    # Index 4: Wallbox
    # It should have 4.0 - (30min/15min * 0.25h) = 4.0 - 0.5 = 3.5 operating hours
    # Wait, the Controller just takes the value from input_text. 
    # In a real HA environment, the Wallbox TRIGGER would have updated the input_text.
    # Here, we provided wb_json as input.
    # To truly test the decouping, we should verify that the Controller doesn't 
    # try to re-calculate wb_json based on index 0 logic.
    assert optim_payload["operating_hours_of_each_deferrable_load"][4] == 4.0
    
    # Check if optimization is triggered
    # The Dishwasher signaled needs_optim=True
    assert context_json["result"]["action_needed"] == True
    assert "optim" in context_json["result"]
