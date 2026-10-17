#!/usr/bin/env python3
"""
Home Assistant Deep Health & Ghost Entity Inspector
Scans registries, YAML configurations, Lovelace dashboards, helpers,
and the SQLite database for dead entities, broken references, unused sensors,
and database bloaters not covered by HA Datenbank Purge.
"""

import json
import glob
import re
import os
import sys

def main():
    config_dir = '/homeassistant'
    storage_dir = os.path.join(config_dir, '.storage')

    report = {
        "broken_automations": [],
        "broken_dashboards": [],
        "dead_registry_entities": [],
        "unused_custom_sensors": [],
        "template_issues": [],
        "deprecated_configs": [],
        "database_purge_sync": {},
        "database_bloat_uncovered": [],
        "database_top_contributors": []
    }

    # 1. Load Entity Registry
    ent_reg_path = os.path.join(storage_dir, 'core.entity_registry')
    entities = {}
    if os.path.exists(ent_reg_path):
        with open(ent_reg_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for e in data.get('data', {}).get('entities', []):
                entities[e['entity_id']] = e

    # 2. Load Restore State
    restore_entities = {}
    rst_path = os.path.join(storage_dir, 'core.restore_state')
    if os.path.exists(rst_path):
        with open(rst_path, 'r', encoding='utf-8') as f:
            rst = json.load(f)
            for item in rst.get('data', []):
                st = item.get('state', {})
                eid = st.get('entity_id')
                if eid:
                    restore_entities[eid] = st

    # 3. Known built-ins and dynamic entities
    builtin_entities = {
        "sun.sun",
        "zone.home"
    }
    dynamic_entities = {f"sensor.p_deferrable{i}" for i in range(10)} | {
        "sensor.p_load_forecast",
        "sensor.p_pv_forecast",
        "sensor.cost_fun_profit"
    }

    known_entity_ids = set(entities.keys()) | set(restore_entities.keys()) | builtin_entities | dynamic_entities

    # Common HA action/service strings that look like entity_ids
    service_actions = {
        'homeassistant.turn_on', 'homeassistant.turn_off', 'homeassistant.toggle',
        'homeassistant.reload_all', 'homeassistant.update_entity',
        'number.set_value', 'select.select_option', 'switch.turn_on', 'switch.turn_off',
        'light.turn_on', 'light.turn_off', 'climate.set_temperature',
        'climate.set_hvac_mode', 'cover.open_cover', 'cover.close_cover',
        'cover.set_cover_position', 'system_log.write', 'tts.speak',
        'tts.google_translate_de_de', 'input_boolean.turn_on', 'input_boolean.turn_off',
        'input_boolean.toggle', 'input_select.select_option', 'input_text.set_value'
    }

    # 4. Scan Automations & Scripts
    yaml_files = glob.glob(os.path.join(config_dir, '*.yaml'))
    
    # Check for deprecated config in configuration.yaml
    config_yaml_path = os.path.join(config_dir, 'configuration.yaml')
    if os.path.exists(config_yaml_path):
        with open(config_yaml_path, 'r', encoding='utf-8') as f:
            cfg_text = f.read()
            if 'platform: waste_collection_schedule' in cfg_text:
                report["deprecated_configs"].append({
                    "file": "configuration.yaml",
                    "issue": "waste_collection_schedule configured under 'sensor: - platform: waste_collection_schedule' is deprecated. Move under 'sensors:' key of 'waste_collection_schedule:'"
                })

    # Check custom_template.yaml for template issues (e.g. float(unavailable))
    custom_template_path = os.path.join(config_dir, 'custom_template.yaml')
    if os.path.exists(custom_template_path):
        with open(custom_template_path, 'r', encoding='utf-8') as f:
            tpl_text = f.read()
            if 'float(unavailable)' in tpl_text:
                report["template_issues"].append({
                    "file": "custom_template.yaml",
                    "issue": "float(unavailable) uses unquoted 'unavailable' variable which evaluates to undefined. Use float('unavailable') or a default like float(0)"
                })

    # Helper function to extract entity_ids from text
    def extract_entity_ids(text):
        tpl_matches = re.findall(r"(?:states|is_state|state_attr|is_state_attr)\s*\(\s*['\"]([a-z_]+)\.([a-z0-9_]+)['\"]", text)
        res = {f"{dom}.{obj}" for dom, obj in tpl_matches}

        lines = text.splitlines()
        in_globs = False
        for line in lines:
            line_str = line.strip()
            if 'entity_globs:' in line_str:
                in_globs = True
                continue
            if in_globs:
                if line_str.startswith('-') and not line_str.startswith('- id:'):
                    continue
                else:
                    in_globs = False

            m = re.findall(r'(?:entity_id|media_player_entity_id|target_sensor|source_sensor|wait_sensor|stop_sensor):\s*([a-z_]+)\.([a-z0-9_]+)', line_str)
            for dom, obj in m:
                res.add(f"{dom}.{obj}")

            if line_str.startswith('-') and '.' in line_str:
                m_list = re.findall(r'^-\s+([a-z_]+)\.([a-z0-9_]+)$', line_str)
                for dom, obj in m_list:
                    res.add(f"{dom}.{obj}")
        return res

    # Scan automations.yaml
    automations_path = os.path.join(config_dir, 'automations.yaml')
    if os.path.exists(automations_path):
        with open(automations_path, 'r', encoding='utf-8') as f:
            auto_text = f.read()
            auto_blocks = auto_text.split('- id:')
            for block in auto_blocks:
                if not block.strip():
                    continue
                alias_match = re.search(r'alias:\s*(.+)', block)
                alias = alias_match.group(1).strip().strip("'\"") if alias_match else "Unknown Automation"
                id_match = re.search(r'^\s*[\'"]?([0-9a-zA-Z_]+)[\'"]?', block)
                auto_id = id_match.group(1) if id_match else "unknown"

                found = extract_entity_ids(block)
                for eid in found:
                    if eid in service_actions or eid.endswith('_'):
                        continue
                    if eid not in known_entity_ids:
                        report["broken_automations"].append({
                            "automation_id": auto_id,
                            "alias": alias,
                            "missing_entity": eid
                        })

    # 5. Scan Lovelace Dashboards
    dashboard_files = glob.glob(os.path.join(storage_dir, 'lovelace.*'))
    for db in dashboard_files:
        db_name = os.path.basename(db).replace('lovelace.', '')
        try:
            with open(db, 'r', encoding='utf-8') as f:
                db_text = f.read()
                matches = re.findall(r'\b([a-z_]+)\.([a-z0-9_]+)\b', db_text)
                db_entities = {f"{d}.{o}" for d, o in matches}
                for eid in sorted(db_entities):
                    if eid in service_actions or eid.endswith('_') or eid.startswith('zone.'):
                        continue
                    if eid.split('.')[0] in {'sensor', 'binary_sensor', 'switch', 'light', 'climate', 'media_player', 'camera', 'cover', 'button', 'number', 'select', 'input_boolean', 'input_select', 'input_text', 'input_number', 'weather', 'update'}:
                        if eid not in known_entity_ids:
                            report["broken_dashboards"].append({
                                "dashboard": db_name,
                                "missing_entity": eid
                            })
        except Exception:
            pass

    # 6. Check All Configs & Storage for Unused Custom Sensors / Helpers
    full_search_text = ""
    for yf in yaml_files:
        try:
            with open(yf, 'r', encoding='utf-8') as f:
                full_search_text += "\n" + f.read()
        except:
            pass

    for db in dashboard_files:
        try:
            with open(db, 'r', encoding='utf-8') as f:
                full_search_text += "\n" + f.read()
        except:
            pass

    cfg_entries_path = os.path.join(storage_dir, 'core.config_entries')
    if os.path.exists(cfg_entries_path):
        try:
            with open(cfg_entries_path, 'r', encoding='utf-8') as f:
                full_search_text += "\n" + f.read()
        except:
            pass

    custom_yaml_sensors = [
        "sensor.weichwassernutzung_gruenbeck_template",
        "sensor.total_water_usage",
        "sensor.family_group_count_present",
        "sensor.tibber_rohdaten_cache"
    ]
    modbus_sensors = [
        "sensor.kostal_load_from_gid_modbus"
    ]

    all_custom = custom_yaml_sensors + modbus_sensors
    for ce in all_custom:
        count = len(re.findall(re.escape(ce), full_search_text))
        obj_id = ce.split('.')[1]
        count_obj = len(re.findall(re.escape(obj_id), full_search_text))
        if count <= 1 and count_obj <= 1:
            report["unused_custom_sensors"].append({
                "entity_id": ce,
                "references_count": count
            })

    # 7. Check Person device_trackers
    person_path = os.path.join(storage_dir, 'person')
    if os.path.exists(person_path):
        try:
            with open(person_path, 'r', encoding='utf-8') as f:
                p_data = json.load(f)
                for item in p_data.get('data', {}).get('items', []):
                    p_name = item.get('name', item.get('id'))
                    for dt in item.get('device_trackers', []):
                        ent = entities.get(dt)
                        if not ent:
                            report["broken_automations"].append({
                                "automation_id": f"person.{item.get('id')}",
                                "alias": f"Person ({p_name})",
                                "missing_entity": f"{dt} (assigned device_tracker not found in registry)"
                            })
                        elif ent.get('disabled_by'):
                            report["template_issues"].append({
                                "file": f"person.{item.get('id')}",
                                "issue": f"Person '{p_name}' tracks disabled entity '{dt}' (disabled by: {ent.get('disabled_by')})"
                            })
        except Exception:
            pass

    # 8. Database Bloat & Purge Audit
    db_path = os.path.join(config_dir, "home-assistant_v2.db")
    if os.path.exists(db_path):
        try:
            import sqlite3
            import fnmatch
            import base64
            import yaml

            # Connect read-only to avoid locking
            con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cur = con.cursor()
            query = """
            SELECT COUNT(s.state_id) AS cnt, sm.entity_id
            FROM states s
            JOIN states_meta sm ON s.metadata_id = sm.metadata_id
            GROUP BY sm.entity_id
            ORDER BY cnt DESC
            LIMIT 40;
            """
            cur.execute(query)
            top_rows = cur.fetchall()
            con.close()

            # Load HA Datenbank Purge automation from automations.yaml
            live_purge_auto = None
            if os.path.exists(automations_path):
                with open(automations_path, "r", encoding="utf-8") as f:
                    ha_autos = yaml.safe_load(f)
                    if isinstance(ha_autos, list):
                        for a in ha_autos:
                            if a.get("alias") == "HA Datenbank Purge":
                                live_purge_auto = a
                                break

            # Compare with local Git automation if provided via LOCAL_PURGE_B64
            local_auto = None
            local_purge_b64 = os.environ.get("LOCAL_PURGE_B64", "").strip()
            if local_purge_b64:
                try:
                    local_raw = base64.b64decode(local_purge_b64).decode("utf-8")
                    local_auto = yaml.safe_load(local_raw)

                    if not live_purge_auto:
                        report["database_purge_sync"] = {
                            "status": "missing_in_ha",
                            "message": "Automation 'HA Datenbank Purge' not found in live automations.yaml"
                        }
                    else:
                        diffs = []
                        for field in ["triggers", "conditions", "actions", "mode"]:
                            if local_auto.get(field) != live_purge_auto.get(field):
                                diffs.append(field)
                        if not diffs:
                            report["database_purge_sync"] = {
                                "status": "in_sync",
                                "automation_id": live_purge_auto.get("id"),
                                "alias": live_purge_auto.get("alias")
                            }
                        else:
                            report["database_purge_sync"] = {
                                "status": "mismatch",
                                "automation_id": live_purge_auto.get("id"),
                                "differing_fields": diffs
                            }
                except Exception as e:
                    report["database_purge_sync"] = {
                        "status": "error",
                        "error": str(e)
                    }

            # Extract purge rules from live automation (or fallback to local)
            target_auto = live_purge_auto or local_auto
            purged_domains = set()
            purged_entities = set()
            purged_globs = set()

            if target_auto:
                for act in target_auto.get("actions", []):
                    if act.get("action") == "recorder.purge_entities":
                        d = act.get("data", {})
                        for dom in d.get("domains", []):
                            purged_domains.add(dom)
                        for ent in d.get("entity_id", []):
                            purged_entities.add(ent)
                        for glb in d.get("entity_globs", []):
                            purged_globs.add(glb)

            # Protected EMHASS sensors (must keep >= 60 days for mlforecaster)
            protected_emhass_sensors = {
                "sensor.scb_solar_power",
                "sensor.emhass_config_home_power_no_var_loads"
            }

            for cnt, eid in top_rows:
                est_mb = round((cnt * 256.0) / 1024.0 / 1024.0, 2)
                domain = eid.split(".")[0] if "." in eid else ""

                if eid in protected_emhass_sensors:
                    status = "protected_emhass"
                elif domain in purged_domains:
                    status = "purged_by_domain"
                elif eid in purged_entities:
                    status = "purged_by_entity_id"
                elif any(fnmatch.fnmatch(eid, pat) for pat in purged_globs):
                    status = "purged_by_glob"
                else:
                    status = "uncovered_bloat"
                    # Smart recommendation: domain vs glob vs entity
                    if domain in {"image", "camera"}:
                        rec = f"Add domain '{domain}' to domains list in HA Datenbank Purge"
                    else:
                        tokens = eid.split(".")[1].split("_")
                        if len(tokens) >= 3:
                            rec_glob = f"{domain}.{'_'.join(tokens[:3])}_*"
                        elif len(tokens) >= 2:
                            rec_glob = f"{domain}.{'_'.join(tokens[:2])}_*"
                        else:
                            rec_glob = f"{domain}.{tokens[0]}_*"
                        rec = f"Add to entity_globs: '{rec_glob}'"

                    report["database_bloat_uncovered"].append({
                        "entity_id": eid,
                        "state_count": cnt,
                        "estimated_mb": est_mb,
                        "recommendation": rec
                    })

                report["database_top_contributors"].append({
                    "entity_id": eid,
                    "state_count": cnt,
                    "estimated_mb": est_mb,
                    "status": status
                })

        except Exception as e:
            report["database_purge_sync"] = {
                "status": "error_inspecting_database",
                "error": str(e)
            }

    # Print Report in clean JSON format
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
