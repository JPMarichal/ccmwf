from pathlib import Path
import sys
import timeit

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.services.email_html_parser import extract_primary_table
from app.services.email_content_utils import collect_table_texts, extract_fecha_generacion

HTML_PATH = ROOT / "originalBody.html"

if not HTML_PATH.exists():
    raise SystemExit(f"HTML sample not found at {HTML_PATH}")

html = HTML_PATH.read_text(encoding="utf-8")


def run() -> int:
    table, errors = extract_primary_table(html)
    texts = collect_table_texts(table)
    extract_fecha_generacion(None, "", html=html, table_texts=texts)
    return len(errors)


if __name__ == "__main__":
    runs = 20
    avg = timeit.timeit(run, number=runs) / runs
    print(f"Average parse+extract time over {runs} runs: {avg * 1000:.3f} ms")
