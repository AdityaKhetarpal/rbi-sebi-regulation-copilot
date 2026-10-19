# RBI/SEBI Regulation Copilot

**Ask a question about India's banking rules, and get the answer from the official rulebook, with the page number.**

**Live site:** [X] (add the Vercel link after deploying)

---

## What is this, in plain words?

- **RBI** (Reserve Bank of India) and **SEBI** (Securities and Exchange Board of India) are India's financial regulators. They write the rules that banks, fintechs, brokers and mutual funds must follow.
- Those rules sit in long PDFs called **Master Directions**. The KYC one alone is 100+ pages.
- Compliance teams search these PDFs by hand for every question. A normal chatbot answers from memory, can be out of date, and can't show where the rule is written.

**This project:** you type *"How often must KYC be updated for high-risk customers?"* and get

> "…periodic updation at least once in every **two years** for high-risk customers…" (KYC Master Direction, page 41)

If the rulebooks don't cover the question (*"What is the repo rate?"*), it says **"I couldn't find this in the provided documents"** instead of guessing.

## How it works: 8 steps, one file each

The method is called **RAG (Retrieval-Augmented Generation)**: *look it up first, then answer only from what you found*, like an open-book exam.

```
 PREPARE (once a week)                                ANSWER (every question)
 1 Download PDFs → 2 Read pages → 3 Cut into chunks → 4 Turn chunks into numbers
                                                                 │
                    8 Agent (harder questions) ← 6 Answer with sources ← 5 Search best chunks
                                                 7 Test it automatically
```

| Step | File | What it does | What it saves |
|---|---|---|---|
| 1 | [`step1_download.py`](pipeline/step1_download.py) | Downloads RBI's Master Directions from rbi.org.in | `data/pdfs/`, `data/downloads.json` |
| 2 | [`step2_read_pdfs.py`](pipeline/step2_read_pdfs.py) | Pulls the text out of every page | `data/pages.csv` (one row per page) |
| 3 | [`step3_chunk.py`](pipeline/step3_chunk.py) | Cuts pages into ~300-word pieces ("chunks") | `data/chunks.csv` |
| 4 | [`step4_embed.py`](pipeline/step4_embed.py) | Turns each chunk into 384 numbers that capture its meaning | `data/vectors.npy` |
| 5 | [`step5_search.py`](pipeline/step5_search.py) | Finds the 5 chunks that best answer a question | – |
| 6 | [`step6_answer.py`](pipeline/step6_answer.py) | Writes the answer only from those chunks, with [1] [2] citations, or refuses | – |
| 7 | [`step7_test.py`](pipeline/step7_test.py) | Asks 11 questions with known answers and scores the results | `data/test_report.json` |
| 8 | [`step8_agent.py`](pipeline/step8_agent.py) | Lets the AI decide what to search, in a loop (needs an API key) | – |

Each file starts with a short note: **what** it does, **why**, and **what it saves**. Run them one by one and open the saved files to see what happened.

**Learn it step by step:** [`notebooks/regcopilot.ipynb`](notebooks/regcopilot.ipynb) is the same 8 steps in Google Colab, one idea per cell.

## Words you'll hear

| Word | Meaning | Step |
|---|---|---|
| **Chunk** | A small piece of a document (~300 words) | 3 |
| **Embedding** | A list of numbers that captures what a text *means*. Similar meaning → similar numbers | 4 |
| **Keyword search (BM25)** | Classic search-engine scoring: chunks containing the question's words, rare words counting more | 5 |
| **Re-ranker** | A second model that reads the question and a chunk *together* and scores how well the chunk answers it | 5 |
| **RAG** | Retrieve the right chunks, then generate the answer from them | 5–6 |
| **Agent** | An AI in a loop that uses tools (like search) and decides its next step | 8 |

## Two answer modes, so it never breaks

- **With an API key:** Claude (`claude-haiku-5-5`) writes a short answer from the chunks and cites them.
- **Without a key (quote mode):** the system quotes the best sentences from the regulation, word for word. Free, and it can't make anything up.

## Results

First build (19 Oct 2026): 4 RBI Master Directions (KYC, Prepaid Payment Instruments, Fraud Risk Management, Payment Aggregators), 193 pages, 314 chunks.

| Test (11 questions) | Score |
|---|---|
| Found the right passage (8 known-answer questions) | 8/8 |
| Answer contains the right fact | 8/8 |
| Refused off-topic questions (3) | 3/3 |

Eleven questions is a sanity check, not a benchmark. The test re-runs every Monday, and if any score drops below 90%, the new version is not published. That has already happened once: RBI's page changed and a wrong PDF was downloaded. The test caught it, and the downloader was fixed.

## Automation

- **Every push** ([`ci.yml`](.github/workflows/ci.yml)): runs the tests (with tiny fake models, no downloads) and builds the website.
- **Every Monday** ([`build-index.yml`](.github/workflows/build-index.yml)): runs `pipeline/build_all.py`. It re-downloads the rulebooks, rebuilds the chunks and numbers, re-tests, and publishes only if the scores hold.

## Run it yourself

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

python pipeline/step1_download.py      # then open data/pdfs/
python pipeline/step2_read_pdfs.py     # then open data/pages.csv
python pipeline/step3_chunk.py         # then open data/chunks.csv
python pipeline/step4_embed.py
python pipeline/step5_search.py        # see the 3 kinds of search side by side
python pipeline/step6_answer.py        # see answers, and a refusal
python pipeline/step7_test.py          # see the scores
pytest -q                              # tests, no downloads needed

# website
cd web && npm install && npm run dev   # http://localhost:3000
```

Optional: set `ANTHROPIC_API_KEY` for AI-written answers and step 8. Keep it only in Vercel → Environment Variables, GitHub → Secrets, or your terminal, never in code.

**Adding SEBI or other PDFs:** put them in `data/pdfs_manual/` named like `SEBI_Master_Circular_Stock_Brokers.pdf`. The next build includes them.

## Limits

- It only knows the documents it has read (see the Results page).
- Scanned PDFs can't be read.
- The website uses fast keyword search; the Python pipeline adds meaning search and the re-ranker.
- Information, not legal advice. Always check the original circular.

---

Built by [Aditya Khetarpal](https://github.com/AdityaKhetarpal) · [LinkedIn](https://www.linkedin.com/in/adityakhetarpal)
