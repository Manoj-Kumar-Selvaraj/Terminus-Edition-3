#include "freight/selftest.h"

#include <cstdio>
#include <map>
#include <string>

#include "freight/codecs.h"
#include "freight/formats.h"
#include "freight/hashes.h"
#include "freight/normalize.h"
#include "freight/sha256.h"
#include "freight/stats.h"
#include "freight/tables.h"

namespace freight {
namespace {

const int kProbeCount = 64;
const int kSeriesCount = 24;
const int kSeriesLength = 17;
const int kRecordCount = 40;

std::string hex64(unsigned long long value) {
  char buffer[32];
  std::snprintf(buffer, sizeof(buffer), "%016llx", value);
  return std::string(buffer);
}

unsigned long long foldFnv1a64(unsigned long long state, const std::string& text) {
  for (size_t i = 0; i < text.size(); ++i) {
    state ^= static_cast<unsigned char>(text[i]);
    state *= 1099511628211ULL;
  }
  return state;
}

}  // namespace

unsigned int probeMix32(unsigned int seed) {
  unsigned int x = seed;
  x ^= x >> 16;
  x *= 0x7FEB352Du;
  x ^= x >> 15;
  x *= 0x846CA68Bu;
  x ^= x >> 16;
  return x;
}

std::string probeString(int index) {
  char head[32];
  std::snprintf(head, sizeof(head), "FRT-%04d-", index);
  std::string out(head);
  const int tail = index % 11;
  for (int k = 0; k < tail; ++k) {
    out.push_back(static_cast<char>('a' + ((index * 7 + k * 3) % 26)));
  }
  return out;
}

std::vector<long long> probeSeries(int series) {
  std::vector<long long> values;
  values.reserve(kSeriesLength);
  for (int k = 0; k < kSeriesLength; ++k) {
    values.push_back(3 + static_cast<long long>(probeMix32(static_cast<unsigned int>(series * 977 + k * 31)) % 4093u));
  }
  return values;
}

std::vector<ProbeRecord> probeRecords() {
  std::vector<ProbeRecord> records;
  records.reserve(kRecordCount);
  for (int index = 0; index < kRecordCount; ++index) {
    unsigned int m = probeMix32(static_cast<unsigned int>(index * 131 + 17));
    char id[16];
    std::snprintf(id, sizeof(id), "RC-%03d", index);
    ProbeRecord record;
    record.recordId = id;
    record.laneIndex = m % 360u;
    record.massKg = 50 + static_cast<long long>((m >> 7) % 48000u);
    record.priority = static_cast<long long>((m >> 3) % 5u);
    record.hazmatClass = static_cast<long long>((m >> 11) % 9u);
    record.sealLength = 6 + static_cast<long long>((m >> 17) % 7u);
    records.push_back(record);
  }
  return records;
}

Json buildSelftestReport() {
  std::map<std::string, std::map<std::string, std::string> > families;

  const std::vector<HashAlgorithm>& hashes = hashRegistry();
  for (size_t i = 0; i < hashes.size(); ++i) {
    unsigned long long folded = 14695981039346656037ULL;
    for (int p = 0; p < kProbeCount; ++p) {
      folded = foldFnv1a64(folded, hex64(hashes[i].apply(probeString(p))));
    }
    families["hash"][hashes[i].name] = hex64(folded);
  }

  const std::vector<CodecAlgorithm>& codecs = codecRegistry();
  for (size_t i = 0; i < codecs.size(); ++i) {
    unsigned long long folded = 14695981039346656037ULL;
    bool roundTrip = true;
    for (int p = 0; p < kProbeCount; ++p) {
      const std::string probe = probeString(p);
      const std::string encoded = codecs[i].encode(probe);
      folded = foldFnv1a64(folded, encoded);
      if (codecs[i].decode(encoded) != probe) {
        roundTrip = false;
      }
    }
    if (!roundTrip) {
      folded ^= 0xDEADBEEFCAFEF00DULL;
    }
    families["codec"][codecs[i].name] = hex64(folded);
  }

  const std::vector<StatKernel>& kernels = statRegistry();
  for (size_t i = 0; i < kernels.size(); ++i) {
    unsigned long long folded = 14695981039346656037ULL;
    for (int s = 0; s < kSeriesCount; ++s) {
      char buffer[32];
      std::snprintf(buffer, sizeof(buffer), "%lld", kernels[i].apply(probeSeries(s)));
      folded = foldFnv1a64(folded, buffer);
    }
    families["stats"][kernels[i].name] = hex64(folded);
  }

  const std::vector<TriageRule>& rules = ruleRegistry();
  const std::vector<ProbeRecord> records = probeRecords();
  for (size_t i = 0; i < rules.size(); ++i) {
    unsigned long long folded = 14695981039346656037ULL;
    for (size_t r = 0; r < records.size(); ++r) {
      folded = foldFnv1a64(folded, rules[i].apply(records[r]) ? "1" : "0");
    }
    families["rules"][rules[i].name] = hex64(folded);
  }

  const std::vector<Formatter>& formatters = formatterRegistry();
  for (size_t i = 0; i < formatters.size(); ++i) {
    unsigned long long folded = 14695981039346656037ULL;
    for (int s = 0; s < kSeriesCount; ++s) {
      const std::vector<long long> series = probeSeries(s);
      for (size_t v = 0; v < series.size(); ++v) {
        folded = foldFnv1a64(folded, formatters[i].apply(series[v]));
        folded = foldFnv1a64(folded, formatters[i].apply(-series[v]));
      }
    }
    families["format"][formatters[i].name] = hex64(folded);
  }

  const std::vector<Normalizer>& normalizers = normalizerRegistry();
  for (size_t i = 0; i < normalizers.size(); ++i) {
    unsigned long long folded = 14695981039346656037ULL;
    for (int p = 0; p < kProbeCount; ++p) {
      folded = foldFnv1a64(folded, normalizers[i].apply(probeString(p)));
    }
    families["norm"][normalizers[i].name] = hex64(folded);
  }

  {
    unsigned long long folded = 14695981039346656037ULL;
    const std::vector<LaneTableRow>& rows = laneTableRows();
    for (size_t i = 0; i < rows.size(); ++i) {
      folded = foldFnv1a64(folded, laneTableCanonical(rows[i]));
    }
    families["tables"]["lane"] = hex64(folded);
  }
  {
    unsigned long long folded = 14695981039346656037ULL;
    const std::vector<CarrierTableRow>& rows = carrierTableRows();
    for (size_t i = 0; i < rows.size(); ++i) {
      folded = foldFnv1a64(folded, carrierTableCanonical(rows[i]));
    }
    families["tables"]["carrier"] = hex64(folded);
  }
  {
    unsigned long long folded = 14695981039346656037ULL;
    const std::vector<CommodityTableRow>& rows = commodityTableRows();
    for (size_t i = 0; i < rows.size(); ++i) {
      folded = foldFnv1a64(folded, commodityTableCanonical(rows[i]));
    }
    families["tables"]["commodity"] = hex64(folded);
  }
  {
    unsigned long long folded = 14695981039346656037ULL;
    const std::vector<TariffTableRow>& rows = tariffTableRows();
    for (size_t i = 0; i < rows.size(); ++i) {
      folded = foldFnv1a64(folded, tariffTableCanonical(rows[i]));
    }
    families["tables"]["tariff"] = hex64(folded);
  }
  {
    unsigned long long folded = 14695981039346656037ULL;
    const std::vector<ZoneTableRow>& rows = zoneTableRows();
    for (size_t i = 0; i < rows.size(); ++i) {
      folded = foldFnv1a64(folded, zoneTableCanonical(rows[i]));
    }
    families["tables"]["zone"] = hex64(folded);
  }
  {
    unsigned long long folded = 14695981039346656037ULL;
    const std::vector<HazmatTableRow>& rows = hazmatTableRows();
    for (size_t i = 0; i < rows.size(); ++i) {
      folded = foldFnv1a64(folded, hazmatTableCanonical(rows[i]));
    }
    families["tables"]["hazmat"] = hex64(folded);
  }

  Sha256 hasher;
  Json familyJson = Json::object();
  for (std::map<std::string, std::map<std::string, std::string> >::const_iterator family =
           families.begin();
       family != families.end(); ++family) {
    Json bucket = Json::object();
    for (std::map<std::string, std::string>::const_iterator entry = family->second.begin();
         entry != family->second.end(); ++entry) {
      bucket[entry->first] = Json(entry->second);
      hasher.update(family->first + "|" + entry->first + "|" + entry->second + "\n");
    }
    familyJson[family->first] = bucket;
  }

  Json report = Json::object();
  report["digest"] = Json(hasher.hexDigest());
  report["families"] = familyJson;
  report["generator"] = Json(std::string("cpp"));
  report["probe_count"] = Json(static_cast<long long>(kProbeCount));
  report["record_count"] = Json(static_cast<long long>(kRecordCount));
  report["schema_version"] = Json(std::string("freight-selftest/2"));
  report["series_count"] = Json(static_cast<long long>(kSeriesCount));
  return report;
}

}  // namespace freight
