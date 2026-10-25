#pragma once
#include <array>
#include <cstdint>
#include <FastCRC.h>

namespace esphome::comfortzone {
// Fixed, captured read request for two bytes at v1.70 heating setting 00:a602.
// Deliberately no arbitrary address, payload or write opcode exposed to API.
inline std::array<uint8_t, 23> heating_read_probe(bool panel_address) {
  std::array<uint8_t, 23> packet = {0x65,0x6f,0xde,0x02,0xd3,0x5e,
    0x45,0x72,0x69,0x63,0x17,'R',1,2,3,4,0x0b,8,0,0xa6,2,2,0};
  if (panel_address) {
    packet[6]=0x41; packet[7]=0x44; packet[8]=0x44; packet[9]=0x52;
  }
  FastCRC8 crc;
  packet.back() = crc.maxim(packet.data(), packet.size()-1);
  return packet;
}
}
