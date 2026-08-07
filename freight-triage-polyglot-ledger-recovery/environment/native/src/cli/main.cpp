#include <cstdio>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "freight/json.h"
#include "freight/ledger.h"
#include "freight/manifest.h"
#include "freight/registry.h"
#include "freight/selftest.h"
#include "freight/timeutil.h"

namespace {

struct Options {
  std::string root = "/app";
  std::string registryDir;
  std::string manifestDir;
  std::string outPath;
};

void usage() {
  std::cout << "freightctl - native freight ledger engine\n"
            << "\n"
            << "usage:\n"
            << "  freightctl ledger [--root DIR] [--registry DIR] [--manifests DIR] [--out FILE]\n"
            << "  freightctl selftest [--out FILE]\n"
            << "  freightctl inspect --manifest FILE\n"
            << "  freightctl version\n";
}

bool writeText(const std::string& path, const std::string& body) {
  std::ofstream stream(path.c_str(), std::ios::binary | std::ios::trunc);
  if (!stream) {
    return false;
  }
  stream << body;
  return true;
}

Options parseOptions(int argc, char** argv, int start) {
  Options options;
  for (int i = start; i < argc; ++i) {
    std::string flag(argv[i]);
    std::string value = (i + 1 < argc) ? std::string(argv[i + 1]) : std::string();
    if (flag == "--root" && !value.empty()) {
      options.root = value;
      ++i;
    } else if (flag == "--registry" && !value.empty()) {
      options.registryDir = value;
      ++i;
    } else if (flag == "--manifests" && !value.empty()) {
      options.manifestDir = value;
      ++i;
    } else if ((flag == "--out" || flag == "--output") && !value.empty()) {
      options.outPath = value;
      ++i;
    }
  }
  if (options.registryDir.empty()) {
    options.registryDir = options.root + "/environment/data/registry";
  }
  if (options.manifestDir.empty()) {
    options.manifestDir = options.root + "/environment/data/manifests";
  }
  return options;
}

int runLedger(int argc, char** argv) {
  Options options = parseOptions(argc, argv, 2);
  if (options.outPath.empty()) {
    options.outPath = options.root + "/output/ledger-snapshot.json";
  }

  freight::Registry registry;
  std::string error;
  if (!registry.load(options.registryDir, &error)) {
    std::cerr << "freightctl: registry load failed: " << error << "\n";
    return 2;
  }

  std::vector<std::string> files = freight::listManifestFiles(options.manifestDir);
  if (files.empty()) {
    std::cerr << "freightctl: no manifests found in " << options.manifestDir << "\n";
  }

  std::vector<freight::Manifest> manifests;
  for (size_t i = 0; i < files.size(); ++i) {
    freight::Manifest manifest;
    if (!freight::loadManifest(files[i], &manifest, &error)) {
      std::cerr << "freightctl: manifest load failed: " << error << "\n";
      return 3;
    }
    manifests.push_back(manifest);
  }

  freight::Json snapshot = freight::buildLedgerSnapshot(registry, manifests);
  if (!writeText(options.outPath, snapshot.dump(2) + "\n")) {
    std::cerr << "freightctl: cannot write " << options.outPath << "\n";
    return 4;
  }
  std::cout << "freightctl: wrote " << options.outPath << " manifests="
            << snapshot.at("totals").at("manifest_count").asInt() << " digest="
            << snapshot.at("ledger_digest").asString() << "\n";
  return 0;
}

int runSelftest(int argc, char** argv) {
  Options options = parseOptions(argc, argv, 2);
  if (options.outPath.empty()) {
    options.outPath = options.root + "/output/selftest-cpp.json";
  }
  freight::Json report = freight::buildSelftestReport();
  if (!writeText(options.outPath, report.dump(2) + "\n")) {
    std::cerr << "freightctl: cannot write " << options.outPath << "\n";
    return 4;
  }
  std::cout << "freightctl: selftest digest=" << report.at("digest").asString() << "\n";
  return 0;
}

int runInspect(int argc, char** argv) {
  std::string path;
  for (int i = 2; i + 1 < argc; ++i) {
    if (std::string(argv[i]) == "--manifest") {
      path = argv[i + 1];
    }
  }
  if (path.empty()) {
    usage();
    return 1;
  }
  freight::Manifest manifest;
  std::string error;
  if (!freight::loadManifest(path, &manifest, &error)) {
    std::cerr << "freightctl: " << error << "\n";
    return 2;
  }
  long long epochSeconds = 0;
  freight::parseFreightTimestamp(manifest.arrivalLocal, &epochSeconds);
  std::cout << "manifest_id=" << manifest.manifestId << "\n"
            << "lane_id=" << manifest.laneId << "\n"
            << "seal_normalized=" << freight::normalizeSeal(manifest.seal) << "\n"
            << "arrival_epoch_s=" << epochSeconds << "\n"
            << "window_index=" << freight::windowIndexFor(epochSeconds) << "\n"
            << "gross_kg=" << freight::manifestGrossKg(manifest) << "\n"
            << "piece_count=" << manifest.pieces.size() << "\n";
  return 0;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) {
    usage();
    return 1;
  }
  std::string command(argv[1]);
  if (command == "ledger") {
    return runLedger(argc, argv);
  }
  if (command == "selftest") {
    return runSelftest(argc, argv);
  }
  if (command == "inspect") {
    return runInspect(argc, argv);
  }
  if (command == "version") {
    std::cout << "freightctl freight-ledger/2\n";
    return 0;
  }
  usage();
  return 1;
}
