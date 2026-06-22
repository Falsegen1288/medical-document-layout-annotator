# Layout Corpora: Run Notes

This document records domain-by-domain decisions for empirical vs. heuristic
sourcing of layout-skeleton geometry, as required by the Addendum Spec.

---

## Source Dataset

- **Name:** DocLayNet
- **License:** CC-BY-4.0
- **HuggingFace ID:** `ds4sd/DocLayNet`
- **Harvest Script:** `tools/harvest_doclaynet.py`
- **Harvest Parameters:** `--max-pages 200` (capped for speed)

---

## Per-Domain Decisions

### financial_invoice ✅ Empirical
- **Source:** DocLayNet pages classified as financial/invoice via heuristic
  (pages with ≥2 tables and/or table+text combinations)
- **Coverage:** Good — DocLayNet contains substantial financial document pages
- **Skeleton fields sourced:** margins, header/footer zone heights, column count

### scientific_paper ✅ Empirical
- **Source:** DocLayNet pages classified as scientific (presence of formulas,
  multi-column layouts, section headers)
- **Coverage:** Excellent — DocLayNet's strongest domain match
- **Skeleton fields sourced:** margins, column count/gap, header/footer zones

### legal_opinion ✅ Empirical
- **Source:** DocLayNet pages classified as legal (heavy text + section headers,
  single-column, few tables/pictures)
- **Coverage:** Good — many government/legal-style pages in DocLayNet
- **Skeleton fields sourced:** margins, line spacing density, zone heights

### medical_report ⚠️ Geometric Proxy
- **Source:** DocLayNet single-column report-style pages used as geometric proxy
- **Rationale:** No empirical data from PHI-containing sources is permitted.
  DocLayNet contains no actual medical records. We use its single-column,
  text-heavy pages (classified as "medical_report" by our heuristic, which
  catches single-column text-dominant pages that don't match other domains)
  as a geometric proxy for margin/zone statistics only.
- **PHI status:** ✅ No PHI data was accessed or used. All content in generated
  medical reports is fabricated using Faker.
- **Skeleton fields sourced:** margins, zone heights (geometry only, not content)

### commercial_catalog ⚠️ Heuristic Fallback
- **Source:** `HeuristicFallbackBackend` with existing grid-based Playwright layouts
- **Rationale:** DocLayNet has minimal catalog/retail document coverage.
  The few pages classified as "commercial_catalog" (3+ pictures) do not
  provide statistically meaningful skeleton distributions.
- **Fallback strategy:** Use hardcoded margins with ±5% jitter, maintaining
  the existing 2-column grid layout optimized for product card displays.
- **Skeleton fields sourced:** None from empirical data; all from heuristic defaults

---

## Invariants Preserved

1. **Canonical taxonomy:** Frozen at 11 labels. No expansion.
2. **Bounding boxes:** Captured at render time only by ReportLab/Playwright.
3. **JSON schema:** Unchanged from Master Spec v1.0.0.
4. **PHI:** No real patient data accessed for any domain.
