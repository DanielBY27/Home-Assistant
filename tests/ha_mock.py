import yaml
import json
import jinja2
import datetime

class StateObj:
    def __init__(self, data):
        self.state = data.get("state", "unknown")
        self.attributes = data.get("attributes", {})
        # Mocking .context.user_id
        context_data = data.get("context", {})
        self.context = type('obj', (object,), {'user_id': context_data.get('user_id')})
        self.last_changed = data.get("last_changed", "2026-03-14T10:00:00+01:00")
        self.entity_id = data.get("entity_id", "unknown")
    def __str__(self): return self.state

class HomeAssistantMockEnv:
    def __init__(self, mock_data):
        self.mock_data = mock_data

        # Configure Jinja2 environment with custom HA functions
        self.env = jinja2.Environment(
            extensions=['jinja2.ext.loopcontrols', 'jinja2.ext.do'],
            undefined=jinja2.Undefined # Default is strict enough, but let's make it explicit or use a more lenient one
        )
        self.env.globals['now'] = self.mock_now
        self.env.globals['states'] = self.mock_states_func()
        self.env.globals['state_attr'] = self.mock_state_attr
        self.env.globals['is_state'] = self.mock_is_state
        self.env.globals['timedelta'] = datetime.timedelta
        
        # Add basic math filters needed by templates (if any)
        self.env.filters['int'] = self.filter_int
        self.env.filters['float'] = self.filter_float
        self.env.filters['string'] = str
        self.env.filters['lower'] = lambda x: str(x).lower()
        self.env.filters['bool'] = self.filter_bool
        self.env.filters['default'] = self.filter_default
        self.env.filters['min'] = lambda x: min(x)
        self.env.filters['max'] = lambda x: max(x)
        self.env.filters['length'] = len
        self.env.filters['list'] = list
        self.env.filters['regex_findall_index'] = self.filter_regex_findall_index
        
        # Add HA specific filters
        self.env.filters['from_json'] = self.filter_from_json
        self.env.filters['to_json'] = self.filter_to_json
        self.env.filters['as_datetime'] = self.filter_as_datetime
        self.env.filters['as_local'] = self.filter_as_local
        self.env.filters['as_timestamp'] = self.filter_as_timestamp
        self.env.filters['combine'] = self.filter_combine

        # Also map HA functions that can be called globally
        self.env.globals['as_timestamp'] = self.filter_as_timestamp
        self.env.globals['as_datetime'] = self.filter_as_datetime
        self.env.globals['as_local'] = self.filter_as_local

        # For state.person | selectattr ... logic
        self.env.filters['selectattr'] = self.filter_selectattr

        # has_value global
        self.env.globals['has_value'] = self.mock_has_value

    def mock_now(self):
        return datetime.datetime.fromisoformat(self.mock_data["now"])

    def mock_states_func(self):
        class StatesDict(dict):
            def __getitem__(self, key):
                if key in self:
                    return super().__getitem__(key)
                return StateObj({"entity_id": str(key), "state": "unknown"})

            def __call__(self, entity_id):
                return str(self[entity_id].state)
            
            def __getattr__(self, name):
                # Simulates states.domain access, e.g., states.person
                parts = name.split(".")
                if len(parts) == 1:
                    domain = parts[0]
                    # return list of entity state objects for that domain
                    entities = []
                    for k, v in self.items():
                        if k.startswith(f"{domain}."):
                            entities.append(v)
                    return entities
                # Handle cases like states.light.kitchen
                return self.get(name, StateObj({"entity_id": name, "state": "unknown"}))

        states = StatesDict()
        for k, v in self.mock_data.get("states", {}).items():
            if isinstance(v, dict):
                states[k] = StateObj({"entity_id": k, **v})
            else:
                states[k] = StateObj({"entity_id": k, "state": v})
        
        return states

    def mock_state_attr(self, entity_id, attr_name):
        state = self.mock_data.get("states", {}).get(entity_id, {})
        if isinstance(state, dict):
            return state.get("attributes", {}).get(attr_name, None)
        return None
    
    def mock_is_state(self, entity_id, state_val):
        curr = self.mock_states_func()(entity_id)
        return str(curr) == str(state_val)

    def mock_has_value(self, entity_id):
        val = self.mock_states_func()(entity_id)
        return val not in ("unknown", "unavailable", None, "")

    def mock_timestamp_now(self):
        return self.mock_now().timestamp()
    
    # --- Filters ---
    def filter_int(self, value, default=0):
        if isinstance(value, jinja2.Undefined): return default
        try:
            return int(float(value)) if value else default
        except (ValueError, TypeError):
            return default

    def filter_float(self, value, default=0.0):
        if isinstance(value, jinja2.Undefined): return default
        try:
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            return default
    
    def filter_bool(self, value, default=False):
        if isinstance(value, jinja2.Undefined): return default
        if str(value).lower() in ("true", "1", "yes", "on"):
            return True
        if str(value).lower() in ("false", "0", "no", "off", "none"):
            return False
        return bool(value)

    def filter_default(self, value, default_val, boolean=False):
        if boolean:
            if not value:
                return default_val
        if value is None or (isinstance(value, jinja2.Undefined)) or value == "":
            return default_val
        return value

    def filter_from_json(self, value, default=None):
        if isinstance(value, (dict, list)):
            return self._wrap_json(value)
        if value is None or isinstance(value, jinja2.Undefined) or str(value).strip() == "":
            return self._wrap_json(default or {})
        try:
            val_str = str(value)
            if not isinstance(val_str, str):
                return self._wrap_json(value)
            return self._wrap_json(json.loads(val_str))
        except (json.JSONDecodeError, ValueError):
            return self._wrap_json(default or {})

    def _wrap_json(self, data):
        """Wraps dicts in a proxy that returns Undefined for missing keys, like HA."""
        if isinstance(data, dict):
            class SafeDict(dict):
                def __getitem__(self, key):
                    if key in self:
                        val = super().__getitem__(key)
                        if isinstance(val, (dict, list)):
                             return SafeDict(val) if isinstance(val, dict) else [SafeDict(x) if isinstance(x, dict) else x for x in val]
                        return val
                    return jinja2.Undefined(name=key)
                def get(self, key, default=None):
                    val = super().get(key, default)
                    if isinstance(val, (dict, list)):
                        return SafeDict(val) if isinstance(val, dict) else [SafeDict(x) if isinstance(x, dict) else x for x in val]
                    return val
            return SafeDict(data)
        elif isinstance(data, list):
            return [self._wrap_json(x) for x in data]
        return data

    def filter_to_json(self, value):
        try:
            return json.dumps(value, separators=(',', ':'))
        except TypeError as e:
            raise TypeError(f"Serialization failed for: {value}. Original error: {e}") from e

    def filter_as_datetime(self, value):
        if value is None or isinstance(value, jinja2.Undefined):
            return None
        if isinstance(value, datetime.datetime):
            return value
        if not value or str(value).strip() == "":
            return None
        try:
            val_str = str(value).replace("Z", "+00:00")
            # Handle standard ISO formats
            return datetime.datetime.fromisoformat(val_str)
        except ValueError:
            # Try some common date formats if isoformat fails
            for fmt in ("%Y-%m-%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.datetime.strptime(val_str, fmt)
                except ValueError:
                    continue
            return None

    def filter_as_local(self, value):
        if value is None or isinstance(value, datetime.datetime) is False:
            return value
        return value # Mocking as local (could add TZ logic if needed)

    def filter_as_timestamp(self, value):
        if value is None or isinstance(value, jinja2.Undefined):
            return 0
        if isinstance(value, (int, float)):
            return float(value)
        dt = self.filter_as_datetime(value)
        if dt:
            return dt.timestamp()
        return 0

    def filter_combine(self, dict1, dict2):
        if not isinstance(dict1, dict): dict1 = {}
        if not isinstance(dict2, dict): dict2 = {}
        res = dict1.copy()
        res.update(dict2)
        return res
    
    def filter_selectattr(self, context, attribute_path, operator, test_value):
        if not isinstance(context, list):
            return context
        
        result = []
        parts = attribute_path.split('.')
        
        for item in context:
            val = item
            try:
                for part in parts:
                    if isinstance(val, dict):
                        val = val.get(part)
                    else:
                        val = getattr(val, part)
            except Exception:
                val = None
                
            if operator == 'eq':
                if val == test_value:
                    result.append(item)
            elif operator == 'ne':
                 if val != test_value:
                    result.append(item)
        return result

    def filter_regex_findall_index(self, value, pattern, index=0):
        import re
        matches = re.findall(pattern, str(value))
        try:
            return matches[index]
        except (IndexError, TypeError):
            return ""

def load_example_inputs(example_path):
    with open(example_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data.get('use_blueprint', {}).get('input', {})

def load_blueprint_and_render_variables(blueprint_path, mock_data):
    class SafeLoaderIgnoreUnknown(yaml.SafeLoader):
        pass
    def construct_input(loader, node):
        return {"!input": loader.construct_scalar(node)}
    SafeLoaderIgnoreUnknown.add_constructor('!input', construct_input)

    with open(blueprint_path, 'r', encoding='utf-8') as f:
        blueprint_data = yaml.load(f, Loader=SafeLoaderIgnoreUnknown)

    # Extract defaults from blueprint inputs (recursively find all inputs)
    def extract_inputs(input_schema):
        inputs = {}
        for k, v in input_schema.items():
            if isinstance(v, dict):
                if "default" in v:
                    inputs[k] = v["default"]
                elif "input" in v and isinstance(v["input"], dict):
                    # Recurse into nested inputs
                    inputs.update(extract_inputs(v["input"]))
                elif "selector" in v:
                    # It's an input without a default
                    inputs[k] = ""
        return inputs

    blueprint_inputs_schema = blueprint_data.get("blueprint", {}).get("input", {})
    input_defaults = extract_inputs(blueprint_inputs_schema)

    env_wrapper = HomeAssistantMockEnv(mock_data)
    env = env_wrapper.env
    
    # Pre-render inputs if they are templates, merging provided inputs with defaults
    all_inputs = {**input_defaults, **mock_data.get("inputs", {})}
    rendered_inputs = {}
    for k, v in all_inputs.items():
        if isinstance(v, str) and ("{{" in v or "{%" in v):
            try:
                template = env.from_string(v)
                rendered_inputs[k] = template.render()
            except Exception:
                rendered_inputs[k] = v
        else:
            rendered_inputs[k] = v

    # Separate top-level variables and action variables
    top_level_vars = blueprint_data.get('variables', {})
    actions_block = blueprint_data.get('actions', [])

    # 1. Resolve top-level variables
    resolved_vars = {}
    context_vars = {
        "trigger": mock_data.get("trigger", {}),
        "this": {"entity_id": "automation.test_automation"}
    }
    
    # helper to render a value
    def render_val(name, val, current_vars):
        if isinstance(val, dict) and "!input" in val:
            input_name = val["!input"]
            return rendered_inputs.get(input_name, "")
        elif isinstance(val, str) and ("{{" in val or "{%" in val):
            eval_context = {**context_vars, **rendered_inputs, **current_vars}
            template = env.from_string(val)
            rendered = template.render(**eval_context)
            
            # Auto-parse JSON if it looks like a dict/list
            if isinstance(rendered, str) and rendered.strip().startswith(("{", "[")):
                try:
                    # Replace single quotes with double quotes for JSON parsing if needed, 
                    # though Jinja's to_json usually produces valid JSON.
                    parsed = json.loads(rendered.replace("'", '"')) if "'" in rendered and '"' not in rendered else json.loads(rendered)
                    return parsed
                except (ValueError, TypeError):
                    pass
            
            if isinstance(rendered, (dict, list)):
                return rendered
            return rendered
        else:
            return val

    for var_name, var_val in top_level_vars.items():
        resolved_vars[var_name] = render_val(var_name, var_val, resolved_vars)

    # 2. Evaluate conditions
    conditions_block = blueprint_data.get('conditions', [])
    for cond in conditions_block:
        if isinstance(cond, dict) and cond.get('condition') == 'template':
            template_str = cond.get('value_template', '')
            if template_str:
                eval_context = {**context_vars, **rendered_inputs, **resolved_vars}
                template = env.from_string(template_str)
                if not env_wrapper.filter_bool(template.render(**eval_context)):
                    # If a condition fails, we return the top level variables but mark actions as blocked
                    return {**resolved_vars, "actions_blocked_by_condition": True, "context": json.dumps({"result": {"action_needed": False}})}

    # 3. Resolve action variables if conditions passed
    for action in actions_block:
        if isinstance(action, dict) and 'variables' in action:
            for var_name, var_val in action['variables'].items():
                resolved_vars[var_name] = render_val(var_name, var_val, resolved_vars)

    return resolved_vars

def load_mock_data(mock_path):
    with open(mock_path, 'r') as f:
        return json.load(f)

def load_scenario(scenario_path):
    """
    Loads a scenario from a JSON file.
    A scenario file should contain:
    - base_mock: path to the base mock file (e.g. 'tests/mocks/emhass_basic_trigger_mock.json')
    - example_inputs: path to example inputs (e.g. 'examples/blueprints/emhass_basic_trigger_dishwasher.yaml')
    - overrides: dictionary of entity state / input overrides
    - trigger: dictionary for the trigger object
    - expected: dictionary of expected results in variables / context
    """
    with open(scenario_path, 'r') as f:
        scenario = json.load(f)
    
    # 1. Load base mock
    mock_data = load_mock_data(scenario.get("base_mock", "tests/mocks/emhass_basic_trigger_mock.json"))
    
    # 2. Apply blueprint example inputs if provided
    if "example_inputs" in scenario:
        example_inputs = load_example_inputs(scenario["example_inputs"])
        mock_data["inputs"].update(example_inputs)
        
    # 3. Apply specific overrides
    if "overrides" in scenario:
        overrides = scenario["overrides"]
        for entity_id, state_val in overrides.items():
            if entity_id in mock_data.get("inputs", {}):
                mock_data["inputs"][entity_id] = state_val
            else:
                if entity_id not in mock_data["states"]:
                    mock_data["states"][entity_id] = {"attributes": {}}
                    
                if isinstance(state_val, dict):
                    if "state" in state_val:
                        mock_data["states"][entity_id]["state"] = state_val["state"]
                    if "attributes" in state_val:
                        mock_data["states"][entity_id]["attributes"].update(state_val["attributes"])
                    if "context" in state_val:
                        mock_data["states"][entity_id]["context"] = state_val["context"]
                    if "last_changed" in state_val:
                        mock_data["states"][entity_id]["last_changed"] = state_val["last_changed"]
                else:
                    mock_data["states"][entity_id]["state"] = str(state_val)

    # 4. Apply trigger
    if "trigger" in scenario:
        mock_data["trigger"] = scenario["trigger"]

    # 5. Apply time override
    if "now" in scenario:
        if isinstance(scenario["now"], int):
            mock_data["now"] = datetime.datetime.fromtimestamp(scenario["now"], tz=datetime.timezone.utc).isoformat()
        else:
            mock_data["now"] = scenario["now"]

    return mock_data, scenario.get("expected", {})

def assert_scenario_result(variables, expected):
    """Standardized assertion for scenario results."""
    def to_dict(val):
        if isinstance(val, dict): return val
        if isinstance(val, str):
            try: return json.loads(val.replace("'", '"')) if "'" in val and '"' not in val else json.loads(val)
            except: pass
        return val

    # Check variables directly
    for key, expected_val in expected.get("variables", {}).items():
        actual_val = variables.get(key)
        
        expected_json = to_dict(expected_val)
        actual_json = to_dict(actual_val)

        if isinstance(expected_json, dict) and isinstance(actual_json, dict):
            for k, v in expected_json.items():
                assert actual_json.get(k) == v, f"Variable '{key}'['{k}'] (JSON) mismatch. Expected {v}, got {actual_json.get(k)}"
        else:
            assert actual_val == expected_val, f"Variable '{key}' mismatch. Expected {expected_val}, got {actual_val}"

    # Check result context if present
    if "context" in expected:
        # Resolve 'context' from variables (it might be a JSON string or a dict)
        actual_context_raw = variables.get("context", "{}")
        actual_context = to_dict(actual_context_raw)
        
        # In our blueprints, the actual result is usually under a 'result' key in the context JSON
        actual_result = actual_context.get("result", actual_context) if isinstance(actual_context, dict) else {}
        expected_context = expected["context"]
        
        # Helper for recursive dict comparison
        def assert_dict_match(actual, expected, path=""):
            for k, v in expected.items():
                curr_path = f"{path}.{k}" if path else k
                if isinstance(v, dict):
                    assert_dict_match(actual.get(k, {}), v, curr_path)
                else:
                    assert actual.get(k) == v, f"Result match failed at {curr_path}. Expected {v}, got {actual.get(k)}"
        
        assert_dict_match(actual_result, expected_context)
