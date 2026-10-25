# Task Spec: T65 Portrait Kiosk Dashboard Architecture & Iterative Development

## 1. Context & Goal
Develop, refactor, and deploy a modern, responsive Home Assistant Kiosk Dashboard saved in [dashboards/kiosk.yaml](../../dashboards/kiosk.yaml) and synchronized via `ha_mcp` to the live Home Assistant instance.
The dashboard is designed primarily for a **Teclast T65 tablet** running in Kiosk Mode (portrait / vertical orientation in the hallway), while remaining fully responsive across desktop and mobile screen sizes.

---

## 2. Global Architecture & Design Rules

### 2.1 Display, Responsiveness & Theme Adaptation
- **Screen Adaptation:** Fluid CSS Grid / Flexbox layout (`panel` view mode) optimized for the Teclast T65 display resolution and aspect ratio, automatically scaling to fit without unnecessary scrolling on the main view.
- **Theme Support (Normal, Light, Dark Mode):**
  - Do **not** hardcode dark-only colors (`white`, `rgba(0,0,0,0.3)`).
  - Use Home Assistant CSS theme variables (`var(--primary-text-color)`, `var(--secondary-text-color)`, `var(--card-background-color)`, `var(--ha-card-background)`, `var(--divider-color)`, `var(--primary-color)`) and CSS `@media (prefers-color-scheme: light/dark)` queries so the UI adapts seamlessly to Normal, Light, and Dark device modes.
- **Kiosk Mode:** Hide top Home Assistant header and native left drawer via `kiosk_mode` configuration.
- **Version Footer:** Fixed text element at the **bottom right** displaying the current dashboard version in the format `vYYYYMM` (e.g., `v202610` for Year/Month).

### 2.2 Left Navigation Sidebar (`sidebar_layout`)
Persistent left-hand vertical navigation menu across all views with the following 10 entries and Home Assistant Area mappings:

| # | Menu Label | Navigation Path | Mapped Home Assistant Areas | Icon / Resident Presence Logic |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **Home** | `home` | *Global Overview* | `mdi:home-variant` |
| 2 | **Wohnen** | `wohnzimmer` | `roomLivingRoom`, `Wohnzimmer` | `mdi:sofa` |
| 3 | **Küche** | `kueche` | `Küche` | `mdi:fridge` |
| 4 | **Eltern** | `parents` | `Eltern` | Resident Avatar/Icon (`person.tanja` & `person.daniel`). Highlighted in color when at least one is `home`, plus badge count (`1` or `2`); grayscale/muted when away. |
| 5 | **Stefan** | `stefan` | `Stefan` | Resident Avatar/Icon (`person.stefan`). Highlighted in color when `home`; grayscale/muted when away. |
| 6 | **Simon** | `simon` | `Simon` | Resident Avatar/Icon (`person.simon`). Highlighted in color when `home`; grayscale/muted when away. |
| 7 | **Lukas** | `lukas` | `Lukas` | Resident Avatar/Icon (`person.lukas`). Highlighted in color when `home`; grayscale/muted when away. |
| 8 | **Büro** | `buero` | `Büro` | `mdi:office-chair` |
| 9 | **Garage** | `garage` | `Autos` | `mdi:garage` |
| 10 | **Energie** | `energie` | `Systemsteuerung`, `Technik`, `Vorratsraum`, `Waschhaus` | `mdi:flash` |

### 2.3 Fixed Top Information Bar (Header)
Compact, single-row fixed header bar at the top of the content area using icons to save space:
- **Left / Center Status Badges (`status_chip`):**
  1. **CCU Errors:** `sensor.ccu3_webui_servicemeldungen` (`mdi:alert-circle`) – visible when `> 0`. Tapping opens either a detail overlay or navigates directly to `/homematic-config` (`http://homeassistant.local:8123/homematic-config`).
  2. **Low Battery Alert:** Badge displaying the count of devices with low battery levels (`mdi:battery-alert`) – visible when `> 0`. Tapping opens an overlay listing the affected devices with their percentage values or navigates directly to `/maintenance` (`http://homeassistant.local:8123/maintenance`).
  3. **Waste Collection (Paper):** `sensor.abholung_papier` (`mdi:recycle`) – shows days until pickup.
  4. **Waste Collection (Residual Waste):** `sensor.abholung_restmull` (`mdi:trash-can`) – shows days until pickup.
  5. **Current Tibber Electricity Price:** `sensor.tibber27a_strompreis` (`mdi:flash` / `mdi:currency-eur`) – displays live price with a visual warning animation (pulsing/glowing red) when the price exceeds the expensive threshold.
- **Right Edge:**
  - **Digital Clock:** Current time in `HH:mm` format with compact icon (`mdi:clock-outline`), continuously updating live in the background (via `sensor.time` trigger or live JS interval so it never freezes at dashboard load time).

---

## 3. View Specifications

### 3.1 "Home" View (`path: home`) — Modern Interactive Hub
Structured vertically from top to bottom inside the main panel right of the sidebar:

1. **Top Information Bar:** As specified in Section 2.3.
2. **Camera Section (Asymmetric Split + 80% Modal Overlay):**
   - Displays two live/snapshot camera cards side-by-side:
     - **Entryway (`camera.entryway`):** Displayed larger (e.g., `2fr` or `3fr` width).
     - **Garden (`camera.backyard`):** Displayed smaller (e.g., `1fr` width).
   - **Resilient Live Stream & Auto-Recovery:** Must prevent black screens on initial load or after long Kiosk uptime (e.g., using WebRTC / resilient `picture-entity` / `custom:webrtc-camera` or periodic snapshot/stream keep-alive refresh) so camera feeds update continuously without requiring a manual page refresh.
   - **Overlay Action:** Tapping either camera opens an **80% screen size modal overlay** (`browser_mod.popup`, native `more-info` dialog, or custom full-screen overlay layer) showing the enlarged camera stream with an immediate, prominent **Close (X)** button.
3. **Interactive Energy Flow Hub (Central House + Surrounding Nodes):**
   - **Center Node:** A stylized **House** graphic/card containing a battery icon and the current **PV Battery SoC (%)** in the center.
   - **Surrounding Nodes:** Positioned around the central house:
     - **PV System (Solar):** `sensor.scb_sum_power_of_all_pv_dc_inputs`
     - **Grid (Stromlieferant):** `sensor.scb_home_power_from_grid`
     - **Washing Machine (Waschmaschine):** `input_select.washing_machine_emhass_status` + power sensor
     - **Dishwasher (Geschirrspüler):** `input_select.dishwasher_emhass_status` + power sensor
     - **Tumble Dryer (Wäschetrockner):** `input_select.tumble_dryer_emhass_status` + power sensor
     - **Hot Water (Heißwasser):** `input_select.water_bioler_emhass_status` + power sensor
     - **Wallbox / EV (Auto):** `input_select.wallbox_emhass_status` + `sensor.goe_297534_nrg_11`
   - **Status Highlighting & Animation:** Active/running/charging nodes are highlighted and animated.
   - **Animated Dotted Flow Lines & Live Wattage Labels:**
     - True circular/dotted connection particles (`stroke-linecap: round` with `stroke-dasharray` SVG or discrete animated dots rather than elongated bars) between each surrounding device and the central House/Battery, starting cleanly at the **outer perimeter of the central House circle** (not from the center point) and moving at a calm, readable animation speed.
     - **Color & Direction:**
       - **Positive (Supplying power to House/Battery, e.g., PV production, Battery discharge):** Green/Positive color flowing toward the house.
       - **Negative (Consuming power from House/Battery/Grid, e.g., Washing Machine running, Grid import):** Red/Orange/Blue negative indicator flowing from house to appliance.
     - **Inline Value Labels:** Each connection line displays the live power value in Watts/kW (`+` for generation/supply, `-` for consumption).
   - **Action Overlays with Smart Price Warnings:**
     - Tapping an appliance or the Wallbox opens an **interactive Overlay / Popup** instead of immediately firing an action.
     - The overlay provides detailed status texts, mode selection buttons (e.g., EMHASS `wait`, `force`, or Wallbox `surplus`, `force-6`..`force-16`), and a **dynamic high-price warning banner** if the user attempts to `force` start a device or EV charge while the current Tibber price (`sensor.tibber27a_strompreis`) is in a high/expensive tier.
4. **Energy Forecast Mini-Chart (Tibber & Solcast):**
   - Located directly beneath the Energy Flow Hub.
   - Based on the existing chart in `/dashboard-ubersicht/overview` (Energie-Monitor), adapted to show **unaveraged hourly/30-min values** (no 12h smoothing) with a time window of **max 1 hour into the past (`-1h`) and +24 hours into the future (`+24h`)**, combining:
     - Actual & forecasted Tibber electricity price.
     - Actual & forecasted Solcast PV generation.
5. **Compact Weather Row + 80% Forecast Overlay:**
   - Located at the bottom of the Home view (sized to fit remaining vertical space).
   - Displays current outdoor temperature, condition icon, and compact daily summary.
   - **Overlay Action:** Tapping the weather bar opens an **80% screen size overlay** with detailed hourly/daily weather forecasts and sensor metrics.

### 3.2 Standardized Room Views (`wohnen`, `kueche`, `parents`, `stefan`, `simon`, `lukas`, `buero`, `garage`, `energie`)
- All room views must share an **identical, functional structure and visual layout**:
  - Left column: Persistent `sidebar_layout` with the active room highlighted.
  - Top bar: Identical Fixed Information Bar (Section 2.3) + optional room category pills (Overview, Climate, Lighting, Devices).
  - Main content grid: Standardized sections for **Climate/Heating**, **Lighting**, **Covers/Shutters**, **Media/Devices**, and **Room Sensors** mapped strictly from the assigned Home Assistant Areas:
    - **Wohnen:** `roomLivingRoom`, `Wohnzimmer`
    - **Küche:** `Küche`
    - **Eltern:** `Eltern`
    - **Stefan:** `Stefan`
    - **Simon:** `Simon`
    - **Lukas:** `Lukas`
    - **Büro:** `Büro`
    - **Garage:** `Autos`
    - **Energie:** `Systemsteuerung`, `Technik`, `Vorratsraum`, `Waschhaus`
- Existing dashboards in Home Assistant must be inspected via `ha_mcp` (`ha_config_get_dashboard`, `ha_get_overview`, `ha_search`) to reuse proven entities, cards, and filters.

---

## 4. Workflow & Execution Guidelines for Agents

1. **Discovery & Entity Verification via `ha_mcp`:**
   - Before writing or modifying [dashboards/kiosk.yaml](../../dashboards/kiosk.yaml), query Home Assistant via `ha_mcp` to:
     - Inspect `/dashboard-ubersicht/overview` and existing room dashboards.
     - Verify all entity IDs (`person.*`, `camera.*`, `sensor.*`, `input_select.*`, `climate.*`, `light.*`, `weather.*`).
     - Check installed custom frontend resources (`ha_config_list_dashboard_resources`) such as `button-card`, `card-mod`, `apexcharts-card`, `browser-mod`, or `kiosk-mode` to ensure 100% compatibility and fix why the current `kiosk.yaml` fails to load.
2. **Iterative Implementation:**
   - Build and validate in structured phases (see Sprint Backlog below).
   - Keep [dashboards/kiosk.yaml](../../dashboards/kiosk.yaml) in sync with the live Home Assistant dashboard via `ha_config_set_dashboard`.
3. **Custom Frontend Plugins & HACS Extensions Policy:**
   - If installing an additional HACS/Lovelace plugin significantly improves dashboard rendering performance, stream stability, or substantially reduces YAML/JS code complexity, the agent may proactively recommend it.
   - **Manual Installation by User:** Do **not** install new plugins automatically. Instead, specify the exact plugin name, repository URL, and justification, and wait for the user to install it manually before integrating it into [dashboards/kiosk.yaml](../../dashboards/kiosk.yaml).

---

## 5. Implementation Roadmap & Sprint Backlog

- [x] **Phase 1: Diagnostics & Foundation**
  - [x] Inspect installed Lovelace resources (`ha_config_list_dashboard_resources`) and existing `/dashboard-ubersicht/overview` config via `ha_mcp`.
  - [x] Diagnose why the current [dashboards/kiosk.yaml](../../dashboards/kiosk.yaml) fails to render in Home Assistant.
  - [x] Refactor base CSS / `button_card_templates` for full Light/Dark/Normal theme support and T65 responsive scaling.
  - [x] Implement the Left Navigation Sidebar with live resident presence highlighting (`Eltern`, `Stefan`, `Simon`, `Lukas`), Top Information Header (CCU, Waste, animated Tibber badge, `HH:mm` clock), and bottom-right version tag (`v202610`).
- [x] **Phase 2: Home View — Cameras, Energy Flow Hub & Overlays**
  - [x] Implement asymmetric Entryway (large) & Garden (small) camera row with 80% screen overlay + close button on tap.
  - [x] Build the Central House (with Battery SoC %) + surrounding appliance/PV/Grid/Wallbox nodes with animated dotted flow lines and signed power labels (`+W` / `-W`).
  - [x] Implement tap overlays for appliances and Wallbox including Tibber high-price warnings on `force` actions.
- [x] **Phase 3: Home View — Forecast Chart & Weather Bar**
  - [x] Extract the Energie-Monitor chart from `/dashboard-ubersicht/overview` and adapt it to a compact `-1h` to `+24h` unsmoothed line chart for Tibber price and Solcast PV forecast.
  - [x] Add the compact Weather footer row with an 80% detailed weather overlay on tap.
- [x] **Phase 4: Standardized Room Views**
  - [x] Query all entities per mapped Area (`roomLivingRoom`/`Wohnzimmer`, `Küche`, `Eltern`, `Stefan`, `Simon`, `Lukas`, `Büro`, `Autos`, `Systemsteuerung`/`Technik`/`Vorratsraum`/`Waschhaus`) and existing room dashboards via `ha_mcp`.
  - [x] Generate uniform, functional room views for all 9 room tabs.
- [x] **Phase 5: Deployment & Verification**
  - [x] Deploy [dashboards/kiosk.yaml](../../dashboards/kiosk.yaml) to Home Assistant via `ha_mcp` and verify error-free rendering.
- [x] **Phase 6: Optimierung Home Seite Part 1**
  - [x] **Live Header Clock:** Fix the header clock (`HH:mm`) so it updates continuously in the background (e.g., bound to `sensor.time` / `triggers_update` or a live timer) instead of staying frozen at the initial dashboard startup time.
  - [x] **Camera Stream Stability & Auto-Recovery:** Fix the Entryway and Garden camera cards so they do not stay black on initial dashboard load or turn black after prolonged Kiosk operation without refreshing; ensure reliable live stream / periodic refresh recovery.
  - [x] **Energy Hub Flow Lines (Geometry, Dots & Speed):** Refactor the connection lines between the central House node and the surrounding consumers/sources so they render as true dots (`stroke-linecap: round` / discrete particles) rather than elongated bars, move at a slower and calmer animation speed, and originate cleanly from the **outer edge of the central House circle** rather than from its center.
  - [x] **Low Battery Alert Badge (Header):** Add a conditional status badge in the top alert/header bar showing the number of devices with low battery levels (`> 0`), including either a tap overlay displaying the affected devices and their battery percentages (`%`) or a direct navigation action to `/maintenance` (`http://homeassistant.local:8123/maintenance`).
  - [x] **Homematic Service Alert Action (Header):** Add a tap action to the Homematic CCU error badge (`sensor.ccu3_webui_servicemeldungen`) in the top alert/header bar that opens either a detail overlay or navigates directly to `/homematic-config` (`http://homeassistant.local:8123/homematic-config`).
  - [x] **Evaluate Optional Custom Plugins:** Check whether additional frontend plugins (e.g., for WebRTC camera streaming, battery state aggregation, or simplified energy/popup cards) would significantly improve dashboard performance or reduce YAML/JS code complexity, and propose them to the user for manual installation before use.
