# Data and evaluation provenance

All released memory records, people, relationships, events and conversations are synthetic. I did not copy a personal archive, database, photograph, recording or family backup into this repository. Some older fixtures have no synthetic-data flag, so this document applies to those as well.

## How I prepared the evaluation data

Newer holdouts were authored by separate development agents before they saw the implementation or model outputs being tested. This helped separate test design from implementation, but it is not independent human validation. The fixture manifests record the scope, any corrections and prior exposure.

Reference plans and rubrics are aids for evaluating the answers, not automatic proof of semantic correctness. All published holdouts have already been used; new refinements need fresh, unseen cases.

## What the evidence contains

The `evidence/` directory includes saved aggregate results, source reviews and selected synthetic final answers. I omitted raw request/response traffic, generated request plans, internal reasoning, runtime logs and per-second host measurements. Literal source excerpts and failed final answers remain included because they are important to understanding the results.

Published scores and judgments are historical. I did not recalculate them during publication. Answer hashes refer to the original final answer text; sanitized wrappers have separate public checksums.

Generic source and model identifiers and model-blob digests are retained for reproducibility. There is no data license at present.
