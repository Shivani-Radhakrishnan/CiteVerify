"""Build the held-out citation benchmark (deterministic).

Usage::

    python -m evaluation.build_benchmark

Inputs (hand-curated, checked against Crossref/DataCite):
    data/benchmark/sources/real_papers.csv           80 real papers with correct DOIs
    data/benchmark/sources/overlap_probe_papers.csv  25 real papers whose first authors
                                                     appear in the legacy known-papers table

Outputs:
    data/benchmark/benchmark.csv      labelled citations, split into ``dev`` and ``test``
    data/benchmark/overlap_probe.csv  correct citations of the probe papers (all real)

Class "real" (human_label=0) is a correct citation of a real paper, rendered in one of
three common reference styles (APA, IEEE, Vancouver), once with its DOI and once
without. Class "fabricated" (human_label=1) is synthetic: each item is produced by one
of the perturbations below, using a fixed random seed so the file is reproducible.

    fabricated_doi      invented authors/title + a DOI that does not resolve
    fabricated_arxiv    invented authors/title + an arXiv DOI that does not exist
    doi_swap            a real citation paired with another paper's DOI
    wrong_year_doi      a real citation with the year shifted by 2-6 years, real DOI
    wrong_author_doi    a real citation whose first author is replaced, real DOI
    future_year_doi     a real citation with an impossible future year, real DOI
    fabricated_text     invented authors/title/venue, no DOI
    chimeric_text       real authors/year/venue with an invented title, no DOI
    misattributed_text  a real title credited to another paper's authors/year, no DOI
    future_year_text    invented citation with an impossible future year, no DOI

Papers are split 50/50 into ``dev`` and ``test`` before any item is generated, so a
paper (and every perturbation derived from it) appears in only one split. Detection
changes are developed against ``dev``; ``test`` is reported.
"""
from __future__ import annotations

import csv
import random
import string
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "data" / "benchmark" / "sources"
OUT_DIR = ROOT / "data" / "benchmark"

SEED = 13
REFERENCE_YEAR = 2026  # benchmark construction year; "future" years are >= this + 3

FAKE_SURNAMES = [
    "Halvorsen", "Okonkwo", "Lindqvist", "Marchetti", "Duvall", "Szabo", "Kowalczyk",
    "Ferreira", "Nakamura", "Abernathy", "Castellano", "Ivanova", "Thibodeaux",
    "Oyelaran", "Brennan", "Kallio", "Moreau", "Vasquez", "Holm", "Achterberg",
    "Petrakis", "Sundaram", "Whitcombe", "Esposito", "Rasmussen", "Delacroix",
    "Mbeki", "Sorensen", "Quintero", "Hargreaves",
]
ADJECTIVES = [
    "Scalable", "Robust", "Hierarchical", "Contrastive", "Adaptive", "Sparse", "Federated",
    "Causal", "Probabilistic", "Multimodal", "Self-supervised", "Differentiable",
    "Lightweight", "Interpretable", "Uncertainty-aware", "Curriculum-guided",
]
METHODS = [
    "graph transformers", "diffusion priors", "attention routing", "kernel embeddings",
    "variational inference", "retrieval networks", "spectral clustering",
    "policy distillation", "neural operators", "token pruning", "prototype learning",
    "mixture-of-experts adapters",
]
TASKS = [
    "long-document summarization", "protein-ligand binding prediction",
    "traffic forecasting", "low-resource machine translation",
    "medical image segmentation", "citation recommendation",
    "anomaly detection in power grids", "few-shot relation extraction",
    "soil moisture estimation", "code clone detection", "wildfire spread modelling",
    "multilingual hate speech detection",
]
NOUNS = ["convergence", "robustness", "calibration", "generalization", "sample complexity"]
FAKE_VENUES = [
    "Proceedings of the AAAI Conference on Artificial Intelligence",
    "IEEE Transactions on Pattern Analysis and Machine Intelligence",
    "Nature Machine Intelligence",
    "Journal of Machine Learning Research",
    "Proceedings of the ACM Web Conference",
    "Transactions of the Association for Computational Linguistics",
    "Neural Networks",
    "Pattern Recognition",
]


@dataclass
class Paper:
    key: str
    authors: list[tuple[str, str]]  # (family, initials)
    et_al: bool
    year: int
    title: str
    venue: str
    doi: str


def load_papers(path: Path) -> list[Paper]:
    papers = []
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            authors = []
            for a in row["authors"].split(";"):
                family, _, initials = a.strip().partition(",")
                authors.append((family.strip(), initials.strip()))
            papers.append(Paper(
                key=row["key"], authors=authors, et_al=row["et_al"] == "1",
                year=int(row["year"]), title=row["title"], venue=row["venue"],
                doi=row["doi"].strip(),
            ))
    return papers


# ── Reference styles ────────────────────────────────────────────────────────

def _end(title: str) -> str:
    return title if title[-1:] in "?!." else title + "."


def fmt_apa(p: Paper) -> str:
    names = [f"{f}, {i}" for f, i in p.authors]
    if p.et_al:
        authors = ", ".join(names) + ", et al."
    elif len(names) == 1:
        authors = names[0]
    else:
        authors = ", ".join(names[:-1]) + ", & " + names[-1]
    return f"{authors} ({p.year}). {_end(p.title)} {p.venue}."


def fmt_ieee(p: Paper) -> str:
    names = [f"{i} {f}" for f, i in p.authors]
    if p.et_al:
        authors = names[0] + " et al."
    elif len(names) == 1:
        authors = names[0]
    elif len(names) == 2:
        authors = f"{names[0]} and {names[1]}"
    else:
        authors = ", ".join(names[:-1]) + ", and " + names[-1]
    title = p.title if p.title[-1:] in "?!" else p.title + ","
    return f'{authors}, "{title}" {p.venue}, {p.year}.'


def fmt_vancouver(p: Paper) -> str:
    names = [f"{f} {i.replace('.', '').replace(' ', '')}" for f, i in p.authors]
    authors = ", ".join(names) + (", et al" if p.et_al else "")
    return f"{authors}. {_end(p.title)} {p.venue}. {p.year}."


STYLES = {"apa": fmt_apa, "ieee": fmt_ieee, "vancouver": fmt_vancouver}


# ── Fabrication helpers ─────────────────────────────────────────────────────

def _initials(rng: random.Random) -> str:
    n = rng.choice([1, 1, 2])
    return " ".join(f"{rng.choice(string.ascii_uppercase)}." for _ in range(n))


def fake_authors(rng: random.Random, k: int | None = None) -> list[tuple[str, str]]:
    k = k or rng.choice([1, 2, 3, 3, 4])
    return [(s, _initials(rng)) for s in rng.sample(FAKE_SURNAMES, k)]


def fake_title(rng: random.Random) -> str:
    adj, meth, task = rng.choice(ADJECTIVES), rng.choice(METHODS), rng.choice(TASKS)
    pattern = rng.randrange(4)
    if pattern == 0:
        return f"{adj} {meth} for {task}"
    if pattern == 1:
        return f"Towards {adj.lower()} {meth} in {task}"
    if pattern == 2:
        return f"{meth[0].upper() + meth[1:]}: Rethinking {task} with {adj.lower()} objectives"
    return f"On the {rng.choice(NOUNS)} of {adj.lower()} {meth}"


def fake_doi(rng: random.Random, year: int) -> str:
    """A syntactically valid DOI placed in a number range the publisher has not issued."""
    d = lambda n: "".join(rng.choice(string.digits) for _ in range(n))  # noqa: E731
    kind = rng.randrange(5)
    if kind == 0:
        return f"10.1145/97{d(5)}.97{d(5)}"
    if kind == 1:
        return f"10.1109/TPAMI.{year}.8{d(6)}"
    if kind == 2:
        return f"10.1016/j.neunet.{year}.1{d(6)}"
    if kind == 3:
        return f"10.18653/v1/{year}.acl-long.19{d(2)}"
    return f"10.1038/s42256-0{str(year)[2:]}-9{d(4)}-{rng.randrange(10)}"


def fake_arxiv_doi(rng: random.Random, year: int) -> str:
    month = rng.randint(1, 12)
    return f"10.48550/arXiv.{str(year)[2:]}{month:02d}.9{rng.randint(5000, 9999)}"


def fake_paper(rng: random.Random, year: int | None = None) -> Paper:
    return Paper(
        key="fabricated", authors=fake_authors(rng), et_al=False,
        year=year or rng.randint(2015, 2024), title=fake_title(rng),
        venue=rng.choice(FAKE_VENUES), doi="",
    )


def _replace(p: Paper, **kw) -> Paper:
    data = dict(p.__dict__)
    data.update(kw)
    return Paper(**data)


# ── Build ───────────────────────────────────────────────────────────────────

FAKE_COUNTS = {
    "fabricated_doi": 8, "fabricated_arxiv": 3, "doi_swap": 6, "wrong_year_doi": 6,
    "wrong_author_doi": 5, "future_year_doi": 3, "fabricated_text": 10,
    "chimeric_text": 6, "misattributed_text": 5, "future_year_text": 4,
}


def build_split(papers: list[Paper], split: str, rng: random.Random) -> list[dict]:
    rows: list[dict] = []

    def add(p: Paper, doi: str, label: int, category: str, note: str = "") -> None:
        style = rng.choice(sorted(STYLES))
        rows.append({
            "split": split, "citation": STYLES[style](p), "doi": doi,
            "human_label": label, "category": category, "style": style,
            "source_key": p.key, "note": note,
        })

    for p in papers:
        add(p, p.doi, 0, "real_with_doi")
        add(p, "", 0, "real_text_only")

    def pick(n: int) -> list[Paper]:
        return rng.sample(papers, n)

    for _ in range(FAKE_COUNTS["fabricated_doi"]):
        fp = fake_paper(rng)
        add(fp, fake_doi(rng, fp.year), 1, "fabricated_doi")
    for _ in range(FAKE_COUNTS["fabricated_arxiv"]):
        fp = fake_paper(rng, year=rng.randint(2018, 2024))
        fp = _replace(fp, venue="arXiv preprint")
        add(fp, fake_arxiv_doi(rng, fp.year), 1, "fabricated_arxiv")
    for p in pick(FAKE_COUNTS["doi_swap"]):
        other = rng.choice([q for q in papers if q.key != p.key])
        add(p, other.doi, 1, "doi_swap", f"DOI belongs to {other.key}")
    for p in pick(FAKE_COUNTS["wrong_year_doi"]):
        shift = rng.choice([-6, -5, -4, -3, -2, 2, 3, 4, 5, 6])
        year = p.year + shift
        if year > REFERENCE_YEAR:
            year = p.year - abs(shift)
        add(_replace(p, year=year), p.doi, 1, "wrong_year_doi", f"true year {p.year}")
    for p in pick(FAKE_COUNTS["wrong_author_doi"]):
        new_first = (rng.choice(FAKE_SURNAMES), _initials(rng))
        authors = [new_first] + p.authors[1:]
        add(_replace(p, authors=authors), p.doi, 1, "wrong_author_doi",
            f"true first author {p.authors[0][0]}")
    for p in pick(FAKE_COUNTS["future_year_doi"]):
        add(_replace(p, year=rng.randint(REFERENCE_YEAR + 3, REFERENCE_YEAR + 14)), p.doi, 1,
            "future_year_doi", f"true year {p.year}")
    for _ in range(FAKE_COUNTS["fabricated_text"]):
        add(fake_paper(rng), "", 1, "fabricated_text")
    for p in pick(FAKE_COUNTS["chimeric_text"]):
        add(_replace(p, title=fake_title(rng)), "", 1, "chimeric_text",
            f"authors/venue/year from {p.key}")
    for p in pick(FAKE_COUNTS["misattributed_text"]):
        other = rng.choice([q for q in papers if q.key != p.key])
        add(_replace(p, authors=other.authors, et_al=other.et_al, year=other.year), "", 1,
            "misattributed_text", f"title of {p.key}, authors/year of {other.key}")
    for _ in range(FAKE_COUNTS["future_year_text"]):
        add(fake_paper(rng, year=rng.randint(REFERENCE_YEAR + 3, REFERENCE_YEAR + 14)), "", 1,
            "future_year_text")
    return rows


def build() -> tuple[list[dict], list[dict]]:
    rng = random.Random(SEED)
    papers = load_papers(SOURCES / "real_papers.csv")
    order = papers[:]
    rng.shuffle(order)
    half = len(order) // 2
    rows = build_split(order[:half], "dev", rng) + build_split(order[half:], "test", rng)
    for i, r in enumerate(rows, 1):
        r["id"] = f"B{i:03d}"

    probe_rows = []
    for i, p in enumerate(load_papers(SOURCES / "overlap_probe_papers.csv"), 1):
        style = rng.choice(sorted(STYLES))
        probe_rows.append({
            "id": f"P{i:03d}", "split": "probe", "citation": STYLES[style](p), "doi": "",
            "human_label": 0, "category": "real_text_only", "style": style,
            "source_key": p.key, "note": "first author appears in the legacy known-papers table",
        })
    return rows, probe_rows


FIELDS = ["id", "split", "citation", "doi", "human_label", "category", "style", "source_key", "note"]


def write(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    rows, probe = build()
    write(rows, OUT_DIR / "benchmark.csv")
    write(probe, OUT_DIR / "overlap_probe.csv")
    n_dev = sum(r["split"] == "dev" for r in rows)
    print(f"benchmark.csv: {len(rows)} rows ({n_dev} dev, {len(rows) - n_dev} test)")
    print(f"overlap_probe.csv: {len(probe)} rows")


if __name__ == "__main__":
    main()
