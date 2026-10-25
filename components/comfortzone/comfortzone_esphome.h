#pragma once
#include "comfortzone_energy.h"

#include <cmath>
#include <vector>

#include "esphome/core/component.h"
#include "esphome/components/socket/socket.h"
#include "esphome/components/uart/uart.h"
#include "esphome/components/globals/globals_component.h"
#include "esphome/components/api/custom_api_device.h"

#ifdef USE_BINARY_SENSOR
#include "esphome/components/binary_sensor/binary_sensor.h"
#endif

#ifdef USE_CLIMATE
#include "esphome/components/climate/climate.h"
#endif

#ifdef USE_SENSOR
#include "esphome/components/sensor/sensor.h"
#endif

#ifdef USE_TEXT_SENSOR
#include "esphome/components/text_sensor/text_sensor.h"
#endif

#include "comfortzone_heatpump.h"
#include "comfortzone_controls.h"

namespace esphome::comfortzone
{
class ComfortzoneComponent;
class EspHomeRS485Interface;
#ifdef USE_CLIMATE
  class ComfortzoneHeatpumpClimate : public climate::Climate
  {
  public:
    void control(const climate::ClimateCall &call) override;
    climate::ClimateTraits traits() override;
    void set_parent(ComfortzoneComponent *parent);
  private:
    ComfortzoneComponent *parent_{nullptr};
  };

  class ComfortzoneWaterHeaterClimate : public climate::Climate
  {
  public:
    void control(const climate::ClimateCall &call) override;
    climate::ClimateTraits traits() override;
    void set_parent(ComfortzoneComponent *parent);
  private:
    ComfortzoneComponent *parent_{nullptr};
  };
#endif

  class ComfortzoneComponent :
#ifdef USE_API
      public api::CustomAPIDevice,
#endif
      public Component,
      public uart::UARTDevice
  {
  public:
    float get_setup_priority() const override;

    void set_te3_offset_global(globals::RestoringGlobalsComponent<float> *te3_offset);
    void set_re_de_pin(GPIOPin *re_de_pin);
    void set_rx_idle_pin(int pin) { rx_idle_pin_ = pin; }
    void set_tx_monitor_pin(int pin) { tx_monitor_pin_ = pin; }
    void set_controller_address(uint32_t address) { controller_address_ = address; }

#ifdef USE_SELECT
    void set_fan_select(ComfortzoneFanSelect *entity) { fan_select_ = entity; entity->set_parent(this); }
#endif
#ifdef USE_NUMBER
    void set_curve_number(ComfortzoneCurveNumber *entity) { curve_number_ = entity; entity->set_parent(this); }
#endif
#ifdef USE_SENSOR
    void set_sensors_te10_temp_sensor(sensor::Sensor *value) { sensors_te10_temp_ = value; }
    void set_heating_curve_sensor(sensor::Sensor *value) { heating_curve_ = value; }
    void set_hot_water_max_runtime_sensor(sensor::Sensor *value) { hot_water_max_runtime_ = value; }
    void set_hot_water_pause_time_sensor(sensor::Sensor *value) { hot_water_pause_time_ = value; }
    void set_hot_water_extra_setting_sensor(sensor::Sensor *value) { hot_water_extra_setting_ = value; }
    void set_hot_water_extra_time_sensor(sensor::Sensor *value) { hot_water_extra_time_ = value; }
    void set_normal_fan_speed_sensor(sensor::Sensor *value) { normal_fan_speed_ = value; }
    void set_hot_water_compressor_min_frequency_sensor(sensor::Sensor *value) { hot_water_compressor_min_frequency_ = value; }
    void set_hot_water_compressor_max_frequency_sensor(sensor::Sensor *value) { hot_water_compressor_max_frequency_ = value; }
    void set_pending_alarm_mask_sensor(sensor::Sensor *value) { pending_alarm_mask_ = value; }
    void set_acknowledged_alarm_mask_sensor(sensor::Sensor *value) { acknowledged_alarm_mask_ = value; }
    void set_fan_time_to_filter_change_sensor(sensor::Sensor *fan_time_to_filter_change);
    void set_te0_outdoor_temp_sensor(sensor::Sensor *sensors_te0_outdoor_temp);
    void set_te1_flow_water_sensor(sensor::Sensor *sensors_te1_flow_water);
    void set_te2_return_water_sensor(sensor::Sensor *sensors_te2_return_water);
    void set_te3_indoor_temp_sensor(sensor::Sensor *sensors_te3_indoor_temp);
    void set_te4_hot_gas_temp_sensor(sensor::Sensor *sensors_te4_hot_gas_temp);
    void set_te5_exchanger_out_sensor(sensor::Sensor *sensors_te5_exchanger_out);
    void set_te6_evaporator_in_sensor(sensor::Sensor *sensors_te6_evaporator_in);
    void set_te7_exhaust_air_sensor(sensor::Sensor *sensors_te7_exhaust_air);
    void set_te24_hot_water_temp_sensor(sensor::Sensor *sensors_te24_hot_water_temp);
    void set_current_compressor_frequency_sensor(sensor::Sensor *heatpump_current_compressor_frequency);
    void set_current_compressor_power_sensor(sensor::Sensor *heatpump_current_compressor_power);
    void set_current_add_power_sensor(sensor::Sensor *heatpump_current_add_power);
    void set_current_total_power_sensor(sensor::Sensor *heatpump_current_total_power);
    void set_current_compressor_input_power_sensor(sensor::Sensor *heatpump_current_compressor_input_power);
    void set_current_compressor_heating_input_power_sensor(sensor::Sensor *heatpump_current_compressor_heating_input_power);
    void set_current_compressor_water_input_power_sensor(sensor::Sensor *heatpump_current_compressor_water_input_power);
    void set_compressor_energy_sensor(sensor::Sensor *compressor_energy);
    void set_add_energy_sensor(sensor::Sensor *add_energy);
    void set_hot_water_energy_sensor(sensor::Sensor *hot_water_energy);
    void set_compressor_runtime_sensor(sensor::Sensor *compressor_runtime);
    void set_total_runtime_sensor(sensor::Sensor *total_runtime);
    void set_hot_water_setting_sensor(sensor::Sensor *hot_water_setting);
    void set_room_heating_setting_sensor(sensor::Sensor *room_heating_setting);
    void set_fan_speed_duty_sensor(sensor::Sensor *fan_speed_duty);
    void set_hot_water_calculated_setting_sensor(sensor::Sensor *hot_water_calculated_setting);
    void set_expansion_valve_calculated_setting_sensor(sensor::Sensor *expansion_valve_calculated_setting);
    void set_expansion_valve_temperature_difference_sensor(sensor::Sensor *expansion_valve_temperature_difference);
    void set_heating_cop_sensor(sensor::Sensor *heating_cop);
    void set_water_cop_sensor(sensor::Sensor *water_cop);
    void set_te3_indoor_temp_offset_sensor(sensor::Sensor *sensors_te3_indoor_temp_offset);
    void set_target_flow_water_temperature_sensor(sensor::Sensor *target_flow_water_temperature);
#endif

#ifdef USE_BINARY_SENSOR
    void set_filter_alarm_sensor(binary_sensor::BinarySensor *filter_alarm);
    void set_hot_water_production_sensor(binary_sensor::BinarySensor *hot_water_production);
    void set_room_heating_in_progress_sensor(binary_sensor::BinarySensor *room_heating_in_progress);
    void set_additional_power_enabled_sensor(binary_sensor::BinarySensor *additional_power_enabled);
    void set_defrost_enabled_sensor(binary_sensor::BinarySensor *defrost_enabled);
    void set_extra_hot_water_setting_sensor(binary_sensor::BinarySensor *extra_hot_water_setting);
#endif

#ifdef USE_TEXT_SENSOR
    void set_pump_datetime_sensor(text_sensor::TextSensor *value) { pump_datetime_ = value; }
    void set_last_write_result_sensor(text_sensor::TextSensor *value) { last_write_result_ = value; }
    void set_compressor_activity_sensor(text_sensor::TextSensor *compressor_activity);
    void set_mode_sensor(text_sensor::TextSensor *mode);
    void set_fan_speed_sensor(text_sensor::TextSensor *fan_speed);
    void set_hot_water_priority_setting_sensor(text_sensor::TextSensor *hot_water_priority_setting);
#endif

#ifdef USE_CLIMATE
    void set_heatpump_climate(ComfortzoneHeatpumpClimate *heatpump_climate);
    void set_water_heater_climate(ComfortzoneWaterHeaterClimate *water_heater_climate);
#endif
    comfortzone_heatpump *get_heatpump() const;
    bool request_write(comfortzone_heatpump::WriteKind kind, float value, uint16_t sensor = 0);

    void dump_config() override;

#ifdef USE_API
    void debug_reroute(std::string ip, float port, float timeout);
    void debug_uart(std::string ip, float port, float timeout, float rx_pin);
    void debug_direction();
    void debug_read_probe(float requested_mode);
    void debug_tx_pad();
    void set_sensor_offset(float sensor_num, float temp_offset); // sensor: [0:7], offset in °C (-10.0° -> 10.0°)
    void override_indoor_temperature(float temp);
    void enable_fireplace_mode();
    void disable_fireplace_mode();
#endif

    void setup() override;
    void loop() override;
    void on_shutdown() override;

  private:
#ifdef USE_SELECT
    ComfortzoneFanSelect *fan_select_{nullptr};
#endif
#ifdef USE_NUMBER
    ComfortzoneCurveNumber *curve_number_{nullptr};
#endif
    void finish_write();
#if HP_PROTOCOL == HP_PROTOCOL_1_7
    void publish_operating_170_(uint32_t now);
    uint32_t last_operating_update_{0};
#endif
    EspHomeRS485Interface *rs485_adapter_{nullptr};
    int rx_idle_pin_{-1};
    int tx_monitor_pin_{-1};
    uint8_t probe_phase_{0}; // 0=idle, 1=waiting, 2=DE preamble, 3=receiving
    int probe_mode_{0};
    uint32_t probe_started_{0};
    uint32_t probe_phase_started_{0};
    void poll_read_probe_();
    uint32_t controller_address_{0x45726963};
    bool raw_uart_debug_{false};
    bool direction_active_{false};
    bool direction_settled_{false};
    uint32_t direction_started_{0};
    uint32_t direction_rx_start_{0};
    uint32_t direction_low_samples_{0};
    uint32_t direction_high_samples_{0};
    void disable_debugging();
    void forward_to_udp();
    void set_fireplace_mode(bool enable);

    globals::RestoringGlobalsComponent<float> *te3_offset_{nullptr};

    GPIOPin *re_de_pin_{nullptr};

#ifdef USE_SENSOR
    sensor::Sensor *sensors_te10_temp_{nullptr};
    sensor::Sensor *heating_curve_{nullptr};
    sensor::Sensor *hot_water_max_runtime_{nullptr};
    sensor::Sensor *hot_water_pause_time_{nullptr};
    sensor::Sensor *hot_water_extra_setting_{nullptr};
    sensor::Sensor *hot_water_extra_time_{nullptr};
    sensor::Sensor *normal_fan_speed_{nullptr};
    sensor::Sensor *hot_water_compressor_min_frequency_{nullptr};
    sensor::Sensor *hot_water_compressor_max_frequency_{nullptr};
    sensor::Sensor *pending_alarm_mask_{nullptr};
    sensor::Sensor *acknowledged_alarm_mask_{nullptr};
    sensor::Sensor *fan_time_to_filter_change_{nullptr};   // days (proto: 1.60, 1.80)
    sensor::Sensor *sensors_te0_outdoor_temp_{nullptr};    // °C, * 10 (proto: 1.60, 1.80)
    sensor::Sensor *sensors_te1_flow_water_{nullptr};      // °C, * 10 (proto: 1.60, 1.80)
    sensor::Sensor *sensors_te2_return_water_{nullptr};    // °C, * 10 (proto: 1.60, 1.80)
    sensor::Sensor *sensors_te3_indoor_temp_{nullptr};     // °C, * 10 (proto: 1.60, 1.80)
    sensor::Sensor *sensors_te4_hot_gas_temp_{nullptr};    // °C, * 10 (proto: 1.60, 1.80)
    sensor::Sensor *sensors_te5_exchanger_out_{nullptr};   // °C, * 10 (proto: 1.60, 1.80)
    sensor::Sensor *sensors_te6_evaporator_in_{nullptr};   // °C, * 10 (proto: 1.60, 1.80)
    sensor::Sensor *sensors_te7_exhaust_air_{nullptr};     // °C, * 10 (proto: 1.60, 1.80)
    sensor::Sensor *sensors_te24_hot_water_temp_{nullptr}; // °C, * 10 (proto: 1.60, 1.80)

    sensor::Sensor *heatpump_current_compressor_frequency_{nullptr}; // Hz, * 10 (proto: 1.60, 1.80)

    sensor::Sensor *heatpump_current_compressor_power_{nullptr};               // W = power generated by compressor (proto: 1.60, 1.80)
    sensor::Sensor *heatpump_current_add_power_{nullptr};                      // W = additional power (resistor) (proto: 1.60, 1.80)
    sensor::Sensor *heatpump_current_total_power_{nullptr};                    // W = total power produced (proto: 1.60, 1.80)
    sensor::Sensor *heatpump_current_compressor_input_power_{nullptr};         // W = power sent to compressor (proto: 1.60, 1.80)
    sensor::Sensor *heatpump_current_compressor_heating_input_power_{nullptr}; // W = power sent to compressor (proto: 1.60, 1.80)
    sensor::Sensor *heatpump_current_compressor_water_input_power_{nullptr};   // W = power sent to compressor (proto: 1.60, 1.80)

    sensor::Sensor *compressor_energy_{nullptr}; // kWh, * 100 (proto: 1.60, 1.80)
    sensor::Sensor *add_energy_{nullptr};        // kWh, * 100 (proto: 1.60, 1.80)
    sensor::Sensor *hot_water_energy_{nullptr};  // kWh, * 100 (proto: 1.60, 1.80)

    sensor::Sensor *compressor_runtime_{nullptr}; // minutes (proto: 1.60, 1.80)
    sensor::Sensor *total_runtime_{nullptr};      // minutes (proto: 1.60, 1.80)

    sensor::Sensor *room_heating_setting_{nullptr}; // °C, * 10 (user selected) (proto: 1.60, 1.80)
    sensor::Sensor *hot_water_setting_{nullptr};    // °C, * 10 (user selected) (proto: 1.60, 1.80)

    // current heatpump calculated setting
    sensor::Sensor *fan_speed_duty_{nullptr};               // %, * 10 (proto: 1.60, 1.80)
    sensor::Sensor *hot_water_calculated_setting_{nullptr}; // °C, * 10 (heatpump selected). can be hot_water_setting (no extra hot water) or a different value (proto: 1.60, 1.80)

    sensor::Sensor *expansion_valve_calculated_setting_{nullptr};     // K, * 10 (proto: 1.60, 1.80)
    sensor::Sensor *expansion_valve_temperature_difference_{nullptr}; // K, * 10 (proto: 1.60, 1.80)

    sensor::Sensor *heating_cop_{nullptr};
    sensor::Sensor *water_cop_{nullptr};

    sensor::Sensor *sensors_te3_indoor_temp_offset_{nullptr};

    sensor::Sensor *target_flow_water_temperature_{nullptr};
#endif

#ifdef USE_BINARY_SENSOR
    binary_sensor::BinarySensor *filter_alarm_{nullptr}; // true = replace/clean filter alarm, false = filter ok (proto: 1.60, 1.80)

    binary_sensor::BinarySensor *hot_water_production_{nullptr};     // true = on, false = off
    binary_sensor::BinarySensor *room_heating_in_progress_{nullptr}; // true = on, false = off

    binary_sensor::BinarySensor *additional_power_enabled_{nullptr}; // true = resistor is enabled, false = resistor is disabled (proto: 1.60, 1.80)

    binary_sensor::BinarySensor *defrost_enabled_{nullptr};         // true = defrost in progress, false = no defrost in progress (proto: 1.60, 1.80)
    binary_sensor::BinarySensor *extra_hot_water_setting_{nullptr}; // true = on, false = off
#endif

#ifdef USE_TEXT_SENSOR
    text_sensor::TextSensor *pump_datetime_{nullptr};
    text_sensor::TextSensor *last_write_result_{nullptr};
    int last_clock_second_{-1};
    text_sensor::TextSensor *compressor_activity_{nullptr}; // (proto: 1.60, 1.80)
    text_sensor::TextSensor *mode_{nullptr};                // (proto: 1.60, 1.80)

    // current user settings
    text_sensor::TextSensor *fan_speed_{nullptr}; // 1 = low, 2 = normal, 3 = fast

    text_sensor::TextSensor *hot_water_priority_setting_{nullptr}; // 1 = low, 2 = normal, 3 = fast
#endif

#ifdef USE_CLIMATE
    ComfortzoneHeatpumpClimate *heatpump_climate_{nullptr};
    ComfortzoneWaterHeaterClimate *water_heater_climate_{nullptr};
#endif

    // for debugging purposes
    uint8_t *grab_buffer_ = new uint8_t[256];
    uint16_t grab_frame_size_ = 0;
    uint32_t debug_started_ms_{0};
    uint32_t debug_duration_ms_{0};
    uint32_t last_trace_flush_{0};
    struct sockaddr_in src_addr_;
    struct sockaddr_in dest_addr_;
    std::unique_ptr<socket::Socket> sock_ = nullptr;

    comfortzone_heatpump *heatpump_{nullptr};
    bool pending_write_{false};
    bool pending_offset_override_{false};
    comfortzone_heatpump::WriteKind pending_write_kind_{comfortzone_heatpump::WriteKind::ROOM_TEMPERATURE};
    float pending_write_value_{0};
    uint32_t received_frames_{0};
    uint32_t corrupted_frames_{0};
    uint32_t unknown_frames_{0};
    uint32_t last_bus_report_{0};

    uint32_t last_indoor_temperature_override_{0};
    bool has_indoor_override_{false};
  };
}
