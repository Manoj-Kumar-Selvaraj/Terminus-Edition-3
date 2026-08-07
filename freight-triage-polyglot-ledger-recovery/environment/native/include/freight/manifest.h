#ifndef FREIGHT_MANIFEST_H
#define FREIGHT_MANIFEST_H

// Manifest document model plus loading and seal normalization helpers.

#include <string>
#include <vector>

namespace freight {

struct Piece {
  std::string pieceId;
  long long grossMassKg = 0;
  long long hazmatClass = 0;
};

struct Manifest {
  std::string manifestId;
  std::string carrierCode;
  std::string laneId;
  std::string commodityCode;
  std::string arrivalLocal;
  std::string seal;
  std::string bookingRef;
  std::string trailerPlate;
  std::string sourceFile;
  long long priority = 0;
  std::vector<Piece> pieces;
};

std::vector<std::string> listManifestFiles(const std::string& directory);
bool loadManifest(const std::string& path, Manifest* out, std::string* error);

std::string normalizeSeal(const std::string& seal);
long long manifestGrossKg(const Manifest& manifest);
long long manifestHazmatMax(const Manifest& manifest);
long long manifestAveragePieceGrams(const Manifest& manifest);

}  // namespace freight

#endif  // FREIGHT_MANIFEST_H
