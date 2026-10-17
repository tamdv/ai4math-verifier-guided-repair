"""Generates one ready-to-import Kaggle notebook per session from the template.

The template `notebooks/kaggle_experiments.ipynb` stays the single source of the
code cells; each session file only differs in the CẤU HÌNH cell, so nobody has
to edit flags inside Kaggle.

Usage:
    python3 scripts/make_kaggle_notebooks.py
"""

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "notebooks" / "kaggle_experiments.ipynb"
OUT_DIR = ROOT / "notebooks" / "sessions"

SESSIONS = {
    "run3b_scale_100_1k": {
        "title": "Lần 3b — scale 100 + 1K (chỉ Lean, $0, ~1,5 giờ)",
        "flags": dict(RUN_DATA=False, RUN_RQ_FREE=False, RUN_PILOT=False, RUN_LLM_MAIN=False,
                      SCALE_TIERS=["errors_100", "errors_1k"]),
        "secret": False,
    },
    "run3a_scale_10k": {
        "title": "Lần 3a — scale 10K (chỉ Lean, $0, ~10 giờ)",
        "flags": dict(RUN_DATA=False, RUN_RQ_FREE=False, RUN_PILOT=False, RUN_LLM_MAIN=False,
                      SCALE_TIERS=["errors_10k"]),
        "secret": False,
    },
    "run2b_llm_PAID": {
        "title": "Lần 2b — thí nghiệm LLM chính (TỐN CREDIT ~$3,9, trần $5,8, ~2 giờ)",
        "flags": dict(RUN_DATA=False, RUN_RQ_FREE=False, RUN_PILOT=False, RUN_LLM_MAIN=True,
                      SCALE_TIERS=[]),
        "secret": True,
    },
}


def config_cell(flags: dict) -> str:
    return "\n".join([
        f"RUN_DATA     = {flags['RUN_DATA']}",
        "N_SEEDS      = 5000",
        f"RUN_RQ_FREE  = {flags['RUN_RQ_FREE']}",
        f"RUN_PILOT    = {flags['RUN_PILOT']}",
        f"RUN_LLM_MAIN = {flags['RUN_LLM_MAIN']}",
        f"SCALE_TIERS  = {json.dumps(flags['SCALE_TIERS'])}",
        "SCALE_WORKERS, SCALE_REPEATS = [1, 2, 4], [1, 2, 3]",
        'RUN_TAG      = ""',
        'BRANCH = "feat/verifier-guided-pipeline"',
    ])


def intro(title: str, secret: bool) -> str:
    return "\n".join([
        f"# {title}",
        "",
        "**Không cần sửa gì trong notebook này** — cấu hình đã điền sẵn.",
        "",
        "Trước khi bấm *Save Version → Save & Run All*:",
        "1. **Settings:** Accelerator = *None* · Internet = *On*.",
        "2. **Input:** chỉ cần dataset **`g6-errors-v1`** (Add Input → Your Work → Datasets).",
        "   Không thêm input nào khác.",
        ("3. **Secrets:** `GEMINI_API_KEY` phải được tick cho notebook này."
         if secret else "3. **Secrets:** không cần."),
        "",
        "Kết quả: tải file `out_<phiên>_<giờ>.zip` ở tab **Output** khi chạy xong.",
    ])


def main() -> None:
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, spec in SESSIONS.items():
        nb = copy.deepcopy(template)
        cells = nb["cells"]
        cells[0]["source"] = intro(spec["title"], spec["secret"])
        for cell in cells:
            src = "".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]
            if src.startswith("RUN_DATA "):
                cell["source"] = config_cell(spec["flags"])
        path = OUT_DIR / f"{name}.ipynb"
        path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
        print("wrote", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
