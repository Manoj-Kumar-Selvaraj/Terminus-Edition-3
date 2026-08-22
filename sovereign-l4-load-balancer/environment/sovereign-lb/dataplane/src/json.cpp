#include "sovereign/json.hpp"
#include <charconv>
#include <cctype>
#include <limits>
#include <sstream>

namespace sovereign {
const Json& Json::at(const std::string& key) const { auto found = object().find(key); if (found == object().end()) throw JsonError("missing key: " + key); return found->second; }
bool Json::contains(const std::string& key) const { return is_object() && object().find(key) != object().end(); }

class Parser {
 public:
  explicit Parser(const std::string& input) : input_(input) {}
  Json parse() { skip(); Json value = parse_value(); skip(); if (position_ != input_.size()) fail("trailing input"); return value; }
 private:
  Json parse_value() {
    skip(); if (position_ >= input_.size()) fail("unexpected end");
    char token = input_[position_];
    if (token == '{') return parse_object(); if (token == '[') return parse_array(); if (token == '"') return Json(parse_string());
    if (token == 't') { literal("true"); return Json(true); } if (token == 'f') { literal("false"); return Json(false); } if (token == 'n') { literal("null"); return Json(); }
    if (token == '-' || std::isdigit(static_cast<unsigned char>(token))) return Json(parse_integer());
    fail("invalid token"); return Json();
  }
  Json parse_object() {
    consume('{'); Json::Object result; skip(); if (take('}')) return Json(std::move(result));
    while (true) { skip(); if (peek() != '"') fail("object key required"); std::string key = parse_string(); skip(); consume(':'); Json value = parse_value(); if (!result.emplace(key, std::move(value)).second) fail("duplicate object key"); skip(); if (take('}')) break; consume(','); }
    return Json(std::move(result));
  }
  Json parse_array() {
    consume('['); Json::Array result; skip(); if (take(']')) return Json(std::move(result));
    while (true) { result.push_back(parse_value()); skip(); if (take(']')) break; consume(','); }
    return Json(std::move(result));
  }
  std::string parse_string() {
    consume('"'); std::string result;
    while (position_ < input_.size()) { char value = input_[position_++]; if (value == '"') return result; if (static_cast<unsigned char>(value) < 0x20) fail("control byte in string"); if (value != '\\') { result.push_back(value); continue; }
      if (position_ >= input_.size()) fail("unfinished escape"); char escaped = input_[position_++];
      switch (escaped) { case '"': result.push_back('"'); break; case '\\': result.push_back('\\'); break; case '/': result.push_back('/'); break; case 'b': result.push_back('\b'); break; case 'f': result.push_back('\f'); break; case 'n': result.push_back('\n'); break; case 'r': result.push_back('\r'); break; case 't': result.push_back('\t'); break; default: fail("unsupported escape"); }
    } fail("unterminated string"); return {};
  }
  std::int64_t parse_integer() { std::size_t start = position_; if (take('-') && position_ == input_.size()) fail("invalid integer"); if (take('0')) { if (position_ < input_.size() && std::isdigit(static_cast<unsigned char>(peek()))) fail("leading zero"); } else { while (position_ < input_.size() && std::isdigit(static_cast<unsigned char>(peek()))) position_++; } std::int64_t value{}; auto converted = std::from_chars(input_.data()+start, input_.data()+position_, value); if (converted.ec != std::errc{}) fail("integer out of range"); return value; }
  void literal(const char* text) { while (*text) { if (position_ >= input_.size() || input_[position_++] != *text++) fail("invalid literal"); } }
  void skip() { while (position_ < input_.size() && std::isspace(static_cast<unsigned char>(input_[position_]))) position_++; }
  char peek() const { return position_ < input_.size() ? input_[position_] : '\0'; }
  bool take(char value) { if (peek() != value) return false; position_++; return true; }
  void consume(char value) { if (!take(value)) fail(std::string("expected ") + value); }
  [[noreturn]] void fail(const std::string& reason) const { throw JsonError(reason + " at byte " + std::to_string(position_)); }
  const std::string& input_; std::size_t position_{0};
};

static void append_string(std::string& output, const std::string& value) { output.push_back('"'); for (unsigned char item : value) { switch (item) { case '"': output += "\\\""; break; case '\\': output += "\\\\"; break; case '\n': output += "\\n"; break; case '\r': output += "\\r"; break; case '\t': output += "\\t"; break; default: if (item < 0x20) throw JsonError("control byte cannot be serialized"); output.push_back(static_cast<char>(item)); } } output.push_back('"'); }
static void append_json(std::string& output, const Json& value) {
  std::visit([&output](const auto& item) { using T = std::decay_t<decltype(item)>; if constexpr (std::is_same_v<T,std::nullptr_t>) output += "null"; else if constexpr (std::is_same_v<T,bool>) output += item ? "true" : "false"; else if constexpr (std::is_same_v<T,std::int64_t>) output += std::to_string(item); else if constexpr (std::is_same_v<T,std::string>) append_string(output,item); else if constexpr (std::is_same_v<T,Json::Array>) { output.push_back('['); bool first=true; for (const auto& child:item) { if(!first) output.push_back(','); first=false; append_json(output,child); } output.push_back(']'); } else { output.push_back('{'); bool first=true; for(const auto& [key,child]:item){ if(!first) output.push_back(','); first=false; append_string(output,key); output.push_back(':'); append_json(output,child);} output.push_back('}'); } }, value.value());
}
Json parse_json(const std::string& input) { return Parser(input).parse(); }
std::string write_json(const Json& value) { std::string output; append_json(output,value); return output; }
}