# Tuya IR Climate for Home Assistant

Custom Home Assistant integration for a Tuya universal infrared hub controlling an air conditioner.

This integration uses the Tuya Cloud IR endpoints that were validated in the Python lab:

- status: `GET /v1.0/devices/{remote_id}/status`
- command: `POST /v2.0/infrareds/{infrared_id}/air-conditioners/{remote_id}/command`

The climate entity exposes:

- HVAC modes: Off, Cool, Dry
- Fan modes: Auto, Low, High
- Target temperature: 16°C to 30°C
- Current temperature: read from an external room sensor

Important: infrared is one-way. The displayed state is Tuya's cloud shadow for the virtual remote, not a physical reading from the air conditioner. If the original remote control is used, Home Assistant might not know.

## Smart thermostat regulation

The AC's own thermostat reacts to its badly-placed internal sensor, so it keeps
the compressor running (and noisy) even once the room is already cold. Instead
of blindly mapping the target temperature onto the IR remote, this integration
turns Home Assistant into the thermostat:

- It reads the real room temperature from an **external sensor** (required at
  setup) and exposes it as the entity's current temperature.
- In **Cool** mode it regulates with a hysteresis band around the target:
  - `room ≥ target + delta` → power the unit on in cool mode.
  - `room ≤ target − delta` → cut power entirely (silence) while keeping the
    Cool mode active. `hvac_action` reports `idle` during this window.
- An **anti-short-cycle guard** (`min_cycle_duration`) keeps a minimum delay
  between on/off switches to protect the compressor.

Both `delta` (default `0.5°C`) and `min_cycle_duration` (default `300s`) are
configurable from the integration's options.

> **Breaking change:** a room temperature sensor is now mandatory. Existing
> installs must be reconfigured to select a sensor entity.

## Install

Copy `custom_components/tuya_ir_climate` into Home Assistant's `custom_components` directory, or add this repository to HACS as a custom integration.

Restart Home Assistant, then add **Tuya IR Climate** from Settings > Devices & services.

You need:

- Tuya Cloud Access ID / Client ID
- Tuya Cloud Access Secret / Client Secret
- Tuya region, for example `eu`
- IR hub device ID

The setup wizard discovers the AC remotes attached to the hub and then lets you confirm the mapping values. The defaults match the tested Tuya IR AC profile:

- Cool mode: `0`
- Dry mode: `4`
- Fan auto: `0`
- Fan low: `1`
- Fan high: `3`

## Tested Mapping

| Home Assistant | Tuya IR code | Tuya value |
| -- | -- | -- |
| Off | `power` | `0` |
| Cool | `mode` + `power` | `0` + `1` |
| Dry | `mode` + `power` | `4` + `1` |
| Fan auto | `wind` | `0` |
| Fan low | `wind` | `1` |
| Fan high | `wind` | `3` |
