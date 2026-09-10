# DO-178C DAL A Requirements-Based Test Matrix & MC/DC Analysis
**Module Prefix:** `AIR`  
**Total Test Vectors:** `12` (Nominal: `3`, Boundary: `2`, Robustness: `7`)  
**DO-178C Verification Objectives:** Table A-5 (LLR Conformance), Table A-7 Obj 2 (MC/DC Independence)  

---

## 1. Executive Test Partition Summary

| Partition / Category | Count | DO-178C Standard Objective | Verification Intent |
| :--- | :--- | :--- | :--- |
| **NOMINAL** | 3 | §6.4.2.1 Normal Range | Verifies valid operating combinations and nominal output behavior |
| **BOUNDARY** | 2 | §6.4.2.2 Equivalence Boundary | Exercises edge transitions at minimum and maximum boundaries |
| **ROBUSTNESS** | 7 | §6.4.2.3 Robustness & Faults | Exercises out-of-bounds parameters, invalid inputs, and simulated timeouts |
| **TOTAL** | **12** | **Table A-7 Obj 2** | **Full requirements-based coverage with MC/DC traceability** |

---

## 2. Modified Condition / Decision Coverage (MC/DC) Analysis

> [!NOTE]
> **DO-178C DAL A Requirement (Table A-7 Objective 2):**
> Each condition in a multi-condition decision must be shown to independently affect the decision outcome.
> In requirements-based testing, independent effect is proven when varying a single condition (from in-range/boundary to out-of-range/fault)
> toggles the decision outcome (e.g. from nominal success to defensive error containment) while holding all other parameters valid.

### Requirement `LLR-IAS-0001`: `airspeed_read_knots`
> **Statement:** The software shall sample the digitized dynamic pressure counts from AIRSPEED_DATA_REG, calculate indicated airspeed scaled to knots within the range 0.0 to 450.0 knots, and write the result into out_knots upon ready confirmation.

| Condition ID | Condition Description | True Vector (In-Range / Bound) | False Vector (Fault / OOB) | Decision Outcome Toggle | MC/DC Independence Proof |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **C1** | <code>sensor_id &gt;= 0</code> (Lower Bound) | `TC-IAS-0004` | `TC-IAS-0006` | <code>ACT_OK</code> &rarr; <code>ACT_ERR_INVALID_PARAM</code> | Violating <code>sensor_id</code> minimum triggers rejection while other parameters remain valid. |
| **C2** | <code>sensor_id &lt;= 1</code> (Upper Bound) | `TC-IAS-0005` | `TC-IAS-0007` | <code>ACT_OK</code> &rarr; <code>ACT_ERR_INVALID_PARAM</code> | Exceeding <code>sensor_id</code> maximum triggers rejection while other parameters remain valid. |
| **C3** | <code>out_knots</code> within defined operational range | `TC-IAS-0001` | `TC-IAS-0006` | <code>SUCCESS</code> &rarr; <code>ERR_RANGE_VIOLATION</code> | Out-of-range <code>out_knots</code> triggers defensive containment. |
| **C4** | Hardware status register error flag clear | `TC-IAS-0001` | `TC-IAS-0009` | <code>ACT_OK</code> &rarr; <code>ERR_HARDWARE_FAULT</code> | Hardware error bit assertion halts transaction defensively. |
| **C5** | Hardware status register error flag clear | `TC-IAS-0001` | `TC-IAS-0010` | <code>ACT_OK</code> &rarr; <code>ERR_HARDWARE_FAULT</code> | Hardware error bit assertion halts transaction defensively. |

---

## 3. Comprehensive Test Vector Specifications

| Test Case ID | Category | Traced LLR | Input Vectors | Expected Outputs | Fault Injection | Verification Objective |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `TC-IAS-0001` | `NOMINAL` | `LLR-IAS-0001` | <code>sensor_id = 0</code><br><code>simulated_AIRSPEED_DATA_REG_counts = 500</code><br><code>simulated_AIRSPEED_STATUS_REG_ready_bit = true</code><br><code>simulated_AIRSPEED_STATUS_REG_fault_bit = false</code><br><code>out_knots_pointer_valid = true</code> | <code>return_value = AIRSPEED_OK</code><br><code>out_knots_value = 50.0</code> | *None* | Verify successful airspeed read for sensor_id 0 with a nominal airspeed value (50.0 knots), ensuring all pre-conditions are met. |
| `TC-IAS-0002` | `NOMINAL` | `LLR-IAS-0001` | <code>sensor_id = 1</code><br><code>simulated_AIRSPEED_DATA_REG_counts = 2500</code><br><code>simulated_AIRSPEED_STATUS_REG_ready_bit = true</code><br><code>simulated_AIRSPEED_STATUS_REG_fault_bit = false</code><br><code>out_knots_pointer_valid = true</code> | <code>return_value = AIRSPEED_OK</code><br><code>out_knots_value = 250.0</code> | *None* | Verify successful airspeed read for sensor_id 1 with a nominal mid-range airspeed value (250.0 knots), ensuring all pre-conditions are met. |
| `TC-IAS-0003` | `NOMINAL` | `LLR-IAS-0001` | <code>sensor_id = 0</code><br><code>simulated_AIRSPEED_DATA_REG_counts = 4000</code><br><code>simulated_AIRSPEED_STATUS_REG_ready_bit = true</code><br><code>simulated_AIRSPEED_STATUS_REG_fault_bit = false</code><br><code>out_knots_pointer_valid = true</code> | <code>return_value = AIRSPEED_OK</code><br><code>out_knots_value = 400.0</code> | *None* | Verify successful airspeed read for sensor_id 0 with a nominal high-range airspeed value (400.0 knots), ensuring all pre-conditions are met. |
| `TC-IAS-0004` | `BOUNDARY` | `LLR-IAS-0001` | <code>sensor_id = 0</code><br><code>simulated_AIRSPEED_DATA_REG_counts = 0</code><br><code>simulated_AIRSPEED_STATUS_REG_ready_bit = true</code><br><code>simulated_AIRSPEED_STATUS_REG_fault_bit = false</code><br><code>out_knots_pointer_valid = true</code> | <code>return_value = AIRSPEED_OK</code><br><code>out_knots_value = 0.0</code> | *None* | Verify airspeed read for sensor_id at its minimum valid value (0), with output airspeed at its minimum specified boundary (0.0 knots). |
| `TC-IAS-0005` | `BOUNDARY` | `LLR-IAS-0001` | <code>sensor_id = 1</code><br><code>simulated_AIRSPEED_DATA_REG_counts = 4500</code><br><code>simulated_AIRSPEED_STATUS_REG_ready_bit = true</code><br><code>simulated_AIRSPEED_STATUS_REG_fault_bit = false</code><br><code>out_knots_pointer_valid = true</code> | <code>return_value = AIRSPEED_OK</code><br><code>out_knots_value = 450.0</code> | *None* | Verify airspeed read for sensor_id at its maximum valid value (1), with output airspeed at its maximum specified boundary (450.0 knots). |
| `TC-IAS-0006` | `ROBUSTNESS` | `LLR-IAS-0001` | <code>sensor_id = -1</code><br><code>simulated_AIRSPEED_DATA_REG_counts = 1000</code><br><code>simulated_AIRSPEED_STATUS_REG_ready_bit = true</code><br><code>simulated_AIRSPEED_STATUS_REG_fault_bit = false</code><br><code>out_knots_pointer_valid = true</code> | <code>return_value = AIRSPEED_ERR_INVALID_PARAM</code><br><code>out_knots_value = *null*</code> | *None* | Verify error handling when sensor_id is less than the minimum valid value (0), i.e., sensor_id = -1. |
| `TC-IAS-0007` | `ROBUSTNESS` | `LLR-IAS-0001` | <code>sensor_id = 2</code><br><code>simulated_AIRSPEED_DATA_REG_counts = 1000</code><br><code>simulated_AIRSPEED_STATUS_REG_ready_bit = true</code><br><code>simulated_AIRSPEED_STATUS_REG_fault_bit = false</code><br><code>out_knots_pointer_valid = true</code> | <code>return_value = AIRSPEED_ERR_INVALID_PARAM</code><br><code>out_knots_value = *null*</code> | *None* | Verify error handling when sensor_id is greater than the maximum valid value (1), i.e., sensor_id = 2. |
| `TC-IAS-0008` | `ROBUSTNESS` | `LLR-IAS-0001` | <code>sensor_id = 0</code><br><code>simulated_AIRSPEED_DATA_REG_counts = 1000</code><br><code>simulated_AIRSPEED_STATUS_REG_ready_bit = true</code><br><code>simulated_AIRSPEED_STATUS_REG_fault_bit = false</code><br><code>out_knots_pointer_valid = false</code> | <code>return_value = AIRSPEED_ERR_INVALID_PARAM</code><br><code>out_knots_value = *null*</code> | *None* | Verify error handling when the 'out_knots' pointer is null, as per pre-condition. |
| `TC-IAS-0009` | `ROBUSTNESS` | `LLR-IAS-0001` | <code>sensor_id = 0</code><br><code>simulated_AIRSPEED_DATA_REG_counts = 1000</code><br><code>simulated_AIRSPEED_STATUS_REG_ready_bit = false</code><br><code>simulated_AIRSPEED_STATUS_REG_fault_bit = false</code><br><code>out_knots_pointer_valid = true</code> | <code>return_value = AIRSPEED_ERR_TIMEOUT</code><br><code>out_knots_value = *null*</code> | `Transducer ready bit fails to assert within 300 microseconds.` | Verify error handling when the transducer ready bit fails to assert within 300 microseconds. |
| `TC-IAS-0010` | `ROBUSTNESS` | `LLR-IAS-0001` | <code>sensor_id = 0</code><br><code>simulated_AIRSPEED_DATA_REG_counts = 1000</code><br><code>simulated_AIRSPEED_STATUS_REG_ready_bit = true</code><br><code>simulated_AIRSPEED_STATUS_REG_fault_bit = true</code><br><code>out_knots_pointer_valid = true</code> | <code>return_value = AIRSPEED_ERR_SENSOR_FAULT</code><br><code>out_knots_value = *null*</code> | `Transducer fault bit is active in AIRSPEED_STATUS_REG.` | Verify error handling when the transducer fault bit is active in AIRSPEED_STATUS_REG. |
| `TC-IAS-0011` | `ROBUSTNESS` | `LLR-IAS-0001` | <code>sensor_id = 0</code><br><code>simulated_AIRSPEED_DATA_REG_counts = -100</code><br><code>simulated_AIRSPEED_STATUS_REG_ready_bit = true</code><br><code>simulated_AIRSPEED_STATUS_REG_fault_bit = false</code><br><code>out_knots_pointer_valid = true</code> | <code>return_value = AIRSPEED_OK</code><br><code>out_knots_value = 0.0</code> | *None* | Verify that calculated airspeed values below 0.0 knots are clamped to 0.0 knots as per the specified output range. |
| `TC-IAS-0012` | `ROBUSTNESS` | `LLR-IAS-0001` | <code>sensor_id = 0</code><br><code>simulated_AIRSPEED_DATA_REG_counts = 5000</code><br><code>simulated_AIRSPEED_STATUS_REG_ready_bit = true</code><br><code>simulated_AIRSPEED_STATUS_REG_fault_bit = false</code><br><code>out_knots_pointer_valid = true</code> | <code>return_value = AIRSPEED_OK</code><br><code>out_knots_value = 450.0</code> | *None* | Verify that calculated airspeed values above 450.0 knots are clamped to 450.0 knots as per the specified output range. |
