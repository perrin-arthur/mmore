# Budget estimate — Mistral OCR for mmore benchmark

**Goal:** request lab access to a Mistral API key in order to integrate
`mistral-ocr-latest` as an alternative backend for mmore's `PDFProcessor`, and
benchmark its extraction quality against the current pipeline (Marker/Surya) on
a **1000-PDF** corpus.

## Mistral OCR pricing

Source: Mistral AI public pricing (announced March 2025).

| Mode     | Price              | Latency           | Recommended usage           |
| -------- | ------------------ | ----------------- | --------------------------- |
| Standard | $1.00 / 1000 pages | near real-time    | dev, debug, small volumes   |
| Batch    | $0.50 / 1000 pages | a few hours       | offline benchmarks, bulk    |

Assumed conversion: **1 USD ≈ 0.90 CHF** (to be re-confirmed at purchase time).

## Estimates for 1000 PDFs

Cost scales with the number of **pages**, not the number of files. A few
profiles depending on corpus shape:

| Corpus profile               | Pages/PDF | Total pages | Standard cost | Standard (CHF) | Batch (CHF) |
| ---------------------------- | --------- | ----------- | ------------- | -------------- | ----------- |
| Slides, short memos          | 5         | 5,000       | $5            | **~4.5**       | ~2.3        |
| Mid-sized reports / papers   | 15        | 15,000      | $15           | **~13.5**      | ~6.8        |
| Long reports (WHO-style)     | 30        | 30,000      | $30           | **~27**        | ~13.5       |
| Books, theses                | 50        | 50,000      | $50           | **~45**        | ~22.5       |
| Very long (200-page theses)  | 200       | 200,000     | $200          | **~180**       | ~90         |

## Recommendation for the lab

Target corpus: documents like those in **examples/who/** (WHO reports,
guidelines), typically 20–80 pages.

- **Central estimate:** ~30 pages × 1000 PDFs = 30,000 pages → **~27 CHF** standard, **~14 CHF** batch.
- **Recommended budget (×3 margin for re-runs, debug, ablations):** **80–100 CHF**.

## Caveats worth flagging

1. **Per-page billing**, not per-document — measure actual corpus size before purchase.
2. **Frequent re-runs** during benchmarking (prompt tweaks, hyperparams, sample size): provision ×2 to ×3.
3. **Floating USD/CHF rate** — re-check on the day of purchase.
4. **No cost on the current pipeline side** (Marker/Surya runs on lab GPUs, RCP/CSCS).

## Measuring the exact page count before purchase

```bash
find <corpus_dir> -name "*.pdf" -exec pdfinfo {} \; \
  | grep "^Pages" | awk '{s+=$2} END {print "Total pages:", s}'
```

Estimated cost = `total_pages * 0.001 * 0.9` CHF in standard mode,
or `total_pages * 0.0005 * 0.9` CHF in batch mode.

## Summary / request

> To integrate and benchmark Mistral OCR (`mistral-ocr-latest`) as an
> alternative backend for mmore's PDFProcessor on a 1000-document corpus
> (~30,000 pages estimated), I'm requesting access to a Mistral API key with a
> projected budget of **~100 CHF** covering the initial run plus 2–3 bench
> iterations (prompt changes, ablations on sub-corpora).
