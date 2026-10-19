# RBI/SEBI Regulation Copilot

Ask a question about Indian financial regulation and get an answer built **only from the official RBI and SEBI documents**, with the page it came from. If the documents don't cover the question, it says so instead of guessing.

**Live site:** [X] (add the Vercel link after deploying)

## The problem

Compliance, risk and product teams at banks, NBFCs and fintechs spend hours searching long Master Directions for one rule ("How often must KYC be re-done for high-risk customers?"). A general chatbot answers from memory, which can be out of date and comes with no source. In compliance, an answer without a citation can't be used.

## What it does

| Page | What it does |
|---|---|
| Ask | Type a question → answer with numbered citations → open each source passage. **Agent** mode lets Claude plan and search several times for multi-part questions |
| Documents | Every document indexed: regulator, pages, passages, link to the official PDF, scanned-page warnings |
| Evaluation | Scores on a fixed question set: right passage found, right fact in the answer, off-topic questions refused |
| How it works | The pipeline, design decisions and limitations |

## How it works

```
rbi.org.in ──► PDFs ──► pages ──► 300-word chunks ──► embeddings (bge-small) + keyword index (BM25)
                                                              │
question ──► meaning search + keyword search ──► merge (RRF) ──► re-rank (cross-encoder) ──► top 5 passages
                                                                                                │
                              relevance below threshold? ──► "I couldn't find this in the documents"
                                                                                                │
                                          writer: Claude ► free local model ► exact sentences ──► answer with [1] [2]
```

1. **Ingest** (`copilot/ingest.py`): reads RBI's Master Directions page, finds each topic, skips amendments and ombudsman documents, downloads the PDF. SEBI master circulars go in `data/pdfs_manual/`.
2. **Chunk** (`copilot/chunking.py`): cleans each page and cuts it into ~300-word passages overlapping by 50 words. Every passage keeps its document and page.
3. **Embed** (`copilot/index.py`): `BAAI/bge-small-en-v1.5` turns each passage into 384 numbers.
4. **Retrieve** (`copilot/retrieve.py`): meaning search + BM25 keyword search, merged with Reciprocal Rank Fusion, then a cross-encoder (`ms-marco-MiniLM-L-6-v2`) re-ranks the top 20.
5. **Answer** (`copilot/answer.py`): the top 5 passages go to the writer with strict rules (only these sources, cite `[n]`, quote numbers exactly, refuse if missing).
6. **Agent** (`copilot/agent.py`): Claude gets three tools (`search_regulations`, `read_chunk`, `list_documents`) and decides what to call, in a loop, before answering with chunk-level citations.
7. **Evaluate** (`copilot/evaluate.py`): 11 questions with known answers (8 facts, 3 that must be refused).

### Design decisions

- **Never depends on a paid key.** Three writers, best first: Claude (`claude-haiku-5-5`) → a free open-source model (Qwen2.5-1.5B, on a GPU) → extractive (the best sentences from the regulation, word for word). Retrieval is always free.
- **Says "I don't know" from data.** The re-ranker scores the best passage before anything is written; below the threshold it refuses. The threshold was calibrated on real questions (scores above 4) vs an off-topic one ("current repo rate", −10).
- **Hybrid search.** Meaning search alone found the right document but missed exact rules like "small PPI … Rs.10,000"; adding BM25 and the re-ranker moved the exact rule to the top.
- **Two runtimes, one pipeline.** The notebook and scripts run the full hybrid pipeline (measured on the Evaluation page). The website runs the same passages with BM25 and a word-rarity relevance check, so it answers instantly on a free server.

## Automation

- `.github/workflows/ci.yml`: every push runs the Python tests (fake models, no downloads) and the website's lint, tests and build.
- `.github/workflows/build-index.yml`: every Monday (or on demand) downloads the current Master Directions, rebuilds the index, re-runs the evaluation, tests the website on the real passages, and commits the results.

## Results

First build (19 Oct 2026): 4 RBI Master Directions, 193 pages, 314 passages.

| Measure (11 questions) | Python pipeline, extractive engine |
|---|---|
| Right passage in the top 5 | 8/8 (100%) |
| Answer contains the right fact | 8/8 (100%) |
| Off-topic questions refused | 3/3 (100%) |

The website's keyword-only search is tested on the same questions on every rebuild (`web/lib/real-data.test.ts`). It finds the right passage for all 8 within its top 6 and refuses all 3 off-topic questions. The set is small, so these are checks, not benchmark scores. The Digital Lending Directions were not found on RBI's page by the downloader; add the PDF to `data/pdfs_manual/` to include it.

## Limitations

- Only the documents on the Documents page are covered (RBI: KYC, Prepaid Payment Instruments, Fraud Risk Management, Payment Aggregators; SEBI master circulars once added to `data/pdfs_manual/`).
- Scanned PDFs can't be searched; the Documents page flags them.
- Changes made after a Master Direction's last update may be missing until RBI updates it.
- Information, not legal advice.

## Run it yourself

```bash
# Python pipeline (3.12)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
python scripts/build_index.py                     # download, chunk, embed, export
python scripts/run_eval.py                        # score it
python scripts/ask.py "How often must KYC be updated for high-risk customers?"
export ANTHROPIC_API_KEY=...                      # optional: Claude writer + agent
python scripts/ask.py --agent "Compare KYC update rules for high and low risk customers"
pytest -q                                         # tests, no downloads needed

# Website (Node 20.9+)
cd web && npm install && npm test && npm run dev  # http://localhost:3000
```

**Step-by-step notebook:** [`notebooks/regcopilot.ipynb`](notebooks/regcopilot.ipynb) builds the whole thing in Google Colab, one idea per cell (RAG Parts 1–7, the agent in Part 8).

**API key:** only in Vercel → Settings → Environment Variables (`ANTHROPIC_API_KEY`) or `web/.env.local`, and in GitHub → Settings → Secrets for the weekly evaluation. Never in code.

---

Built by [Aditya Khetarpal](https://github.com/AdityaKhetarpal) · [LinkedIn](https://www.linkedin.com/in/adityakhetarpal)

*Information, not legal advice. Always check the original circular.*
