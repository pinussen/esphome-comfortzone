#include "comfortzone_esphome.h"

#include <cmath>
#include <cstring>
#include <vector>
#include "comfortzone_heatpump.h"
#include "esphome_rs485.h"
#include "comfortzone_probe.h"
#include "esp_rom_sys.h"
#include "esphome/components/uart/uart_component_esp_idf.h"
#include "hal/gpio_ll.h"
#include "hal/uart_ll.h"
#include "soc/gpio_struct.h"
#include "esphome/core/version.h"

#include "esphome/components/api/api_server.h"

namespace esphome::comfortzone
{
  static const char *TAG = "comfortzone";

#ifdef USE_SENSOR
  static void on_temperature_sensor_update(int16_t value, void *context)
  {
    if (!context)
    {
      return;
    }
    auto sensor = (sensor::Sensor *)context;
    sensor->publish_state(value == -990 || value == -999 ? NAN : (float)value / 10.0);
  }

  static void on_integer_sensor_update(int16_t value, void *context) {
    if (context) static_cast<sensor::Sensor *>(context)->publish_state(value);
  }

  static void on_frequency_sensor_update(int16_t value, void *context)
  {
    if (!context)
    {
      return;
    }
    auto sensor = (sensor::Sensor *)context;
    sensor->publish_state((float)value / 10.0);
  }

  static void on_power_sensor_update(int16_t value, void *context)
  {
    if (!context)
    {
      return;
    }
    auto sensor = (sensor::Sensor *)context;
    sensor->publish_state(value);
  }

  static void on_energy_sensor_update(uint32_t value, void *context)
  {
    if (!context)
    {
      return;
    }
    auto sensor = (sensor::Sensor *)context;
    sensor->publish_state((float)value / 100.0);
  }

  static void on_minutes_sensor_update(uint32_t value, void *context)
  {
    if (!context)
    {
      return;
    }
    auto sensor = (sensor::Sensor *)context;
    sensor->publish_state(value);
  }

  static void on_days_sensor_update(uint16_t value, void *context)
  {
    if (!context)
    {
      return;
    }
    auto sensor = (sensor::Sensor *)context;
    sensor->publish_state(value);
  }

  static void on_percentage_sensor_update(uint16_t value, void *context)
  {
    if (!context)
    {
      return;
    }
    auto sensor = (sensor::Sensor *)context;
    sensor->publish_state((float)value / 10.0);
  }
#endif

#ifdef USE_BINARY_SENSOR
  static void on_bool_sensor_update(bool value, void *context)
  {
    if (!context)
    {
      return;
    }
    auto sensor = (binary_sensor::BinarySensor *)context;
    sensor->publish_state(value);
  }
#endif

#ifdef USE_TEXT_SENSOR
  static void on_speed_sensor_update(byte value, void *context)
  {
    if (!context)
    {
      return;
    }
    auto sensor = (text_sensor::TextSensor *)context;
    if (value == 1)
    {
      sensor->publish_state("low");
    }
    else if (value == 2)
    {
      sensor->publish_state("normal");
    }
    else if (value == 3)
    {
      sensor->publish_state("fast");
    }
    else
    {
      sensor->publish_state("incorrect");
    }
  }

  static void on_mode_sensor_update(COMFORTZONE_MODE value, void *context)
  {
    if (!context)
    {
      return;
    }
    auto sensor = (text_sensor::TextSensor *)context;
    if (value == CZMD_IDLE)
    {
      sensor->publish_state("idle");
    }
    else if (value == CZMD_ROOM_HEATING)
    {
      sensor->publish_state("heating");
    }
    else if (value == CZMD_HOT_WATER)
    {
      sensor->publish_state("hot_water");
    }
//    else if (value == CZMD_ROOM_HEATING_AND_HOT_WATER)
//    {
//      sensor->publish_state("heating_and_hot_water");
//    }
    else
    {
      sensor->publish_state("incorrect");
    }
  }

  static void on_compressor_activity_sensor_update(COMFORTZONE_COMPRESSOR_ACTIVITY value, void *context)
  {
    if (!context)
    {
      return;
    }
    auto sensor = (text_sensor::TextSensor *)context;
    if (value == CZCMP_STOPPED)
    {
      sensor->publish_state("stopped");
    }
//    else if (value == CZCMP_DEFROST)
//    {
//      sensor->publish_state("defrost");
//    }
    else if (value == CZCMP_RUNNING)
    {
      sensor->publish_state("running");
    }
    else if (value == CZCMP_STOPPING)
    {
      sensor->publish_state("stopping");
    }
    else
    {
      sensor->publish_state("incorrect");
    }
  }
#endif

#ifdef USE_CLIMATE
  void ComfortzoneHeatpumpClimate::control(const climate::ClimateCall &call)
  {
    if (call.get_mode().has_value() && *call.get_mode() != climate::CLIMATE_MODE_HEAT) {
      ESP_LOGW(TAG, "Heat/off control is not implemented; request rejected"); return;
    }
    if (parent_ && call.get_target_temperature().has_value())
      parent_->request_write(comfortzone_heatpump::WriteKind::ROOM_TEMPERATURE, *call.get_target_temperature());
  }

  climate::ClimateTraits ComfortzoneHeatpumpClimate::traits()
  {
    // The capabilities of the climate device
    auto traits = climate::ClimateTraits();
#if ESPHOME_VERSION_CODE >= VERSION_CODE(2026, 3, 0)
    traits.add_feature_flags(climate::CLIMATE_SUPPORTS_CURRENT_TEMPERATURE);
#else
    traits.set_supports_current_temperature(true);
#endif
    traits.set_supported_modes({climate::CLIMATE_MODE_HEAT});
    return traits;
  }

  void ComfortzoneHeatpumpClimate::set_parent(ComfortzoneComponent *parent)
  {
    parent_ = parent;
  }

  void ComfortzoneWaterHeaterClimate::control(const climate::ClimateCall &call)
  {
    if (call.get_mode().has_value() && *call.get_mode() != climate::CLIMATE_MODE_HEAT) {
      ESP_LOGW(TAG, "Heat/off control is not implemented; request rejected"); return;
    }
    if (parent_ && call.get_target_temperature().has_value())
      parent_->request_write(comfortzone_heatpump::WriteKind::HOT_WATER_TEMPERATURE, *call.get_target_temperature());
  }

  climate::ClimateTraits ComfortzoneWaterHeaterClimate::traits()
  {
    // The capabilities of the climate device
    auto traits = climate::ClimateTraits();
#if ESPHOME_VERSION_CODE >= VERSION_CODE(2026, 3, 0)
    traits.add_feature_flags(climate::CLIMATE_SUPPORTS_CURRENT_TEMPERATURE);
#else
    traits.set_supports_current_temperature(true);
#endif
    traits.set_supported_modes({climate::CLIMATE_MODE_HEAT});
    return traits;
  }

  void ComfortzoneWaterHeaterClimate::set_parent(ComfortzoneComponent *parent)
  {
    parent_ = parent;
  }
#endif

  float ComfortzoneComponent::get_setup_priority() const { return esphome::setup_priority::DATA; }

  void ComfortzoneComponent::set_te3_offset_global(globals::RestoringGlobalsComponent<float> *te3_offset)
  {
    this->te3_offset_ = te3_offset;
  }

  void ComfortzoneComponent::set_re_de_pin(GPIOPin *re_de_pin) {
    this->re_de_pin_ = re_de_pin;

    // pull down the pin ASAP to avoid any communication with the heatpump
    this->re_de_pin_->digital_write(false);
  }

#ifdef USE_SENSOR
  void ComfortzoneComponent::set_fan_time_to_filter_change_sensor(sensor::Sensor *fan_time_to_filter_change) { this->fan_time_to_filter_change_ = fan_time_to_filter_change; }
  void ComfortzoneComponent::set_te0_outdoor_temp_sensor(sensor::Sensor *sensors_te0_outdoor_temp) { this->sensors_te0_outdoor_temp_ = sensors_te0_outdoor_temp; }
  void ComfortzoneComponent::set_te1_flow_water_sensor(sensor::Sensor *sensors_te1_flow_water) { this->sensors_te1_flow_water_ = sensors_te1_flow_water; }
  void ComfortzoneComponent::set_te2_return_water_sensor(sensor::Sensor *sensors_te2_return_water) { this->sensors_te2_return_water_ = sensors_te2_return_water; }
  void ComfortzoneComponent::set_te3_indoor_temp_sensor(sensor::Sensor *sensors_te3_indoor_temp) { this->sensors_te3_indoor_temp_ = sensors_te3_indoor_temp; }
  void ComfortzoneComponent::set_te4_hot_gas_temp_sensor(sensor::Sensor *sensors_te4_hot_gas_temp) { this->sensors_te4_hot_gas_temp_ = sensors_te4_hot_gas_temp; }
  void ComfortzoneComponent::set_te5_exchanger_out_sensor(sensor::Sensor *sensors_te5_exchanger_out) { this->sensors_te5_exchanger_out_ = sensors_te5_exchanger_out; }
  void ComfortzoneComponent::set_te6_evaporator_in_sensor(sensor::Sensor *sensors_te6_evaporator_in) { this->sensors_te6_evaporator_in_ = sensors_te6_evaporator_in; }
  void ComfortzoneComponent::set_te7_exhaust_air_sensor(sensor::Sensor *sensors_te7_exhaust_air) { this->sensors_te7_exhaust_air_ = sensors_te7_exhaust_air; }
  void ComfortzoneComponent::set_te24_hot_water_temp_sensor(sensor::Sensor *sensors_te24_hot_water_temp) { this->sensors_te24_hot_water_temp_ = sensors_te24_hot_water_temp; }
  void ComfortzoneComponent::set_current_compressor_frequency_sensor(sensor::Sensor *heatpump_current_compressor_frequency) { this->heatpump_current_compressor_frequency_ = heatpump_current_compressor_frequency; }
  void ComfortzoneComponent::set_current_compressor_power_sensor(sensor::Sensor *heatpump_current_compressor_power) { this->heatpump_current_compressor_power_ = heatpump_current_compressor_power; }
  void ComfortzoneComponent::set_current_add_power_sensor(sensor::Sensor *heatpump_current_add_power) { this->heatpump_current_add_power_ = heatpump_current_add_power; }
  void ComfortzoneComponent::set_current_total_power_sensor(sensor::Sensor *heatpump_current_total_power) { this->heatpump_current_total_power_ = heatpump_current_total_power; }
  void ComfortzoneComponent::set_current_compressor_input_power_sensor(sensor::Sensor *heatpump_current_compressor_input_power) { this->heatpump_current_compressor_input_power_ = heatpump_current_compressor_input_power; }
  void ComfortzoneComponent::set_current_compressor_heating_input_power_sensor(sensor::Sensor *heatpump_current_compressor_heating_input_power) { this->heatpump_current_compressor_heating_input_power_ = heatpump_current_compressor_heating_input_power; }
  void ComfortzoneComponent::set_current_compressor_water_input_power_sensor(sensor::Sensor *heatpump_current_compressor_water_input_power) { this->heatpump_current_compressor_water_input_power_ = heatpump_current_compressor_water_input_power; }
  void ComfortzoneComponent::set_compressor_energy_sensor(sensor::Sensor *compressor_energy) { this->compressor_energy_ = compressor_energy; }
  void ComfortzoneComponent::set_add_energy_sensor(sensor::Sensor *add_energy) { this->add_energy_ = add_energy; }
  void ComfortzoneComponent::set_hot_water_energy_sensor(sensor::Sensor *hot_water_energy) { this->hot_water_energy_ = hot_water_energy; }
  void ComfortzoneComponent::set_compressor_runtime_sensor(sensor::Sensor *compressor_runtime) { this->compressor_runtime_ = compressor_runtime; }
  void ComfortzoneComponent::set_total_runtime_sensor(sensor::Sensor *total_runtime) { this->total_runtime_ = total_runtime; }
  void ComfortzoneComponent::set_hot_water_setting_sensor(sensor::Sensor *hot_water_setting) { this->hot_water_setting_ = hot_water_setting; }
  void ComfortzoneComponent::set_room_heating_setting_sensor(sensor::Sensor *room_heating_setting) { this->room_heating_setting_ = room_heating_setting; }
  void ComfortzoneComponent::set_fan_speed_duty_sensor(sensor::Sensor *fan_speed_duty) { this->fan_speed_duty_ = fan_speed_duty; }
  void ComfortzoneComponent::set_hot_water_calculated_setting_sensor(sensor::Sensor *hot_water_calculated_setting) { this->hot_water_calculated_setting_ = hot_water_calculated_setting; }
  void ComfortzoneComponent::set_expansion_valve_calculated_setting_sensor(sensor::Sensor *expansion_valve_calculated_setting) { this->expansion_valve_calculated_setting_ = expansion_valve_calculated_setting; }
  void ComfortzoneComponent::set_expansion_valve_temperature_difference_sensor(sensor::Sensor *expansion_valve_temperature_difference) { this->expansion_valve_temperature_difference_ = expansion_valve_temperature_difference; }
  void ComfortzoneComponent::set_heating_cop_sensor(sensor::Sensor *heating_cop) { this->heating_cop_ = heating_cop; }
  void ComfortzoneComponent::set_water_cop_sensor(sensor::Sensor *water_cop) { this->water_cop_ = water_cop; }
  void ComfortzoneComponent::set_te3_indoor_temp_offset_sensor(sensor::Sensor *sensors_te3_indoor_temp_offset) { this->sensors_te3_indoor_temp_offset_ = sensors_te3_indoor_temp_offset; }
  void ComfortzoneComponent::set_target_flow_water_temperature_sensor(sensor::Sensor *target_flow_water_temperature) { this->target_flow_water_temperature_ = target_flow_water_temperature; }
#endif

#ifdef USE_BINARY_SENSOR
  void ComfortzoneComponent::set_filter_alarm_sensor(binary_sensor::BinarySensor *filter_alarm) { this->filter_alarm_ = filter_alarm; }
  void ComfortzoneComponent::set_hot_water_production_sensor(binary_sensor::BinarySensor *hot_water_production) { this->hot_water_production_ = hot_water_production; }
  void ComfortzoneComponent::set_room_heating_in_progress_sensor(binary_sensor::BinarySensor *room_heating_in_progress) { this->room_heating_in_progress_ = room_heating_in_progress; }
  void ComfortzoneComponent::set_additional_power_enabled_sensor(binary_sensor::BinarySensor *additional_power_enabled) { this->additional_power_enabled_ = additional_power_enabled; }
  void ComfortzoneComponent::set_defrost_enabled_sensor(binary_sensor::BinarySensor *defrost_enabled) { this->defrost_enabled_ = defrost_enabled; }
  void ComfortzoneComponent::set_extra_hot_water_setting_sensor(binary_sensor::BinarySensor *extra_hot_water_setting) { this->extra_hot_water_setting_ = extra_hot_water_setting; }
#endif

#ifdef USE_TEXT_SENSOR
  void ComfortzoneComponent::set_compressor_activity_sensor(text_sensor::TextSensor *compressor_activity) { this->compressor_activity_ = compressor_activity; }
  void ComfortzoneComponent::set_mode_sensor(text_sensor::TextSensor *mode) { this->mode_ = mode; }
  void ComfortzoneComponent::set_fan_speed_sensor(text_sensor::TextSensor *fan_speed) { this->fan_speed_ = fan_speed; }
  void ComfortzoneComponent::set_hot_water_priority_setting_sensor(text_sensor::TextSensor *hot_water_priority_setting) { this->hot_water_priority_setting_ = hot_water_priority_setting; }
#endif

#ifdef USE_CLIMATE
  void ComfortzoneComponent::set_heatpump_climate(ComfortzoneHeatpumpClimate *heatpump_climate)
  {
    this->heatpump_climate_ = heatpump_climate;
    if (heatpump_climate_)
      heatpump_climate_->set_parent(this);
  }
  void ComfortzoneComponent::set_water_heater_climate(ComfortzoneWaterHeaterClimate *water_heater_climate)
  {
    this->water_heater_climate_ = water_heater_climate;
    if (water_heater_climate_)
      water_heater_climate_->set_parent(this);
  }

#endif

  comfortzone_heatpump *ComfortzoneComponent::get_heatpump() const
  {
    return heatpump_;
  }

  void ComfortzoneComponent::setup()
  {
    rs485_adapter_ = new EspHomeRS485Interface(this, re_de_pin_, rx_idle_pin_);
    heatpump_ = new comfortzone_heatpump(rs485_adapter_);
    const byte controller_address[] = {static_cast<byte>(controller_address_ >> 24),
                                      static_cast<byte>(controller_address_ >> 16),
                                      static_cast<byte>(controller_address_ >> 8),
                                      static_cast<byte>(controller_address_)};
    heatpump_->set_controller_addr(controller_address);

    //esp_log_level_set("*", ESP_LOG_DEBUG);
    ESP_LOGI("Main", "Logging is working!");
    ESP_LOGI(TAG, "Free heap: %d", esp_get_free_heap_size());
    auto &status = heatpump_->comfortzone_status;
    status.sensors_te3_indoor_temp.subscribe([](int16_t raw, void *context) {
      auto *self = static_cast<ComfortzoneComponent *>(context);
#ifdef USE_SENSOR
      on_temperature_sensor_update(raw, self->sensors_te3_indoor_temp_);
#endif
#ifdef USE_CLIMATE
      if (self->heatpump_climate_) {
        self->heatpump_climate_->current_temperature = raw == -990 || raw == -999 ? NAN : raw / 10.0f;
        self->heatpump_climate_->mode = climate::CLIMATE_MODE_HEAT;
        self->heatpump_climate_->publish_state();
      }
#endif
    }, this);
    status.sensors_te24_hot_water_temp.subscribe([](int16_t raw, void *context) {
      auto *self = static_cast<ComfortzoneComponent *>(context);
#ifdef USE_SENSOR
      on_temperature_sensor_update(raw, self->sensors_te24_hot_water_temp_);
#endif
#ifdef USE_CLIMATE
      if (self->water_heater_climate_) {
        self->water_heater_climate_->current_temperature = raw == -990 || raw == -999 ? NAN : raw / 10.0f;
        self->water_heater_climate_->mode = climate::CLIMATE_MODE_HEAT;
        self->water_heater_climate_->publish_state();
      }
#endif
    }, this);
    status.room_heating_setting.subscribe([](int16_t raw, void *context) {
      auto *self = static_cast<ComfortzoneComponent *>(context);
#ifdef USE_SENSOR
      on_temperature_sensor_update(raw, self->room_heating_setting_);
#endif
#ifdef USE_CLIMATE
      if (self->heatpump_climate_) {
        self->heatpump_climate_->target_temperature = raw == -990 || raw == -999 ? NAN : raw / 10.0f;
        self->heatpump_climate_->mode = climate::CLIMATE_MODE_HEAT;
        self->heatpump_climate_->publish_state();
      }
#endif
    }, this);
    status.hot_water_setting.subscribe([](int16_t raw, void *context) {
      auto *self = static_cast<ComfortzoneComponent *>(context);
#ifdef USE_SENSOR
      on_temperature_sensor_update(raw, self->hot_water_setting_);
#endif
#ifdef USE_CLIMATE
      if (self->water_heater_climate_) {
        self->water_heater_climate_->target_temperature = raw == -990 || raw == -999 ? NAN : raw / 10.0f;
        self->water_heater_climate_->mode = climate::CLIMATE_MODE_HEAT;
        self->water_heater_climate_->publish_state();
      }
#endif
    }, this);
    status.fan_speed.subscribe([](byte value, void *context) {
      auto *self = static_cast<ComfortzoneComponent *>(context);
#ifdef USE_TEXT_SENSOR
      on_speed_sensor_update(value, self->fan_speed_);
#endif
#ifdef USE_SELECT
      if (self->fan_select_ && value >= 1 && value <= 3)
        self->fan_select_->publish_state(value == 1 ? "Low" : value == 2 ? "Normal" : "High");
#endif
    }, this);
    status.heating_curve.subscribe([](int16_t value, void *context) {
      auto *self = static_cast<ComfortzoneComponent *>(context);
#ifdef USE_SENSOR
      on_integer_sensor_update(value, self->heating_curve_);
#endif
#ifdef USE_NUMBER
      if (self->curve_number_) self->curve_number_->publish_state(value);
#endif
    }, this);


#ifdef USE_SENSOR
    status.sensors_te0_outdoor_temp.subscribe(on_temperature_sensor_update, sensors_te0_outdoor_temp_);
    status.sensors_te1_flow_water.subscribe(on_temperature_sensor_update, sensors_te1_flow_water_);
    status.sensors_te2_return_water.subscribe(on_temperature_sensor_update, sensors_te2_return_water_);
    status.sensors_te4_hot_gas_temp.subscribe(on_temperature_sensor_update, sensors_te4_hot_gas_temp_);
    status.sensors_te5_exchanger_out.subscribe(on_temperature_sensor_update, sensors_te5_exchanger_out_);
    status.sensors_te6_evaporator_in.subscribe(on_temperature_sensor_update, sensors_te6_evaporator_in_);
    status.sensors_te7_exhaust_air.subscribe(on_temperature_sensor_update, sensors_te7_exhaust_air_);

    status.sensors_te10_temp.subscribe(on_temperature_sensor_update, sensors_te10_temp_);
    status.hot_water_max_runtime.subscribe(on_integer_sensor_update, hot_water_max_runtime_);
    status.hot_water_pause_time.subscribe(on_integer_sensor_update, hot_water_pause_time_);
    status.hot_water_extra_setting.subscribe(on_temperature_sensor_update, hot_water_extra_setting_);
    status.hot_water_extra_time.subscribe(on_integer_sensor_update, hot_water_extra_time_);
    status.normal_fan_speed.subscribe(on_temperature_sensor_update, normal_fan_speed_);
    status.hot_water_compressor_min_frequency.subscribe(on_frequency_sensor_update, hot_water_compressor_min_frequency_);
    status.hot_water_compressor_max_frequency.subscribe(on_frequency_sensor_update, hot_water_compressor_max_frequency_);
    status.pending_alarm_mask.subscribe(on_days_sensor_update, pending_alarm_mask_);
    status.acknowledged_alarm_mask.subscribe(on_days_sensor_update, acknowledged_alarm_mask_);

    status.expansion_valve_calculated_setting.subscribe(on_temperature_sensor_update, expansion_valve_calculated_setting_);
    status.expansion_valve_temperature_difference.subscribe(on_temperature_sensor_update, expansion_valve_temperature_difference_);

    status.heatpump_current_compressor_frequency.subscribe(on_frequency_sensor_update, heatpump_current_compressor_frequency_);
    status.heatpump_current_compressor_power.subscribe(on_power_sensor_update, heatpump_current_compressor_power_);
    status.heatpump_current_add_power.subscribe(on_power_sensor_update, heatpump_current_add_power_);
    status.heatpump_current_total_power.subscribe(on_power_sensor_update, heatpump_current_total_power_);
    status.heatpump_current_compressor_input_power.subscribe(on_power_sensor_update, heatpump_current_compressor_input_power_);

    status.compressor_energy.subscribe(on_energy_sensor_update, compressor_energy_);
    status.add_energy.subscribe(on_energy_sensor_update, add_energy_);
    status.hot_water_energy.subscribe(on_energy_sensor_update, hot_water_energy_);

    status.compressor_runtime.subscribe(on_minutes_sensor_update, compressor_runtime_);
    status.total_runtime.subscribe(on_minutes_sensor_update, total_runtime_);

    status.fan_speed_duty.subscribe(on_percentage_sensor_update, fan_speed_duty_);

    status.hot_water_calculated_setting.subscribe(on_temperature_sensor_update, hot_water_calculated_setting_);


    status.fan_time_to_filter_change.subscribe(on_days_sensor_update, fan_time_to_filter_change_);

    status.calculated_flow_set.subscribe(on_temperature_sensor_update, target_flow_water_temperature_);

    if (te3_offset_ && sensors_te3_indoor_temp_offset_)
    {
      sensors_te3_indoor_temp_offset_->publish_state(id(te3_offset_));
    }
#endif

#ifdef USE_BINARY_SENSOR
    status.filter_alarm.subscribe(on_bool_sensor_update, filter_alarm_);
    status.hot_water_production.subscribe(on_bool_sensor_update, hot_water_production_);
    status.room_heating_in_progress.subscribe(on_bool_sensor_update, room_heating_in_progress_);
    status.additional_power_enabled.subscribe(on_bool_sensor_update, additional_power_enabled_);

    status.extra_hot_water_setting.subscribe(on_bool_sensor_update, extra_hot_water_setting_);
    status.defrost_enabled.subscribe(on_bool_sensor_update, defrost_enabled_);
#endif

#ifdef USE_TEXT_SENSOR
    status.compressor_activity.subscribe(on_compressor_activity_sensor_update, compressor_activity_);
    status.mode.subscribe(on_mode_sensor_update, mode_);
    status.hot_water_priority_setting.subscribe(on_speed_sensor_update, hot_water_priority_setting_);
#endif



#ifdef USE_API
    // Services exposed to Home Assistant are declared here
    register_service(&ComfortzoneComponent::set_sensor_offset, "set_sensor_offset",
                     {"sensor_num", "offset"});
    register_service(&ComfortzoneComponent::override_indoor_temperature, "override_indoor_temperature",
                     {"current_temperature"});
    register_service(&ComfortzoneComponent::debug_reroute, "debug_reroute",
                     {"ip", "port", "timeout"});
    register_service(&ComfortzoneComponent::debug_uart, "debug_uart",
                     {"ip", "port", "timeout", "rx_pin"});
    register_service(&ComfortzoneComponent::debug_direction, "debug_direction", {});
    register_service(&ComfortzoneComponent::debug_read_probe, "debug_read_probe", {"mode"});
    register_service(&ComfortzoneComponent::debug_tx_pad, "debug_tx_pad", {});
    register_service(&ComfortzoneComponent::enable_fireplace_mode, "enable_fireplace_mode",
                     {});
    register_service(&ComfortzoneComponent::disable_fireplace_mode, "disable_fireplace_mode",
                     {});
#endif

    heatpump_->begin();
    heatpump_->enable_debug_mode(true);
  }

  void ComfortzoneComponent::loop()
  {
    // Keep parsing/logging throughout the test; restore locally even if the
    // API client disappears. Unsigned elapsed time also handles millis wrap.
    if (direction_active_) {
      const uint32_t elapsed = esphome::millis() - direction_started_;
      if (elapsed >= 2000) {
        rs485_adapter_->enable_receiver_mode();
        direction_active_ = false;
        ESP_LOGI(TAG, "Direction hold ended: DE restored LOW after %u ms; RX bytes after settling=%u, pin LOW/HIGH samples=%u/%u",
                 static_cast<unsigned>(elapsed),
                 static_cast<unsigned>(direction_settled_ ? rs485_adapter_->rx_byte_count() - direction_rx_start_ : 0),
                 static_cast<unsigned>(direction_low_samples_), static_cast<unsigned>(direction_high_samples_));
      } else if (elapsed >= 100) {
        if (!direction_settled_) {
          direction_rx_start_ = rs485_adapter_->rx_byte_count();
          direction_settled_ = true;
        }
        if (gpio_get_level(static_cast<gpio_num_t>(rx_idle_pin_))) ++direction_high_samples_;
        else ++direction_low_samples_;
      }
    }
    rs485_adapter_->sample_rx_pin();
    const auto frame = heatpump_->process();
    if (frame != comfortzone_heatpump::PFT_NONE) ++received_frames_;
    if (frame == comfortzone_heatpump::PFT_CORRUPTED) ++corrupted_frames_;
    if (frame == comfortzone_heatpump::PFT_UNKNOWN) ++unknown_frames_;
    const uint32_t now = esphome::millis();
    if (now - last_bus_report_ >= 30000) {
      last_bus_report_ = now;
      ESP_LOGI(TAG, "RS485: frames=%u CRC errors=%u unknown registers=%u", received_frames_, corrupted_frames_, unknown_frames_);
    }
#ifdef USE_TEXT_SENSOR
    auto &clock = heatpump_->comfortzone_status;
    if (pump_datetime_ && clock.year.has_value() && clock.second.has_value() &&
        last_clock_second_ != static_cast<byte>(clock.second)) {
      last_clock_second_ = static_cast<byte>(clock.second);
      char value[32];
      snprintf(value, sizeof(value), "%04u-%02u-%02u %02u:%02u:%02u",
               static_cast<unsigned>(clock.year), static_cast<unsigned>(clock.month),
               static_cast<unsigned>(clock.day), static_cast<unsigned>(clock.hour),
               static_cast<unsigned>(clock.minute), static_cast<unsigned>(clock.second));
      pump_datetime_->publish_state(value);
    }
#endif
    poll_read_probe_();
    if (!direction_active_ && probe_phase_ == 0) {
      heatpump_->poll_write();
      finish_write();
    }

#ifdef USE_SENSOR
    // Derive from library state, independently of optional HA sensor entities.
    if (frame == comfortzone_heatpump::PFT_REPLY) {
      const auto &s = heatpump_->comfortzone_status;
      float heating = NAN, water = NAN, heating_cop = NAN, water_cop = NAN;
      if (s.mode.has_value() && s.heatpump_current_compressor_input_power.has_value() &&
          s.heatpump_current_add_power.has_value()) {
        const float input = static_cast<int16_t>(s.heatpump_current_compressor_input_power) +
                            static_cast<int16_t>(s.heatpump_current_add_power);
        const float cop = input > 0 && s.heatpump_current_total_power.has_value()
            ? static_cast<int16_t>(s.heatpump_current_total_power) / input : NAN;
        if (s.mode == CZMD_ROOM_HEATING) { heating = input; water = 0; heating_cop = cop; }
        else if (s.mode == CZMD_HOT_WATER) { heating = 0; water = input; water_cop = cop; }
        else if (s.mode == CZMD_IDLE && input == 0) { heating = water = 0; }
        // Unknown / simultaneous modes cannot safely partition energy by use.
      }
      if (heatpump_current_compressor_heating_input_power_) heatpump_current_compressor_heating_input_power_->publish_state(heating);
      if (heatpump_current_compressor_water_input_power_) heatpump_current_compressor_water_input_power_->publish_state(water);
      if (heating_cop_) heating_cop_->publish_state(heating_cop);
      if (water_cop_) water_cop_->publish_state(water_cop);
    }
#endif

    if (debug_duration_ms_ != 0)
    {
      if (esphome::millis() - debug_started_ms_ >= debug_duration_ms_)
      {
        disable_debugging();
      }
      else if (raw_uart_debug_ && sock_)
      {
        const auto size = rs485_adapter_->trace_size();
        // Batch raw byte/sample records; per-loop UDP floods lost trace packets.
        if (size && (size >= 900 || now - last_trace_flush_ >= 20)) {
          last_trace_flush_ = now;
          sock_->sendto(rs485_adapter_->trace_data(), size, 0, (struct sockaddr *)&dest_addr_, sizeof(dest_addr_));
          rs485_adapter_->clear_trace();
        }
      }
      else if (frame != comfortzone_heatpump::PFT_NONE && grab_frame_size_ > 0 && sock_)
      {
        forward_to_udp();
      }
    }
  }

  void ComfortzoneComponent::disable_debugging()
  {
    debug_duration_ms_ = 0;
    raw_uart_debug_ = false;
    if (rs485_adapter_) rs485_adapter_->set_trace(false);
    if (heatpump_) heatpump_->set_grab_buffer(nullptr, 0, nullptr);
    grab_frame_size_ = 0;

    if (sock_)
    {
      ESP_LOGE(TAG, "Shutting down debug socket");
      sock_->shutdown(0);
      sock_->close();
      sock_ = nullptr;
    }
    ESP_LOGE(TAG, "Debugging disabled");
  }

  void ComfortzoneComponent::forward_to_udp()
  {
    int err = sock_->sendto(grab_buffer_, grab_frame_size_, 0, (struct sockaddr *)&dest_addr_, sizeof(dest_addr_));
    if (err < 0)
    {
      ESP_LOGE(TAG, "Error occurred during sending: errno %d", errno);
      disable_debugging();
      return;
    }
  }

  void ComfortzoneComponent::dump_config()
  {
    ESP_LOGCONFIG(TAG, "Comfortzone initialized, protocol=%d, asynchronous writes", HP_PROTOCOL);
    ESP_LOGCONFIG(TAG, "Controller address: %08lX", static_cast<unsigned long>(controller_address_));
    ESP_LOGCONFIG(TAG, "Physical RX edge detection: %s (GPIO%d)",
                  rs485_adapter_->edge_detection_ready() ? "enabled" : "disabled", rx_idle_pin_);
#if HP_PROTOCOL == HP_PROTOCOL_1_7
    ESP_LOGCONFIG(TAG, "Protocol 170: bounded register ranges; fan, curve and hot water controls");
#endif
  }

  void ComfortzoneComponent::on_shutdown()
  {
    if (rs485_adapter_) rs485_adapter_->enable_receiver_mode();
    direction_active_ = false;
    probe_phase_ = 0;
  }

  void ComfortzoneComponent::poll_read_probe_()
  {
    if (probe_phase_ == 0) return;
    const uint32_t now = esphome::millis();
    const uint32_t preamble_ms = probe_mode_ < 2 ? 0 : probe_mode_ < 4 ? 20 : 100;
    if (probe_phase_ == 1 && (rs485_adapter_->idle_break(100) || now - probe_started_ >= 5000)) {
      ESP_LOGI(TAG, "Read probe acquiring bus: mode=%d idle=%d preamble=%u ms",
               probe_mode_, rs485_adapter_->idle_break(100), static_cast<unsigned>(preamble_ms));
      rs485_adapter_->enable_sender_mode();
      probe_phase_ = 2;
      probe_phase_started_ = now;
    }
    if (probe_phase_ == 2 && now - probe_phase_started_ >= preamble_ms) {
      const auto packet = heating_read_probe(probe_mode_ % 2 != 0);
      const uint32_t edges = rs485_adapter_->tx_edges();
      const int tx_before = gpio_get_level(static_cast<gpio_num_t>(tx_monitor_pin_));
      const auto started = esp_timer_get_time();
      rs485_adapter_->write_bytes(packet.data(), packet.size());
      const auto queued = esp_timer_get_time();
      unsigned low = 0, high = 0, transitions = 0;
      int previous = tx_before;
      // Independent pad sampling checks that a zero ISR count is not merely
      // interrupt instrumentation failure. Bound the observation to 15 ms.
      while (esp_timer_get_time() - queued < 15000) {
        const int level = gpio_get_level(static_cast<gpio_num_t>(tx_monitor_pin_));
        if (level) ++high; else ++low;
        if (level != previous) ++transitions;
        previous = level;
        esp_rom_delay_us(4);
      }
      rs485_adapter_->flush();
      const auto duration = esp_timer_get_time() - started;
      const int tx_after = gpio_get_level(static_cast<gpio_num_t>(tx_monitor_pin_));
      rs485_adapter_->enable_receiver_mode();
      probe_phase_ = 3;
      probe_phase_started_ = esphome::millis();
      ESP_LOGI(TAG, "Read probe sent: mode=%d bytes=23 tx_us=%u GPIO%d edges=%u idle=%d/%d; DE restored LOW",
               probe_mode_, static_cast<unsigned>(duration), tx_monitor_pin_,
               static_cast<unsigned>(rs485_adapter_->tx_edges()-edges), tx_before, tx_after);
      ESP_LOGI(TAG, "TX pad samples: queued_us=%u low/high=%u/%u transitions=%u",
               static_cast<unsigned>(queued-started), low, high, transitions);
    }
    if (probe_phase_ == 3 && now - probe_phase_started_ < 0x80000000U && now - probe_phase_started_ >= 3000) {
      probe_phase_ = 0;
      ESP_LOGI(TAG, "Read probe finished: mode=%d, inspect raw trace for reply", probe_mode_);
    }
  }

#ifdef USE_API
  void ComfortzoneComponent::debug_tx_pad()
  {
    if (!rs485_adapter_ || !heatpump_ || tx_monitor_pin_ < 0 || probe_phase_ || direction_active_ ||
        pending_write_ || heatpump_->write_busy()) return;
    rs485_adapter_->enable_receiver_mode();
    // With DE low this only tests the local DI wire, not the RS485 bus.
    const auto pin = static_cast<gpio_num_t>(tx_monitor_pin_);
    const auto port = static_cast<uart_port_t>(static_cast<uart::IDFUARTComponent *>(parent_)->get_hw_serial_number());
    gpio_set_level(pin, 1);
    const auto direction_result = gpio_set_direction(pin, GPIO_MODE_INPUT_OUTPUT);
    const auto level_result = gpio_set_level(pin, 0); esp_rom_delay_us(500);
    const int low = gpio_get_level(pin);
    const unsigned latch_low = (GPIO.out >> tx_monitor_pin_) & 1;
    gpio_io_config_t low_cfg{};
    const auto cfg_result = gpio_get_io_config(pin, &low_cfg);
    gpio_set_level(pin, 1); esp_rom_delay_us(500);
    const int high = gpio_get_level(pin);
    gpio_hold_dis(pin);
    gpio_set_level(pin, 0); esp_rom_delay_us(500);
    const int unheld_low = gpio_get_level(pin);
    gpio_set_level(pin, 1); esp_rom_delay_us(500);
    const int unheld_high = gpio_get_level(pin);
    // Also bypass peripheral output-enable arbitration, ruling out its state
    // before diagnosing an external load or a damaged output stage.
    gpio_ll_set_output_enable_ctrl(&GPIO, tx_monitor_pin_, false, false);
    gpio_ll_output_enable(&GPIO, tx_monitor_pin_);
    gpio_set_level(pin, 0); esp_rom_delay_us(500);
    const int forced_low = gpio_get_level(pin);
    gpio_set_level(pin, 1); esp_rom_delay_us(500);
    const int forced_high = gpio_get_level(pin);
    // Isolate the physical TX pad before testing the UART's internal path.
    // DE remains low, and the external TX output stays disabled throughout.
    const auto disabled = gpio_set_direction(pin, GPIO_MODE_INPUT);
    int loop_count = -1;
    bool loop_match = false;
    if (disabled == ESP_OK) {
      for (unsigned i=0; i<2048 && available(); ++i) read();
      const auto expected = heating_read_probe(false);
      uint8_t received[23]{};
      uart_ll_set_loop_back(UART_LL_GET_HW(port), true);
      // Finish a possible external character, then clear both the driver and
      // ESPHome peek cache after isolating RX. Otherwise stale pump bytes can
      // make a working internal loopback look like a failure.
      esp_rom_delay_us(1000);
      static_cast<uart::IDFUARTComponent *>(parent_)->flush_input();
      uart_write_bytes(port, expected.data(), expected.size());
      uart_wait_tx_done(port, pdMS_TO_TICKS(100));
      loop_count = uart_read_bytes(port, received, sizeof(received), pdMS_TO_TICKS(30));
      uart_ll_set_loop_back(UART_LL_GET_HW(port), false);
      loop_match = loop_count == sizeof(received) && std::memcmp(received, expected.data(), sizeof(received)) == 0;
    }
    const auto restored = uart_set_pin(port, tx_monitor_pin_, UART_PIN_NO_CHANGE,
                                       UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    if (restored != ESP_OK) parent_->load_settings(false);
    const bool observed = rs485_adapter_->observe_tx(tx_monitor_pin_);
    ESP_LOGI(TAG, "TX pad self-test: GPIO%d UART%d requested LOW/HIGH read=%d/%d; after hold_dis=%d/%d; UART restore=%d monitor=%d DE=LOW",
             tx_monitor_pin_, static_cast<int>(port), low, high, unheld_low, unheld_high,
             static_cast<int>(restored), observed);
    ESP_LOGI(TAG, "TX pad LOW configuration: api=%d/%d/%d latch=%u mux=%u signal=%u IE=%d OE=%d peripheral_oe=%d; physical_input=%d",
             static_cast<int>(direction_result), static_cast<int>(level_result), static_cast<int>(cfg_result),
             latch_low, static_cast<unsigned>(low_cfg.fun_sel), static_cast<unsigned>(low_cfg.sig_out),
             low_cfg.ie, low_cfg.oe, low_cfg.oe_ctrl_by_periph, low);
    ESP_LOGI(TAG, "UART internal loopback: physical TX disabled=%d bytes=%d match=%d; normal UART and DE LOW restored",
             disabled == ESP_OK, loop_count, loop_match);
    ESP_LOGI(TAG, "TX pad forced GPIO output-enable: requested LOW/HIGH read=%d/%d", forced_low, forced_high);
  }

  void ComfortzoneComponent::debug_read_probe(float requested_mode)
  {
    if (HP_PROTOCOL != HP_PROTOCOL_1_7 || !std::isfinite(requested_mode) || requested_mode < 0 ||
        requested_mode > 5 || std::floor(requested_mode) != requested_mode || !rs485_adapter_ || !heatpump_ ||
        rx_idle_pin_ < 0 || tx_monitor_pin_ < 0 || probe_phase_ || direction_active_ ||
        pending_write_ || heatpump_->write_busy()) {
      ESP_LOGW(TAG, "Read probe refused: invalid mode/protocol or busy");
      return;
    }
    const int mode = static_cast<int>(requested_mode);
    if (!rs485_adapter_->observe_tx(tx_monitor_pin_)) {
      ESP_LOGW(TAG, "Read probe refused: cannot observe TX pad");
      return;
    }
    gpio_io_config_t cfg{};
    if (gpio_get_io_config(static_cast<gpio_num_t>(tx_monitor_pin_), &cfg) == ESP_OK) {
      ESP_LOGI(TAG, "TX pad config GPIO%d: mux=%u signal=%u input=%d output=%d peripheral_oe=%d open_drain=%d",
               tx_monitor_pin_, static_cast<unsigned>(cfg.fun_sel), static_cast<unsigned>(cfg.sig_out),
               cfg.ie, cfg.oe, cfg.oe_ctrl_by_periph, cfg.od);
    }
    // This explicit diagnostic may interrupt traffic after a 5 s wait. It only
    // sends the fixed R command; no settings are changed and there is no retry.
    probe_mode_ = mode;
    probe_started_ = esphome::millis();
    probe_phase_ = 1;
    ESP_LOGI(TAG, "Read probe queued: mode=%d (address=%s)", mode, mode % 2 ? "ADDR" : "Eric");
  }

  void ComfortzoneComponent::debug_direction()
  {
    // Explicit diagnostic: drives the bus for two seconds without UART data.
    // May disturb pump/panel communication. No configurable indefinite hold.
    if (!rs485_adapter_ || !heatpump_ || rx_idle_pin_ < 0 ||
        direction_active_ || probe_phase_ || pending_write_ || heatpump_->write_busy()) {
      ESP_LOGW(TAG, "Direction hold refused: unavailable RX pin or test/write in progress");
      return;
    }
    direction_started_ = esphome::millis();
    direction_rx_start_ = rs485_adapter_->rx_byte_count();
    direction_low_samples_ = direction_high_samples_ = 0;
    direction_settled_ = false;
    direction_active_ = true;
    rs485_adapter_->enable_sender_mode();
    ESP_LOGI(TAG, "Direction hold started: DE HIGH for 2000 ms; UART reading continues, no UART bytes sent");
  }

  void ComfortzoneComponent::debug_uart(std::string ip, float port, float timeout, float rx_pin)
  {
    if (!std::isfinite(rx_pin) || rx_pin < 0 || rx_pin > 39 || std::floor(rx_pin) != rx_pin ||
        !GPIO_IS_VALID_GPIO(static_cast<int>(rx_pin)) || !std::isfinite(port) || port < 1 || port > 65535 ||
        std::floor(port) != port || !std::isfinite(timeout) || timeout < 1 || timeout > 3600 ||
        inet_addr(ip.c_str()) == INADDR_NONE) return;
    debug_reroute(ip, port, timeout);
    if (!sock_) return;
    sock_->setblocking(false);
    heatpump_->set_grab_buffer(nullptr, 0, nullptr);
    raw_uart_debug_ = true;
    rs485_adapter_->set_trace_rx_pin(static_cast<int>(rx_pin));
    rs485_adapter_->set_trace(true);
    ESP_LOGI(TAG, "Raw UART trace enabled (software read timestamps)");
  }

  void ComfortzoneComponent::debug_reroute(std::string ip, float port, float timeout)
  {
    if (!heatpump_ || !std::isfinite(port) || port < 1 || port > 65535 || std::floor(port) != port ||
        !std::isfinite(timeout) || timeout < 1 || timeout > 3600 || inet_addr(ip.c_str()) == INADDR_NONE) {
      ESP_LOGE(TAG, "Invalid debug destination, port or duration (1-3600 seconds)");
      return;
    }
    disable_debugging();
    const int port_i = static_cast<int>(port);
    const int timeout_i = static_cast<int>(timeout);

    debug_started_ms_ = esphome::millis();
    debug_duration_ms_ = timeout_i * 1000U;
    heatpump_->set_grab_buffer(grab_buffer_, 256, &grab_frame_size_);

    memset(&src_addr_, 0, sizeof(src_addr_));
    src_addr_.sin_family = AF_INET;
    src_addr_.sin_addr.s_addr = htonl(INADDR_ANY);
    src_addr_.sin_port = htons(9502);

    dest_addr_.sin_addr.s_addr = inet_addr(ip.c_str());
    dest_addr_.sin_family = AF_INET;
    dest_addr_.sin_port = htons(port_i);

    sock_ = socket::socket(AF_INET, SOCK_DGRAM, IPPROTO_IP);
    if (!sock_)
    {
      ESP_LOGE(TAG, "Unable to create socket: errno %d", errno);
      disable_debugging();
      return;
    }

    if (sock_->bind((struct sockaddr *)&src_addr_, sizeof(src_addr_)) < 0)
    {
      ESP_LOGE(TAG, "Unable to bind socket: errno %d", errno);
      disable_debugging();
      return;
    }

    ESP_LOGI(TAG, "Debugging enabled, forwarding to %s:%d for %d seconds", ip.c_str(), port_i, timeout_i);
  }

  void ComfortzoneComponent::set_sensor_offset(float sensor_num, float temp_offset)
  {
    if (!std::isfinite(sensor_num) || sensor_num < 0 || sensor_num > 7 || std::floor(sensor_num) != sensor_num) {
      ESP_LOGE(TAG, "Sensor number must be an integer from 0 to 7");
      return;
    }
    request_write(comfortzone_heatpump::WriteKind::SENSOR_OFFSET, temp_offset, static_cast<uint16_t>(sensor_num));
  }

  void ComfortzoneComponent::override_indoor_temperature(float temp)
  {
#ifdef USE_SENSOR
    if (!std::isfinite(temp) || !te3_offset_ || !sensors_te3_indoor_temp_ || !sensors_te3_indoor_temp_offset_ ||
        !sensors_te3_indoor_temp_->has_state() ||
        (has_indoor_override_ && esphome::millis() - last_indoor_temperature_override_ < 300000U)) return;
    const float offset = id(te3_offset_) + temp - sensors_te3_indoor_temp_->state;
    if (std::abs(offset - id(te3_offset_)) < 0.1f) return;
    if (request_write(comfortzone_heatpump::WriteKind::SENSOR_OFFSET, offset, 3))
      pending_offset_override_ = true;
#endif
  }

  void ComfortzoneComponent::enable_fireplace_mode() { set_fireplace_mode(true); }
  void ComfortzoneComponent::disable_fireplace_mode() { set_fireplace_mode(false); }
#endif

  void ComfortzoneComponent::set_fireplace_mode(bool enable)
  {
    request_write(comfortzone_heatpump::WriteKind::FIREPLACE, enable ? 1.0f : 0.0f);
  }

  bool ComfortzoneComponent::request_write(comfortzone_heatpump::WriteKind kind, float value, uint16_t sensor)
  {
    if (!heatpump_ || pending_write_ || direction_active_ || probe_phase_) {
      ESP_LOGW(TAG, "Write rejected: component unavailable, direction test active or another write is pending");
      return false;
    }
    if (!heatpump_->begin_write(kind, value, sensor)) {
      ESP_LOGW(TAG, "Write rejected: %s", heatpump_->last_message);
#ifdef USE_TEXT_SENSOR
      if (last_write_result_) last_write_result_->publish_state(heatpump_->last_message);
#endif
      return false;
    }
#ifdef USE_TEXT_SENSOR
    if (last_write_result_) last_write_result_->publish_state("Waiting for bus");
#endif
    pending_write_ = true;
    pending_offset_override_ = false;
    pending_write_kind_ = kind;
    pending_write_value_ = value;
    ESP_LOGI(TAG, "Write accepted: kind=%d value=%.1f sensor=%u", static_cast<int>(kind), value, sensor);
    return true;
  }

  void ComfortzoneComponent::finish_write()
  {
    if (!pending_write_ || heatpump_->write_busy()) return;
    pending_write_ = false;
#ifdef USE_TEXT_SENSOR
    if (last_write_result_) last_write_result_->publish_state(heatpump_->last_message);
#endif
    if (heatpump_->write_result() != comfortzone_heatpump::WriteResult::SUCCESS) {
      ESP_LOGW(TAG, "Write failed: %s", heatpump_->last_message);
      return;
    }
    ESP_LOGI(TAG, "Write succeeded: %s", heatpump_->last_message);
#ifdef USE_CLIMATE
    auto *entity = pending_write_kind_ == comfortzone_heatpump::WriteKind::ROOM_TEMPERATURE
        ? static_cast<climate::Climate *>(heatpump_climate_)
        : pending_write_kind_ == comfortzone_heatpump::WriteKind::HOT_WATER_TEMPERATURE
          ? static_cast<climate::Climate *>(water_heater_climate_) : nullptr;
    if (entity) {
      entity->target_temperature = std::round(pending_write_value_ * 10.0f) / 10.0f;
      entity->publish_state();
    }
#endif
#if defined(USE_API) && defined(USE_SENSOR)
    if (pending_offset_override_ && te3_offset_ && sensors_te3_indoor_temp_offset_) {
      id(te3_offset_) = pending_write_value_;
      sensors_te3_indoor_temp_offset_->publish_state(pending_write_value_);
      last_indoor_temperature_override_ = esphome::millis();
      has_indoor_override_ = true;
    }
#endif
  }

  void app_error_handler(int err_code, uint32_t line_num, const char *p_file_name) {
    ESP_LOGE(TAG, "Error occurred! Code: %d, Line: %u, File: %s", err_code, static_cast<unsigned>(line_num), p_file_name);
  }

}
