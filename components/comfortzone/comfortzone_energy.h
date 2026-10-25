#pragma once
#include <cmath>
#include <cstdint>

namespace esphome { namespace comfortzone {
// Internal input for right-hand energy integration. Public power remains NaN
// when unknown. Exclude gaps instead of attributing them to the next sample.
class ObservedPower {
 public:
  float sample(float power, uint32_t now) {
    const bool valid = std::isfinite(power) && power >= 0;
    const float result = valid && previous_valid_ && now - previous_time_ <= 2000 ? power : 0;
    previous_valid_ = valid;
    previous_time_ = now;
    return result;
  }
 private:
  bool previous_valid_{false};
  uint32_t previous_time_{0};
};
}}
