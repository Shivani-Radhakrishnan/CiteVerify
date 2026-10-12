"""CiteVerify: detect fabricated or mis-cited academic references.

    >>> from citeverify import Auditor
    >>> result = Auditor().audit("He, K., et al. (2016). Deep residual learning ...", doi="10.1109/CVPR.2016.90")
    >>> result.label, result.tier
"""
from citeverify.models import AuditResult, Label, ParsedCitation, Signal, Stage, Tier, WorkRecord
from citeverify.parsing import extract_core_citation, find_doi, normalise_doi, parse_citation
from citeverify.pipeline import AuditConfig, Auditor, audit_citation, default_auditor

__all__ = [
    "AuditConfig", "AuditResult", "Auditor", "Label", "ParsedCitation", "Signal", "Stage", "Tier",
    "WorkRecord", "audit_citation", "default_auditor", "extract_core_citation", "find_doi",
    "normalise_doi", "parse_citation",
]
__version__ = "2.2.0"
