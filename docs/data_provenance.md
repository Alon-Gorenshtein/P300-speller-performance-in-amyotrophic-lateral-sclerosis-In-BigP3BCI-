# Data provenance

The analysis is pinned to the downloaded bigP3BCI v1.0.0 ZIP. Its SHA256 is `eea294aa34e9ed11e5a25d07e30aeefdf8b2d467a8309e2c38405a289afcd72f`.

Before any EDF is read, the ingestion script verifies this archive-level digest, parses the distributor-provided `SHA256SUMS.txt`, selects only non-AppleDouble EDF files beneath Studies F, L, and N, verifies every selected member against its authoritative digest, and atomically materializes an exact cache. The cache and all derived outputs are excluded from version control; the validation JSON is regenerated on each run.
