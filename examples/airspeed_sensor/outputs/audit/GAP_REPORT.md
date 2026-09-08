# DO-178C DAL A Prototype Gap & Defensive Audit Report
**Target System:** `Pitot_Static_Airspeed_Transducer` (ARM_Cortex_M4)
**Audited Code:** `examples\airspeed_sensor\inputs\airspeed_sensor.c`
**Default Hardware Timeout:** `300.0 µs`

## Executive Summary

| Severity | Count | DO-178C Status |
| :--- | :--- | :--- |
| **CRITICAL** | 2 | Non-Compliant (Certification Blocker) |
| **HIGH** | 2 | Action Required |
| **MEDIUM** | 2 | Review Recommended |
| **LOW** | 0 | Informational |
| **TOTAL** | **6** | |

---

## Detailed Audit Findings (DO-178C Table A-5 Compliance)

### `GAP-0001`: UNBOUNDED_HARDWARE_POLL [⛔ CRITICAL]
- **Function:** `airspeed_read_knots`
- **Location:** `examples\airspeed_sensor\inputs\airspeed_sensor.c:18`
- **DO-178C Objective:** Table A-5 Obj 3 (Verifiable Code: Absence of Unbounded Execution)
- **Problem:** Unbounded hardware polling loop detected on condition '(!(AIRSPEED_STATUS_REG & AIRSPEED_READY_BIT))'. Missing iteration limit or timeout watchdog counter.

```c
// Offending code at line 18:
while ((!(AIRSPEED_STATUS_REG & AIRSPEED_READY_BIT))) {
        /* Busy wait */
    }
```

**Required Remediation:**
> Introduce a deterministic timeout counter bounded by max hardware latency (e.g., uint32_t timeout = 300UL; while (--timeout && ...) ).

---

### `GAP-0002`: UNHANDLED_ERROR_REGISTER [⛔ CRITICAL]
- **Function:** `airspeed_read_knots`
- **Location:** `examples\airspeed_sensor\inputs\airspeed_sensor.c:18`
- **DO-178C Objective:** Table A-5 Obj 2 (Architecture Compliance: Hardware Fault Handling)
- **Problem:** Register 'AIRSPEED_STATUS_REG' has hardware error bitmask (0x00000002), but function 'airspeed_read_knots' accesses it without verifying error status flags.

```c
// Offending code at line 18:
AIRSPEED_STATUS_REG & AIRSPEED_READY_BIT
```

**Required Remediation:**
> Evaluate error mask before proceeding: if (AIRSPEED_STATUS_REG & 0x00000002) return ERR_HARDWARE_FAULT;

---

### `GAP-0003`: MISSING_INPUT_RANGE_CHECK [⚠️ HIGH]
- **Function:** `airspeed_read_knots`
- **Location:** `examples\airspeed_sensor\inputs\airspeed_sensor.c:14`
- **DO-178C Objective:** Table A-5 Obj 1 & 4 (Robustness: Input Range Validation)
- **Problem:** Function 'airspeed_read_knots' consumes parameters (uint8_t sensor_id, float* out_knots) without defensive pre-condition range assertions or validation before processing.

```c
// Offending code at line 14:
airspeed_status_t airspeed_read_knots(uint8_t sensor_id, float* out_knots)
```

**Required Remediation:**
> Add defensive boundary checks on all input parameters before execution.

---

### `GAP-0004`: ARITHMETIC_OVERFLOW_RISK [⚠️ MEDIUM]
- **Function:** `airspeed_read_knots`
- **Location:** `examples\airspeed_sensor\inputs\airspeed_sensor.c:28`
- **DO-178C Objective:** Table A-5 Obj 3 (Robustness: Arithmetic Anomaly Freedom)
- **Problem:** Potential integer overflow risk in calculation '(float)raw_counts * 0.1f'.

```c
// Offending code at line 28:
(float)raw_counts * 0.1f
```

**Required Remediation:**
> Ensure input operand bounds guarantee saturation or use safe saturating math routines.

---

### `GAP-0005`: MISSING_INPUT_RANGE_CHECK [⚠️ HIGH]
- **Function:** `airspeed_celsius_to_kelvin`
- **Location:** `examples\airspeed_sensor\inputs\airspeed_sensor.c:37`
- **DO-178C Objective:** Table A-5 Obj 1 & 4 (Robustness: Input Range Validation)
- **Problem:** Function 'airspeed_celsius_to_kelvin' consumes parameters (float temp_c) without defensive pre-condition range assertions or validation before processing.

```c
// Offending code at line 37:
float airspeed_celsius_to_kelvin(float temp_c)
```

**Required Remediation:**
> Add defensive boundary checks on all input parameters before execution.

---

### `GAP-0006`: ARITHMETIC_OVERFLOW_RISK [⚠️ MEDIUM]
- **Function:** `airspeed_celsius_to_kelvin`
- **Location:** `examples\airspeed_sensor\inputs\airspeed_sensor.c:38`
- **DO-178C Objective:** Table A-5 Obj 3 (Robustness: Arithmetic Anomaly Freedom)
- **Problem:** Potential integer overflow risk in calculation 'temp_c + 273.15f'.

```c
// Offending code at line 38:
temp_c + 273.15f
```

**Required Remediation:**
> Ensure input operand bounds guarantee saturation or use safe saturating math routines.

---

## Guidance for DO-178C DAL A Transition
1. **Bounded Execution:** Every loop interacting with memory-mapped I/O must have a proven deterministic upper bound.
2. **Hardware Register Contracts:** All status register polls must test error bitmasks before accepting data.
3. **Defensive Preconditions:** Public and internal API functions must validate parameter boundaries before arithmetic operations.
