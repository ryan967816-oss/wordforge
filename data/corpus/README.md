# WordForge Corpus

`passages.jsonl` is the committed, copyright-clean seed corpus for Translate.
It is intentionally small first: enough to test whether the learning loop feels
"touchable" before scaling.

Local-only textbook passages, including OCR from California Edge C, should go in:

```text
data/corpus/local/
```

That directory is gitignored. The Studio app loads any `*.jsonl` files there
alongside the public corpus, so private textbook study can work locally without
publishing copyrighted passage text.

Raw OCR/source rows that still need to be processed should go in:

```text
data/corpus/sources_local/
```

They are also gitignored, but the Studio does **not** load them directly. Use
`scripts/ocr_edge_pages.py` to make local source rows, then
`scripts/build_corpus.py --source-jsonl ... --out data/corpus/local/<name>.jsonl`
to bake them into full practice packages.

Required fields mirror `wordforge.translate` outputs:

```text
id, source, level, title, text_en, target_structures, glosses, scaffold,
palette, grammar, note, vocab_targets
```
