#include "comfortzone_esphome.h"
namespace esphome::comfortzone {
#ifdef USE_SELECT
void ComfortzoneFanSelect::control(const std::string &value) {
  if (!parent_) return;
  const int setting = value == "Low" ? 1 : value == "Normal" ? 2 : value == "High" ? 3 : 0;
  if (setting) parent_->request_write(comfortzone_heatpump::WriteKind::FAN_SPEED, setting);
}
#endif
#ifdef USE_NUMBER
void ComfortzoneCurveNumber::control(float value) {
  if (parent_) parent_->request_write(comfortzone_heatpump::WriteKind::HEATING_CURVE, value);
}
#endif
#ifdef USE_BUTTON
void ComfortzoneHotWaterButton::press_action() {
  if (!parent_) return;
  if (action_ == 2) { parent_->start_clock_sync(); return; }
  parent_->request_write(action_ == 1 ? comfortzone_heatpump::WriteKind::FIREPLACE :
                         comfortzone_heatpump::WriteKind::EXTRA_HOT_WATER, enable_ ? 1 : 0);
}
#endif
}
