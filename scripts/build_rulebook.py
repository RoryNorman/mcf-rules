#!/usr/bin/env python3
"""Build the Modern Carry Federation rulebook PDF.

Requires Python 3.9+ and ReportLab:
    python -m pip install reportlab

Usage:
    python scripts/build_rulebook.py
    python scripts/build_rulebook.py --output path/to/rulebook.pdf
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path
from typing import Iterable

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import (
        BaseDocTemplate,
        Frame,
        HRFlowable,
        Image,
        ListFlowable,
        ListItem,
        NextPageTemplate,
        PageBreak,
        PageTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )
    from reportlab.platypus.tableofcontents import TableOfContents
except ImportError as exc:
    raise SystemExit(
        "ReportLab is required. Install it with: "
        f"{sys.executable} -m pip install reportlab"
    ) from exc


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPOSITORY_ROOT / "output" / "pdf" / "mcf-rulebook.pdf"
LOGO_SOURCE = REPOSITORY_ROOT / "assets" / "mcf-logo.png"
SOURCE_FILES = (
    "rulebook/01-purpose.md",
    "rulebook/02-tenets.md",
    "rulebook/03-safety.md",
    "rulebook/04-commands.md",
    "rulebook/05-stages.md",
    "rulebook/06-divisions.md",
    "rulebook/07-equipment.md",
    "rulebook/08-scoring.md",
    "rulebook/09-dq.md",
    "rulebook/10-admin.md",
    "rulebook/appendix.md",
)


def normalize_text(value: str) -> str:
    """Normalize characters unsupported by the built-in PDF fonts."""
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u00a0": " ",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value


def inline_markup(value: str) -> str:
    """Convert the small Markdown inline subset used by the rulebook."""
    value = html.escape(normalize_text(value.strip()))
    value = re.sub(r"\[([^]]+)]\(([^)]+)\)", r"\1", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", value)
    value = re.sub(r"`([^`]+)`", r"<font name=\"Courier\">\1</font>", value)
    return value


class RulebookDocument(BaseDocTemplate):
    """Document template that records headings for the table of contents."""

    def __init__(self, filename: str, **kwargs: object) -> None:
        super().__init__(filename, **kwargs)
        content_frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="content",
        )
        self.addPageTemplates(
            [
                PageTemplate(id="title", frames=[content_frame]),
                PageTemplate(
                    id="body",
                    frames=[content_frame],
                    onPage=self._draw_page_number,
                ),
            ]
        )

    @staticmethod
    def _draw_page_number(canvas: object, document: object) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#5A6068"))
        canvas.drawCentredString(LETTER[0] / 2, 0.42 * inch, str(document.page))
        canvas.restoreState()

    def afterFlowable(self, flowable: object) -> None:
        if not isinstance(flowable, Paragraph):
            return
        level = getattr(flowable, "toc_level", None)
        if level is None:
            return
        text = flowable.getPlainText()
        key = f"heading-{self.seq.nextf('heading')}"
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(text, key, level=level, closed=False)
        self.notify("TOCEntry", (level, text, self.page, key))


def make_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "RulebookTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=27,
            leading=33,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#20252B"),
            spaceAfter=16,
        ),
        "subtitle": ParagraphStyle(
            "RulebookSubtitle",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=13,
            leading=18,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#5A6068"),
        ),
        "h1": ParagraphStyle(
            "Heading1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=21,
            leading=25,
            textColor=colors.HexColor("#20252B"),
            spaceAfter=13,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "Heading2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            textColor=colors.HexColor("#343B44"),
            spaceBefore=14,
            spaceAfter=7,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "Heading3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=15,
            textColor=colors.HexColor("#343B44"),
            leftIndent=14,
            spaceBefore=11,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "RulebookBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10.3,
            leading=15,
            textColor=colors.HexColor("#20252B"),
            spaceAfter=8,
        ),
        "quote": ParagraphStyle(
            "RulebookQuote",
            parent=base["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=10.3,
            leading=15,
            leftIndent=18,
            borderColor=colors.HexColor("#8B929B"),
            borderWidth=0,
            borderPadding=6,
            textColor=colors.HexColor("#4B535C"),
            spaceAfter=10,
        ),
        "toc_title": ParagraphStyle(
            "TocTitle",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            spaceAfter=14,
        ),
        "toc_1": ParagraphStyle(
            "TOC1",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=15,
            leftIndent=0,
            firstLineIndent=0,
            spaceBefore=3,
        ),
        "toc_2": ParagraphStyle(
            "TOC2",
            parent=base["Normal"],
            fontSize=9.5,
            leading=13,
            leftIndent=14,
            firstLineIndent=0,
        ),
        "toc_3": ParagraphStyle(
            "TOC3",
            parent=base["Normal"],
            fontSize=9,
            leading=12,
            leftIndent=28,
            firstLineIndent=0,
            textColor=colors.HexColor("#4B535C"),
        ),
    }


def paragraph_from_lines(lines: list[str], style: ParagraphStyle) -> Paragraph:
    text = " ".join(line.strip() for line in lines)
    return Paragraph(inline_markup(text), style)


def markdown_to_flowables(
    markdown: str,
    styles: dict[str, ParagraphStyle],
    *,
    first_chapter: bool,
) -> list[object]:
    lines = markdown.splitlines()
    story: list[object] = []
    paragraph_lines: list[str] = []
    list_items: list[str] = []
    table_rows: list[list[str]] = []

    def flush_paragraph() -> None:
        if paragraph_lines:
            story.append(paragraph_from_lines(paragraph_lines, styles["body"]))
            paragraph_lines.clear()

    def flush_list() -> None:
        if list_items:
            items = [
                ListItem(Paragraph(inline_markup(item), styles["body"]), leftIndent=12)
                for item in list_items
            ]
            story.append(
                ListFlowable(
                    items,
                    bulletType="bullet",
                    start="circle",
                    leftIndent=20,
                    bulletFontName="Helvetica",
                    bulletFontSize=7,
                    spaceAfter=7,
                )
            )
            list_items.clear()

    def flush_table() -> None:
        if not table_rows:
            return
        rows = table_rows[:]
        table_rows.clear()
        if len(rows) > 1 and all(re.fullmatch(r":?-{3,}:?", cell) for cell in rows[1]):
            del rows[1]
        data = [
            [Paragraph(inline_markup(cell), styles["body"]) for cell in row]
            for row in rows
        ]
        table = Table(data, repeatRows=1, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9ECEF")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#20252B")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#AAB0B7")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.extend([table, Spacer(1, 8)])

    for raw_line in lines:
        line = raw_line.rstrip()
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        table_line = line.startswith("|") and line.endswith("|")

        if heading:
            flush_paragraph()
            flush_list()
            flush_table()
            level = len(heading.group(1))
            if level == 1 and (story or not first_chapter):
                story.append(PageBreak())
            heading_paragraph = Paragraph(
                inline_markup(heading.group(2)), styles[f"h{level}"]
            )
            heading_paragraph.toc_level = level - 1
            story.append(heading_paragraph)
        elif table_line:
            flush_paragraph()
            flush_list()
            table_rows.append([cell.strip() for cell in line.strip("|").split("|")])
        elif line.startswith("- "):
            flush_paragraph()
            flush_table()
            list_items.append(line[2:].strip())
        elif line.startswith("> "):
            flush_paragraph()
            flush_list()
            flush_table()
            story.append(Paragraph(inline_markup(line[2:]), styles["quote"]))
        elif line.strip() in {"---", "***"}:
            flush_paragraph()
            flush_list()
            flush_table()
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.6,
                    color=colors.HexColor("#AAB0B7"),
                    spaceBefore=5,
                    spaceAfter=9,
                )
            )
        elif not line.strip():
            flush_paragraph()
            flush_list()
            flush_table()
        else:
            flush_list()
            flush_table()
            paragraph_lines.append(line)

    flush_paragraph()
    flush_list()
    flush_table()
    return story


def existing_sources() -> Iterable[Path]:
    missing: list[str] = []
    sources: list[Path] = []
    for relative_path in SOURCE_FILES:
        source = REPOSITORY_ROOT / relative_path
        if source.is_file():
            sources.append(source)
        else:
            missing.append(relative_path)
    if missing:
        formatted = "\n - ".join(missing)
        raise SystemExit(f"Missing rulebook source files:\n - {formatted}")
    return sources


def build_pdf(output_path: Path) -> None:
    if not LOGO_SOURCE.is_file():
        raise SystemExit(
            f"Missing rulebook logo: {LOGO_SOURCE.relative_to(REPOSITORY_ROOT)}"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    styles = make_styles()
    logo_width, logo_height = ImageReader(LOGO_SOURCE).getSize()
    rendered_logo_width = 4.8 * inch
    rendered_logo_height = rendered_logo_width * logo_height / logo_width
    story: list[object] = [
        Spacer(1, 1.15 * inch),
        Image(
            str(LOGO_SOURCE),
            width=rendered_logo_width,
            height=rendered_logo_height,
        ),
        Spacer(1, 0.5 * inch),
        Paragraph("Modern Carry Federation Rulebook", styles["title"]),
        Spacer(1, 2.5 * inch),
        Paragraph("Modern Carry Federation", styles["subtitle"]),
        NextPageTemplate("body"),
        PageBreak(),
        Paragraph("Table of Contents", styles["toc_title"]),
    ]

    toc = TableOfContents()
    toc.levelStyles = [styles["toc_1"], styles["toc_2"], styles["toc_3"]]
    toc.dotsMinLevel = 0
    story.extend([toc, PageBreak()])

    for index, source in enumerate(existing_sources()):
        story.extend(
            markdown_to_flowables(
                source.read_text(encoding="utf-8"),
                styles,
                first_chapter=index == 0,
            )
        )

    document = RulebookDocument(
        str(output_path),
        pagesize=LETTER,
        rightMargin=0.72 * inch,
        leftMargin=0.72 * inch,
        topMargin=0.68 * inch,
        bottomMargin=0.68 * inch,
        title="Modern Carry Federation Rulebook",
        author="Modern Carry Federation",
        subject="Competition rulebook",
    )
    document.multiBuild(story)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"PDF output path (default: {DEFAULT_OUTPUT})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = args.output.expanduser().resolve()
    build_pdf(output_path)
    print(f"Created {output_path} ({output_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
