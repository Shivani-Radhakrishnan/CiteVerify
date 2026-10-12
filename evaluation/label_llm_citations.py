"""Label citations written by language models as real or fabricated, independently of CiteVerify.

    python -m evaluation.label_llm_citations            # replay data/llm_citations/label_cache.json
    python -m evaluation.label_llm_citations --record   # query OpenAlex / doi.org / arXiv live

Ground truth comes mainly from OpenAlex, which CiteVerify never queries, so the labels are
not produced by the system being evaluated. Rules (written before CiteVerify was run on
this set):

* A citation is REAL when a work exists whose title matches (similarity >= 0.90, or the
  same main title when the registry drops the subtitle), whose author list contains the
  cited first author's surname, and whose year is within two of the cited year
  (online-first or preprint vs. print). If a DOI / arXiv ID is given, it must point to
  that same work.
* Otherwise it is FABRICATED, with a category:
    doi_nonexistent  the DOI / arXiv ID does not resolve at all
    doi_mismatch     the identifier resolves, but to a different work (or wrong year/author)
    wrong_author     the titled work exists, the cited first author is not on it
    wrong_year       the titled work exists, the year is off by more than one
    no_match         no work with that title was found (invented title)
* no_match items with a near miss (best title similarity 0.75-0.90) are written to the
  review file and decided by hand; decisions live in ``manual_labels.csv``.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "llm_citations"
RAW = DATA / "raw"
CACHE = DATA / "label_cache.json"
MANUAL = DATA / "manual_labels.csv"
OUT = DATA / "llm_citations.csv"
REVIEW = DATA / "needs_review.csv"   # written only when something needs a decision
UA = {"User-Agent": "CiteVerify-labeller/1.0 (+https://github.com/Shivani-Radhakrishnan/CiteVerify)"}

ARXIV_ID = re.compile(r"(?:arxiv[:/ ]*)?(\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?", re.I)


def norm(s: str) -> str:
    s = re.sub(r"[\u2010-\u2015\u2212-]", " ", s or "")      # any dash separates words
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s.lower()).split())


def sim(a: str, b: str) -> float:
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def main_title(t: str) -> str:
    """The part before a subtitle ("NavCog: A navigational ..." -> "NavCog")."""
    return re.split(r"\s*[:?]\s+", t or "", maxsplit=1)[0]


def titles_match(cited: str, record: str, pinned: bool) -> bool:
    """Same work's title. Registries often drop the subtitle, so the main titles may match
    instead; a one- or two-word main title only counts when an identifier pins the work."""
    if sim(cited, record) >= 0.90:
        return True
    a, b = main_title(cited), main_title(record)
    short = min(len(norm(a).split()), len(norm(b).split()))
    if not (sim(a, b) >= 0.95 and (pinned or short >= 3)):
        return False
    # The shorter title must be all of the other's main title, not just a shared opening.
    return norm(a) == norm(b) or norm(cited).startswith(norm(record)) or norm(record).startswith(norm(cited))


def parse_apa(text: str) -> dict:
    """First-author surname, year and title from an APA-style reference."""
    m = re.search(r"\((\d{4})[a-z]?(?:,[^)]*)?\)\.?\s*(.+)", text)
    year, title = (int(m.group(1)), m.group(2)) if m else (None, text)
    # The title runs to the first sentence end (". eClinicalMedicine", ". arXiv", "USA. Remote"
    # all end it); a bracketed note such as "[Doctoral dissertation]" is not part of it.
    title = re.sub(r"\s*\[[^\]]*\]", "", title.strip())
    t = re.split(r"(?<=[^\s.])(?<!\b[A-Z])(?<!\bvs)(?<!\be\.g)(?<!\bi\.e)(?<!\bal)(?<!\bSt)[.!]\s+|(?<=\?)\s+(?=[A-Z])", title, maxsplit=1)[0].strip().rstrip(".")
    author = re.split(r",|\s&\s|\s\(", text.strip(), maxsplit=1)[0].strip()
    return {"year": year, "title": t, "first_author": author}


def slim(url: str, body):
    """Keep only what the labeller reads, so the cache stays small enough to commit."""
    def work(w):
        return {"id": w.get("id"), "display_name": w.get("display_name"), "publication_year": w.get("publication_year"),
                "authorships": [{"author": {"display_name": a.get("author", {}).get("display_name")}}
                                for a in w.get("authorships", [])[:25]]}
    if body is None:
        return None
    if "arxiv.org" in url:
        keep = []
        for e in re.findall(r"<entry>.*?</entry>", body, re.S):
            keep.append("<entry>" + "".join(re.findall(r"<title>.*?</title>|<published>.*?</published>|<name>.*?</name>", e, re.S)) + "</entry>")
        return "".join(keep)
    if "api.openalex.org/works?" in url:
        return {"results": [work(w) for w in body.get("results") or []]}
    if "api.openalex.org/works/" in url:
        return work(body)
    if "doi.org/api/handles" in url:
        return {"responseCode": body.get("responseCode")}
    return body


class Fetcher:
    def __init__(self, record: bool):
        self.record = record
        self.cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}

    def get(self, url: str):
        if url in self.cache:
            return self.cache[url]
        if not self.record:
            raise SystemExit(f"not in label cache (run with --record): {url}")
        for attempt in range(6):
            try:
                r = requests.get(url, headers=UA, timeout=30, allow_redirects=False)
            except requests.RequestException:
                time.sleep(2 ** attempt)
                continue
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(3 * 2 ** attempt)
                continue
            body = r.text if "arxiv.org" in url else (r.json() if r.status_code == 200 and r.text.strip() else None)
            self.cache[url] = {"status": r.status_code, "body": slim(url, body)}
            time.sleep(3.0 if "arxiv.org" in url else 0.12)   # arXiv asks for 3 s between calls
            return self.cache[url]
        self.save()
        raise SystemExit(f"failed: {url}")

    def save(self):
        self.cache = {k: {"status": v["status"], "body": slim(k, v["body"])} for k, v in self.cache.items()}
        CACHE.write_text(json.dumps(self.cache, indent=0, sort_keys=True, ensure_ascii=False))


def surname_in(author: str, names: list[str]) -> bool:
    key = norm(author).split()
    key = key[-1] if key else ""
    if not key:
        return False
    return any(key in norm(n).split() for n in names)


def work_fields(w: dict) -> dict:
    return {
        "title": w.get("display_name") or w.get("title") or "",
        "year": w.get("publication_year"),
        "authors": [a.get("author", {}).get("display_name", "") for a in w.get("authorships", [])],
        "openalex": w.get("id", ""),
    }


def arxiv_record(f: Fetcher, arxiv_id: str):
    r = f.get(f"https://export.arxiv.org/api/query?id_list={arxiv_id}")
    body = r["body"] or ""
    entries = re.findall(r"<entry>(.*?)</entry>", body, re.S)
    if not entries or "<title>Error</title>" in entries[0]:
        return None
    e = entries[0]
    title = re.sub(r"\s+", " ", re.search(r"<title>(.*?)</title>", e, re.S).group(1)).strip()
    year = int(re.search(r"<published>(\d{4})", e).group(1))
    authors = [re.sub(r"\s+", " ", a).strip() for a in re.findall(r"<name>(.*?)</name>", e, re.S)]
    return {"title": title, "year": year, "authors": authors, "openalex": ""}


def resolve_identifier(f: Fetcher, ident: str):
    """Return (exists, record or None)."""
    m = ARXIV_ID.fullmatch(ident.strip()) or (ARXIV_ID.search(ident) if "arxiv" in ident.lower() else None)
    if m:
        rec = arxiv_record(f, m.group(1))
        return rec is not None, rec
    doi = re.sub(r"^(https?://)?(dx\.)?doi\.org/|^doi:\s*", "", ident.strip(), flags=re.I)
    r = f.get(f"https://api.openalex.org/works/doi:{quote(doi, safe='/')}")
    if r["status"] == 200 and r["body"]:
        return True, work_fields(r["body"])
    h = f.get(f"https://doi.org/api/handles/{quote(doi, safe='/')}")
    exists = h["status"] == 200 and (h["body"] or {}).get("responseCode") == 1
    return exists, None


def search_title(f: Fetcher, title: str):
    q = quote(norm(title)[:200])
    r = f.get(f"https://api.openalex.org/works?search={q}&per-page=8")
    cands = [work_fields(w) for w in ((r["body"] or {}).get("results") or [])]
    r2 = f.get(f"https://export.arxiv.org/api/query?search_query=ti:%22{q}%22&max_results=5")
    for e in re.findall(r"<entry>(.*?)</entry>", r2["body"] or "", re.S):
        t = re.search(r"<title>(.*?)</title>", e, re.S)
        y = re.search(r"<published>(\d{4})", e)
        if t and y:
            cands.append({"title": re.sub(r"\s+", " ", t.group(1)).strip(), "year": int(y.group(1)),
                          "authors": [re.sub(r"\s+", " ", a).strip() for a in re.findall(r"<name>(.*?)</name>", e, re.S)],
                          "openalex": ""})
    return cands


def matches(p: dict, rec: dict, pinned: bool = False) -> tuple[bool, str]:
    """Year tolerance is 2: registries often store the online-first year, which can be a
    year or two before the print year that a correct reference cites."""
    if not titles_match(p["title"], rec["title"], pinned):
        return False, "title"
    if not surname_in(p["first_author"], rec["authors"]):
        return False, "author"
    if p["year"] is not None and rec["year"] is not None and abs(p["year"] - rec["year"]) > 2:
        return False, "year"
    return True, ""


def label(f: Fetcher, row: dict) -> dict:
    p = parse_apa(row["citation"])
    out = {"parsed_title": p["title"], "parsed_year": p["year"], "parsed_author": p["first_author"],
           "matched_title": "", "best_sim": 0.0}
    ident = row["doi"].strip()
    if ident:
        exists, rec = resolve_identifier(f, ident)
        if not exists:
            return out | {"human_label": 1, "category": "doi_nonexistent"}
        if rec is None:  # registered DOI that OpenAlex doesn't index: decide by title search below
            pass
        else:
            ok, why = matches(p, rec, pinned=True)
            out["matched_title"] = rec["title"]
            out["best_sim"] = round(sim(p["title"], rec["title"]), 3)
            if ok:
                return out | {"human_label": 0, "category": "real_with_id"}
            return out | {"human_label": 1, "category": "doi_mismatch"}
    cands = search_title(f, p["title"])
    best = max(cands, key=lambda c: sim(p["title"], c["title"]), default=None)
    if best:
        out["matched_title"] = best["title"]
        out["best_sim"] = round(sim(p["title"], best["title"]), 3)
    titled = [c for c in cands if titles_match(p["title"], c["title"], pinned=False)]
    if not titled:
        return out | {"human_label": 1, "category": "no_match"}
    for c in titled:
        if matches(p, c)[0]:
            return out | {"human_label": 0, "category": "real_with_id" if ident else "real_text_only"}
    reasons = {matches(p, c)[1] for c in titled}
    return out | {"human_label": 1, "category": "wrong_author" if "author" in reasons else "wrong_year"}


def build(record: bool = False) -> tuple[list[dict], list[dict]]:
    """Label every raw citation. Returns (rows, rows that need a manual decision)."""
    f = Fetcher(record)
    manual = {}
    if MANUAL.exists():
        with MANUAL.open(newline="") as fh:
            manual = {r["id"]: r for r in csv.DictReader(fh)}
    rows, review = [], []
    for path in sorted(RAW.glob("*.jsonl")):
        model = path.stem
        for i, line in enumerate(l for l in path.read_text().splitlines() if l.strip()):
            item = json.loads(line)
            row = {"id": f"{model}-{i + 1:03d}", "model": model, "topic": item["topic"],
                   "citation": item["citation"].strip(), "doi": (item.get("doi") or "").strip()}
            row |= label(f, row)
            if row["id"] in manual:
                row["human_label"] = int(manual[row["id"]]["human_label"])
                row["category"] = manual[row["id"]]["category"]
                row["note"] = manual[row["id"]].get("note", "manual")
            elif row["category"] == "no_match" and row["best_sim"] >= 0.75:
                review.append(row)
            rows.append(row)
    if record:
        f.save()
    return rows, review


FIELDS = ["id", "model", "topic", "citation", "doi", "human_label", "category", "parsed_author",
          "parsed_year", "parsed_title", "matched_title", "best_sim", "note"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true")
    args = ap.parse_args()
    rows, review = build(args.record)
    fields = FIELDS
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    if review:
        with REVIEW.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(review)
    elif REVIEW.exists():
        REVIEW.unlink()
    from collections import Counter
    print(len(rows), "citations;", Counter((r["model"], r["human_label"]) for r in rows))
    print(Counter(r["category"] for r in rows))
    print(len(review), "need manual review", f"-> {REVIEW.relative_to(ROOT)}" if review else "")


if __name__ == "__main__":
    sys.exit(main())
