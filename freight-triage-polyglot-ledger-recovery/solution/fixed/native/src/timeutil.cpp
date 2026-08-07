#include "freight/timeutil.h"

#include <cstdio>
#include <cstdlib>

namespace freight {

const long long kFreightEpochSeconds = 1577836800LL;
const long long kWindowSeconds = 21600LL;

namespace {

bool isLeap(long long year) {
  return (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0);
}

long long daysFromCivil(long long year, long long month, long long day) {
  static const int cumulative[12] = {0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334};
  long long y = year;
  long long days = 0;
  if (y >= 1970) {
    for (long long cursor = 1970; cursor < y; ++cursor) {
      days += isLeap(cursor) ? 366 : 365;
    }
  } else {
    for (long long cursor = y; cursor < 1970; ++cursor) {
      days -= isLeap(cursor) ? 366 : 365;
    }
  }
  days += cumulative[month - 1];
  if (month > 2 && isLeap(y)) {
    days += 1;
  }
  days += day - 1;
  return days;
}

bool readInt(const std::string& text, size_t offset, size_t width, long long* out) {
  if (offset + width > text.size()) {
    return false;
  }
  long long value = 0;
  for (size_t i = 0; i < width; ++i) {
    char c = text[offset + i];
    if (c < '0' || c > '9') {
      return false;
    }
    value = value * 10 + (c - '0');
  }
  *out = value;
  return true;
}

}  // namespace

bool parseOffsetTimestamp(const std::string& text, long long* unixSeconds) {
  if (text.size() < 19) {
    return false;
  }
  long long year = 0;
  long long month = 0;
  long long day = 0;
  long long hour = 0;
  long long minute = 0;
  long long second = 0;
  if (!readInt(text, 0, 4, &year) || text[4] != '-') {
    return false;
  }
  if (!readInt(text, 5, 2, &month) || text[7] != '-') {
    return false;
  }
  if (!readInt(text, 8, 2, &day)) {
    return false;
  }
  if (text[10] != 'T' && text[10] != ' ') {
    return false;
  }
  if (!readInt(text, 11, 2, &hour) || text[13] != ':') {
    return false;
  }
  if (!readInt(text, 14, 2, &minute) || text[16] != ':') {
    return false;
  }
  if (!readInt(text, 17, 2, &second)) {
    return false;
  }
  if (month < 1 || month > 12 || day < 1 || day > 31) {
    return false;
  }

  long long offsetMinutes = 0;
  size_t cursor = 19;
  if (cursor < text.size() && text[cursor] == '.') {
    ++cursor;
    while (cursor < text.size() && text[cursor] >= '0' && text[cursor] <= '9') {
      ++cursor;
    }
  }
  if (cursor >= text.size()) {
    return false;
  }
  char sign = text[cursor];
  if (sign == 'Z' || sign == 'z') {
    offsetMinutes = 0;
  } else if (sign == '+' || sign == '-') {
    long long offsetHour = 0;
    long long offsetMinute = 0;
    if (!readInt(text, cursor + 1, 2, &offsetHour)) {
      return false;
    }
    size_t minuteOffset = cursor + 3;
    if (minuteOffset < text.size() && text[minuteOffset] == ':') {
      ++minuteOffset;
    }
    if (!readInt(text, minuteOffset, 2, &offsetMinute)) {
      return false;
    }
    offsetMinutes = offsetHour * 60 + offsetMinute;
    if (sign == '-') {
      offsetMinutes = -offsetMinutes;
    }
  } else {
    return false;
  }

  long long days = daysFromCivil(year, month, day);
  long long local = days * 86400LL + hour * 3600LL + minute * 60LL + second;
  *unixSeconds = local - offsetMinutes * 60LL;
  return true;
}

bool parseFreightTimestamp(const std::string& text, long long* epochSeconds) {
  long long unixSeconds = 0;
  if (!parseOffsetTimestamp(text, &unixSeconds)) {
    return false;
  }
  *epochSeconds = unixSeconds - kFreightEpochSeconds;
  return true;
}

long long floorDiv(long long numerator, long long denominator) {
  long long quotient = numerator / denominator;
  long long remainder = numerator % denominator;
  if (remainder != 0 && ((remainder < 0) != (denominator < 0))) {
    quotient -= 1;
  }
  return quotient;
}

long long windowIndexFor(long long epochSeconds) { return floorDiv(epochSeconds, kWindowSeconds); }

long long windowStartFor(long long windowIndex) { return windowIndex * kWindowSeconds; }

std::string formatTonnes(long long kilograms) {
  bool negative = kilograms < 0;
  long long absolute = negative ? -kilograms : kilograms;
  char buffer[64];
  std::snprintf(buffer, sizeof(buffer), "%s%lld.%03lld", negative ? "-" : "", absolute / 1000,
                absolute % 1000);
  return std::string(buffer);
}

}  // namespace freight
