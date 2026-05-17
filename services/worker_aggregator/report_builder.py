"""Construye reporte consolidado HTML+PDF a partir de un caso completado."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from services.shared.models.case import Case

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _severity_summary(case: Case) -> dict[int, int]:
    counts: dict[int, int] = {}
    for f in case.findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    return counts


def render_html(case: Case) -> str:
    tpl = _env.get_template("report.html")
    return tpl.render(
        case=case,
        generated_at=datetime.utcnow().isoformat() + "Z",
        severity_summary=_severity_summary(case),
        findings_by_category=_group_by_category(case),
    )


def render_pdf(html: str) -> bytes:
    from weasyprint import HTML  # import diferido para tests

    return HTML(string=html).write_pdf()


def _group_by_category(case: Case) -> dict[str, list]:
    grouped: dict[str, list] = {}
    for f in case.findings:
        grouped.setdefault(f.category, []).append(f)
    return grouped
