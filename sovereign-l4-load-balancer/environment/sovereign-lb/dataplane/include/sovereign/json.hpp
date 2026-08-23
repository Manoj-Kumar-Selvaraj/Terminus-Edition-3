#pragma once
#include <cstdint>
#include <map>
#include <stdexcept>
#include <string>
#include <variant>
#include <vector>

namespace sovereign {
class Json {
 public:
  using Array = std::vector<Json>;
  using Object = std::map<std::string, Json>;
  using Value = std::variant<std::nullptr_t, bool, std::int64_t, std::string, Array, Object>;
  Json() : value_(nullptr) {}
  Json(bool value) : value_(value) {}
  Json(std::int64_t value) : value_(value) {}
  Json(std::string value) : value_(std::move(value)) {}
  Json(Array value) : value_(std::move(value)) {}
  Json(Object value) : value_(std::move(value)) {}
  bool is_object() const { return std::holds_alternative<Object>(value_); }
  bool is_array() const { return std::holds_alternative<Array>(value_); }
  const Object& object() const { return std::get<Object>(value_); }
  const Array& array() const { return std::get<Array>(value_); }
  const std::string& string() const { return std::get<std::string>(value_); }
  std::int64_t integer() const { return std::get<std::int64_t>(value_); }
  bool boolean() const { return std::get<bool>(value_); }
  const Json& at(const std::string& key) const;
  bool contains(const std::string& key) const;
  const Value& value() const { return value_; }
 private:
  Value value_;
};

class JsonError : public std::runtime_error { public: using std::runtime_error::runtime_error; };
Json parse_json(const std::string& input);
std::string write_json(const Json& value);
}