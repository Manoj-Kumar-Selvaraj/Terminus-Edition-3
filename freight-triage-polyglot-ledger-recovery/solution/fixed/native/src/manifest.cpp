#include "freight/manifest.h"

#include <dirent.h>

#include <algorithm>

#include "freight/json.h"

namespace freight {
namespace {

std::string trimAscii(const std::string& text) {
  size_t begin = 0;
  size_t end = text.size();
  while (begin < end && (text[begin] == ' ' || text[begin] == '\t' || text[begin] == '\n' ||
                         text[begin] == '\r')) {
    ++begin;
  }
  while (end > begin && (text[end - 1] == ' ' || text[end - 1] == '\t' || text[end - 1] == '\n' ||
                         text[end - 1] == '\r')) {
    --end;
  }
  return text.substr(begin, end - begin);
}

bool hasJsonSuffix(const std::string& name) {
  return name.size() > 5 && name.compare(name.size() - 5, 5, ".json") == 0;
}

}  // namespace

std::vector<std::string> listManifestFiles(const std::string& directory) {
  std::vector<std::string> names;
  DIR* handle = opendir(directory.c_str());
  if (handle == nullptr) {
    return names;
  }
  struct dirent* entry = nullptr;
  while ((entry = readdir(handle)) != nullptr) {
    std::string name(entry->d_name);
    if (name == "." || name == "..") {
      continue;
    }
    if (!hasJsonSuffix(name)) {
      continue;
    }
    names.push_back(directory + "/" + name);
  }
  closedir(handle);
  std::sort(names.begin(), names.end());
  return names;
}

bool loadManifest(const std::string& path, Manifest* out, std::string* error) {
  Json document;
  if (!Json::parseFile(path, &document, error)) {
    return false;
  }
  Manifest manifest;
  manifest.sourceFile = path;
  manifest.manifestId = document.at("manifest_id").asString();
  manifest.carrierCode = document.at("carrier_code").asString();
  manifest.laneId = document.at("lane_id").asString();
  manifest.commodityCode = document.at("commodity_code").asString();
  manifest.arrivalLocal = document.at("arrival_local").asString();
  manifest.seal = document.at("seal").asString();
  manifest.bookingRef = document.at("booking_ref").asString();
  manifest.trailerPlate = document.at("trailer_plate").asString();
  manifest.priority = document.at("priority").asInt();

  const JsonArray& pieces = document.at("pieces").items();
  for (size_t i = 0; i < pieces.size(); ++i) {
    Piece piece;
    piece.pieceId = pieces[i].at("piece_id").asString();
    piece.grossMassKg = pieces[i].at("gross_mass_kg").asInt();
    piece.hazmatClass = pieces[i].at("hazmat_class").asInt();
    manifest.pieces.push_back(piece);
  }
  *out = manifest;
  return true;
}

std::string normalizeSeal(const std::string& seal) {
  std::string trimmed = trimAscii(seal);
  for (size_t i = 0; i < trimmed.size(); ++i) {
    if (trimmed[i] >= 'a' && trimmed[i] <= 'z') {
      trimmed[i] = static_cast<char>(trimmed[i] - 32);
    }
  }
  return trimmed;
}

long long manifestGrossKg(const Manifest& manifest) {
  long long total = 0;
  for (size_t i = 0; i < manifest.pieces.size(); ++i) {
    total += manifest.pieces[i].grossMassKg;
  }
  return total;
}

long long manifestHazmatMax(const Manifest& manifest) {
  long long worst = 0;
  for (size_t i = 0; i < manifest.pieces.size(); ++i) {
    if (manifest.pieces[i].hazmatClass > worst) {
      worst = manifest.pieces[i].hazmatClass;
    }
  }
  return worst;
}

long long manifestAveragePieceGrams(const Manifest& manifest) {
  if (manifest.pieces.empty()) {
    return 0;
  }
  return manifestGrossKg(manifest) * 1000 / static_cast<long long>(manifest.pieces.size());
}

}  // namespace freight
