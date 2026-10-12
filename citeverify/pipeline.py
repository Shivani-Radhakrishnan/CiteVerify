"""The audit pipeline: route a citation through the detection tiers.

Order (the first tier that decides wins):

1. **Temporal check** — a future year is impossible, with or without a DOI.
2. **DOI registry** — if a DOI is given (or written in the text), resolve it and compare
   title, year and first author with the registry record.
3. **Known-papers table** — legacy, disabled by default (see ``detectors/known_papers``).
4. **Registry search** — no DOI: search Crossref, then arXiv, by title and compare.
5. **Plausibility heuristics** — last resort when nothing could be looked up.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from typing import Iterable, Optional

from citeverify.clients.http import HttpClient, HttpError
from citeverify.clients.registries import ArxivClient, CrossrefClient, DataCiteClient, DoiOrgClient
from citeverify.detectors import Decision, heuristics, known_papers, temporal
from citeverify.detectors.doi import DoiVerifier
from citeverify.detectors.search import RegistrySearch
from citeverify.models import AuditResult, ParsedCitation, Signal, Stage, Tier
from citeverify.parsing import normalise_doi, parse_citation


@dataclass(frozen=True)
class AuditConfig:
    """Pipeline switches. Defaults are what the app uses."""

    use_registry: bool = True       # resolve DOIs
    use_search: bool = True         # title search when there is no DOI
    use_known_papers: bool = False  # legacy lookup table (kept for the ablation only)
    threshold: float = 0.20         # scores below this are labelled HALLUCINATED
    not_found_score: float = 0.15   # score when a title search finds nothing
    current_year: Optional[int] = None  # for the temporal check; defaults to today


class Auditor:
    """Audits citations. Thread-safe; reuse one instance so the HTTP cache is shared."""

    def __init__(self, config: AuditConfig = AuditConfig(), http: Optional[HttpClient] = None) -> None:
        self.config = config
        self.http = http or HttpClient()
        crossref, arxiv = CrossrefClient(self.http), ArxivClient(self.http)
        self.doi_verifier = DoiVerifier(crossref, DataCiteClient(self.http), arxiv, DoiOrgClient(self.http))
        self.search = RegistrySearch(crossref, arxiv, not_found_score=config.not_found_score)

    def with_config(self, **changes) -> "Auditor":
        """A new auditor sharing this one's HTTP client (and cache) with some settings changed."""
        return Auditor(replace(self.config, **changes), self.http)

    # ── public API ──────────────────────────────────────────────────────────

    def audit(self, text: str, doi: Optional[str] = None) -> AuditResult:
        """Audit one citation. ``doi`` is optional; a DOI found in ``text`` is also used."""
        parsed = parse_citation(text)
        signals: list[Signal] = []
        trace: list[Stage] = []

        doi_norm = normalise_doi(doi) if doi and str(doi).strip() else None
        if doi and str(doi).strip() and doi_norm is None:
            signals.append(Signal("DOI field", "warn", f"'{str(doi).strip()[:60]}' is not a valid DOI; ignored."))
        doi_norm = doi_norm or parsed.doi
        if doi_norm is None and parsed.arxiv_id:
            doi_norm = f"10.48550/arXiv.{parsed.arxiv_id}"
        if doi_norm and parsed.doi != doi_norm:
            parsed = replace(parsed, doi=doi_norm)

        # 1. temporal
        decision, sig = temporal.check(parsed, self.config.current_year)
        signals.append(sig)
        if decision:
            return self._finish(parsed, decision, Tier.TEMPORAL, trace, signals[:-1])
        trace.append(Stage(Tier.TEMPORAL, "passed"))

        # 2. DOI registry
        if doi_norm and self.config.use_registry:
            decision = self.doi_verifier.check(parsed, doi_norm)
            return self._finish(parsed, decision, Tier.DOI, trace, signals)
        trace.append(Stage(Tier.DOI, "skipped", "no DOI" if not doi_norm else "disabled"))

        # 3. legacy known-papers table
        if self.config.use_known_papers:
            decision = known_papers.check(parsed.cleaned)
            if decision:
                return self._finish(parsed, decision, Tier.KNOWN, trace, signals)
            trace.append(Stage(Tier.KNOWN, "passed", "no match"))

        # 4. registry search
        if self.config.use_search and self.search.applicable(parsed):
            try:
                decision = self.search.check(parsed)
            except HttpError as exc:
                signals.append(Signal("Registry search", "warn", f"Unavailable: {exc}"))
                trace.append(Stage(Tier.SEARCH, "skipped", "registry unreachable"))
                result = self._finish(parsed, heuristics.check(parsed.cleaned), Tier.HEURISTIC, trace, signals)
                result.error = str(exc)
                return result
            if decision:
                return self._finish(parsed, decision, Tier.SEARCH, trace, signals)
        trace.append(Stage(
            Tier.SEARCH, "skipped",
            "disabled" if not self.config.use_search else "no searchable title",
        ))

        # 5. heuristics
        return self._finish(parsed, heuristics.check(parsed.cleaned), Tier.HEURISTIC, trace, signals)

    def audit_many(self, items: Iterable[tuple[str, Optional[str]]], max_workers: int = 4) -> list[AuditResult]:
        """Audit ``(text, doi)`` pairs concurrently, preserving order."""
        items = list(items)
        if max_workers <= 1 or len(items) <= 1:
            return [self.audit(t, d) for t, d in items]
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            return list(pool.map(lambda td: self.audit(*td), items))

    # ── internals ───────────────────────────────────────────────────────────

    def _finish(self, parsed: ParsedCitation, d: Decision, tier: Tier,
                trace: list[Stage], signals: list[Signal]) -> AuditResult:
        trace = trace + [Stage(tier, "decided")]
        return AuditResult(
            verdict=d.verdict, sub=d.sub, tier=tier.value, explanation=d.explanation,
            action=d.action, score=d.score, threshold=self.config.threshold,
            signals=signals + d.signals, trace=trace, parsed=parsed, record=d.record,
            features=d.features, error=d.error,
            details={"real_title": d.record.title, "real_year": d.record.year,
                     "source": d.record.source} if d.record else {},
        )


_default: Optional[Auditor] = None


def default_auditor() -> Auditor:
    """Process-wide auditor with default settings (shared HTTP cache)."""
    global _default
    if _default is None:
        _default = Auditor()
    return _default


def audit_citation(text: str, doi: Optional[str] = None) -> AuditResult:
    """Convenience wrapper around :meth:`Auditor.audit` with default settings."""
    return default_auditor().audit(text, doi)
