#pragma once
#include <cstdint>
#include <cstdlib>

namespace esphome { namespace comfortzone {
// Explicit, bounded hour/minute synchronization. No date, DST or second writes.
// Every write needs both its ACK and a later full clock readback.
class ClockSync {
 public:
  struct Clock {
    bool valid{false};
    int year{}, month{}, day{}, hour{}, minute{}, second{};
    uint32_t sequence{};
  };
  enum class Action { NONE, HOUR, MINUTE, DONE, FAILED };
  bool start(uint32_t now) {
    if (active_) return false;
    active_=true; phase_=0; waiting_ack_=false; started_=now; error_=nullptr;
    return true;
  }
  bool active() const { return active_; }
  int value() const { return value_; }
  const char *error() const { return error_ ? error_ : "Clock synchronization failed"; }
  void acknowledged(bool success, uint32_t sequence, uint32_t now) {
    if (!active_ || !waiting_ack_) return;
    waiting_ack_=false;
    if (!success) { error_="Clock write failed; no retry"; return; }
    read_sequence_=sequence; read_started_=now; ++phase_;
  }
  Action poll(const Clock &pump, const Clock &reference, uint32_t now) {
    if (!active_) return Action::NONE;
    if (error_) return fail(error_);
    if (now-started_ > 90000) return fail("Clock synchronization timed out");
    if (!reference.valid) return fail("Time source is not synchronized");
    if (!pump.valid) return fail("No fresh pump clock readback");
    if (pump.year!=reference.year || pump.month!=reference.month || pump.day!=reference.day)
      return fail("Pump date differs; set the date on the pump first");
    if (waiting_ack_) return Action::NONE;
    if (phase_==1 || phase_==3) {
      if (now-read_started_ > 20000) return fail("Clock write not confirmed by readback");
      if (pump.sequence==read_sequence_) return Action::NONE;
      if (phase_==1) {
        if (pump.hour!=value_) return Action::NONE;
        phase_=2;
      } else {
        const int delta=(pump.hour-reference.hour)*3600+(pump.minute-reference.minute)*60+
                        pump.second-reference.second;
        if (std::abs(delta)<60) { active_=false; return Action::DONE; }
        return Action::NONE;
      }
    }
    if (phase_==0) {
      if (pump.hour!=reference.hour) {
        value_=reference.hour; waiting_ack_=true; return Action::HOUR;
      }
      phase_=2;
    }
    if (phase_==2) {
      // Avoid queuing a value just before the next minute/hour. The bus wait
      // is bounded to 15 seconds; reference time is sampled again each poll.
      if (reference.second>=40) return Action::NONE;
      // An hour rollover during the sequence must not silently succeed.
      if (pump.hour!=reference.hour) return fail("Hour changed during sync; press synchronize again");
      value_=reference.minute; waiting_ack_=true; return Action::MINUTE;
    }
    return Action::NONE;
  }
 private:
  Action fail(const char *reason) { error_=reason; active_=false; return Action::FAILED; }
  bool active_{false}, waiting_ack_{false};
  int phase_{0}, value_{0};
  uint32_t started_{0}, read_started_{0}, read_sequence_{0};
  const char *error_{nullptr};
};
}}
