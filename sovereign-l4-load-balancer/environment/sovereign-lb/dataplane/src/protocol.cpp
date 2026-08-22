#include "sovereign/protocol.hpp"
#include <arpa/inet.h>
#include <cstring>
#include <set>

namespace sovereign {
std::vector<std::string> FrameDecoder::push(const std::uint8_t* data, std::size_t size) {
  buffer_.insert(buffer_.end(), data, data+size); std::vector<std::string> frames;
  while (buffer_.size() >= 4) { std::uint32_t network{}; std::memcpy(&network,buffer_.data(),4); std::uint32_t length=ntohl(network); if(length==0||length>maximum_) throw JsonError("invalid frame length"); if(buffer_.size()<4+length) break; frames.emplace_back(reinterpret_cast<const char*>(buffer_.data()+4),length); buffer_.erase(buffer_.begin(),buffer_.begin()+4+length); }
  return frames;
}
static std::string text(const Json& root,const std::string& key){ return root.at(key).string(); }
static std::uint64_t positive(const Json& root,const std::string& key){ auto value=root.at(key).integer(); if(value<1) throw JsonError(key+" must be positive"); return static_cast<std::uint64_t>(value); }
Envelope decode_envelope(const std::string& payload) { Json root=parse_json(payload); if(!root.is_object()) throw JsonError("envelope must be object"); static const std::set<std::string> types={"hello","prepare","prepared","rejected","activate","active","status"}; Envelope result; result.type=text(root,"type"); if(!types.contains(result.type)) throw JsonError("unknown message type"); result.node_id=text(root,"node_id"); result.session_id=text(root,"session_id"); result.sequence=positive(root,"sequence"); result.sent_at=text(root,"sent_at"); result.body=root.at("body"); if(root.contains("generation")) result.generation=positive(root,"generation"); if(root.contains("digest")) result.digest=text(root,"digest"); if(result.node_id.empty()||result.session_id.empty()||!result.body.is_object()) throw JsonError("incomplete envelope"); if(result.type!="hello"&&result.type!="status"&&(result.generation==0||result.digest.size()!=64)) throw JsonError("generation envelope incomplete"); return result; }
std::string encode_envelope(const Envelope& value) { Json::Object root{{"body",value.body},{"node_id",Json(value.node_id)},{"sent_at",Json(value.sent_at)},{"sequence",Json(static_cast<std::int64_t>(value.sequence))},{"session_id",Json(value.session_id)},{"type",Json(value.type)}}; if(value.generation){root.emplace("digest",Json(value.digest));root.emplace("generation",Json(static_cast<std::int64_t>(value.generation)));} return write_json(Json(std::move(root))); }
std::vector<std::uint8_t> frame_payload(const std::string& payload,std::uint32_t maximum){if(payload.empty()||payload.size()>maximum)throw JsonError("invalid frame size");std::vector<std::uint8_t> output(4+payload.size());std::uint32_t length=htonl(static_cast<std::uint32_t>(payload.size()));std::memcpy(output.data(),&length,4);std::memcpy(output.data()+4,payload.data(),payload.size());return output;}
}