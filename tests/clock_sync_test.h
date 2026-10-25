#pragma once
#include "../components/comfortzone/comfortzone_clock_sync.h"

inline void test_clock_sync() {
  using Sync=esphome::comfortzone::ClockSync;
  using A=Sync::Action;
  Sync sync;
  Sync::Clock pump{true,2026,10,25,20,14,8,1}, ref{true,2026,10,25,20,10,0,0};
  assert(sync.start(100)); assert(!sync.start(100));
  assert(sync.poll(pump,ref,100)==A::MINUTE && sync.value()==10);
  assert(sync.poll(pump,ref,200)==A::NONE); // one write at a time
  sync.acknowledged(true,1,200);
  pump.minute=10;
  assert(sync.poll(pump,ref,300)==A::NONE); // ACK/cache alone is not readback
  pump.sequence=2;
  assert(sync.poll(pump,ref,400)==A::DONE && !sync.active());
  assert(sync.start(1000)); pump.hour=19;
  assert(sync.poll(pump,ref,1000)==A::HOUR && sync.value()==20);
  sync.acknowledged(true,2,1100); pump.hour=20; pump.sequence=3;
  assert(sync.poll(pump,ref,1200)==A::MINUTE);
  sync.acknowledged(false,3,1300);
  assert(sync.poll(pump,ref,1400)==A::FAILED && !sync.active());
  sync.start(2000); ref.valid=false;
  assert(sync.poll(pump,ref,2000)==A::FAILED); ref.valid=true;
  sync.start(3000); pump.day=24;
  assert(sync.poll(pump,ref,3000)==A::FAILED); pump.day=25;
  sync.start(4000); pump.valid=false;
  assert(sync.poll(pump,ref,4000)==A::FAILED); pump.valid=true;
  sync.start(5000); ref.second=50;
  assert(sync.poll(pump,ref,5000)==A::NONE);
  ref.second=0; ref.minute=11;
  assert(sync.poll(pump,ref,15000)==A::MINUTE && sync.value()==11);
  sync.acknowledged(true,3,16000);
  assert(sync.poll(pump,ref,36001)==A::FAILED); // no fresh readback
  sync.start(0xfffffff0U); ref.minute=12;
  assert(sync.poll(pump,ref,0x10U)==A::MINUTE);
  sync.acknowledged(true,3,0x20U); pump.sequence=4; pump.minute=12;
  assert(sync.poll(pump,ref,0x30U)==A::DONE);
  sync.start(100); assert(sync.poll(pump,ref,90101)==A::FAILED);
}
