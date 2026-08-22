from __future__ import annotations

import math
from pathlib import Path

from .reference_catalog import correlation_rows


def swamee_jain_factor(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
  term = relative_roughness / (3.7 * diameter_m) + 5.74 / (reynolds ** 0.9)
  return 0.25 / (math.log10(term) ** 2)


def churchill_factor(reynolds: float, relative_roughness: float) -> float:
  a = (7.0 / reynolds) ** 0.9
  b = (2.457 * math.log(1.0 / ((a + 0.27 * relative_roughness) ** 1.5))) ** 16
  c = (37530.0 / reynolds) ** 16
  return 8.0 * ((8.0 / reynolds) ** 12 + 1.0 / (b + c) ** 1.5) ** (1.0 / 12.0)


def blended_friction_factor(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
  factors = [
    swamee_jain_factor(reynolds, relative_roughness, diameter_m),
    churchill_factor(reynolds, relative_roughness),
  ]
  return sum(factors) / len(factors)


def catalog_correlation_mean(root: Path, reynolds: float) -> float:
  rows = correlation_rows(root, reynolds)
  coeffs = [float(row["coeff_a"]) + float(row["coeff_b"]) for row in rows]
  return sum(coeffs) / max(len(coeffs), 1)


def correlation_report(root: Path, reynolds: float, relative_roughness: float, diameter_m: float) -> dict[str, float]:
  return {
    "swamee_jain": swamee_jain_factor(reynolds, relative_roughness, diameter_m),
    "churchill": churchill_factor(reynolds, relative_roughness),
    "blended": blended_friction_factor(reynolds, relative_roughness, diameter_m),
    "catalog_mean": catalog_correlation_mean(root, reynolds),
  }
