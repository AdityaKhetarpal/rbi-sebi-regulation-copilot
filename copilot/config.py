"""Every setting in one place, so the notebook, scripts and tests agree."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# where things live
PDF_DIR = ROOT / "data" / "pdfs"                 # downloaded RBI PDFs (not committed, re-downloaded by the workflow)
MANUAL_PDF_DIR = ROOT / "data" / "pdfs_manual"   # PDFs added by hand, e.g. SEBI master circulars (committed)
INDEX_DIR = ROOT / "data" / "index"              # chunks, vectors and the document list (committed)
EVAL_FILE = ROOT / "data" / "eval" / "questions.json"
SITE_DATA = ROOT / "web" / "public" / "data"     # the website reads these JSON files

# models: all free and open, run on CPU or Colab
EMBED_MODEL = "BAAI/bge-small-en-v1.5"                          # text -> 384 numbers
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "   # bge wants this on questions only
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"           # reads question + passage together
LOCAL_LLM = "Qwen/Qwen2.5-1.5B-Instruct"                        # free fallback writer (needs a GPU)
CLAUDE_MODEL = "claude-haiku-5-5"                               # best writer, needs ANTHROPIC_API_KEY

# chunking and retrieval
CHUNK_WORDS = 300          # words per chunk
CHUNK_OVERLAP = 50         # words repeated between neighbouring chunks
TOP_K = 5                  # chunks sent to the writer
POOL = 20                  # candidates from each search before merging and re-ranking
RRF_K = 60                 # standard Reciprocal Rank Fusion constant
RELEVANCE_THRESHOLD = 0.0  # re-ranker score below this = "not in the documents" (calibrated: real questions > 4, off-topic = -10)

# where the RBI Master Directions come from
RBI_LIST_PAGE = "https://www.rbi.org.in/Scripts/BS_ViewMasterDirections.aspx"
RBI_WANTED = {             # topic as written on RBI's page -> file name we save it as
    "Know Your Customer": "RBI_KYC_Master_Direction.pdf",
    "Prepaid Payment Instruments": "RBI_PPI_Master_Direction.pdf",
    "Digital Lending": "RBI_Digital_Lending_Directions.pdf",
    "Fraud Risk Management": "RBI_Fraud_Risk_Management.pdf",
    "Payment Aggregator": "RBI_Payment_Aggregators.pdf",
}
SKIP_WORDS = ["ombudsman", "amendment", "repeal", "withdrawal"]   # titles that are not the main Direction

REFUSAL = "I couldn't find this in the provided RBI/SEBI documents."
