#ifndef FREIGHT_JSON_H
#define FREIGHT_JSON_H

// Minimal dependency-free JSON value, parser and canonical writer.
//
// The writer always emits object keys in ascending byte order, two space
// indentation and LF line endings so artifacts are reproducible.

#include <cstdint>
#include <map>
#include <string>
#include <vector>

namespace freight {

class Json;

using JsonArray = std::vector<Json>;
using JsonObject = std::map<std::string, Json>;

class Json {
 public:
  enum class Type { Null, Bool, Int, Real, String, Array, Object };

  Json();
  Json(bool value);
  Json(int value);
  Json(long long value);
  Json(double value);
  Json(const char* value);
  Json(std::string value);
  Json(JsonArray value);
  Json(JsonObject value);

  static Json array();
  static Json object();

  Type type() const { return type_; }
  bool isNull() const { return type_ == Type::Null; }
  bool isBool() const { return type_ == Type::Bool; }
  bool isInt() const { return type_ == Type::Int; }
  bool isReal() const { return type_ == Type::Real; }
  bool isNumber() const { return type_ == Type::Int || type_ == Type::Real; }
  bool isString() const { return type_ == Type::String; }
  bool isArray() const { return type_ == Type::Array; }
  bool isObject() const { return type_ == Type::Object; }

  bool asBool(bool fallback = false) const;
  long long asInt(long long fallback = 0) const;
  double asReal(double fallback = 0.0) const;
  const std::string& asString() const;
  std::string asStringOr(const std::string& fallback) const;

  const JsonArray& items() const { return array_; }
  JsonArray& items() { return array_; }
  const JsonObject& fields() const { return object_; }
  JsonObject& fields() { return object_; }

  bool has(const std::string& key) const;
  const Json& at(const std::string& key) const;
  Json& operator[](const std::string& key);
  void push(Json value);

  std::string dump(int indent = 2) const;
  std::string dumpCompact() const;

  static bool parse(const std::string& text, Json* out, std::string* error);
  static bool parseFile(const std::string& path, Json* out, std::string* error);

 private:
  void render(std::string* out, int indent, int depth) const;

  Type type_;
  bool bool_;
  long long int_;
  double real_;
  std::string string_;
  JsonArray array_;
  JsonObject object_;
};

std::string jsonEscape(const std::string& raw);

}  // namespace freight

#endif  // FREIGHT_JSON_H
