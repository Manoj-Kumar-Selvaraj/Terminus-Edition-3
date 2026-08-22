#pragma once
#include "sovereign/json.hpp"
#include <cstdint>
#include <string>
#include <vector>

namespace sovereign {
struct Envelope { std::string type; std::string node_id; std::string session_id; std::uint64_t sequence{}; std::string sent_at; std::uint64_t generation{}; std::string digest; Json body; };
class FrameDecoder {
 public:
  explicit FrameDecoder(std::uint32_t maximum) : maximum_(maximum) {}
  std::vector<std::string> push(const std::uint8_t* data, std::size_t size);
  bool empty() const { return buffer_.empty(); }
 private:
  std::uint32_t maximum_; std::vector<std::uint8_t> buffer_;
};
Envelope decode_envelope(const std::string& payload);
std::string encode_envelope(const Envelope& value);
std::vector<std::uint8_t> frame_payload(const std::string& payload, std::uint32_t maximum);
}