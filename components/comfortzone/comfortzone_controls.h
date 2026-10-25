#pragma once
#include "esphome/core/defines.h"
#ifdef USE_SELECT
#include "esphome/components/select/select.h"
#endif
#ifdef USE_NUMBER
#include "esphome/components/number/number.h"
#endif
#ifdef USE_BUTTON
#include "esphome/components/button/button.h"
#endif
namespace esphome::comfortzone {
class ComfortzoneComponent;
#ifdef USE_SELECT
class ComfortzoneFanSelect : public select::Select {
 public:
  void set_parent(ComfortzoneComponent *parent) { parent_ = parent; }
 protected:
  void control(const std::string &value) override;
  ComfortzoneComponent *parent_{nullptr};
};
#endif
#ifdef USE_NUMBER
class ComfortzoneCurveNumber : public number::Number {
 public:
  void set_parent(ComfortzoneComponent *parent) { parent_ = parent; }
 protected:
  void control(float value) override;
  ComfortzoneComponent *parent_{nullptr};
};
#endif
#ifdef USE_BUTTON
class ComfortzoneHotWaterButton : public button::Button {
 public:
  void set_parent(ComfortzoneComponent *parent) { parent_ = parent; }
  void set_enable(bool enable) { enable_ = enable; }
 protected:
  void press_action() override;
  ComfortzoneComponent *parent_{nullptr};
  bool enable_{false};
};
#endif
}
