# Rulebook PDF Builder

`build_rulebook.py` combines the Markdown chapters in `rulebook/` into a single PDF.

## Requirements

- Python 3.9 or newer
- [ReportLab](https://pypi.org/project/reportlab/)

Install ReportLab with:

```shell
python -m pip install reportlab
```

## Usage

Run the script from the repository root:

```shell
python scripts/build_rulebook.py
```

The default output is:

```text
output/pdf/mcf-rulebook.pdf
```

To choose another output location, use `--output`:

```shell
python scripts/build_rulebook.py --output path/to/rulebook.pdf
```

The script works on Windows, macOS, and Linux. Source paths are resolved relative to the repository, so the command may also be run from another working directory.

## Included Content

The PDF contains all numbered chapters in order, followed by the appendix. It includes a title page, generated table of contents, PDF bookmarks, formatted tables and lists, and page numbers.

If a required chapter is missing, the script stops and lists the missing file. If ReportLab is unavailable, it prints the command needed to install it.
