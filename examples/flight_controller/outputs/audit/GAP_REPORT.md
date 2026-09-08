# DO-178C DAL A Prototype Gap & Defensive Audit Report
**Target System:** `FlightSurface_Actuator_Controller` (ARM_Cortex_M4)
**Audited Code:** `examples\flight_controller\inputs\actuator_control.c`
**Default Hardware Timeout:** `500.0 µs`

## Executive Summary

| Severity | Count | DO-178C Status |
| :--- | :--- | :--- |
| **CRITICAL** | 2 | Non-Compliant (Certification Blocker) |
| **HIGH** | 2 | Action Required |
| **MEDIUM** | 4 | Review Recommended |
| **LOW** | 0 | Informational |
| **TOTAL** | **8** | |

---

## Detailed Audit Findings (DO-178C Table A-5 Compliance)

### `GAP-0001`: UNBOUNDED_HARDWARE_POLL [⛔ CRITICAL]
- **Function:** `actuator_set_position`
- **Location:** `examples\flight_controller\inputs\actuator_control.c:19`
- **DO-178C Objective:** Table A-5 Obj 3 (Verifiable Code: Absence of Unbounded Execution)
- **Problem:** Unbounded hardware polling loop detected on condition '(!(ACT_STATUS_REG & ACT_READY_BIT))'. Missing iteration limit or timeout watchdog counter.

```c
// Offending code at line 19:
while ((!(ACT_STATUS_REG & ACT_READY_BIT))) {
        /* Busy wait */
    }
```

**Required Remediation:**
> Introduce a deterministic timeout counter bounded by max hardware latency (e.g., uint32_t timeout = 500UL; while (--timeout && ...) ).

---

### `GAP-0002`: UNHANDLED_ERROR_REGISTER [⛔ CRITICAL]
- **Function:** `actuator_set_position`
- **Location:** `examples\flight_controller\inputs\actuator_control.c:19`
- **DO-178C Objective:** Table A-5 Obj 2 (Architecture Compliance: Hardware Fault Handling)
- **Problem:** Register 'ACT_STATUS_REG' has hardware error bitmask (0x00000002), but function 'actuator_set_position' accesses it without verifying error status flags.

```c
// Offending code at line 19:
ACT_STATUS_REG & ACT_READY_BIT
```

**Required Remediation:**
> Evaluate error mask before proceeding: if (ACT_STATUS_REG & 0x00000002) return ERR_HARDWARE_FAULT;

---

### `GAP-0003`: MISSING_INPUT_RANGE_CHECK [⚠️ HIGH]
- **Function:** `actuator_set_position`
- **Location:** `examples\flight_controller\inputs\actuator_control.c:15`
- **DO-178C Objective:** Table A-5 Obj 1 & 4 (Robustness: Input Range Validation)
- **Problem:** Function 'actuator_set_position' consumes parameters (uint8_t channel, float target_angle_deg) without defensive pre-condition range assertions or validation before processing.

```c
// Offending code at line 15:
act_status_t actuator_set_position(uint8_t channel, float target_angle_deg)
```

**Required Remediation:**
> Add defensive boundary checks on all input parameters before execution.

---

### `GAP-0004`: ARITHMETIC_OVERFLOW_RISK [⚠️ MEDIUM]
- **Function:** `actuator_set_position`
- **Location:** `examples\flight_controller\inputs\actuator_control.c:26`
- **DO-178C Objective:** Table A-5 Obj 3 (Robustness: Arithmetic Anomaly Freedom)
- **Problem:** Potential integer overflow risk in calculation 'target_angle_deg * 1000.0f'.

```c
// Offending code at line 26:
target_angle_deg * 1000.0f
```

**Required Remediation:**
> Ensure input operand bounds guarantee saturation or use safe saturating math routines.

---

### `GAP-0005`: ARITHMETIC_OVERFLOW_RISK [⚠️ MEDIUM]
- **Function:** `actuator_set_position`
- **Location:** `examples\flight_controller\inputs\actuator_control.c:30`
- **DO-178C Objective:** Table A-5 Obj 3 (Robustness: Arithmetic Anomaly Freedom)
- **Problem:** Potential integer overflow risk in calculation '1U << channel'.

```c
// Offending code at line 30:
1U << channel
```

**Required Remediation:**
> Ensure input operand bounds guarantee saturation or use safe saturating math routines.

---

### `GAP-0006`: ARITHMETIC_OVERFLOW_RISK [⚠️ MEDIUM]
- **Function:** `actuator_apply_rate_filter`
- **Location:** `examples\flight_controller\inputs\actuator_control.c:47`
- **DO-178C Objective:** Table A-5 Obj 3 (Robustness: Arithmetic Anomaly Freedom)
- **Problem:** Potential integer overflow risk in calculation 'current_val + delta'.

```c
// Offending code at line 47:
current_val + delta
```

**Required Remediation:**
> Ensure input operand bounds guarantee saturation or use safe saturating math routines.

---

### `GAP-0007`: MISSING_INPUT_RANGE_CHECK [⚠️ HIGH]
- **Function:** `actuator_switch_mode`
- **Location:** `examples\flight_controller\inputs\actuator_control.c:54`
- **DO-178C Objective:** Table A-5 Obj 1 & 4 (Robustness: Input Range Validation)
- **Problem:** Function 'actuator_switch_mode' consumes parameters (act_mode_t mode) without defensive pre-condition range assertions or validation before processing.

```c
// Offending code at line 54:
act_status_t actuator_switch_mode(act_mode_t mode)
```

**Required Remediation:**
> Add defensive boundary checks on all input parameters before execution.

---

### `GAP-0008`: SWITCH_MISSING_DEFAULT [⚠️ MEDIUM]
- **Function:** `actuator_switch_mode`
- **Location:** `examples\flight_controller\inputs\actuator_control.c:55`
- **DO-178C Objective:** Table A-5 Obj 4 (Coding Standards: Defensive Control Flow)
- **Problem:** Switch statement in 'actuator_switch_mode' lacks a default handler clause.

```c
// Offending code at line 55:
switch (...) in actuator_switch_mode
```

**Required Remediation:**
> Add a 'default:' branch asserting unexpected state or returning an error code.

---

## Guidance for DO-178C DAL A Transition
1. **Bounded Execution:** Every loop interacting with memory-mapped I/O must have a proven deterministic upper bound.
2. **Hardware Register Contracts:** All status register polls must test error bitmasks before accepting data.
3. **Defensive Preconditions:** Public and internal API functions must validate parameter boundaries before arithmetic operations.
