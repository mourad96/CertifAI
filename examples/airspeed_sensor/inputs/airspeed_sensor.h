#ifndef AIRSPEED_SENSOR_H
#define AIRSPEED_SENSOR_H

#include <stdint.h>
#include <stdbool.h>

#define AIRSPEED_MAX_SENSORS        2
#define AIRSPEED_MIN_KNOTS        0.0f
#define AIRSPEED_MAX_KNOTS      450.0f

typedef enum {
    AIRSPEED_OK = 0,
    AIRSPEED_ERR_INVALID_PARAM = -1,
    AIRSPEED_ERR_TIMEOUT = -2,
    AIRSPEED_ERR_SENSOR_FAULT = -3
} airspeed_status_t;

/* Core Airspeed API */
airspeed_status_t airspeed_read_knots(uint8_t sensor_id, float *out_knots);
float airspeed_celsius_to_kelvin(float temp_c);

#endif /* AIRSPEED_SENSOR_H */
