from __future__ import annotations

from pathlib import Path
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
ARTICLE = ROOT / "axi_outstanding_backpressure_article.md"
DIAGRAMS = [
    ROOT / f"assets/axi-outstanding/{name}.drawio"
    for name in (
        "01-ot-lifecycle",
        "02-ot-counter",
        "03-threshold-backpressure",
        "04-long-response-delay",
        "05-read-write-id",
        "06-same-cycle-alloc-retire",
        "07-reset-flush",
    )
]
SNIPPETS = [
    ROOT / f"snippets/{name}"
    for name in (
        "axi_ot_reference_model.sv",
        "axi_ot_delayed_response_seq.svh",
        "axi_ot_checker.svh",
        "axi_ot_sva.sv",
        "axi_ot_coverage.sv",
    )
]
REQUIRED_ARTICLE_TEXT = (
    "AWVALID",
    "AWREADY",
    "ARVALID",
    "ARREADY",
    "BVALID",
    "BREADY",
    "RVALID",
    "RREADY",
    "AWID",
    "ARID",
    "BID",
    "RID",
    "RLAST",
    "ot_count",
    "backpressure",
    "coverage",
)
FORBIDDEN_TEXT = ("NBIF", "HPHOST", "hpdma", "hphost")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    require(ARTICLE.is_file(), f"missing article: {ARTICLE}", errors)

    article = ARTICLE.read_text(encoding="utf-8") if ARTICLE.is_file() else ""
    for token in REQUIRED_ARTICLE_TEXT:
        require(token in article, f"article missing required token: {token}", errors)
    for token in FORBIDDEN_TEXT:
        require(
            token.lower() not in article.lower(),
            f"article contains forbidden token: {token}",
            errors,
        )

    for path in DIAGRAMS:
        require(path.is_file(), f"missing diagram: {path}", errors)
        if path.is_file():
            try:
                root = ET.parse(path).getroot()
                require(root.tag == "mxGraphModel", f"invalid draw.io root: {path}", errors)
                ids = [cell.attrib.get("id") for cell in root.iter("mxCell")]
                require("0" in ids and "1" in ids, f"draw.io root cells missing: {path}", errors)
            except ET.ParseError as exc:
                errors.append(f"invalid XML in {path}: {exc}")

    for path in SNIPPETS:
        require(path.is_file(), f"missing snippet: {path}", errors)
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            require(len(text.strip()) > 120, f"snippet is unexpectedly short: {path}", errors)

    if errors:
        print("AXI outstanding article validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1

    print("AXI outstanding article validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
