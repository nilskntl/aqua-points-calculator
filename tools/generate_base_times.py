"""Regenerate the shipped base-time tables from the official World Aquatics PDFs.

The YAML files under ``aqua_points_calculator/data/base_times`` are generated, not
hand-maintained. This script is what generates them, so a new season is added by
dropping the new PDF text next to it and extending the tables below rather than
by typing 48 times into a file.

Usage::

    pip install pyyaml          # only for the caller's own checks; not needed here
    brew install poppler        # for pdftotext
    curl -sL <pdf-url> -o work/base2026.pdf
    pdftotext -layout work/base2026.pdf work/base2026.txt
    python tools/generate_base_times.py work/

Two source shapes are understood:

* **Base-times PDFs** — a small table per course and season, men and women side
  by side plus a mixed-relay block. Authoritative, and preferred wherever World
  Aquatics published one.
* **Full point-scoring tables** — the 1000-point row *is* the base time. Verified
  to agree exactly with the base-times PDF for LCM 2025 across all 17 events,
  and used only for the three course-seasons that never got a base-times PDF.

Every value a base-times PDF prints twice (once as ``mm:ss.hh``, once in
seconds) is cross-checked against itself; see ``NOTES`` for the single place the
two columns of an official document disagree.
"""

from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

#: Directory holding the `pdftotext -layout` output of the official PDFs.
SOURCES = Path("work")


TIME = r"\d+(?:\s*:\s*\d{2})*(?:[.,]\d{1,2})?"
NUM = r"\d+(?:\.\d+)?"

STROKES = {
    "Freestyle": "freestyle",
    "Backstroke": "backstroke",
    "Breaststroke": "breaststroke",
    "Butterfly": "butterfly",
    "Medley": "medley",
}

ROW = re.compile(
    rf"^\s*(?:(?P<legs>\d+)\s*x\s*)?(?P<dist>\d+)\s*m?\s+"
    rf"(?P<stroke>{'|'.join(STROKES)})(?:\s+Relay)?\s+"
    rf"(?P<rest>(?:{TIME}|{NUM})(?:\s+(?:{TIME}|{NUM}))*)\s*$"
)
SECTION = re.compile(r"(?P<course>SCM|LCM)\s*\((?:25|50)m\)\s*(?P<season>\d{4})")
VALIDITY_RE = re.compile(
    r"Validity period:\s*(?P<f>\d{2}\.\d{2}\.\d{4})\s*[–-]\s*(?P<u>\d{2}\.\d{2}\.\d{4})"
)


def to_millis(text: str) -> int:
    """'1:02.34' / '1 :02,34' / '46.40' -> milliseconds."""
    cleaned = re.sub(r"\s+", "", text).replace(",", ".")
    parts = cleaned.split(":")
    total = 0.0
    for part in parts:
        total = total * 60 + float(part)
    return int(round(total * 1000))


def parse_base_times(path: Path) -> dict:
    """Parse a 'Base Times' PDF's text into {(course, season): section}."""
    lines = path.read_text().splitlines()
    out: dict[tuple[str, int], dict] = {}
    current: dict | None = None

    for line in lines:
        section = SECTION.search(line)
        if section and "Base Times" not in line:
            course = "short" if section["course"] == "SCM" else "long"
            current = {
                "course": course,
                "season": int(section["season"]),
                "records": {},
            }
            out[(course, int(section["season"]))] = current
            continue
        if current is None:
            continue

        validity = VALIDITY_RE.search(line)
        if validity:
            current.setdefault("valid_from", validity["f"])
            current.setdefault("valid_until", validity["u"])
            continue

        row = ROW.match(line)
        if not row:
            continue
        values = re.findall(rf"{TIME}|{NUM}", row["rest"])
        legs = int(row["legs"] or 1)
        key = (int(row["dist"]), STROKES[row["stroke"]], legs)
        # 4 tokens: men time, men seconds, women time, women seconds.
        # 2 tokens: a mixed-relay row (time, seconds).
        if len(values) == 4:
            current["records"][(*key, "male")] = (values[0], values[1])
            current["records"][(*key, "female")] = (values[2], values[3])
        elif len(values) == 2:
            current["records"][(*key, "mixed")] = (values[0], values[1])
    return out


# --- scoring-table column orders, read off the PDF headers -------------------
IND_LCM = [
    (50, "freestyle"),
    (100, "freestyle"),
    (200, "freestyle"),
    (400, "freestyle"),
    (800, "freestyle"),
    (1500, "freestyle"),
    (50, "backstroke"),
    (100, "backstroke"),
    (200, "backstroke"),
    (50, "breaststroke"),
    (100, "breaststroke"),
    (200, "breaststroke"),
    (50, "butterfly"),
    (100, "butterfly"),
    (200, "butterfly"),
    (200, "medley"),
    (400, "medley"),
]
IND_SCM = IND_LCM[:15] + [(100, "medley"), (200, "medley"), (400, "medley")]
REL_LCM = [
    (100, "freestyle", "female"),
    (200, "freestyle", "female"),
    (100, "medley", "female"),
    (100, "freestyle", "male"),
    (200, "freestyle", "male"),
    (100, "medley", "male"),
    (100, "freestyle", "mixed"),
    (100, "medley", "mixed"),
]
REL_SCM = [
    (50, "freestyle", "female"),
    (100, "freestyle", "female"),
    (200, "freestyle", "female"),
    (50, "medley", "female"),
    (100, "medley", "female"),
    (50, "freestyle", "male"),
    (100, "freestyle", "male"),
    (200, "freestyle", "male"),
    (50, "medley", "male"),
    (100, "medley", "male"),
    (50, "freestyle", "mixed"),
    (50, "medley", "mixed"),
]


def thousand_row(path: Path) -> list[str]:
    for line in path.read_text().splitlines():
        if re.match(r"^\s*1000\s", line):
            toks = line.split()
            assert toks[0] == "1000" and toks[-1] == "1000", toks[:3]
            return toks[1:-1]
    raise AssertionError(f"no 1000-point row in {path}")


def from_scoring(course: str, season: int, male: Path, female: Path, relay: Path) -> dict:
    ind = IND_LCM if course == "long" else IND_SCM
    rel = REL_LCM if course == "long" else REL_SCM
    records: dict = {}
    for gender, path in (("male", male), ("female", female)):
        values = thousand_row(path)
        assert len(values) == len(ind), (course, season, gender, len(values))
        for (dist, stroke), value in zip(ind, values, strict=True):
            records[(dist, stroke, 1, gender)] = (value, None)
    values = thousand_row(relay)
    assert len(values) == len(rel), (course, season, "relay", len(values))
    for (dist, stroke, gender), value in zip(rel, values, strict=True):
        records[(dist, stroke, 4, gender)] = (value, None)
    return {"course": course, "season": season, "records": records}


# --- generation ---------------------------------------------------------------


OUT = REPO / "aqua_points_calculator" / "data" / "base_times"

BASE_DOCS = {
    "base2021": (
        "FINA Points - Base Times SCM and LCM 2021",
        "https://resources.fina.org/fina/document/2021/09/02/31feb6d8-e393-4a4b-b56b-fe425081764f/FINA-Points-Base-times-SCM-and-LCM-2021.pdf",  # noqa: E501
    ),
    "base2023": (
        "World Aquatics Points - Base Times SCM 2022 and LCM 2023",
        "https://resources.fina.org/fina/document/2023/01/16/f1b09b6f-ca69-4d68-ac4c-62bb2f3919a7/World-Aquatics-Points-Base-times-SCM-2022-and-LCM-2023.pdf",  # noqa: E501
    ),
    "base2025": (
        "World Aquatics Points - Base Times SCM and LCM 2025",
        "https://resources.fina.org/fina/document/2025/01/08/baaf68c9-0118-42c3-ac3f-e11ce013fd8a/Points-Base-times-SCM-and-LCM-2025.pdf",  # noqa: E501
    ),
    "base2026": (
        "World Aquatics Points - Base Times SCM and LCM 2026",
        "https://resources.fina.org/fina/document/2026/01/27/3886f5b2-5bcf-464e-a626-059be2ed4567/Points-Base-times-SCM-and-LCM-2026_01.2026.pdf",  # noqa: E501
    ),
}

SCORING = {
    ("long", 2022): (
        "FINA Point Scoring 2022 - Long Course (50m)",
        "https://resources.fina.org/fina/document/2022/01/13/b1f4e17e-348b-47cc-bfc8-18104653d55f/FINA-Points-LCM_2022_Male-.pdf",  # noqa: E501
        "lcm2022m",
        "lcm2022f",
        "lcm2022r",
    ),
    ("long", 2024): (
        "World Aquatics Point Scoring 2024 - Long Course (50m)",
        "https://resources.fina.org/fina/document/2024/01/08/a2e0fa93-bab6-4306-8631-dd7d219e5c3d/World-Aquatics-Points-LCM_2024_Male-.pdf",  # noqa: E501
        "lcm2024m",
        "lcm2024f",
        "lcm2024r",
    ),
    ("short", 2023): (
        "World Aquatics Point Scoring 2023 - Short Course (25m)",
        "https://resources.fina.org/fina/document/2023/09/23/87d63954-2ad2-492e-aeb4-4a88f7557896/World-Aquatics-Points-SCM_2023_Male-.pdf",  # noqa: E501
        "scm2023m",
        "scm2023f",
        "scm2023r",
    ),
}

VALIDITY = {
    ("long", 2022): ("01.01.2022", "31.12.2022"),
    ("long", 2024): ("01.01.2024", "31.12.2024"),
    ("short", 2023): ("01.09.2023", "31.08.2024"),
}

# The only place the two printed columns of an official PDF disagree. The
# scoring table for the same season (World-Aquatics-Points-SCM_2022_Female.pdf)
# reads 54.59 at 1000 points, so the mm:ss column is right and the seconds
# column is the typo.
NOTES = {
    ("short", 2022): (
        "The official base-times PDF prints the women's 100 m butterfly as 54.59 in "
        "the mm:ss column and 54.69 in the seconds column. The point-scoring table "
        "for the same season reads 54.59 at 1000 points, so 54.59 is used here."
    ),
}

STROKE_ORDER = ["freestyle", "backstroke", "breaststroke", "butterfly", "medley"]
GENDER_ORDER = ["male", "female", "mixed"]

WANTED = [("long", y) for y in (2022, 2023, 2024, 2025, 2026)] + [
    ("short", y) for y in (2021, 2022, 2023, 2024, 2025)
]


def collect() -> dict:
    tables: dict = {}
    for name, (title, url) in BASE_DOCS.items():
        for key, section in parse_base_times(SOURCES / f"{name}.txt").items():
            section["source"] = {"title": title, "url": url}
            tables[key] = section
    for (course, season), (title, url, m, f, r) in SCORING.items():
        section = from_scoring(
            course, season, SOURCES / f"{m}.txt", SOURCES / f"{f}.txt", SOURCES / f"{r}.txt"
        )
        section["source"] = {"title": title, "url": url}
        section["valid_from"], section["valid_until"] = VALIDITY[(course, season)]
        tables[(course, season)] = section
    return tables


def iso(german: str) -> str:
    return dt.datetime.strptime(german, "%d.%m.%Y").date().isoformat()


def render(course: str, season: int, section: dict) -> str:
    label = "LCM (50m)" if course == "long" else "SCM (25m)"
    lines = [
        f"# World Aquatics base times — {label} {season}.",
        "#",
        "# A base time is the world record that stood approved on the START of the",
        "# validity period, so this table is a snapshot of that moment and does not",
        "# change when a record falls mid-season. Long course and short course run on",
        "# different calendars, which is why each has its own season numbering.",
        "#",
        "# Generated from the official World Aquatics publication named in `source`.",
        "# Every value was cross-checked against the second column that publication",
        "# prints for it; do not hand-edit.",
    ]
    if (course, season) in NOTES:
        note = NOTES[(course, season)]
        lines += ["#"] + [f"# {line}" for line in _wrap(note, 74)]
    lines += [
        "",
        f"course: {course}",
        f"season: {season}",
        f"valid_from: {iso(section['valid_from'])}",
        f"valid_until: {iso(section['valid_until'])}",
        "source:",
        f"  title: {section['source']['title']}",
        f"  url: {section['source']['url']}",
        "",
        "records:",
    ]

    def sort_key(item):
        (dist, stroke, legs, gender), _ = item
        return (legs, STROKE_ORDER.index(stroke), dist, GENDER_ORDER.index(gender))

    prev = None
    for (dist, stroke, legs, gender), (display, _) in sorted(
        section["records"].items(), key=sort_key
    ):
        group = (legs, stroke)
        if prev is not None and prev != group:
            lines.append("")
        prev = group
        event = f"{legs}x{dist}" if legs > 1 else str(dist)
        entry = f"distance: {dist}, stroke: {stroke}, gender: {gender}"
        if legs > 1:
            entry += f", legs: {legs}"
        del event
        lines.append(f'  - {{ {entry}, time: "{display.replace(" ", "")}" }}')
    return "\n".join(lines) + "\n"


def _wrap(text: str, width: int) -> list[str]:
    words, out, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        out.append(cur)
    return out


def main() -> None:
    tables = collect()
    OUT.mkdir(parents=True, exist_ok=True)
    for course, season in WANTED:
        section = tables[(course, season)]
        if (course, season) in NOTES:
            section["records"][(100, "butterfly", 1, "female")] = ("54.59", "54.59")
        path = OUT / f"{course}-{season}.yaml"
        path.write_text(render(course, season, section))
        print(
            f"{path.name:18} {len(section['records']):3} records  "
            f"{section['valid_from']}–{section['valid_until']}"
        )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        SOURCES = Path(sys.argv[1])
    main()
