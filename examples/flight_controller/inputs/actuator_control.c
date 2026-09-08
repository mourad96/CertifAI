#include "actuator_control.h"

/* Simulated Memory-Mapped Hardware Registers */
volatile uint32_t ACT_CTRL_REG = 0;
volatile uint32_t ACT_STATUS_REG = 0;
volatile uint32_t ACT_POS_REG = 0;

#define ACT_READY_BIT  (1U << 0)
#define ACT_FAULT_BIT  (1U << 1)

/**
 * Commands actuator position.
 * Prototype flaw: Unbounded hardware poll, missing parameter checks, unhandled error register.
 */
act_status_t actuator_set_position(uint8_t channel, float target_angle_deg) {
    /* Architectural omission: No input validation on channel or target_angle_deg */

    /* Critical Defect: Unbounded polling loop on hardware register without timeout watchdog */
    while (!(ACT_STATUS_REG & ACT_READY_BIT)) {
        /* Busy wait */
    }

    /* Omission: Never evaluates ACT_FAULT_BIT on ACT_STATUS_REG */

    /* Write target position */
    int32_t raw_counts = (int32_t)(target_angle_deg * 1000.0f);
    ACT_POS_REG = (uint32_t)raw_counts;

    /* Trigger command */
    ACT_CTRL_REG = (1U << channel) | 0x01;

    return ACT_OK;
}

/**
 * Filter raw sensor/target rate.
 * Prototype flaw: Derived functionality with no allocated parent HLR.
 * Potential divide-by-zero risk if step is zero.
 */
float actuator_apply_rate_filter(float current_val, float target_val, float max_rate) {
    float delta = target_val - current_val;
    if (delta > max_rate) {
        delta = max_rate;
    } else if (delta < -max_rate) {
        delta = -max_rate;
    }
    return current_val + delta;
}

/**
 * Mode switcher.
 * Prototype flaw: Missing default case in switch.
 */
act_status_t actuator_switch_mode(act_mode_t mode) {
    switch (mode) {
        case ACT_MODE_STANDBY:
            ACT_CTRL_REG = 0x00;
            break;
        case ACT_MODE_ACTIVE:
            ACT_CTRL_REG = 0x01;
            break;
        case ACT_MODE_CALIBRATE:
            ACT_CTRL_REG = 0x04;
            break;
        /* Omission: Missing default clause */
    }
    return ACT_OK;
}
