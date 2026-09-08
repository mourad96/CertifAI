#include "airspeed_sensor.h"

/* Simulated Memory-Mapped Hardware Registers */
volatile uint32_t AIRSPEED_STATUS_REG = 0;
volatile uint32_t AIRSPEED_DATA_REG = 0;

#define AIRSPEED_READY_BIT  (1U << 0)
#define AIRSPEED_FAULT_BIT  (1U << 1)

/**
 * Acquire indicated airspeed in knots.
 * Prototype flaw: Unbounded hardware loop, missing parameter range validation, unhandled error bit.
 */
airspeed_status_t airspeed_read_knots(uint8_t sensor_id, float *out_knots) {
    /* Architectural omission: Missing range check on sensor_id and NULL check on out_knots */

    /* Critical Defect: Unbounded polling on hardware register */
    while (!(AIRSPEED_STATUS_REG & AIRSPEED_READY_BIT)) {
        /* Busy wait */
    }

    /* Omission: Never evaluates AIRSPEED_FAULT_BIT on AIRSPEED_STATUS_REG */

    /* Read raw differential pressure counts */
    uint32_t raw_counts = AIRSPEED_DATA_REG;

    /* Convert raw counts to knots */
    *out_knots = (float)raw_counts * 0.1f;

    return AIRSPEED_OK;
}

/**
 * Helper function converting Celsius to Kelvin.
 * Prototype flaw: Derived functionality without allocated parent HLR.
 */
float airspeed_celsius_to_kelvin(float temp_c) {
    return temp_c + 273.15f;
}
