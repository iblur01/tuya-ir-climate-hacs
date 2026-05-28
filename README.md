# Tuya IR Climate for Home Assistant

Custom Home Assistant integration for a Tuya universal infrared hub controlling an air conditioner.

This integration uses the Tuya Cloud IR endpoints that were validated in the Python lab:

- status: `GET /v1.0/devices/{remote_id}/status`
- command: `POST /v2.0/infrareds/{infrared_id}/air-conditioners/{remote_id}/command`

The climate entity exposes:

- HVAC modes: Off, Cool, Dry
- Fan modes: Auto, Low, High
- Target temperature: 16°C to 30°C

Important: infrared is one-way. The displayed state is Tuya's cloud shadow for the virtual remote, not a physical reading from the air conditioner. If the original remote control is used, Home Assistant might not know.

## Install

Copy `custom_components/tuya_ir_climate` into Home Assistant's `custom_components` directory, or add this repository to HACS as a custom integration.

Restart Home Assistant, then add **Tuya IR Climate** from Settings > Devices & services.

You need:

- Tuya Cloud Access ID / Client ID
- Tuya Cloud Access Secret / Client Secret
- Tuya region, for example `eu`
- IR hub device ID, for example `bf2b843da25ca8b275uy7a`

The setup wizard discovers the AC remotes attached to the hub and then lets you confirm the mapping values. The defaults match the validated lab device:

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
