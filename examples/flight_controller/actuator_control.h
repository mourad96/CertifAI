#ifndef ACTUATOR_CONTROL_H
#define ACTUATOR_CONTROL_H

#include <stdint.h>
#include <stdbool.h>

#define ACT_MAX_CHANNELS      4
#define ACT_MIN_ANGLE_DEG   -45.0f
#define ACT_MAX_ANGLE_DEG    45.0f

typedef enum {
    ACT_OK = 0,
    ACT_ERR_INVALID_PARAM = -1,
    ACT_ERR_TIMEOUT = -2,
    ACT_ERR_HW_FAULT = -3
} act_status_t;

typedef enum {
    ACT_MODE_STANDBY = 0,
    ACT_MODE_ACTIVE = 1,
    ACT_MODE_CALIBRATE = 2
} act_mode_t;

/* Core actuator API */
act_status_t actuator_set_position(uint8_t channel, float target_angle_deg);
float actuator_apply_rate_filter(float current_val, float target_val, float max_rate);
act_status_t actuator_switch_mode(act_mode_t mode);

#endif /* ACTUATOR_CONTROL_H */
