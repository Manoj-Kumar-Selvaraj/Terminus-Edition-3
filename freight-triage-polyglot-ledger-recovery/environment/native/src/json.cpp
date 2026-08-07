#include "freight/json.h"

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>

namespace freight {
namespace {

const Json& nullValue() {
  static const Json instance;
  return instance;
}

struct Parser {
  const std::string& text;
  size_t pos = 0;
  std::string error;

  explicit Parser(const std::string& source) : text(source) {}

  void skipSpace() {
    while (pos < text.size()) {
      char c = text[pos];
      if (c == ' ' || c == '\t' || c == '\n' || c == '\r') {
        ++pos;
        continue;
      }
      break;
    }
  }

  bool fail(const std::string& message) {
    if (error.empty()) {
      char buffer[64];
      std::snprintf(buffer, sizeof(buffer), " at offset %zu", pos);
      error = message + buffer;
    }
    return false;
  }

  bool parseValue(Json* out) {
    skipSpace();
    if (pos >= text.size()) {
      return fail("unexpected end of input");
    }
    char c = text[pos];
    switch (c) {
      case '{':
        return parseObject(out);
      case '[':
        return parseArray(out);
      case '"': {
        std::string value;
        if (!parseString(&value)) {
          return false;
        }
        *out = Json(value);
        return true;
      }
      case 't':
        return parseLiteral("true", Json(true), out);
      case 'f':
        return parseLiteral("false", Json(false), out);
      case 'n':
        return parseLiteral("null", Json(), out);
      default:
        return parseNumber(out);
    }
  }

  bool parseLiteral(const char* literal, Json value, Json* out) {
    size_t length = std::string(literal).size();
    if (text.compare(pos, length, literal) != 0) {
      return fail("invalid literal");
    }
    pos += length;
    *out = value;
    return true;
  }

  bool parseNumber(Json* out) {
    size_t start = pos;
    if (pos < text.size() && (text[pos] == '-' || text[pos] == '+')) {
      ++pos;
    }
    bool real = false;
    while (pos < text.size()) {
      char c = text[pos];
      if (c >= '0' && c <= '9') {
        ++pos;
        continue;
      }
      if (c == '.' || c == 'e' || c == 'E' || c == '+' || c == '-') {
        real = true;
        ++pos;
        continue;
      }
      break;
    }
    if (start == pos) {
      return fail("invalid number");
    }
    std::string token = text.substr(start, pos - start);
    if (real) {
      *out = Json(std::strtod(token.c_str(), nullptr));
    } else {
      *out = Json(static_cast<long long>(std::strtoll(token.c_str(), nullptr, 10)));
    }
    return true;
  }

  bool parseString(std::string* out) {
    if (pos >= text.size() || text[pos] != '"') {
      return fail("expected string");
    }
    ++pos;
    std::string value;
    while (pos < text.size()) {
      char c = text[pos++];
      if (c == '"') {
        *out = value;
        return true;
      }
      if (c != '\\') {
        value.push_back(c);
        continue;
      }
      if (pos >= text.size()) {
        return fail("truncated escape");
      }
      char esc = text[pos++];
      switch (esc) {
        case '"': value.push_back('"'); break;
        case '\\': value.push_back('\\'); break;
        case '/': value.push_back('/'); break;
        case 'b': value.push_back('\b'); break;
        case 'f': value.push_back('\f'); break;
        case 'n': value.push_back('\n'); break;
        case 'r': value.push_back('\r'); break;
        case 't': value.push_back('\t'); break;
        case 'u': {
          if (pos + 4 > text.size()) {
            return fail("truncated unicode escape");
          }
          unsigned int code = 0;
          for (int i = 0; i < 4; ++i) {
            char h = text[pos + i];
            code <<= 4;
            if (h >= '0' && h <= '9') {
              code |= static_cast<unsigned int>(h - '0');
            } else if (h >= 'a' && h <= 'f') {
              code |= static_cast<unsigned int>(h - 'a' + 10);
            } else if (h >= 'A' && h <= 'F') {
              code |= static_cast<unsigned int>(h - 'A' + 10);
            } else {
              return fail("invalid unicode escape");
            }
          }
          pos += 4;
          appendUtf8(&value, code);
          break;
        }
        default:
          return fail("unknown escape");
      }
    }
    return fail("unterminated string");
  }

  static void appendUtf8(std::string* out, unsigned int code) {
    if (code < 0x80) {
      out->push_back(static_cast<char>(code));
    } else if (code < 0x800) {
      out->push_back(static_cast<char>(0xC0 | (code >> 6)));
      out->push_back(static_cast<char>(0x80 | (code & 0x3F)));
    } else {
      out->push_back(static_cast<char>(0xE0 | (code >> 12)));
      out->push_back(static_cast<char>(0x80 | ((code >> 6) & 0x3F)));
      out->push_back(static_cast<char>(0x80 | (code & 0x3F)));
    }
  }

  bool parseArray(Json* out) {
    ++pos;  // consume '['
    Json result = Json::array();
    skipSpace();
    if (pos < text.size() && text[pos] == ']') {
      ++pos;
      *out = result;
      return true;
    }
    while (true) {
      Json item;
      if (!parseValue(&item)) {
        return false;
      }
      result.push(item);
      skipSpace();
      if (pos >= text.size()) {
        return fail("unterminated array");
      }
      if (text[pos] == ',') {
        ++pos;
        continue;
      }
      if (text[pos] == ']') {
        ++pos;
        *out = result;
        return true;
      }
      return fail("expected ',' or ']'");
    }
  }

  bool parseObject(Json* out) {
    ++pos;  // consume '{'
    Json result = Json::object();
    skipSpace();
    if (pos < text.size() && text[pos] == '}') {
      ++pos;
      *out = result;
      return true;
    }
    while (true) {
      skipSpace();
      std::string key;
      if (!parseString(&key)) {
        return false;
      }
      skipSpace();
      if (pos >= text.size() || text[pos] != ':') {
        return fail("expected ':'");
      }
      ++pos;
      Json value;
      if (!parseValue(&value)) {
        return false;
      }
      result.fields()[key] = value;
      skipSpace();
      if (pos >= text.size()) {
        return fail("unterminated object");
      }
      if (text[pos] == ',') {
        ++pos;
        continue;
      }
      if (text[pos] == '}') {
        ++pos;
        *out = result;
        return true;
      }
      return fail("expected ',' or '}'");
    }
  }
};

}  // namespace

Json::Json() : type_(Type::Null), bool_(false), int_(0), real_(0.0) {}
Json::Json(bool value) : type_(Type::Bool), bool_(value), int_(0), real_(0.0) {}
Json::Json(int value) : type_(Type::Int), bool_(false), int_(value), real_(0.0) {}
Json::Json(long long value) : type_(Type::Int), bool_(false), int_(value), real_(0.0) {}
Json::Json(double value) : type_(Type::Real), bool_(false), int_(0), real_(value) {}
Json::Json(const char* value)
    : type_(Type::String), bool_(false), int_(0), real_(0.0), string_(value ? value : "") {}
Json::Json(std::string value)
    : type_(Type::String), bool_(false), int_(0), real_(0.0), string_(std::move(value)) {}
Json::Json(JsonArray value)
    : type_(Type::Array), bool_(false), int_(0), real_(0.0), array_(std::move(value)) {}
Json::Json(JsonObject value)
    : type_(Type::Object), bool_(false), int_(0), real_(0.0), object_(std::move(value)) {}

Json Json::array() {
  Json value;
  value.type_ = Type::Array;
  return value;
}

Json Json::object() {
  Json value;
  value.type_ = Type::Object;
  return value;
}

bool Json::asBool(bool fallback) const {
  if (type_ == Type::Bool) {
    return bool_;
  }
  if (type_ == Type::Int) {
    return int_ != 0;
  }
  return fallback;
}

long long Json::asInt(long long fallback) const {
  if (type_ == Type::Int) {
    return int_;
  }
  if (type_ == Type::Real) {
    return static_cast<long long>(real_);
  }
  if (type_ == Type::Bool) {
    return bool_ ? 1 : 0;
  }
  return fallback;
}

double Json::asReal(double fallback) const {
  if (type_ == Type::Real) {
    return real_;
  }
  if (type_ == Type::Int) {
    return static_cast<double>(int_);
  }
  return fallback;
}

const std::string& Json::asString() const { return string_; }

std::string Json::asStringOr(const std::string& fallback) const {
  if (type_ == Type::String) {
    return string_;
  }
  return fallback;
}

bool Json::has(const std::string& key) const {
  return type_ == Type::Object && object_.find(key) != object_.end();
}

const Json& Json::at(const std::string& key) const {
  JsonObject::const_iterator it = object_.find(key);
  if (it == object_.end()) {
    return nullValue();
  }
  return it->second;
}

Json& Json::operator[](const std::string& key) {
  if (type_ != Type::Object) {
    type_ = Type::Object;
  }
  return object_[key];
}

void Json::push(Json value) {
  if (type_ != Type::Array) {
    type_ = Type::Array;
  }
  array_.push_back(std::move(value));
}

std::string jsonEscape(const std::string& raw) {
  std::string out;
  out.reserve(raw.size() + 8);
  for (size_t i = 0; i < raw.size(); ++i) {
    unsigned char c = static_cast<unsigned char>(raw[i]);
    switch (c) {
      case '"': out += "\\\""; break;
      case '\\': out += "\\\\"; break;
      case '\b': out += "\\b"; break;
      case '\f': out += "\\f"; break;
      case '\n': out += "\\n"; break;
      case '\r': out += "\\r"; break;
      case '\t': out += "\\t"; break;
      default:
        if (c < 0x20) {
          char buffer[8];
          std::snprintf(buffer, sizeof(buffer), "\\u%04x", c);
          out += buffer;
        } else {
          out.push_back(static_cast<char>(c));
        }
    }
  }
  return out;
}

void Json::render(std::string* out, int indent, int depth) const {
  const std::string pad(static_cast<size_t>(indent * depth), ' ');
  const std::string padInner(static_cast<size_t>(indent * (depth + 1)), ' ');
  const std::string newline = indent > 0 ? "\n" : "";
  switch (type_) {
    case Type::Null:
      *out += "null";
      return;
    case Type::Bool:
      *out += bool_ ? "true" : "false";
      return;
    case Type::Int: {
      char buffer[32];
      std::snprintf(buffer, sizeof(buffer), "%lld", int_);
      *out += buffer;
      return;
    }
    case Type::Real: {
      char buffer[64];
      std::snprintf(buffer, sizeof(buffer), "%.6f", real_);
      *out += buffer;
      return;
    }
    case Type::String:
      out->push_back('"');
      *out += jsonEscape(string_);
      out->push_back('"');
      return;
    case Type::Array: {
      if (array_.empty()) {
        *out += "[]";
        return;
      }
      *out += "[";
      *out += newline;
      for (size_t i = 0; i < array_.size(); ++i) {
        *out += padInner;
        array_[i].render(out, indent, depth + 1);
        if (i + 1 < array_.size()) {
          *out += ",";
        }
        *out += newline;
      }
      *out += pad;
      *out += "]";
      return;
    }
    case Type::Object: {
      if (object_.empty()) {
        *out += "{}";
        return;
      }
      *out += "{";
      *out += newline;
      size_t index = 0;
      for (JsonObject::const_iterator it = object_.begin(); it != object_.end(); ++it, ++index) {
        *out += padInner;
        out->push_back('"');
        *out += jsonEscape(it->first);
        *out += "\": ";
        it->second.render(out, indent, depth + 1);
        if (index + 1 < object_.size()) {
          *out += ",";
        }
        *out += newline;
      }
      *out += pad;
      *out += "}";
      return;
    }
  }
}

std::string Json::dump(int indent) const {
  std::string out;
  render(&out, indent, 0);
  return out;
}

std::string Json::dumpCompact() const {
  std::string out;
  render(&out, 0, 0);
  return out;
}

bool Json::parse(const std::string& text, Json* out, std::string* error) {
  Parser parser(text);
  Json value;
  if (!parser.parseValue(&value)) {
    if (error != nullptr) {
      *error = parser.error;
    }
    return false;
  }
  parser.skipSpace();
  *out = value;
  return true;
}

bool Json::parseFile(const std::string& path, Json* out, std::string* error) {
  std::ifstream stream(path.c_str(), std::ios::binary);
  if (!stream) {
    if (error != nullptr) {
      *error = "cannot open " + path;
    }
    return false;
  }
  std::ostringstream buffer;
  buffer << stream.rdbuf();
  return parse(buffer.str(), out, error);
}

}  // namespace freight
