#pragma once

#include "esphome.h"

namespace esphome::comfortzone {

typedef enum
{
	CZCMP_STOPPED,			// compressor is stopped
	CZCMP_STOPPING,		// compressor is shutting down
	CZCMP_RUNNING,			// compressor is up and running
	CZCMP_UNKNOWN,			// undefined status (very rare)
} COMFORTZONE_COMPRESSOR_ACTIVITY;

typedef enum
{
	CZMD_IDLE,				// no mode chosen (rare)
	CZMD_ROOM_HEATING,	// default mode (even when everything is off)
	CZMD_HOT_WATER,		// hot water production
	CZMD_UNKNOWN,			// undefined mode	(rarer)
} COMFORTZONE_MODE;

// Heatpump status
// Not all values are available on on protocol version
// Supported protocols are 1.60, 1.80. If no protocol version is specified, only 1.60 is supported
typedef struct
{
	sensor::Sensor* fan_time_to_filter_change = new sensor::Sensor();		// days (proto: 1.60, 1.80)

	binary_sensor::BinarySensor* filter_alarm = new binary_sensor::BinarySensor();							// true = replace/clean filter alarm, false = filter ok (proto: 1.60, 1.80)

	binary_sensor::BinarySensor* hot_water_production = new binary_sensor::BinarySensor();					// true = on, false = off
	binary_sensor::BinarySensor* room_heating_in_progress = new binary_sensor::BinarySensor();			// true = on, false = off

	text_sensor::TextSensor* compressor_activity = new text_sensor::TextSensor();		// (proto: 1.60, 1.80)
	binary_sensor::BinarySensor* additional_power_enabled = new binary_sensor::BinarySensor();			// true = resistor is enabled, false = resistor is disabled (proto: 1.60, 1.80)

	text_sensor::TextSensor* mode = new text_sensor::TextSensor();						// (proto: 1.60, 1.80)
	binary_sensor::BinarySensor* defrost_enabled = new binary_sensor::BinarySensor();						// true = defrost in progress, false = no defrost in progress (proto: 1.60, 1.80)

	sensor::Sensor* sensors_te0_outdoor_temp = new sensor::Sensor();		// °C, * 10 (proto: 1.60, 1.80)
	sensor::Sensor* sensors_te1_flow_water = new sensor::Sensor();			// °C, * 10 (proto: 1.60, 1.80)
	sensor::Sensor* sensors_te2_return_water = new sensor::Sensor();		// °C, * 10 (proto: 1.60, 1.80)
	sensor::Sensor* sensors_te3_indoor_temp = new sensor::Sensor();			// °C, * 10 (proto: 1.60, 1.80)
	sensor::Sensor* sensors_te4_hot_gas_temp = new sensor::Sensor();		// °C, * 10 (proto: 1.60, 1.80)
	sensor::Sensor* sensors_te5_exchanger_out = new sensor::Sensor();		// °C, * 10 (proto: 1.60, 1.80)
	sensor::Sensor* sensors_te6_evaporator_in = new sensor::Sensor();		// °C, * 10 (proto: 1.60, 1.80)
	sensor::Sensor* sensors_te7_exhaust_air = new sensor::Sensor();			// °C, * 10 (proto: 1.60, 1.80)
	sensor::Sensor* sensors_te24_hot_water_temp = new sensor::Sensor();	// °C, * 10 (proto: 1.60, 1.80)

	sensor::Sensor* heatpump_current_compressor_frequency = new sensor::Sensor();		// Hz, * 10 (proto: 1.60, 1.80)

	sensor::Sensor* heatpump_current_compressor_power = new sensor::Sensor();	// W = power generated by compressor (proto: 1.60, 1.80)
	sensor::Sensor* heatpump_current_add_power = new sensor::Sensor();				// W = additional power (resistor) (proto: 1.60, 1.80)
	sensor::Sensor* heatpump_current_total_power = new sensor::Sensor();			// W = total power produced (proto: 1.60, 1.80)
	sensor::Sensor* heatpump_current_compressor_input_power = new sensor::Sensor();	// W = power sent to compressor (proto: 1.60, 1.80)

	sensor::Sensor* compressor_energy = new sensor::Sensor();				// kWh, * 100 (proto: 1.60, 1.80)
	sensor::Sensor* add_energy = new sensor::Sensor();							// kWh, * 100 (proto: 1.60, 1.80)
	sensor::Sensor* hot_water_energy = new sensor::Sensor();					// kWh, * 100 (proto: 1.60, 1.80)

	sensor::Sensor* compressor_runtime = new sensor::Sensor();				// minutes (proto: 1.60, 1.80)
	sensor::Sensor* total_runtime = new sensor::Sensor();						// minutes (proto: 1.60, 1.80)

	// heatpump current time
	byte hour; 										// (proto: 1.60, 1.80)
	byte minute; 									// (proto: 1.60, 1.80)
	byte second; 									// (proto: 1.60, 1.80)

	// heatpump current day
	byte day; 										// (proto: 1.60, 1.80)
	byte month; 									// (proto: 1.60, 1.80)
	uint16_t year; 								// (proto: 1.60, 1.80)

	byte day_of_week;								// 1 = monday, 7 = sunday (proto: 1.60, 1.80)

	// current user settings
	text_sensor::TextSensor* fan_speed = new text_sensor::TextSensor();								// 1 = low, 2 = normal, 3 = fast

	sensor::Sensor* room_heating_setting = new sensor::Sensor();				// °C, * 10 (user selected) (proto: 1.60, 1.80)
	sensor::Sensor* hot_water_setting = new sensor::Sensor();					// °C, * 10 (user selected) (proto: 1.60, 1.80)
	binary_sensor::BinarySensor* extra_hot_water_setting = new binary_sensor::BinarySensor();				// true = on, false = off

	text_sensor::TextSensor* hot_water_priority_setting = new text_sensor::TextSensor();			// 1 = low, 2 = normal, 3 = fast

	sensor::Sensor* led_luminosity_setting = new sensor::Sensor();				// 0 = off -> 6 = highest level (proto: 1.60, 1.80)

	// current heatpump calculated setting
	sensor::Sensor* fan_speed_duty = new sensor::Sensor();					// %, * 10 (proto: 1.60, 1.80)
	sensor::Sensor* hot_water_calculated_setting = new sensor::Sensor();	// °C, * 10 (heatpump selected). can be hot_water_setting (no extra hot water) or a different value (proto: 1.60, 1.80)

	text_sensor::TextSensor* unknown_s02_3 = new text_sensor::TextSensor();
	text_sensor::TextSensor* unknown_general_status = new text_sensor::TextSensor();
} COMFORTZONE_STATUS;

}
