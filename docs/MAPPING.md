# Tuya IR Climate Mapping

## IDs

The setup wizard asks for the physical IR hub device ID, then discovers the
virtual AC remotes attached to that hub.

Observed AC category:

- Tuya category: `infrared_ac`
- IR category id: `5`

## Polling

Primary status endpoint:

```text
GET /v1.0/devices/{remote_id}/status
```

Observed payload:

```json
[
  {"code": "power", "value": "0"},
  {"code": "mode", "value": "0"},
  {"code": "temp", "value": "19"},
  {"code": "wind", "value": "1"}
]
```

Alternative batch endpoint:

```text
GET /v1.0/cloud/rc/infrared/ac/status/batch?device_ids={remote_id}
```

## Commands

Command endpoint:

```text
POST /v2.0/infrareds/{infrared_id}/air-conditioners/{remote_id}/command
```

Payload:

```json
{"code": "power", "value": 1}
```

## Home Assistant Mapping

| HA field | HA value | Tuya code | Tuya value |
| -- | -- | -- | -- |
| `hvac_mode` | `off` | `power` | `0` |
| `hvac_mode` | `cool` | `mode`, `power` | `0`, `1` |
| `hvac_mode` | `dry` | `mode`, `wind`, `power` | `4`, `0`, `1` |
| `target_temperature` | `16..30` | `temp` | `16..30` |
| `fan_mode` | `auto` | `wind` | `0` |
| `fan_mode` | `low` | `wind` | `1` |
| `fan_mode` | `high` | `wind` | `3` |

The state is Tuya's virtual remote shadow. It is not physical feedback from the air conditioner.
