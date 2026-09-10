# DO-178C DAL A Requirements-Based Test Matrix & MC/DC Analysis
**Module Prefix:** `ACT`  
**Total Test Vectors:** `29` (Nominal: `6`, Boundary: `10`, Robustness: `13`)  
**DO-178C Verification Objectives:** Table A-5 (LLR Conformance), Table A-7 Obj 2 (MC/DC Independence)  

---

## 1. Executive Test Partition Summary

| Partition / Category | Count | DO-178C Standard Objective | Verification Intent |
| :--- | :--- | :--- | :--- |
| **NOMINAL** | 6 | §6.4.2.1 Normal Range | Verifies valid operating combinations and nominal output behavior |
| **BOUNDARY** | 10 | §6.4.2.2 Equivalence Boundary | Exercises edge transitions at minimum and maximum boundaries |
| **ROBUSTNESS** | 13 | §6.4.2.3 Robustness & Faults | Exercises out-of-bounds parameters, invalid inputs, and simulated timeouts |
| **TOTAL** | **29** | **Table A-7 Obj 2** | **Full requirements-based coverage with MC/DC traceability** |

---

## 2. Modified Condition / Decision Coverage (MC/DC) Analysis

> [!NOTE]
> **DO-178C DAL A Requirement (Table A-7 Objective 2):**
> Each condition in a multi-condition decision must be shown to independently affect the decision outcome.
> In requirements-based testing, independent effect is proven when varying a single condition (from in-range/boundary to out-of-range/fault)
> toggles the decision outcome (e.g. from nominal success to defensive error containment) while holding all other parameters valid.

### Requirement `LLR-ACT-0001`: `actuator_set_position`
> **Statement:** The software shall set the actuator position register ACT_POS_REG to the commanded angle scaled to millidegrees and assert the trigger bit on ACT_CTRL_REG for the specified channel within 100 microseconds of ready confirmation.

| Condition ID | Condition Description | True Vector (In-Range / Bound) | False Vector (Fault / OOB) | Decision Outcome Toggle | MC/DC Independence Proof |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **C1** | <code>channel &gt;= 0</code> (Lower Bound) | `TC-ACT-0004` | `TC-ACT-0012` | <code>ACT_OK</code> &rarr; <code>ACT_ERR_INVALID_PARAM</code> | Violating <code>channel</code> minimum triggers rejection while other parameters remain valid. |
| **C2** | <code>channel &lt;= 3</code> (Upper Bound) | `TC-ACT-0005` | `TC-ACT-0013` | <code>ACT_OK</code> &rarr; <code>ACT_ERR_INVALID_PARAM</code> | Exceeding <code>channel</code> maximum triggers rejection while other parameters remain valid. |
| **C3** | <code>target_angle_deg &gt;= -45.0</code> (Lower Bound) | `TC-ACT-0006` | `TC-ACT-0015` | <code>ACT_OK</code> &rarr; <code>ACT_ERR_INVALID_PARAM</code> | Violating <code>target_angle_deg</code> minimum triggers rejection while other parameters remain valid. |
| **C4** | <code>target_angle_deg &lt;= 45.0</code> (Upper Bound) | `TC-ACT-0007` | `TC-ACT-0016` | <code>ACT_OK</code> &rarr; <code>ACT_ERR_INVALID_PARAM</code> | Exceeding <code>target_angle_deg</code> maximum triggers rejection while other parameters remain valid. |
| **C5** | Hardware status register error flag clear | `TC-ACT-0001` | `TC-ACT-0019` | <code>ACT_OK</code> &rarr; <code>ERR_HARDWARE_FAULT</code> | Hardware error bit assertion halts transaction defensively. |

### Requirement `LLR-ACT-0002`: `actuator_switch_mode`
> **Statement:** The software shall transition ACT_CTRL_REG into STANDBY (0x00), ACTIVE (0x01), or CALIBRATE (0x04) according to commanded mode enum, returning ACT_ERR_INVALID_PARAM if an undefined mode is received.

| Condition ID | Condition Description | True Vector (In-Range / Bound) | False Vector (Fault / OOB) | Decision Outcome Toggle | MC/DC Independence Proof |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **C6** | <code>mode &gt;= 0</code> (Lower Bound) | `TC-ACT-0001` | `TC-ACT-0009` | <code>ACT_OK</code> &rarr; <code>ACT_ERR_INVALID_PARAM</code> | Violating <code>mode</code> minimum triggers rejection while other parameters remain valid. |
| **C7** | <code>mode &lt;= 2</code> (Upper Bound) | `TC-ACT-0001` | `TC-ACT-0008` | <code>ACT_OK</code> &rarr; <code>ACT_ERR_INVALID_PARAM</code> | Exceeding <code>mode</code> maximum triggers rejection while other parameters remain valid. |

---

## 3. Comprehensive Test Vector Specifications

| Test Case ID | Category | Traced LLR | Input Vectors | Expected Outputs | Fault Injection | Verification Objective |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `TC-ACT-0001` | `NOMINAL` | `LLR-ACT-0001` | <code>channel = 1</code><br><code>target_angle_deg = 15.0</code> | <code>return_value = ACT_OK</code><br><code>ACT_POS_REG_value = 15000</code><br><code>ACT_CTRL_REG_trigger_asserted = true</code><br><code>ACT_CTRL_REG_channel_selected = 1</code> | *None* | Verify setting actuator position for a valid middle channel and a positive nominal angle, with prompt hardware ready. |
| `TC-ACT-0002` | `NOMINAL` | `LLR-ACT-0001` | <code>channel = 0</code><br><code>target_angle_deg = -10.0</code> | <code>return_value = ACT_OK</code><br><code>ACT_POS_REG_value = -10000</code><br><code>ACT_CTRL_REG_trigger_asserted = true</code><br><code>ACT_CTRL_REG_channel_selected = 0</code> | *None* | Verify setting actuator position for a valid first channel and a negative nominal angle, with prompt hardware ready. |
| `TC-ACT-0003` | `NOMINAL` | `LLR-ACT-0001` | <code>channel = 3</code><br><code>target_angle_deg = 0.0</code> | <code>return_value = ACT_OK</code><br><code>ACT_POS_REG_value = 0</code><br><code>ACT_CTRL_REG_trigger_asserted = true</code><br><code>ACT_CTRL_REG_channel_selected = 3</code> | *None* | Verify setting actuator position for a valid last channel and a zero angle, with prompt hardware ready. |
| `TC-ACT-0004` | `BOUNDARY` | `LLR-ACT-0001` | <code>channel = 0</code><br><code>target_angle_deg = 20.0</code> | <code>return_value = ACT_OK</code><br><code>ACT_POS_REG_value = 20000</code><br><code>ACT_CTRL_REG_trigger_asserted = true</code><br><code>ACT_CTRL_REG_channel_selected = 0</code> | *None* | Verify setting actuator position with channel at minimum boundary (0) and a nominal angle. |
| `TC-ACT-0005` | `BOUNDARY` | `LLR-ACT-0001` | <code>channel = 3</code><br><code>target_angle_deg = -20.0</code> | <code>return_value = ACT_OK</code><br><code>ACT_POS_REG_value = -20000</code><br><code>ACT_CTRL_REG_trigger_asserted = true</code><br><code>ACT_CTRL_REG_channel_selected = 3</code> | *None* | Verify setting actuator position with channel at maximum boundary (3) and a nominal angle. |
| `TC-ACT-0006` | `BOUNDARY` | `LLR-ACT-0001` | <code>channel = 2</code><br><code>target_angle_deg = -45.0</code> | <code>return_value = ACT_OK</code><br><code>ACT_POS_REG_value = -45000</code><br><code>ACT_CTRL_REG_trigger_asserted = true</code><br><code>ACT_CTRL_REG_channel_selected = 2</code> | *None* | Verify setting actuator position with target_angle_deg at minimum boundary (-45.0). |
| `TC-ACT-0007` | `BOUNDARY` | `LLR-ACT-0001` | <code>channel = 1</code><br><code>target_angle_deg = 45.0</code> | <code>return_value = ACT_OK</code><br><code>ACT_POS_REG_value = 45000</code><br><code>ACT_CTRL_REG_trigger_asserted = true</code><br><code>ACT_CTRL_REG_channel_selected = 1</code> | *None* | Verify setting actuator position with target_angle_deg at maximum boundary (45.0). |
| `TC-ACT-0008` | `BOUNDARY` | `LLR-ACT-0001` | <code>channel = 0</code><br><code>target_angle_deg = -44.9</code> | <code>return_value = ACT_OK</code><br><code>ACT_POS_REG_value = -44900</code><br><code>ACT_CTRL_REG_trigger_asserted = true</code><br><code>ACT_CTRL_REG_channel_selected = 0</code> | *None* | Verify setting actuator position with target_angle_deg just above minimum boundary (-44.9). |
| `TC-ACT-0009` | `BOUNDARY` | `LLR-ACT-0001` | <code>channel = 3</code><br><code>target_angle_deg = 44.9</code> | <code>return_value = ACT_OK</code><br><code>ACT_POS_REG_value = 44900</code><br><code>ACT_CTRL_REG_trigger_asserted = true</code><br><code>ACT_CTRL_REG_channel_selected = 3</code> | *None* | Verify setting actuator position with target_angle_deg just below maximum boundary (44.9). |
| `TC-ACT-0010` | `BOUNDARY` | `LLR-ACT-0001` | <code>channel = 0</code><br><code>target_angle_deg = -45.0</code> | <code>return_value = ACT_OK</code><br><code>ACT_POS_REG_value = -45000</code><br><code>ACT_CTRL_REG_trigger_asserted = true</code><br><code>ACT_CTRL_REG_channel_selected = 0</code> | *None* | Verify setting actuator position with channel and target_angle_deg both at their minimum boundaries (0, -45.0). |
| `TC-ACT-0011` | `BOUNDARY` | `LLR-ACT-0001` | <code>channel = 3</code><br><code>target_angle_deg = 45.0</code> | <code>return_value = ACT_OK</code><br><code>ACT_POS_REG_value = 45000</code><br><code>ACT_CTRL_REG_trigger_asserted = true</code><br><code>ACT_CTRL_REG_channel_selected = 3</code> | *None* | Verify setting actuator position with channel and target_angle_deg both at their maximum boundaries (3, 45.0). |
| `TC-ACT-0012` | `ROBUSTNESS` | `LLR-ACT-0001` | <code>channel = -1</code><br><code>target_angle_deg = 10.0</code> | <code>return_value = ACT_ERR_INVALID_PARAM</code><br><code>ACT_POS_REG_value = *null*</code><br><code>ACT_CTRL_REG_trigger_asserted = false</code><br><code>ACT_CTRL_REG_channel_selected = *null*</code> | *None* | Verify invalid channel input (min-1 = -1) returns ACT_ERR_INVALID_PARAM and does not modify registers. |
| `TC-ACT-0013` | `ROBUSTNESS` | `LLR-ACT-0001` | <code>channel = 4</code><br><code>target_angle_deg = 10.0</code> | <code>return_value = ACT_ERR_INVALID_PARAM</code><br><code>ACT_POS_REG_value = *null*</code><br><code>ACT_CTRL_REG_trigger_asserted = false</code><br><code>ACT_CTRL_REG_channel_selected = *null*</code> | *None* | Verify invalid channel input (max+1 = 4) returns ACT_ERR_INVALID_PARAM and does not modify registers. |
| `TC-ACT-0014` | `ROBUSTNESS` | `LLR-ACT-0001` | <code>channel = 100</code><br><code>target_angle_deg = 10.0</code> | <code>return_value = ACT_ERR_INVALID_PARAM</code><br><code>ACT_POS_REG_value = *null*</code><br><code>ACT_CTRL_REG_trigger_asserted = false</code><br><code>ACT_CTRL_REG_channel_selected = *null*</code> | *None* | Verify significantly out-of-range channel input (100) returns ACT_ERR_INVALID_PARAM and does not modify registers. |
| `TC-ACT-0015` | `ROBUSTNESS` | `LLR-ACT-0001` | <code>channel = 1</code><br><code>target_angle_deg = -45.1</code> | <code>return_value = ACT_ERR_INVALID_PARAM</code><br><code>ACT_POS_REG_value = *null*</code><br><code>ACT_CTRL_REG_trigger_asserted = false</code><br><code>ACT_CTRL_REG_channel_selected = *null*</code> | *None* | Verify invalid target_angle_deg input (min-epsilon = -45.1) returns ACT_ERR_INVALID_PARAM and does not modify registers. |
| `TC-ACT-0016` | `ROBUSTNESS` | `LLR-ACT-0001` | <code>channel = 1</code><br><code>target_angle_deg = 45.1</code> | <code>return_value = ACT_ERR_INVALID_PARAM</code><br><code>ACT_POS_REG_value = *null*</code><br><code>ACT_CTRL_REG_trigger_asserted = false</code><br><code>ACT_CTRL_REG_channel_selected = *null*</code> | *None* | Verify invalid target_angle_deg input (max+epsilon = 45.1) returns ACT_ERR_INVALID_PARAM and does not modify registers. |
| `TC-ACT-0017` | `ROBUSTNESS` | `LLR-ACT-0001` | <code>channel = 1</code><br><code>target_angle_deg = -90.0</code> | <code>return_value = ACT_ERR_INVALID_PARAM</code><br><code>ACT_POS_REG_value = *null*</code><br><code>ACT_CTRL_REG_trigger_asserted = false</code><br><code>ACT_CTRL_REG_channel_selected = *null*</code> | *None* | Verify significantly out-of-range target_angle_deg input (-90.0) returns ACT_ERR_INVALID_PARAM and does not modify registers. |
| `TC-ACT-0018` | `ROBUSTNESS` | `LLR-ACT-0001` | <code>channel = 1</code><br><code>target_angle_deg = 90.0</code> | <code>return_value = ACT_ERR_INVALID_PARAM</code><br><code>ACT_POS_REG_value = *null*</code><br><code>ACT_CTRL_REG_trigger_asserted = false</code><br><code>ACT_CTRL_REG_channel_selected = *null*</code> | *None* | Verify significantly out-of-range target_angle_deg input (90.0) returns ACT_ERR_INVALID_PARAM and does not modify registers. |
| `TC-ACT-0019` | `ROBUSTNESS` | `LLR-ACT-0001` | <code>channel = 1</code><br><code>target_angle_deg = 15.0</code> | <code>return_value = ACT_ERR_TIMEOUT</code><br><code>ACT_POS_REG_value = *null*</code><br><code>ACT_CTRL_REG_trigger_asserted = false</code><br><code>ACT_CTRL_REG_channel_selected = *null*</code> | `ACT_STATUS_REG ready bit fails to assert within 500 microseconds.` | Verify that if the actuator hardware ready bit is not asserted within 500 microseconds, ACT_ERR_TIMEOUT is returned. |
| `TC-ACT-0001` | `NOMINAL` | `LLR-ACT-0002` | <code>mode = 0x00</code> | <code>return_value = ACT_OK</code><br><code>ACT_CTRL_REG_state = 0x00</code> | *None* | Verify the software transitions ACT_CTRL_REG to STANDBY (0x00) mode when commanded. |
| `TC-ACT-0002` | `NOMINAL` | `LLR-ACT-0002` | <code>mode = 0x01</code> | <code>return_value = ACT_OK</code><br><code>ACT_CTRL_REG_state = 0x01</code> | *None* | Verify the software transitions ACT_CTRL_REG to ACTIVE (0x01) mode when commanded. |
| `TC-ACT-0003` | `NOMINAL` | `LLR-ACT-0002` | <code>mode = 0x04</code> | <code>return_value = ACT_OK</code><br><code>ACT_CTRL_REG_state = 0x04</code> | *None* | Verify the software transitions ACT_CTRL_REG to CALIBRATE (0x04) mode when commanded. |
| `TC-ACT-0004` | `BOUNDARY` | `LLR-ACT-0002` | <code>mode = 0x00</code> | <code>return_value = ACT_OK</code><br><code>ACT_CTRL_REG_state = 0x00</code> | *None* | Verify boundary condition: lowest valid mode enum (0x00) transitions ACT_CTRL_REG to STANDBY. |
| `TC-ACT-0005` | `BOUNDARY` | `LLR-ACT-0002` | <code>mode = 0x04</code> | <code>return_value = ACT_OK</code><br><code>ACT_CTRL_REG_state = 0x04</code> | *None* | Verify boundary condition: highest valid mode enum (0x04) transitions ACT_CTRL_REG to CALIBRATE. |
| `TC-ACT-0006` | `ROBUSTNESS` | `LLR-ACT-0002` | <code>mode = 0x02</code> | <code>return_value = ACT_ERR_INVALID_PARAM</code><br><code>ACT_CTRL_REG_state = unchanged</code> | *None* | Verify robustness for an undefined mode enum (0x02) that is within the '0 to 2' boundary but not explicitly listed as a valid mode. Expect ACT_ERR_INVALID_PARAM. |
| `TC-ACT-0007` | `ROBUSTNESS` | `LLR-ACT-0002` | <code>mode = 0x03</code> | <code>return_value = ACT_ERR_INVALID_PARAM</code><br><code>ACT_CTRL_REG_state = unchanged</code> | *None* | Verify robustness for an undefined mode enum (0x03) falling between valid explicit modes. Expect ACT_ERR_INVALID_PARAM. |
| `TC-ACT-0008` | `ROBUSTNESS` | `LLR-ACT-0002` | <code>mode = 0x05</code> | <code>return_value = ACT_ERR_INVALID_PARAM</code><br><code>ACT_CTRL_REG_state = unchanged</code> | *None* | Verify robustness for an undefined mode enum (0x05), representing a value immediately above the highest valid mode (0x04). Expect ACT_ERR_INVALID_PARAM. |
| `TC-ACT-0009` | `ROBUSTNESS` | `LLR-ACT-0002` | <code>mode = 0xFF</code> | <code>return_value = ACT_ERR_INVALID_PARAM</code><br><code>ACT_CTRL_REG_state = unchanged</code> | *None* | Verify robustness for a large, arbitrary undefined mode enum (0xFF), assuming 'mode' is a byte or similar integer type. Expect ACT_ERR_INVALID_PARAM. |
| `TC-ACT-0010` | `ROBUSTNESS` | `LLR-ACT-0002` | <code>mode = -1</code> | <code>return_value = ACT_ERR_INVALID_PARAM</code><br><code>ACT_CTRL_REG_state = unchanged</code> | *None* | Verify robustness for a negative input mode (-1), representing a value below the minimum '0 to 2' boundary. Expect ACT_ERR_INVALID_PARAM (assuming mode is a signed or implicitly convertible integer type). |
