"""All the settings in one place. Every step reads from here, so nothing is hidden inside the code."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# ---- files each step creates (open them to see what happened) ----
PDF_FOLDER = DATA / "pdfs"                    # step 1: the downloaded RBI PDFs (not stored on GitHub)
MANUAL_PDF_FOLDER = DATA / "pdfs_manual"      # PDFs you add by hand, e.g. SEBI circulars (stored on GitHub)
DOWNLOADS_FILE = DATA / "downloads.json"      # step 1: what was downloaded and from where
PAGES_FILE = DATA / "pages.csv"               # step 2: one row per PDF page
CHUNKS_FILE = DATA / "chunks.csv"             # step 3: one row per small piece of text
VECTORS_FILE = DATA / "vectors.npy"           # step 4: 384 numbers for every chunk
QUESTIONS_FILE = DATA / "test_questions.json" # step 7: questions with known answers
REPORT_FILE = DATA / "test_report.json"       # step 7: how well it did
WEBSITE_DATA = ROOT / "web" / "public" / "data"

# ---- step 1: which RBI documents to download ----
RBI_PAGE = "https://www.rbi.org.in/Scripts/BS_ViewMasterDirections.aspx"
DOCUMENTS = {   # topic as written on RBI's page -> name we save it as (REGULATOR_Title.pdf)
    "Know Your Customer": "RBI_KYC_Master_Direction.pdf",
    "Prepaid Payment Instruments": "RBI_PPI_Master_Direction.pdf",
    "Digital Lending": "RBI_Digital_Lending_Directions.pdf",
    "Fraud Risk Management": "RBI_Fraud_Risk_Management.pdf",
    "Payment Aggregator": "RBI_Payment_Aggregators.pdf",
}

# ---- step 3: chunk size ----
CHUNK_WORDS = 300       # words per chunk
OVERLAP_WORDS = 50      # words repeated between neighbouring chunks

# ---- steps 4-5: free models ----
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"                  # turns text into 384 numbers
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"     # scores how well a passage answers a question

# ---- step 6: answering ----
TOP_K = 5               # how many passages the answer is built from
MIN_SCORE = 0.0         # re-ranker score below this = "not in the documents" (real questions score 4+, off-topic -10)
CLAUDE_MODEL = "claude-haiku-5-5"   # used only if ANTHROPIC_API_KEY is set
NOT_FOUND = "I couldn't find this in the provided RBI/SEBI documents."
