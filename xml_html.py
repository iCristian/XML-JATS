from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from lxml import etree


_XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
_SANITIZE_ENTITY_RE = re.compile(r"&(?![a-zA-Z]+;|#\d+;|#x[0-9a-fA-F]+;)")


def _clean_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _node_text(node: etree._Element) -> str:
    parts: List[str] = []
    if node.text:
        parts.append(node.text)
    for child in node:
        parts.append(_node_text(child))
        if child.tail:
            parts.append(child.tail)
    return _clean_whitespace("".join(parts))


def _xpath(node: etree._Element, expression: str, namespaces: Dict[str, str]) -> List[Any]:
  result = node.xpath(expression, namespaces=namespaces)
  if result or "j:" not in expression:
    return result
  fallback_expression = expression.replace("j:", "")
  try:
    return node.xpath(fallback_expression)
  except etree.XPathError:
    return []


def _first_text(node: etree._Element, expression: str, namespaces: Dict[str, str]) -> str:
    results = _xpath(node, expression, namespaces)
    if not results:
        return ""
    candidate = results[0]
    if isinstance(candidate, str):
        return _clean_whitespace(candidate)
    if isinstance(candidate, etree._Element):
        return _node_text(candidate)
    return _clean_whitespace(str(candidate))


def _sanitize_xml(raw_xml: str) -> str:
    cleaned = raw_xml.replace("\u000b", " ").replace("\u000c", " ")
    decl_match = re.search(r"<\?xml[^>]*?>", cleaned)
    decl = decl_match.group(0) if decl_match else '<?xml version="1.0" encoding="UTF-8"?>'
    doctype_match = re.search(r"<!DOCTYPE[^>]*?>", cleaned)
    doctype = doctype_match.group(0) if doctype_match else ""
    article_match = re.search(r"<article[\s\S]*?</article>", cleaned)
    if not article_match:
        raise ValueError("No se encontró un nodo <article> válido en el archivo JATS.")
    article_xml = article_match.group(0)
    payload = "\n".join(part for part in [decl, doctype, article_xml] if part)
    payload = _SANITIZE_ENTITY_RE.sub("&amp;", payload)
    return payload


def _ensure_namespace(root: etree._Element) -> Dict[str, str]:
    namespaces = {prefix: uri for prefix, uri in root.nsmap.items() if prefix}
    default_ns = root.nsmap.get(None)
    if default_ns:
        namespaces.setdefault("j", default_ns)
    namespaces.setdefault("j", "http://www.ncbi.nlm.nih.gov/JATS1")
    namespaces.setdefault("xlink", "http://www.w3.org/1999/xlink")
    return namespaces


def parse_jats(xml_path: str) -> Dict[str, Any]:
    raw_xml = Path(xml_path).read_text(encoding="utf-8")
    sanitized = _sanitize_xml(raw_xml)
    parser = etree.XMLParser(
        resolve_entities=False,
        remove_blank_text=True,
        load_dtd=False,
        no_network=True,
        dtd_validation=False,
    )
    root = etree.fromstring(sanitized.encode("utf-8"), parser)
    namespaces = _ensure_namespace(root)

    front = root.find(".//{*}front")
    body = root.find(".//{*}body")
    back = root.find(".//{*}back")
    article_meta = front.find(".//{*}article-meta") if front is not None else None

    data: Dict[str, Any] = {
        "title": "",
        "translated_title": "",
        "journal_title": "",
        "publisher": "",
        "pub_date": "",
        "volume": "",
        "issue": "",
        "fpage": "",
        "lpage": "",
        "elocation": "",
        "doi": "",
        "authors": [],
        "keywords": [],
        "abstract_paragraphs": [],
        "sections": [],
        "figures": [],
        "tables": [],
        "references": [],
    }

    if article_meta is not None:
        data["title"] = _first_text(article_meta, ".//j:article-title", namespaces)
        data["translated_title"] = _first_text(article_meta, ".//j:translated-title", namespaces)
        data["journal_title"] = _first_text(article_meta, ".//j:journal-title", namespaces)
        data["publisher"] = _first_text(article_meta, ".//j:publisher-name", namespaces)
        data["pub_date"] = _extract_pub_date(article_meta, namespaces)
        data["volume"] = _first_text(article_meta, ".//j:volume", namespaces)
        data["issue"] = _first_text(article_meta, ".//j:issue", namespaces)
        data["fpage"] = _first_text(article_meta, ".//j:fpage", namespaces)
        data["lpage"] = _first_text(article_meta, ".//j:lpage", namespaces)
        data["elocation"] = _first_text(article_meta, ".//j:elocation-id", namespaces)
        data["doi"] = _first_text(article_meta, ".//j:article-id[@pub-id-type='doi']", namespaces)
        data["abstract_paragraphs"] = _extract_paragraphs(article_meta, ".//j:abstract/j:p", namespaces)
        data["keywords"] = _extract_keywords(article_meta, namespaces)
        data["authors"] = _extract_authors(article_meta, namespaces)

    if body is not None:
        data["sections"] = _extract_sections(body, namespaces)
        data["figures"] = _extract_figures(body, namespaces)
        data["tables"] = _extract_tables(body, namespaces)

    if back is not None:
        data["references"] = _extract_references(back, namespaces)

    return data


def _extract_pub_date(article_meta: etree._Element, namespaces: Dict[str, str]) -> str:
    for node in _xpath(article_meta, ".//j:pub-date", namespaces):
        day = _first_text(node, "./j:day", namespaces)
        month = _first_text(node, "./j:month", namespaces)
        year = _first_text(node, "./j:year", namespaces)
        if year and month and day:
            return f"{day}/{month}/{year}"
        if year and month:
            return f"{month}/{year}"
        if year:
            return year
    return ""


def _extract_keywords(article_meta: etree._Element, namespaces: Dict[str, str]) -> List[str]:
    keywords: List[str] = []
    for kwd in _xpath(article_meta, ".//j:kwd-group/j:kwd", namespaces):
        text = _node_text(kwd)
        if text:
            keywords.append(text)
    return keywords


def _extract_authors(article_meta: etree._Element, namespaces: Dict[str, str]) -> List[Dict[str, Any]]:
    affiliations: Dict[str, str] = {}
    for aff in _xpath(article_meta, ".//j:aff", namespaces):
        aff_id = aff.get(_XML_ID) or aff.get("id")
        if aff_id:
            affiliations[aff_id] = _node_text(aff)

    authors: List[Dict[str, Any]] = []
    for contrib in _xpath(article_meta, ".//j:contrib-group/j:contrib[@contrib-type='author']", namespaces):
        surname = _first_text(contrib, "./j:name/j:surname", namespaces)
        given = _first_text(contrib, "./j:name/j:given-names", namespaces)
        collective = _first_text(contrib, "./j:collab", namespaces)
        full_name = collective or " ".join(part for part in [given, surname] if part)
        if not full_name:
            continue

        author_affs: List[str] = []
        for xref in _xpath(contrib, ".//j:xref[@ref-type='aff']", namespaces):
            rid = xref.get("rid")
            if rid and rid in affiliations:
                author_affs.append(affiliations[rid])
        if not author_affs:
            inline_aff = contrib.find(".//{*}aff")
            inline_text = _node_text(inline_aff) if inline_aff is not None else ""
            if inline_text:
                author_affs.append(inline_text)

        emails: List[str] = []
        for email in _xpath(contrib, ".//j:email", namespaces):
            value = _node_text(email)
            if value:
                emails.append(value)

        authors.append(
            {
                "full": full_name,
                "affiliations": author_affs,
                "emails": emails,
            }
        )
    return authors


def _extract_paragraphs(parent: etree._Element, expression: str, namespaces: Dict[str, str]) -> List[str]:
    paragraphs: List[str] = []
    for element in _xpath(parent, expression, namespaces):
        text = _node_text(element)
        if text:
            paragraphs.append(text)
    return paragraphs


def _extract_sections(body: etree._Element, namespaces: Dict[str, str]) -> List[Dict[str, Any]]:
    def serialize(sec: etree._Element, index: int) -> Dict[str, Any]:
        sec_id = sec.get(_XML_ID) or sec.get("id") or f"sec-{index}"
        children = _xpath(sec, "./j:sec", namespaces)
        return {
            "id": sec_id,
            "label": _first_text(sec, "./j:label", namespaces),
            "title": _first_text(sec, "./j:title", namespaces) or f"Sección {index}",
            "paragraphs": _extract_paragraphs(sec, "./j:p", namespaces),
            "subsections": [serialize(child, idx) for idx, child in enumerate(children, start=1)],
        }

    sections: List[Dict[str, Any]] = []
    for idx, sec in enumerate(_xpath(body, "./j:sec", namespaces), start=1):
        sections.append(serialize(sec, idx))
    return sections


def _extract_figures(body: etree._Element, namespaces: Dict[str, str]) -> List[Dict[str, Any]]:
    figures: List[Dict[str, Any]] = []
    for fig in _xpath(body, ".//j:fig", namespaces):
        fig_id = fig.get(_XML_ID) or fig.get("id") or f"fig-{len(figures) + 1}"
        label = _first_text(fig, "./j:label", namespaces)
        caption = _first_text(fig, "./j:caption", namespaces)
        graphic = fig.find(".//{*}graphic")
        href = ""
        if graphic is not None:
            href = graphic.get(f"{{{namespaces['xlink']}}}href", "")
        figures.append(
            {
                "id": fig_id,
                "label": label,
                "caption": caption,
                "href": href,
            }
        )
    return figures


def _extract_tables(body: etree._Element, namespaces: Dict[str, str]) -> List[Dict[str, Any]]:
    tables: List[Dict[str, Any]] = []
    for wrap in _xpath(body, ".//j:table-wrap", namespaces):
        table_id = wrap.get(_XML_ID) or wrap.get("id") or f"table-{len(tables) + 1}"
        label = _first_text(wrap, "./j:label", namespaces)
        caption = _first_text(wrap, "./j:caption", namespaces)
        table_node = wrap.find(".//{*}table")
        rows: List[List[str]] = []
        if table_node is not None:
            for row in table_node.findall(".//{*}tr"):
                cells: List[str] = []
                for cell in list(row.findall(".//{*}th")) + list(row.findall(".//{*}td")):
                    cells.append(_node_text(cell))
                if cells:
                    rows.append(cells)
        tables.append(
            {
                "id": table_id,
                "label": label,
                "caption": caption,
                "rows": rows,
            }
        )
    return tables


def _extract_references(back: etree._Element, namespaces: Dict[str, str]) -> List[Dict[str, str]]:
    references: List[Dict[str, str]] = []
    for ref in _xpath(back, ".//j:ref-list/j:ref", namespaces):
        label = _first_text(ref, "./j:label", namespaces)
        text = _node_text(ref)
        references.append({"label": label, "text": text})
    return references


def _collect_section_entries(sections: List[Dict[str, Any]], prefix: str = "", level: int = 1) -> List[Tuple[int, str, str, str]]:
    entries: List[Tuple[int, str, str, str]] = []
    for idx, section in enumerate(sections, start=1):
        number = f"{prefix}{idx}" if prefix else str(idx)
        label = section.get("label") or number
        entries.append((level, section["id"], label, section["title"]))
        entries.extend(_collect_section_entries(section["subsections"], f"{number}.", level + 1))
    return entries


def _render_keywords(keywords: Iterable[str]) -> str:
    items = [f"<li>{escape(keyword)}</li>" for keyword in keywords if keyword]
    if not items:
        return ""
    return """
    <section class=\"panel\">
      <h3>Palabras clave</h3>
      <ul class=\"keyword-list\">{items}</ul>
    </section>
    """.replace("{items}", "".join(items))


def _render_authors(authors: List[Dict[str, Any]]) -> str:
    if not authors:
        return ""
    author_items = []
    for author in authors:
        parts = [f"<span class=\"author-name\">{escape(author['full'])}</span>"]
        if author.get("affiliations"):
            affs = "; ".join(escape(aff) for aff in author["affiliations"] if aff)
            parts.append(f"<span class=\"author-affiliations\">{affs}</span>")
        if author.get("emails"):
            emails = ", ".join(f"<a href=\"mailto:{escape(email)}\">{escape(email)}</a>" for email in author["emails"] if email)
            parts.append(f"<span class=\"author-emails\">{emails}</span>")
        author_items.append(f"<li class=\"author\">{'<br>'.join(parts)}</li>")
    return """
    <section class=\"panel\">
      <h3>Autores</h3>
      <ul class=\"author-list\">{items}</ul>
    </section>
    """.replace("{items}", "".join(author_items))


def _render_paragraphs(paragraphs: Iterable[str]) -> str:
    return "".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs if paragraph)


def _render_sections(sections: List[Dict[str, Any]], depth: int = 1, prefix: str = "") -> str:
  html_parts: List[str] = []
  heading_tags = {1: "h2", 2: "h3", 3: "h4", 4: "h5"}
  for idx, section in enumerate(sections, start=1):
    number = f"{prefix}{idx}" if prefix else str(idx)
    heading_tag = heading_tags.get(depth, "h6")
    title = escape(section["title"])
    label_text = section.get("label") or number
    label = escape(label_text) if label_text else ""
    section_id = escape(section["id"])
    classes = ["article-section", f"level-{depth}"]
    if depth == 1:
      classes.extend(["main-section", "surface"])
    else:
      classes.append("subsection")
    html_parts.append(f"<section id=\"{section_id}\" class=\"{' '.join(classes)}\">")
    heading_parts = ["<header class=\"section-header\">"]
    if label:
      heading_parts.append(f"<span class=\"section-eyebrow\">{label}</span>")
    heading_parts.append(f"<{heading_tag}>{title}</{heading_tag}>")
    heading_parts.append("</header>")
    html_parts.append("".join(heading_parts))
    body_html = _render_paragraphs(section["paragraphs"])
    if body_html:
      html_parts.append(f"<div class=\"section-body\">{body_html}</div>")
    if section["subsections"]:
      html_parts.append("<div class=\"subsection-group\">")
      html_parts.append(_render_sections(section["subsections"], depth + 1, f"{number}."))
      html_parts.append("</div>")
    html_parts.append("</section>")
  return "".join(html_parts)


def _render_figures(figures: List[Dict[str, Any]]) -> str:
    if not figures:
        return ""
    figure_blocks: List[str] = []
    for fig in figures:
        caption = escape(fig.get("caption") or "")
        label = escape(fig.get("label") or "Figura")
        href = escape(fig.get("href") or "")
        alt = caption or label
        media = f"<img src=\"{href}\" alt=\"{alt}\" loading=\"lazy\">" if href else ""
        figure_blocks.append(
            """
            <figure id=\"{id}\" class=\"media\">
              {media}
              <figcaption><span class=\"media-label\">{label}</span> {caption}</figcaption>
            </figure>
            """.replace("{id}", escape(fig.get("id") or ""))
            .replace("{media}", media)
            .replace("{label}", label)
            .replace("{caption}", caption)
        )
    return """
    <section class=\"panel\" id=\"figures\">
      <h3>Figuras</h3>
      {figures}
    </section>
    """.replace("{figures}", "".join(figure_blocks))


def _render_tables(tables: List[Dict[str, Any]]) -> str:
    if not tables:
        return ""
    table_blocks: List[str] = []
    for table in tables:
        rows_html: List[str] = []
        for row in table["rows"]:
            cells_html = "".join(f"<td>{escape(cell)}</td>" for cell in row)
            rows_html.append(f"<tr>{cells_html}</tr>")
        label = escape(table.get("label") or "Tabla")
        caption = escape(table.get("caption") or "")
        table_blocks.append(
            """
            <figure id=\"{id}\" class=\"table-wrap\">
              <figcaption><span class=\"media-label\">{label}</span> {caption}</figcaption>
              <div class=\"table-scroll\">
                <table>{rows}</table>
              </div>
            </figure>
            """.replace("{id}", escape(table.get("id") or ""))
            .replace("{label}", label)
            .replace("{caption}", caption)
            .replace("{rows}", "".join(rows_html))
        )
    return """
    <section class=\"panel\" id=\"tables\">
      <h3>Tablas</h3>
      {tables}
    </section>
    """.replace("{tables}", "".join(table_blocks))


def _render_references(references: List[Dict[str, str]]) -> str:
  if not references:
    return ""
  items: List[str] = []
  for ref in references:
    label = escape(ref.get("label") or "")
    text = escape(ref.get("text") or "")
    if label:
      items.append(f"<li><span class=\"reference-label\">{label}</span> {text}</li>")
    else:
      items.append(f"<li>{text}</li>")
  return """
  <section class=\"panel\" id=\"references\">
    <h3>Referencias</h3>
    <ol class=\"reference-list\">{items}</ol>
  </section>
  """.replace("{items}", "".join(items))


def _render_sidebar(doc: Dict[str, Any]) -> str:
    sections = doc.get("sections", [])
    entries = _collect_section_entries(sections)
    nav_items: List[str] = []
    for level, sec_id, label, title in entries:
        nav_items.append(
            """
            <li class=\"toc-item level-{level}\">
              <a href=\"#{href}\">
                <span class=\"toc-marker\" aria-hidden=\"true\"></span>
                <span class=\"toc-number\">{label}</span>
                <span class=\"toc-title\">{title}</span>
              </a>
            </li>
            """
            .replace("{level}", str(level))
            .replace("{href}", escape(sec_id))
            .replace("{label}", escape(label))
            .replace("{title}", escape(title))
        )
    toc_html = (
        "".join(nav_items)
        if nav_items
        else "<li class=\"toc-item\"><span class=\"toc-title\">Contenido no disponible</span></li>"
    )

    meta_rows: List[str] = []
    journal = doc.get("journal_title")
    if journal:
        meta_rows.append(f"<li><span>Revista:</span> {escape(journal)}</li>")
    publisher = doc.get("publisher")
    if publisher:
        meta_rows.append(f"<li><span>Editorial:</span> {escape(publisher)}</li>")
    issue_bits = [doc.get("volume"), doc.get("issue")]
    issue = "".join(bit for bit in issue_bits if bit)
    if issue:
        meta_rows.append(f"<li><span>Volumen/Edición:</span> {escape(issue)}</li>")
    pages = "".join(filter(None, [doc.get("fpage"), doc.get("lpage")]))
    if pages:
        meta_rows.append(f"<li><span>Páginas:</span> {escape(pages)}</li>")
    elocation = doc.get("elocation")
    if elocation:
        meta_rows.append(f"<li><span>Ubicación electrónica:</span> {escape(elocation)}</li>")
    doi = doc.get("doi")
    if doi:
        meta_rows.append(f"<li><span>DOI:</span> <a href=\"https://doi.org/{escape(doi)}\">{escape(doi)}</a></li>")
    pub_date = doc.get("pub_date")
    if pub_date:
        meta_rows.append(f"<li><span>Fecha:</span> {escape(pub_date)}</li>")

    template = """
  <aside class=\"sidebar\" id=\"sidebar\" aria-label=\"Índice de contenido\" aria-hidden=\"false\">
      <div class=\"sidebar-header\">
        <h2>Contenido</h2>
        <button class=\"sidebar-close\" id=\"sidebarClose\" aria-label=\"Cerrar índice\">✕</button>
      </div>
      <nav class=\"toc\">
        <ul>{toc}</ul>
      </nav>
      <section class=\"panel meta\">
        <h3>Ficha técnica</h3>
        <ul class=\"meta-list\">{meta}</ul>
      </section>
      {keywords}
    </aside>
    """

    return (
        template.replace("{toc}", toc_html)
        .replace("{meta}", "".join(meta_rows) if meta_rows else "<li>Información no disponible</li>")
        .replace("{keywords}", _render_keywords(doc.get("keywords", [])))
    )


def build_html(doc: Dict[str, Any]) -> str:
    title = escape(doc.get("title") or "Artículo sin título")
    translated_title = escape(doc.get("translated_title") or "")

    css = """
:root {
  color-scheme: light;
  --font-sans: "Inter", "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif;
  --bg-body: linear-gradient(180deg, #eef2ff 0%, #fdf2ff 60%, #ffffff 100%);
  --bg-card: rgba(255, 255, 255, 0.92);
  --accent: #2563eb;
  --accent-secondary: #f97316;
  --accent-soft: rgba(37, 99, 235, 0.14);
  --accent-soft-alt: rgba(249, 115, 22, 0.16);
  --border-soft: rgba(37, 99, 235, 0.14);
  --text-main: #0b1120;
  --text-muted: #3b4860;
  --text-subtle: #5b6477;
  --shadow-soft: 0 30px 70px -40px rgba(30, 41, 83, 0.6);
  --radius-md: 20px;
  --focus-ring: 0 0 0 3px rgba(37, 99, 235, 0.35);
  --bg-soft: rgba(37, 99, 235, 0.08);
  --gradient-header: linear-gradient(120deg, rgba(37, 99, 235, 0.95), rgba(124, 58, 237, 0.9));
}
body[data-theme="dark"] {
  color-scheme: dark;
  --bg-body: #050b18;
  --bg-card: rgba(11, 21, 40, 0.92);
  --accent: #60a5fa;
  --accent-secondary: #fbbf24;
  --accent-soft: rgba(96, 165, 250, 0.2);
  --accent-soft-alt: rgba(251, 191, 36, 0.2);
  --border-soft: rgba(96, 165, 250, 0.22);
  --text-main: #e2e8f0;
  --text-muted: #cbd5f5;
  --text-subtle: #94a3b8;
  --shadow-soft: 0 34px 70px -35px rgba(0, 0, 0, 0.75);
  --focus-ring: 0 0 0 3px rgba(96, 165, 250, 0.5);
  --bg-soft: rgba(96, 165, 250, 0.12);
  --gradient-header: linear-gradient(120deg, rgba(37, 99, 235, 0.35), rgba(124, 58, 237, 0.3));
}
body[data-contrast="high"] {
  --bg-body: #f8fafc;
  --bg-card: #ffffff;
  --accent: #0b1120;
  --accent-secondary: #d97706;
  --accent-soft: rgba(15, 23, 42, 0.14);
  --accent-soft-alt: rgba(217, 119, 6, 0.18);
  --border-soft: rgba(15, 23, 42, 0.45);
  --text-main: #0b1120;
  --text-muted: #0f172a;
  --text-subtle: #1f2937;
  --shadow-soft: none;
  --focus-ring: 0 0 0 3px #0f172a;
  --bg-soft: rgba(15, 23, 42, 0.08);
  --gradient-header: linear-gradient(120deg, rgba(11, 17, 32, 0.95), rgba(59, 7, 100, 0.9));
}
body[data-theme="dark"][data-contrast="high"] {
  --bg-body: #020817;
  --bg-card: #05122e;
  --accent: #facc15;
  --accent-secondary: #34d399;
  --accent-soft: rgba(250, 204, 21, 0.28);
  --accent-soft-alt: rgba(52, 211, 153, 0.28);
  --border-soft: rgba(250, 204, 21, 0.5);
  --text-main: #f8fafc;
  --text-muted: #e2e8f0;
  --text-subtle: #cbd5f5;
  --focus-ring: 0 0 0 3px rgba(250, 204, 21, 0.6);
  --bg-soft: rgba(250, 204, 21, 0.18);
  --gradient-header: linear-gradient(120deg, rgba(250, 204, 21, 0.32), rgba(59, 130, 246, 0.32));
}
*, *::before, *::after {
  box-sizing: border-box;
}
html {
  scroll-behavior: smooth;
}
body {
  margin: 0;
  font-family: var(--font-sans);
  background: var(--bg-body);
  color: var(--text-main);
  transition: background 0.25s ease, color 0.25s ease;
  overflow-x: hidden;
}
body.sidebar-lock {
  overflow: hidden;
}
a {
  color: var(--accent);
  text-decoration: none;
}
a:hover, a:focus {
  text-decoration: underline;
}
a:focus-visible, button:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
}
button {
  font: inherit;
}
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.app-header {
  padding: 32px clamp(16px, 4vw, 48px) 28px;
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 20px;
  background: var(--gradient-header);
  color: #ffffff;
  border-radius: 0 0 var(--radius-md) var(--radius-md);
  box-shadow: var(--shadow-soft);
  position: relative;
  overflow: hidden;
}
.app-header::after {
  content: "";
  position: absolute;
  inset: auto 0 0;
  height: 160px;
  background: radial-gradient(circle at 20% 40%, rgba(255, 255, 255, 0.28), transparent 60%),
    radial-gradient(circle at 80% 20%, rgba(255, 255, 255, 0.18), transparent 55%);
  pointer-events: none;
}
.branding {
  flex: 1 1 320px;
  position: relative;
  z-index: 1;
}
.branding h1 {
  font-size: clamp(2rem, 2.8vw, 2.75rem);
  margin: 0;
  letter-spacing: -0.02em;
  color: #ffffff;
}
.branding .translated-title {
  margin: 8px 0 0;
  font-size: clamp(1.1rem, 2vw, 1.35rem);
  color: rgba(255, 255, 255, 0.8);
}
.control-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  position: relative;
  z-index: 1;
}
.control-bar button {
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.35);
  color: #ffffff;
  padding: 10px 16px;
  border-radius: 999px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}
.control-bar button:hover {
  transform: translateY(-1px);
  background: rgba(255, 255, 255, 0.22);
  box-shadow: var(--shadow-soft);
}
.control-bar button .state {
  font-weight: 500;
}
.layout {
  position: relative;
  padding: 0 clamp(16px, 4vw, 56px) 48px;
}
.sidebar {
  width: min(340px, 82vw);
  background: var(--bg-card);
  border: 1px solid var(--border-soft);
  border-radius: 0 24px 24px 0;
  box-shadow: var(--shadow-soft);
  padding: 28px 24px;
  position: fixed;
  top: 0;
  left: 0;
  height: 100vh;
  overflow: hidden auto;
  transform: translateX(-110%);
  transition: transform 0.32s ease;
  backdrop-filter: blur(22px);
  z-index: 22;
}
body.sidebar-open .sidebar {
  transform: translateX(0);
}
.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.sidebar-header h2 {
  margin: 0;
  font-size: 1.3rem;
  color: var(--accent);
}
.sidebar-close {
  background: transparent;
  border: none;
  color: var(--text-subtle);
  font-size: 1.2rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.sidebar .panel {
  margin-top: 24px;
}
.sidebar .panel h3 {
  margin: 0 0 12px;
  font-size: 1rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-subtle);
}
.toc ul, .meta-list, .keyword-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 10px;
}
.toc-item a {
  display: grid;
  grid-template-columns: auto auto 1fr;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 14px;
  color: var(--text-main);
  background: transparent;
  transition: background 0.2s ease, transform 0.2s ease;
  line-height: 1.35;
  font-weight: 500;
}
.toc-item a:hover {
  background: var(--accent-soft);
  transform: translateX(4px);
}
.toc-marker {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: var(--accent);
  box-shadow: 0 0 0 4px var(--accent-soft);
}
body[data-theme="dark"] .toc-marker {
  box-shadow: 0 0 0 4px var(--accent-soft-alt);
}
.toc-number {
  font-weight: 600;
  color: var(--accent);
  min-width: 2.5ch;
}
.toc-number:empty {
  display: none;
}
.toc-title {
  color: var(--text-main);
}
.toc-item.level-2 {
  margin-left: 12px;
}
.toc-item.level-3 {
  margin-left: 24px;
}
.toc-item.level-4 {
  margin-left: 36px;
}
.toc-item.level-2 a {
  font-size: 0.95rem;
}
.toc-item.level-3 a {
  font-size: 0.9rem;
}
.toc-item.level-4 a {
  font-size: 0.85rem;
}
.meta-list span {
  font-weight: 600;
  display: block;
  color: var(--text-subtle);
}
.keyword-list {
  flex-wrap: wrap;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
}
.keyword-list li {
  background: linear-gradient(135deg, var(--accent-soft), var(--accent-soft-alt));
  color: var(--accent);
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 0.9rem;
}
.main {
  background: transparent;
  width: 100%;
  max-width: 960px;
  margin: 0 auto;
}
.surface {
  background: var(--bg-card);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-soft);
  padding: clamp(24px, 3vw, 48px);
  margin-bottom: 32px;
}
.surface h2, .surface h3, .surface h4, .surface h5, .surface h6 {
  margin-top: 48px;
  margin-bottom: 16px;
  scroll-margin-top: 120px;
}
.article-body {
  margin-bottom: 32px;
}
.section-grid {
  display: grid;
  gap: clamp(18px, 2.8vw, 32px);
  grid-template-columns: minmax(0, 1fr);
}
.article-section {
  transition: transform 0.28s ease, box-shadow 0.28s ease;
}
.article-section.main-section {
  position: relative;
  overflow: hidden;
}
.article-section.main-section::before {
  content: "";
  position: absolute;
  left: clamp(16px, 2.5vw, 32px);
  right: clamp(16px, 2.5vw, 32px);
  top: clamp(16px, 2.5vw, 28px);
  height: 4px;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--accent), var(--accent-secondary));
  opacity: 0.85;
}
.article-section.main-section:hover {
  transform: translateY(-4px);
  box-shadow: 0 40px 70px -45px rgba(37, 99, 235, 0.45);
}
.article-section.main-section .section-header {
  padding-top: clamp(8px, 1.8vw, 14px);
}
.section-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.section-header h2, .section-header h3, .section-header h4, .section-header h5, .section-header h6 {
  margin: 0;
  color: var(--text-main);
}
.section-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent-secondary);
}
.section-body {
  display: grid;
  gap: 16px;
  margin-top: 12px;
}
.section-body p {
  line-height: 1.75;
  font-size: 1.03rem;
  color: var(--text-muted);
}
.subsection-group {
  display: grid;
  gap: 16px;
  margin-top: 20px;
  padding-left: clamp(14px, 1.8vw, 22px);
  border-left: 3px solid var(--accent-soft);
}
.article-section.subsection {
  padding: 0;
  border: none;
  background: transparent;
  box-shadow: none;
}
.article-section.subsection .section-header h3,
.article-section.subsection .section-header h4,
.article-section.subsection .section-header h5,
.article-section.subsection .section-header h6 {
  color: var(--text-main);
}
.article-section.subsection .section-body p {
  font-size: 1rem;
}
.article-section.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 180px;
}
.article-section.empty-state p {
  margin: 0;
  color: var(--text-subtle);
  text-align: center;
}
.meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-top: 16px;
}
.meta-grid .item {
  padding: 16px;
  background: var(--bg-soft);
  border-radius: 12px;
}
.meta-grid .label {
  display: block;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-subtle);
  margin-bottom: 6px;
}
.author-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 16px;
}
.author-name {
  font-weight: 600;
  color: var(--text-main);
}
.author-affiliations, .author-emails {
  color: var(--text-subtle);
  font-size: 0.95rem;
}
.abstract p {
  font-size: 1.05rem;
  line-height: 1.75;
  color: var(--text-muted);
}
.panel {
  margin-bottom: 32px;
  padding: 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-soft);
}
.media {
  margin: 0 0 24px;
  background: var(--bg-soft);
  padding: 16px;
  border-radius: 12px;
}
.media img {
  max-width: 100%;
  display: block;
  border-radius: 12px;
}
.media-label {
  font-weight: 600;
  color: var(--text-subtle);
  margin-right: 8px;
}
.table-wrap {
  margin: 0 0 24px;
  background: var(--bg-soft);
  padding: 16px;
  border-radius: 12px;
}
.table-scroll {
  overflow-x: auto;
  border-radius: 12px;
}
.table-scroll table {
  width: 100%;
  border-collapse: collapse;
  min-width: 480px;
}
.table-scroll th, .table-scroll td {
  padding: 12px 16px;
  border: 1px solid var(--border-soft);
  text-align: left;
}
.reference-list {
  list-style: decimal;
  margin: 0;
  padding-left: 20px;
  display: grid;
  gap: 12px;
}
.reference-label {
  font-weight: 600;
  color: var(--text-subtle);
  margin-right: 8px;
}
.sidebar-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  backdrop-filter: blur(2px);
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.3s ease;
  z-index: 18;
}
.sidebar-backdrop.visible {
  opacity: 1;
  visibility: visible;
}
@media (max-width: 720px) {
  .app-header {
    padding-inline: 16px;
  }
  .layout {
    padding-inline: 16px;
  }
  .surface {
    padding: 20px;
  }
  .control-bar {
    flex-wrap: wrap;
  }
}
"""

    js = """
(function () {
  const body = document.body;
  const themeToggle = document.getElementById('themeToggle');
  const contrastToggle = document.getElementById('contrastToggle');
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  const sidebarClose = document.getElementById('sidebarClose');
  const sidebarBackdrop = document.getElementById('sidebarBackdrop');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const storedTheme = localStorage.getItem('jats-theme');
  const storedContrast = localStorage.getItem('jats-contrast');

  function applyTheme(theme) {
    body.setAttribute('data-theme', theme);
    localStorage.setItem('jats-theme', theme);
    if (themeToggle) {
      themeToggle.querySelector('span.state').textContent = theme === 'dark' ? 'Modo claro' : 'Modo oscuro';
    }
  }

  function applyContrast(contrast) {
    body.setAttribute('data-contrast', contrast);
    localStorage.setItem('jats-contrast', contrast);
    if (contrastToggle) {
      contrastToggle.querySelector('span.state').textContent = contrast === 'high' ? 'Contraste normal' : 'Alto contraste';
    }
  }

  applyTheme(storedTheme || (prefersDark ? 'dark' : 'light'));
  applyContrast(storedContrast || 'normal');

  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const current = body.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
      applyTheme(current === 'dark' ? 'light' : 'dark');
    });
  }

  if (contrastToggle) {
    contrastToggle.addEventListener('click', () => {
      const current = body.getAttribute('data-contrast') === 'high' ? 'high' : 'normal';
      applyContrast(current === 'high' ? 'normal' : 'high');
    });
  }

  function updateSidebarAria(isOpen) {
    sidebarToggle?.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    sidebar?.setAttribute('aria-hidden', isOpen ? 'false' : 'true');
  }

  function openSidebar() {
    if (!sidebar) {
      return;
    }
    body.classList.add('sidebar-open', 'sidebar-lock');
    sidebarBackdrop?.classList.add('visible');
    updateSidebarAria(true);
  }

  function closeSidebar() {
    if (!sidebar) {
      return;
    }
    body.classList.remove('sidebar-open');
    setTimeout(() => body.classList.remove('sidebar-lock'), 250);
    sidebarBackdrop?.classList.remove('visible');
    updateSidebarAria(false);
  }

  updateSidebarAria(false);

  if (sidebarToggle) {
    sidebarToggle.addEventListener('click', () => {
      if (body.classList.contains('sidebar-open')) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });
  }

  sidebarClose?.addEventListener('click', closeSidebar);
  sidebarBackdrop?.addEventListener('click', closeSidebar);

  window.addEventListener('keyup', (event) => {
    if (event.key === 'Escape') {
      closeSidebar();
    }
  });

  const tocLinks = sidebar?.querySelectorAll('.toc a') || [];
  tocLinks.forEach((link) => {
    link.addEventListener('click', () => {
      closeSidebar();
    });
  });
})();
"""

    authors_html = _render_authors(doc.get("authors", []))
    abstract_html = _render_paragraphs(doc.get("abstract_paragraphs", []))
    sections_html = _render_sections(doc.get("sections", []))
    figures_html = _render_figures(doc.get("figures", []))
    tables_html = _render_tables(doc.get("tables", []))
    references_html = _render_references(doc.get("references", []))
    sidebar_html = _render_sidebar(doc)

    abstract_section = (
        f"""
        <section class=\"surface abstract\">
          <h2>Resumen</h2>
          {abstract_html or '<p>No se proporcionó un resumen.</p>'}
        </section>
        """
    )

    main_sections = (
        f"""
        <section class=\"article-body\">
          <div class=\"section-grid\">
            {sections_html or '<div class="surface article-section empty-state"><p>Este artículo no contiene secciones principales.</p></div>'}
          </div>
        </section>
        """
    )

    figures_section = figures_html or ""
    tables_section = tables_html or ""
    references_section = references_html or ""

    doi_value = doc.get("doi") or ""
    meta_values = [
        ("Fecha de publicación", escape(doc.get("pub_date") or "Pendiente")),
        ("Volumen", escape(doc.get("volume") or "N/D")),
        ("Número", escape(doc.get("issue") or "N/D")),
        (
            "Páginas",
            escape(" - ".join(filter(None, [doc.get("fpage"), doc.get("lpage")])) or "N/D"),
        ),
        (
            "DOI",
            (
                f'<a href="https://doi.org/{escape(doi_value)}">{escape(doi_value)}</a>'
                if doi_value
                else "N/D"
            ),
        ),
    ]
    meta_grid_html = "".join(
        f'<div class="item"><span class="label">{label}</span>{value}</div>'
        for label, value in meta_values
    )

    html = f"""<!DOCTYPE html>
<html lang=\"es\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{title}</title>
  <style>{css}</style>
</head>
<body data-theme=\"light\" data-contrast=\"normal\">
  <div class=\"app\">
    <header class=\"app-header\">
      <div class=\"branding\">
        <h1>{title}</h1>
        {f'<p class="translated-title">{translated_title}</p>' if translated_title else ''}
      </div>
      <div class=\"control-bar\">
  <button id=\"sidebarToggle\" type=\"button\" class=\"sidebar-toggle\" aria-label=\"Mostrar índice\" aria-controls=\"sidebar\" aria-expanded=\"false\">
          <span>Índice</span>
        </button>
        <button id=\"themeToggle\" aria-label=\"Cambiar tema\"><span>Modo</span><span class=\"state\">Modo oscuro</span></button>
        <button id=\"contrastToggle\" aria-label=\"Cambiar contraste\"><span>Contraste</span><span class=\"state\">Alto contraste</span></button>
      </div>
    </header>
    <div class=\"layout\">
      {sidebar_html}
      <div class=\"sidebar-backdrop\" id=\"sidebarBackdrop\" aria-hidden=\"true\"></div>
      <main class=\"main\">
        <section class=\"surface metadata\">
          <h2>Información general</h2>
          <div class=\"meta-grid\">
            {meta_grid_html}
          </div>
        </section>
        {authors_html}
        {abstract_section}
        {main_sections}
        {figures_section}
        {tables_section}
        {references_section}
      </main>
    </div>
  </div>
  <script>{js}</script>
</body>
</html>
"""
    return html


def convert(xml_path: str, output_path: str | None = None) -> str:
    doc = parse_jats(xml_path)
    html = build_html(doc)
    if output_path:
        Path(output_path).write_text(html, encoding="utf-8")
    return html


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Convierte un artículo JATS en HTML estilizado y responsivo.")
    parser.add_argument("xml", help="Ruta al archivo XML en formato JATS")
    parser.add_argument("-o", "--output", help="Ruta del archivo HTML resultante")
    parser.add_argument("--json", action="store_true", help="Mostrar datos extraídos en JSON en lugar de HTML")
    args = parser.parse_args(argv)

    try:
        data = parse_jats(args.xml)
    except Exception as exc:  # noqa: BLE001
        print(f"Error al analizar el fichero JATS: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    html = build_html(data)
    if args.output:
        Path(args.output).write_text(html, encoding="utf-8")
    else:
        print(html)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
