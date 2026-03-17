from __future__ import annotations

import argparse
from pathlib import Path
from xml.sax.saxutils import escape

from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer


def parse_markdown_lines(text: str):
    in_code = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\n")

        if line.strip().startswith("```"):
            in_code = not in_code
            yield ("fence", "")
            continue

        if in_code:
            yield ("code", line)
            continue

        stripped = line.strip()
        if not stripped:
            yield ("blank", "")
        elif stripped.startswith("### "):
            yield ("h3", stripped[4:].strip())
        elif stripped.startswith("## "):
            yield ("h2", stripped[3:].strip())
        elif stripped.startswith("# "):
            yield ("h1", stripped[2:].strip())
        elif stripped.startswith("- ") or stripped.startswith("* "):
            yield ("bullet", stripped[2:].strip())
        elif stripped[:2].isdigit() and ". " in stripped[:4]:
            yield ("ordered", stripped)
        else:
            yield ("para", stripped)


def export_docx(md_text: str, output_path: Path) -> None:
    doc = Document()

    for line_type, content in parse_markdown_lines(md_text):
        if line_type == "blank" or line_type == "fence":
            continue
        if line_type == "h1":
            doc.add_heading(content, level=1)
        elif line_type == "h2":
            doc.add_heading(content, level=2)
        elif line_type == "h3":
            doc.add_heading(content, level=3)
        elif line_type == "bullet":
            doc.add_paragraph(content, style="List Bullet")
        elif line_type == "ordered":
            doc.add_paragraph(content, style="List Number")
        elif line_type == "code":
            doc.add_paragraph(content)
        else:
            doc.add_paragraph(content)

    doc.save(output_path)


def _register_pdf_font() -> str:
    windows_arial = Path("C:/Windows/Fonts/arial.ttf")
    if windows_arial.exists():
        pdfmetrics.registerFont(TTFont("Arial", str(windows_arial)))
        return "Arial"
    return "Helvetica"


def export_pdf(md_text: str, output_path: Path) -> None:
    font_name = _register_pdf_font()

    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "BodySl",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=10,
        leading=14,
    )
    h1 = ParagraphStyle(
        "H1Sl",
        parent=styles["Heading1"],
        fontName=font_name,
        fontSize=18,
        leading=22,
        spaceAfter=10,
    )
    h2 = ParagraphStyle(
        "H2Sl",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=14,
        leading=18,
        spaceAfter=8,
    )
    h3 = ParagraphStyle(
        "H3Sl",
        parent=styles["Heading3"],
        fontName=font_name,
        fontSize=12,
        leading=16,
        spaceAfter=6,
    )
    code = ParagraphStyle(
        "CodeSl",
        parent=body,
        fontName="Courier",
        fontSize=9,
        leading=12,
    )

    story = []
    in_code = False

    for line_type, content in parse_markdown_lines(md_text):
        if line_type == "fence":
            in_code = not in_code
            story.append(Spacer(1, 4))
            continue

        if line_type == "blank":
            story.append(Spacer(1, 4))
            continue

        if in_code or line_type == "code":
            story.append(Preformatted(content, code))
            continue

        safe = escape(content)
        if line_type == "h1":
            story.append(Paragraph(safe, h1))
        elif line_type == "h2":
            story.append(Paragraph(safe, h2))
        elif line_type == "h3":
            story.append(Paragraph(safe, h3))
        elif line_type == "bullet":
            story.append(Paragraph(f"• {safe}", body))
        else:
            story.append(Paragraph(safe, body))

    pdf = SimpleDocTemplate(str(output_path), pagesize=A4)
    pdf.build(story)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Markdown report to DOCX and PDF.")
    parser.add_argument("--input", required=True, help="Path to Markdown file")
    parser.add_argument("--outdir", default=".", help="Output directory")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    md_text = input_path.read_text(encoding="utf-8")
    docx_path = outdir / f"{input_path.stem}.docx"
    pdf_path = outdir / f"{input_path.stem}.pdf"

    export_docx(md_text, docx_path)
    export_pdf(md_text, pdf_path)

    print(docx_path)
    print(pdf_path)


if __name__ == "__main__":
    main()
