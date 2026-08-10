# Module: Dashboards & Frontend

This module contains the YAML definitions for our Home Assistant Lovelace Dashboards. Storing dashboards here ensures version control and consistency across different devices (Tablets, Phones, PCs).

## Module Overview

The dashboards are configured to support both detailed administration and simplified touch-friendly kiosk control:
* **[kiosk.yaml](./kiosk.yaml)**: Designed specifically for the **T65 Tablet** in the entryway, running in kiosk mode (removes headers and sidebar). It consolidates all primary home controls in a responsive layout that scales down to mobile phones and up to computers.
* **[uebersicht.yaml](./uebersicht.yaml)**: A general overview dashboard providing system monitoring and troubleshooting views.

---

## File Structure & Dependencies

All files in this module are located in [dashboards/](./).

### Frontend Dependencies (HACS Extensions)
To render these dashboards correctly, ensure the following custom cards are installed via the Home Assistant Community Store (HACS):
* `kiosk-mode`: Hides headers/sidebar for tablet displays.
* `button-card`: Used for highly customizable, dynamic grid actions.
* `apexcharts-card`: Renders energy production and consumption graphs.
* `card-mod`: Used to inject custom CSS styles directly into dashboard cards.

---

## Configuration & Specific Rules

1. **Responsiveness**: Dashboards utilize a responsive grid layout. We utilize approximately 90% of the total available screen width to prevent unnecessary clipping on different aspect ratios.
2. **Kiosk Optimizations**:
   - The camera views (`camera.entryway` and `camera.backyard`) are formatted to prevent black bars by using proper scaling and state templates (`input_boolean.large_garden_camera` to swap view sizes).
   - Dynamic colors are used to indicate state: Green for running/active, yellow for wait (startable), and hidden when done.
3. **Manual Control**:
   - Cards interact directly with status select entities (e.g. `input_select.dishwasher_emhass_status`) to allow "Force Start" overrides directly from the touch interface.

---

## Maintenance & Expansion

* **Adding a New Room / View**:
  - Add the room to the left-hand navigation menu in `kiosk.yaml`.
  - Maintain the design language: Keep elements modern, clean, and use dynamic icons and CSS borders indicating presence.
* **Modifying Layouts**:
  - When changing sensor sources, verify the corresponding entity IDs match the naming standards in [CODING_STANDARDS.md](../CODING_STANDARDS.md).
