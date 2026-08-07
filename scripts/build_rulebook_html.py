#!/usr/bin/env python3
"""Build standalone and WordPress-ready HTML versions of the MCF rulebook."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPOSITORY_ROOT / "output" / "html"
SOURCE_FILES = (
    "rulebook/01-purpose.md",
    "rulebook/02-core-tenets.md",
    "rulebook/03-safety.md",
    "rulebook/04-range-commands.md",
    "rulebook/05-stages-design.md",
    "rulebook/06-divisions.md",
    "rulebook/07-equipment.md",
    "rulebook/08-scoring.md",
    "rulebook/09-penalties.md",
    "rulebook/10-match-administration.md",
    "rulebook/appendix.md",
)

CSS = """.mcf-rulebook{--mcf-ink:#20252b;--mcf-muted:#5a6068;--mcf-line:#d8dde2;--mcf-accent:#a3262a;box-sizing:border-box;max-width:900px;margin:0 auto;color:var(--mcf-ink);font:17px/1.65 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.mcf-rulebook *{box-sizing:border-box}.mcf-rulebook header{text-align:center;padding:2.5rem 1rem;border-bottom:3px solid var(--mcf-accent)}.mcf-rulebook header h1{margin:0;font-size:clamp(2rem,6vw,3.4rem);line-height:1.1}.mcf-rulebook .mcf-tagline{margin:.65rem 0 0;color:var(--mcf-muted);font-style:italic}.mcf-rulebook nav{margin:2rem 0;padding:1.25rem 1.5rem;background:#f5f6f7;border:1px solid var(--mcf-line);border-radius:8px}.mcf-rulebook nav h2{margin-top:0}.mcf-rulebook nav ol{columns:2;column-gap:2rem;margin-bottom:0}.mcf-rulebook nav li{break-inside:avoid;margin:.25rem 0}.mcf-rulebook a{color:var(--mcf-accent);text-decoration-thickness:1px;text-underline-offset:2px}.mcf-rulebook section{scroll-margin-top:2rem}.mcf-rulebook section>h2{margin-top:3.25rem;padding-bottom:.4rem;border-bottom:2px solid var(--mcf-line);font-size:2rem;line-height:1.2}.mcf-rulebook h3{margin-top:2rem;font-size:1.4rem;line-height:1.3}.mcf-rulebook h4{margin-top:1.5rem;font-size:1.12rem}.mcf-rulebook blockquote{margin:1.5rem 0;padding:.75rem 1.25rem;border-left:4px solid var(--mcf-accent);background:#f8f8f8;color:var(--mcf-muted)}.mcf-rulebook table{width:100%;margin:1.5rem 0;border-collapse:collapse}.mcf-rulebook th,.mcf-rulebook td{padding:.65rem .8rem;border:1px solid var(--mcf-line);text-align:left}.mcf-rulebook th{background:#eef0f2}.mcf-rulebook ul{padding-left:1.4rem}.mcf-rulebook footer{margin-top:4rem;padding:1.5rem 0;border-top:1px solid var(--mcf-line);color:var(--mcf-muted);font-size:.9rem}@media(max-width:650px){.mcf-rulebook{font-size:16px}.mcf-rulebook nav ol{columns:1}.mcf-rulebook section>h2{font-size:1.65rem}}@media print{.mcf-rulebook nav{break-after:page}.mcf-rulebook section>h2{break-before:page}.mcf-rulebook a{color:inherit;text-decoration:none}}"""


def slugify(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value).lower()
    # Match the GitHub-style anchors already used by the Markdown sources:
    # punctuation is removed, then runs of whitespace become hyphens.
    value = re.sub(r"[^a-z0-9\s-]", "", value)
    return re.sub(r"[\s-]+", "-", value).strip("-")


def inline_markup(value: str, source: Path) -> str:
    value = html.escape(value.strip(), quote=True)
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", value)

    def link(match: re.Match[str]) -> str:
        label, target = match.groups()
        if target.endswith(".md") or ".md#" in target:
            filename, _, fragment = target.partition("#")
            destination = slugify(fragment) if fragment else slugify(filename.removesuffix(".md"))
            target = f"#{destination}"
        return f'<a href="{html.escape(target, quote=True)}">{label}</a>'

    return re.sub(r"\[([^]]+)]\(([^)]+)\)", link, value)


def markdown_to_html(markdown: str, source: Path) -> tuple[str, list[tuple[int, str, str]]]:
    output: list[str] = []
    headings: list[tuple[int, str, str]] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    table_rows: list[list[str]] = []

    def flush_paragraph() -> None:
        if paragraph:
            output.append(f"<p>{inline_markup(' '.join(paragraph), source)}</p>")
            paragraph.clear()

    def flush_list() -> None:
        if list_items:
            output.append("<ul>" + "".join(f"<li>{inline_markup(item, source)}</li>" for item in list_items) + "</ul>")
            list_items.clear()

    def flush_table() -> None:
        if not table_rows:
            return
        rows = table_rows[:]
        table_rows.clear()
        separator = len(rows) > 1 and all(re.fullmatch(r":?-{3,}:?", cell) for cell in rows[1])
        if separator:
            del rows[1]
        head = rows.pop(0)
        output.append("<table><thead><tr>" + "".join(f"<th>{inline_markup(cell, source)}</th>" for cell in head) + "</tr></thead>")
        if rows:
            output.append("<tbody>" + "".join("<tr>" + "".join(f"<td>{inline_markup(cell, source)}</td>" for cell in row) + "</tr>" for row in rows) + "</tbody>")
        output.append("</table>")

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            flush_paragraph(); flush_list(); flush_table()
            level = len(heading.group(1)) + 1
            title = heading.group(2).strip()
            anchor = slugify(title)
            headings.append((level, title, anchor))
            output.append(f'<h{level} id="{anchor}">{inline_markup(title, source)}</h{level}>')
        elif line.startswith("|") and line.endswith("|"):
            flush_paragraph(); flush_list()
            table_rows.append([cell.strip() for cell in line.strip("|").split("|")])
        elif line.startswith("- "):
            flush_paragraph(); flush_table()
            list_items.append(line[2:].strip())
        elif line.startswith("> "):
            flush_paragraph(); flush_list(); flush_table()
            output.append(f"<blockquote>{inline_markup(line[2:], source)}</blockquote>")
        elif not line.strip():
            flush_paragraph(); flush_list(); flush_table()
        elif line.strip() in {"---", "***"}:
            flush_paragraph(); flush_list(); flush_table(); output.append("<hr>")
        else:
            flush_list(); flush_table(); paragraph.append(line.strip())
    flush_paragraph(); flush_list(); flush_table()
    return "\n".join(output), headings


def build(output_dir: Path) -> None:
    chapters: list[str] = []
    toc: list[tuple[str, str]] = []
    for relative in SOURCE_FILES:
        source = REPOSITORY_ROOT / relative
        if not source.is_file():
            raise SystemExit(f"Missing rulebook source file: {relative}")
        chapter, headings = markdown_to_html(source.read_text(encoding="utf-8"), source)
        if not headings:
            continue
        first_level, first_title, first_anchor = headings[0]
        if first_level != 2:
            raise SystemExit(f"Expected a level-one heading in {relative}")
        toc.append((first_title, first_anchor))
        chapters.append(f'<section aria-labelledby="{first_anchor}">{chapter}</section>')

    navigation = "<nav aria-label=\"Rulebook contents\"><h2>Contents</h2><ol>" + "".join(
        f'<li><a href="#{anchor}">{html.escape(title)}</a></li>' for title, anchor in toc
    ) + "</ol></nav>"
    article = "\n".join((
        '<article class="mcf-rulebook">',
        '<header><h1>Modern Carry Federation Rulebook</h1><p class="mcf-tagline">Ad Futurum</p></header>',
        navigation,
        *chapters,
        '<footer>Modern Carry Federation</footer>',
        "</article>",
    ))
    fragment = f"<style>\n{CSS}\n</style>\n{article}\n"
    document = "\n".join((
        "<!doctype html>", '<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        "<title>Modern Carry Federation Rulebook</title>", f"<style>{CSS}</style>",
        f"</head><body>{article}</body></html>\n",
    ))
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "mcf-rulebook.html").write_text(document, encoding="utf-8")
    (output_dir / "mcf-rulebook-wordpress.html").write_text(fragment, encoding="utf-8")
    print(f"Created HTML rulebook files in {output_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    build(args.output_dir.expanduser().resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
