from __future__ import annotations

"""Convertidor de JATS XML a HTML.

Este módulo se encarga de parsear archivos XML válidos bajo el esquema JATS 1.3
y generar una representación HTML5 moderna, responsiva y estilizada.
Incluye funciones para extracción de metadatos, renderizado de secciones,
y manejo de figuras y tablas.
"""


import argparse
import base64
import json
import mimetypes
import re
import sys
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from lxml import etree

_XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
_XLINK_HREF = "{http://www.w3.org/1999/xlink}href"
_SANITIZE_ENTITY_RE = re.compile(r"&(?![a-zA-Z]+;|#\d+;|#x[0-9a-fA-F]+;)")
IMAGE_DIR = Path("imagenes_extraidas")



def _clean_whitespace(text: str) -> str:
    """Normaliza los espacios en blanco de una cadena.

    Reemplaza múltiples espacios, tabulaciones y saltos de línea por un único espacio
    y elimina espacios al inicio y final.

    Args:
        text (str): Texto a limpiar.

    Returns:
        str: Texto limpio y normalizado.
    """
    return re.sub(r"\s+", " ", text or "").strip()



def _node_text(node: etree._Element) -> str:
    """Extrae todo el texto de un nodo XML y sus descendientes.

    Args:
        node (etree._Element): El nodo raíz desde el cual extraer texto.

    Returns:
        str: Todo el texto contenido en el nodo, concatenado y normalizado.
    """
    parts: List[str] = []
    if node.text:
        parts.append(node.text)
    for child in node:
        parts.append(_node_text(child))
        if child.tail:
            parts.append(child.tail)
    return _clean_whitespace("".join(parts))



def _inline_children_html(node: etree._Element) -> str:
    """Renderiza los hijos de un nodo como HTML inline, preservando marcas de formato.

    Procesa recursivamente los nodos hijos para manejar negritas, itálicas, etc.

    Args:
        node (etree._Element): El nodo padre.

    Returns:
        str: Cadena HTML con el contenido de los hijos.
    """
    segments: List[str] = []
    if node.text:
        segments.append(escape(node.text))
    for child in node:
        segments.append(_inline_element_html(child))
        if child.tail:
            segments.append(escape(child.tail))
    return "".join(segments)



def _inline_element_html(element: etree._Element) -> str:
    """Convierte un elemento XML individual a su representación HTML inline.

    Maneja etiquetas específicas de JATS como xref, italic, bold, sup, sub, ext-link.

    Args:
        element (etree._Element): El elemento a convertir.

    Returns:
        str: Representación HTML del elemento.
    """
    tag = etree.QName(element).localname.lower()
    if tag == "xref" and (element.get("ref-type") or "").lower() == "bibr":
        rid_attr = (element.get("rid") or "").strip()
        first_target = rid_attr.split()[0] if rid_attr else ""
        label_html = _inline_children_html(element) or escape(element.text or "")
        href_attr = f"#{escape(first_target)}" if first_target else "#"
        data_attr = escape(rid_attr)
        return f"<a class=\"citation\" href=\"{href_attr}\" data-rid=\"{data_attr}\">{label_html}</a>"
    if tag in {"italic", "i"}:
        return f"<em>{_inline_children_html(element)}</em>"
    if tag in {"bold", "b", "strong"}:
        return f"<strong>{_inline_children_html(element)}</strong>"
    if tag in {"underline", "u"}:
        return f"<span class=\"underline\">{_inline_children_html(element)}</span>"
    if tag == "sup":
        return f"<sup>{_inline_children_html(element)}</sup>"
    if tag == "sub":
        return f"<sub>{_inline_children_html(element)}</sub>"
    if tag == "ext-link":
        href = element.get(_XLINK_HREF) or element.get("href") or ""
        label = _inline_children_html(element) or escape(element.text or href)
        if href:
            return f"<a class=\"external-link\" href=\"{escape(href)}\" target=\"_blank\" rel=\"noopener\">{label}</a>"
        return label
    return _inline_children_html(element)



def _xpath(node: etree._Element, expression: str, namespaces: Dict[str, str]) -> List[Any]:
    """Ejecuta una expresión XPath, manejando posibles prefijos de namespace faltantes.

    Intenta usar el namespace 'j' (JATS) y si falla intenta sin prefijo como fallback.

    Args:
        node (etree._Element): Nodo sobre el cual ejecutar XPath.
        expression (str): Expresión XPath.
        namespaces (Dict[str, str]): Mapa de namespaces.

    Returns:
        List[Any]: Lista de resultados encontrados.
    """
    result = node.xpath(expression, namespaces=namespaces)
    if result or "j:" not in expression:
        return result
    fallback_expression = expression.replace("j:", "")
    try:
        return node.xpath(fallback_expression)
    except etree.XPathError:
        return []



def _first_text(node: etree._Element, expression: str, namespaces: Dict[str, str]) -> str:
    """Retorna el texto del primer resultado de una búsqueda XPath.

    Args:
        node (etree._Element): Nodo raíz.
        expression (str): Expresión XPath.
        namespaces (Dict[str, str]): Namespaces.

    Returns:
        str: Texto limpio del primer match, o cadena vacía si no hay coincidencias.
    """
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
    """Limpia el XML crudo para asegurar que sea parseable.

    Elimina caracteres de control inválidos, ajusta declaraciones XML/DOCTYPE,
    y asegura que exista un nodo raíz <article>.

    Args:
        raw_xml (str): Contenido XML original.

    Returns:
        str: XML sanitizado y seguro para lxml.

    Raises:
        ValueError: Si no se encuentra un nodo <article> válido.
    """
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
    """Descubre y normaliza los namespaces del documento XML.

    Asigna el prefijo 'j' al namespace por defecto o JATS si no existe.

    Args:
        root (etree._Element): Nodo raíz del documento.

    Returns:
        Dict[str, str]: Mapa de prefijos a URIs.
    """
    namespaces = {prefix: uri for prefix, uri in root.nsmap.items() if prefix}
    default_ns = root.nsmap.get(None)
    if default_ns:
        namespaces.setdefault("j", default_ns)
    namespaces.setdefault("j", "http://www.ncbi.nlm.nih.gov/JATS1")
    namespaces.setdefault("xlink", "http://www.w3.org/1999/xlink")
    return namespaces



def parse_jats(xml_path: str) -> Dict[str, Any]:
    """Parsea un archivo JATS XML y extrae metadatos y contenido estructurado.

    Extrae título, autores, secciones, figuras, tablas y referencias.

    Args:
        xml_path (str): Ruta al archivo XML.

    Returns:
        Dict[str, Any]: Diccionario con toda la información extraída del artículo.
    """
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
    """Extrae la fecha de publicación en formato DD/MM/YYYY o parcial.

    Args:
        article_meta (etree._Element): Elemento article-meta.
        namespaces (Dict[str, str]): Mapa de namespaces.

    Returns:
        str: Fecha formateada o cadena vacía.
    """
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
    """Extrae las palabras clave del artículo.

    Args:
        article_meta (etree._Element): Elemento article-meta.
        namespaces (Dict[str, str]): Namespaces.

    Returns:
        List[str]: Lista de palabras clave.
    """
    keywords: List[str] = []
    for kwd in _xpath(article_meta, ".//j:kwd-group/j:kwd", namespaces):
        text = _node_text(kwd)
        if text:
            keywords.append(text)
    return keywords



def _extract_authors(article_meta: etree._Element, namespaces: Dict[str, str]) -> List[Dict[str, Any]]:
    """Extrae la lista completa de autores y sus metadatos.

    Procesa nombres, afiliaciones, correspondencia y correos electrónicos.

    Args:
        article_meta (etree._Element): Elemento article-meta.
        namespaces (Dict[str, str]): Namespaces.

    Returns:
        List[Dict[str, Any]]: Lista de diccionarios con info de cada autor.
    """
    affiliations: Dict[str, str] = {}
    for aff in _xpath(article_meta, ".//j:aff", namespaces):
        aff_id = aff.get(_XML_ID) or aff.get("id")
        if aff_id:
            affiliations[aff_id] = _node_text(aff)

    corresp_notes: Dict[str, str] = {}
    for cor in _xpath(article_meta, ".//j:author-notes/j:corresp", namespaces):
        cor_id = cor.get(_XML_ID) or cor.get("id")
        email_value = _first_text(cor, ".//j:email", namespaces) or _node_text(cor)
        if cor_id and email_value:
            corresp_notes[cor_id] = email_value

    authors: List[Dict[str, Any]] = []
    for contrib in _xpath(article_meta, ".//j:contrib-group/j:contrib[@contrib-type='author']", namespaces):
        surname = _first_text(contrib, "./j:name/j:surname", namespaces)
        given = _first_text(contrib, "./j:name/j:given-names", namespaces)
        collective = _first_text(contrib, "./j:collab", namespaces)
        full_name = collective or " ".join(part for part in [given, surname] if part)
        if not full_name:
            continue

        is_corresponding = contrib.get("corresp", "").lower() == "yes"
        corresp_rids = [xref.get("rid") for xref in _xpath(contrib, ".//j:xref[@ref-type='corresp']", namespaces) if xref.get("rid")]

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

        if corresp_rids:
            for cor_id in corresp_rids:
                note_email = corresp_notes.get(cor_id)
                if note_email and note_email not in emails:
                    emails.append(note_email)

        orcid_value = ""
        for contrib_id in _xpath(contrib, ".//j:contrib-id[@contrib-id-type='orcid']", namespaces):
            raw = _node_text(contrib_id)
            if raw:
                orcid_value = raw.strip()
                break

        if not is_corresponding:
            is_corresponding = bool(corresp_rids or contrib.get("corresp"))

        authors.append(
            {
                "full": full_name,
                "affiliations": author_affs,
                "emails": emails,
                "orcid": orcid_value,
                "corresponding": is_corresponding,
            }
        )
    return authors



def _extract_paragraphs(parent: etree._Element, expression: str, namespaces: Dict[str, str]) -> List[str]:
    """Extrae párrafos de texto como HTML inline dado un XPath.

    Args:
        parent (etree._Element): Elemento padre.
        expression (str): XPath para encontrar los párrafos.
        namespaces (Dict[str, str]): Namespaces.

    Returns:
        List[str]: Lista de párrafos en HTML.
    """
    paragraphs: List[str] = []
    for element in _xpath(parent, expression, namespaces):
        html = _inline_children_html(element)
        if html:
            paragraphs.append(html)
    return paragraphs



def _extract_sections(body: etree._Element, namespaces: Dict[str, str]) -> List[Dict[str, Any]]:
    """Extrae jerarquía de secciones del cuerpo del artículo recursivamente.

    Args:
        body (etree._Element): Elemento body o section padre.
        namespaces (Dict[str, str]): Namespaces.

    Returns:
        List[Dict[str, Any]]: Lista de secciones con títulos, párrafos y subsecciones.
    """
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
    """Extrae figuras del artículo.

    Args:
        body (etree._Element): Cuerpo del artículo.
        namespaces (Dict[str, str]): Namespaces.

    Returns:
        List[Dict[str, Any]]: Lista de figuras con metadatos y URL de imagen.
    """
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
    """Extrae tablas del artículo.

    Args:
        body (etree._Element): Cuerpo del artículo.
        namespaces (Dict[str, str]): Namespaces.

    Returns:
        List[Dict[str, Any]]: Lista de tablas con sus filas y celdas.
    """
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
    """Extrae las referencias bibliográficas.

    Args:
        back (etree._Element): Sección back del artículo.
        namespaces (Dict[str, str]): Namespaces.

    Returns:
        List[Dict[str, str]]: Lista de referencias con ID, etiqueta y HTML renderizado.
    """
    references: List[Dict[str, str]] = []
    for idx, ref in enumerate(_xpath(back, ".//j:ref-list/j:ref", namespaces), start=1):
        ref_id = ref.get(_XML_ID) or ref.get("id") or ""
        label = _first_text(ref, "./j:label", namespaces)
        citation_node = ref.find("./j:mixed-citation", namespaces) or ref.find("./j:element-citation", namespaces)
        body_html = _inline_children_html(citation_node) if citation_node is not None else _inline_children_html(ref)
        
        # Limpiar números duplicados al inicio del texto de la referencia.
        # El texto puede venir con el número de referencia ya incluido
        # (ej. "1Aldrete..." o "1. Aldrete..."), lo que causa duplicación
        # porque el <ol> HTML y el <label> ya proveen la numeración.
        body_html = _strip_leading_ref_number(body_html, label or str(idx))
        
        references.append({"id": ref_id, "label": label, "html": body_html})
    return references


def _strip_leading_ref_number(text: str, label: str) -> str:
    """Elimina el número de referencia duplicado al inicio del texto.

    Detecta patrones como '1Autor', '1. Autor', '1 Autor' al inicio
    y los elimina si coinciden con el label de la referencia.

    Args:
        text (str): Texto HTML de la referencia.
        label (str): Etiqueta/número esperado de la referencia.

    Returns:
        str: Texto limpio sin número duplicado al inicio.
    """
    if not text or not label:
        return text
    
    # Extraer solo dígitos del label para comparar
    label_digits = re.sub(r'[^\d]', '', label)
    if not label_digits:
        return text
    
    # Patrón: inicio del texto con el número, opcionalmente seguido de
    # punto, guión o espacio (ej. "3", "3.", "3. ", "3-")
    pattern = re.compile(
        r'^\s*' + re.escape(label_digits) + r'[.\-\s)]*',
        re.IGNORECASE
    )
    
    cleaned = pattern.sub('', text, count=1)
    
    # Solo aceptar la limpieza si quedó contenido útil
    if cleaned.strip():
        return cleaned.strip()
    return text



def _collect_section_entries(sections: List[Dict[str, Any]], prefix: str = "", level: int = 1) -> List[Tuple[int, str, str, str]]:
    """Aplana la jerarquía de secciones para generar el índice (TOC).

    Args:
        sections (List[Dict[str, Any]]): Lista de secciones anidadas.
        prefix (str, optional): Prefijo de numeración acumulado.
        level (int, optional): Nivel de profundidad actual.

    Returns:
        List[Tuple[int, str, str, str]]: Lista de tuplas (nivel, id, etiqueta, título).
    """
    entries: List[Tuple[int, str, str, str]] = []
    for idx, section in enumerate(sections, start=1):
        number = f"{prefix}{idx}" if prefix else str(idx)
        label = section.get("label") or number
        entries.append((level, section["id"], label, section["title"]))
        entries.extend(_collect_section_entries(section["subsections"], f"{number}.", level + 1))
    return entries



def _render_keywords(keywords: Iterable[str]) -> str:
    """Genera el HTML para la sección de palabras clave.

    Args:
        keywords (Iterable[str]): Lista de palabras clave.

    Returns:
        str: HTML renderizado o cadena vacía si no hay keywords.
    """
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
    """Genera el HTML para la lista de autores y sus filiaciones.

    Args:
        authors (List[Dict[str, Any]]): Metadatos de autores.

    Returns:
        str: HTML renderizado o cadena vacía.
    """
    if not authors:
        return ""
    author_items: List[str] = []
    for author in authors:
        name_classes = ["author-name"]
        if author.get("corresponding"):
            name_classes.append("author-name--corresponding")
        header_parts = [f"<span class=\"{' '.join(name_classes)}\">{escape(author['full'])}</span>"]
        if author.get("corresponding"):
            header_parts.append("<span class=\"author-corresponding\">Autor de correspondencia</span>")
        sections: List[str] = [f"<div class=\"author-header\">{''.join(header_parts)}</div>"]

        if author.get("affiliations"):
            affs = "; ".join(escape(aff) for aff in author["affiliations"] if aff)
            if affs:
                sections.append(f"<div class=\"author-affiliations\">{affs}</div>")

        contact_links: List[str] = []
        orcid_value = (author.get("orcid") or "").strip()
        if orcid_value:
            orcid_url = orcid_value if orcid_value.lower().startswith("http") else f"https://orcid.org/{orcid_value}"
            orcid_display = orcid_url.rstrip("/").split("/")[-1] or orcid_url
            contact_links.append(
                f"<a class=\"author-link author-orcid\" href=\"{escape(orcid_url)}\" target=\"_blank\" rel=\"noopener\">ORCID: {escape(orcid_display)}</a>"
            )

        for email in author.get("emails", []):
            if email:
                email_classes = ["author-link", "author-email"]
                if author.get("corresponding"):
                    email_classes.append("author-email--corresponding")
                contact_links.append(
                    f"<a class=\"{' '.join(email_classes)}\" href=\"mailto:{escape(email)}\">Email: {escape(email)}</a>"
                )

        if contact_links:
            link_items = "".join(f"<span class=\"author-link-item\">{link}</span>" for link in contact_links)
            sections.append(f"<div class=\"author-links\">{link_items}</div>")

        author_items.append(f"<li class=\"author\">{''.join(sections)}</li>")

    return """
    <section class=\"panel\">
        <h3>Autores</h3>
        <ul class=\"author-list\">{items}</ul>
    </section>
    """.replace("{items}", "".join(author_items))



def _render_paragraphs(paragraphs: Iterable[str]) -> str:
    """Envuelve los párrafos en etiquetas <p>.

    Args:
        paragraphs (Iterable[str]): Lista de párrafos ya escapados/procesados.

    Returns:
        str: HTML concatenado.
    """
    return "".join(f"<p>{paragraph}</p>" for paragraph in paragraphs if paragraph)



def _render_sections(sections: List[Dict[str, Any]], depth: int = 1, prefix: str = "") -> str:
    """Renderiza las secciones y subsecciones de forma recursiva.

    Args:
        sections (List[Dict[str, Any]]): Lista de secciones.
        depth (int, optional): Profundidad actual (para jerarquía h2-h6).
        prefix (str, optional): Prefijo de numeración (ej. "1.1").

    Returns:
        str: HTML de todas las secciones renderizadas.
    """
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
        number_text = label
        if number_text and not number_text.endswith('.'):
            number_text = f"{number_text}."
        number_html = f"<span class=\"section-number\">{number_text}</span>" if number_text else ""
        heading_parts.append(
            f"<{heading_tag} class=\"section-heading\">{number_html}<span class=\"section-title\">{title}</span></{heading_tag}>"
        )
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



def _encode_image_to_base64(image_path: Path) -> str:
    """Codifica una imagen local a Base64.

    Args:
        image_path (Path): Ruta al archivo de imagen.

    Returns:
        str: Cadena Data URI (data:image/xyz;base64,...) o cadena vacía si falla.
    """
    try:
        if not image_path.exists():
            return ""
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_type = "application/octet-stream"
        
        data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        return f"data:{mime_type};base64,{data}"
    except Exception:
        return ""


def _render_figures(figures: List[Dict[str, Any]]) -> str:
    """Genera HTML para las figuras.

    Args:
        figures (List[Dict[str, Any]]): Lista de figuras.

    Returns:
        str: HTML renderizado.
    """
    if not figures:
        return ""
    figure_blocks: List[str] = []
    for fig in figures:
        caption = escape(fig.get("caption") or "")
        label = escape(fig.get("label") or "Figura")
        href = escape(fig.get("href") or "")
        
        # Intentar convertir a Base64 si es un archivo local
        if href and not href.startswith("data:") and not href.startswith("http"):
             local_path = IMAGE_DIR / href
             base64_img = _encode_image_to_base64(local_path)
             if base64_img:
                 href = base64_img
                 
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
    """Genera HTML para las tablas.

    Args:
        tables (List[Dict[str, Any]]): Lista de tablas.

    Returns:
        str: HTML renderizado.
    """
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
    """Genera HTML para la lista de referencias.

    No muestra el label como texto porque el <ol> ya provee la numeración
    automáticamente. Esto evita la duplicación de números.

    Args:
        references (List[Dict[str, str]]): Lista de referencias.

    Returns:
        str: HTML renderizado.
    """
    if not references:
        return ""
    items: List[str] = []
    for ref in references:
        body = ref.get("html") or ""
        item_id = escape(ref.get("id") or "")
        id_attr = f" id=\"{item_id}\"" if item_id else ""
        # No incluir el label como span — el <ol> ya provee numeración.
        items.append(f"<li{id_attr}>{body}</li>")
    return """
    <section class=\"panel\" id=\"references\">
      <h3>Referencias</h3>
      <ol class=\"reference-list\">{items}</ol>
    </section>
    """.replace("{items}", "".join(items))



def _get_logo_base64() -> str:
    """Lee el archivo de logo y lo convierte a Base64."""
    try:
        # Prefer the transparent fixed version if it exists
        logo_path = Path("resources/logo_transparent.png")
        if not logo_path.exists():
            logo_path = Path("resources/logo.png")
            
        if logo_path.exists():
            import base64
            encoded = base64.b64encode(logo_path.read_bytes()).decode("utf-8")
            return f"data:image/png;base64,{encoded}"
    except Exception:
        pass
    return ""

def _render_sidebar(doc: Dict[str, Any]) -> str:
    """Genera el panel lateral con la tabla de contenidos (TOC) y metadatos.

    Args:
        doc (Dict[str, Any]): Datos completos del artículo.

    Returns:
        str: HTML del sidebar.
    """
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

    logo_src = _get_logo_base64()
    logo_html = ""
    if logo_src:
        logo_html = f"""
        <div class=\"logo-container\" style=\"text-align: center; margin-bottom: 20px;\">
            <img src=\"{logo_src}\" alt=\"Logo Revista\" style=\"max-width: 80%; height: auto;\">
        </div>
        """

    template = """
  <aside class=\"sidebar\" id=\"sidebar\" aria-label=\"Índice de contenido\" aria-hidden=\"false\">
      <div class=\"sidebar-header\">
        {logo}
        <div class=\"sidebar-title-row\">
            <h2>Contenido</h2>
            <button class=\"sidebar-close\" id=\"sidebarClose\" aria-label=\"Cerrar índice\">✕</button>
        </div>
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
        .replace("{logo}", logo_html)
    )



def build_html(doc: Dict[str, Any]) -> str:
    """Construye el documento HTML completo a partir de los datos extraídos.

    Ensambla CSS, JS, metadatos y secciones en una plantilla HTML responsiva.

    Args:
        doc (Dict[str, Any]): Datos estructurados del artículo.

    Returns:
        str: Código fuente HTML completo.
    """
    title = escape(doc.get("title") or "Artículo sin título")
    translated_title = escape(doc.get("translated_title") or "")

    css = """
:root {
  color-scheme: light;
  --font-sans: "Inter", "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif;
  --bg-body: #f3f4f6;
  --bg-card: #ffffff;
  --accent: #1f3d7a;
  --accent-secondary: #2f4f8f;
  --accent-soft: rgba(31, 61, 122, 0.12);
  --accent-soft-alt: rgba(31, 61, 122, 0.08);
  --border-soft: rgba(15, 23, 42, 0.14);
  --text-main: #1f2937;
  --text-muted: #374151;
  --text-subtle: #4b5563;
  --shadow-soft: 0 24px 48px -32px rgba(15, 23, 42, 0.35);
  --radius-md: 18px;
  --focus-ring: 0 0 0 3px rgba(31, 61, 122, 0.35);
  --bg-soft: rgba(15, 23, 42, 0.04);
  --header-bg: linear-gradient(135deg, #f9fafc, #eef1f7);
}
body[data-theme="dark"] {
  color-scheme: dark;
  --bg-body: #0b1220;
  --bg-card: #121a2f;
  --accent: #7aa2ff;
  --accent-secondary: #90b4ff;
  --accent-soft: rgba(122, 162, 255, 0.22);
  --accent-soft-alt: rgba(122, 162, 255, 0.12);
  --border-soft: rgba(148, 163, 184, 0.35);
  --text-main: #e2e8f0;
  --text-muted: #cbd5f5;
  --text-subtle: #a5b4d1;
  --shadow-soft: 0 28px 56px -32px rgba(0, 0, 0, 0.65);
  --focus-ring: 0 0 0 3px rgba(122, 162, 255, 0.5);
  --bg-soft: rgba(122, 162, 255, 0.12);
  --header-bg: linear-gradient(135deg, #10182b, #131f36);
}
body[data-contrast="high"] {
  --bg-body: #ffffff;
  --bg-card: #ffffff;
  --accent: #0b1120;
  --accent-secondary: #1f2937;
  --accent-soft: rgba(11, 17, 32, 0.12);
  --accent-soft-alt: rgba(11, 17, 32, 0.08);
  --border-soft: rgba(11, 17, 32, 0.35);
  --text-main: #0b1120;
  --text-muted: #111827;
  --text-subtle: #1f2937;
  --shadow-soft: none;
  --focus-ring: 0 0 0 3px rgba(11, 17, 32, 0.4);
  --bg-soft: rgba(11, 17, 32, 0.08);
  --header-bg: linear-gradient(135deg, #ffffff, #e5e7eb);
}
body[data-theme="dark"][data-contrast="high"] {
  --bg-body: #020817;
  --bg-card: #061226;
  --accent: #f3c969;
  --accent-secondary: #f0d893;
  --accent-soft: rgba(243, 201, 105, 0.28);
  --accent-soft-alt: rgba(243, 201, 105, 0.18);
  --border-soft: rgba(243, 201, 105, 0.5);
  --text-main: #f8fafc;
  --text-muted: #e2e8f0;
  --text-subtle: #cbd5f5;
  --focus-ring: 0 0 0 3px rgba(243, 201, 105, 0.55);
  --bg-soft: rgba(243, 201, 105, 0.18);
  --header-bg: linear-gradient(135deg, #0b172c, #152441);
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
  padding: clamp(20px, 4vw, 36px) clamp(16px, 5vw, 48px) 12px;
  background: var(--bg-body);
  margin-bottom: clamp(16px, 4vw, 32px);
}
.header-panel {
  margin: 0 auto;
  width: 100%;
  max-width: 960px;
  background: var(--bg-card);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-soft);
  padding: clamp(24px, 3vw, 40px);
  display: flex;
  flex-direction: column;
  gap: clamp(16px, 2.5vw, 24px);
}
.branding {
  flex: 1 1 auto;
  width: 100%;
  position: relative;
  z-index: 1;
}
.branding h1 {
  font-size: clamp(2rem, 2.8vw, 2.75rem);
  margin: 0;
  letter-spacing: -0.02em;
  color: var(--text-main);
}
.branding .translated-title {
  margin: 8px 0 0;
  font-size: clamp(1.1rem, 2vw, 1.35rem);
  color: var(--text-subtle);
}
.control-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-start;
  width: 100%;
  border-top: 1px solid var(--border-soft);
  padding-top: clamp(12px, 2vw, 18px);
}
.control-bar button {
  background: transparent;
  border: 1px solid var(--border-soft);
  color: var(--text-main);
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
  background: var(--accent-soft);
  box-shadow: var(--shadow-soft);
}
.control-bar button .state {
  font-weight: 500;
}
.layout {
  position: relative;
  padding: 0 clamp(16px, 4vw, 56px) 48px;
  flex: 1 1 auto;
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
  margin-bottom: 20px;
}
.sidebar-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
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
  grid-template-columns: auto 1fr;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 12px;
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
  display: none;
}
.toc-number {
  font-weight: 600;
  color: var(--text-main);
  min-width: 3ch;
  font-size: 1rem;
  font-variant-numeric: lining-nums;
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
  background: var(--bg-soft);
  color: var(--text-main);
  border: 1px solid var(--border-soft);
  border-radius: 12px;
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
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.article-section.main-section {
  border-left: 6px solid var(--accent);
  padding-left: clamp(24px, 3vw, 36px);
}
.article-section.main-section:hover {
  box-shadow: 0 24px 48px -36px rgba(31, 61, 122, 0.35);
}
.section-header {
  display: flex;
  align-items: baseline;
}
.section-heading {
  display: inline-flex;
  align-items: baseline;
  gap: 12px;
  margin: 0;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--text-main);
}
.section-number {
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--accent);
  font-variant-numeric: lining-nums;
  line-height: 1;
}
.section-title {
  font-weight: 600;
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
.article-section.subsection .section-number {
  color: var(--text-subtle);
  font-size: 0.95rem;
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
.author {
  padding: 18px;
  border: 1px solid var(--border-soft);
  border-radius: 14px;
  background: var(--bg-soft);
}
.author-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.author-name {
  font-weight: 600;
  color: var(--text-main);
}
.author-name--corresponding {
  color: var(--accent);
}
.author-corresponding {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--accent-secondary);
  background: var(--accent-soft);
  border-radius: 999px;
  padding: 2px 10px;
}
.author-affiliations {
  color: var(--text-subtle);
  font-size: 0.95rem;
  margin-bottom: 6px;
}
.author-links {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 4px;
}
.author-link-item {
  display: inline-flex;
}
.author-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--accent-secondary);
  font-weight: 500;
}
.author-link:hover {
  text-decoration: underline;
}
.author-email--corresponding {
  font-weight: 600;
  color: var(--accent);
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
.floating-button {
  position: fixed;
  right: clamp(16px, 4vw, 40px);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: var(--accent);
  color: #ffffff;
  border: none;
  border-radius: 999px;
  box-shadow: var(--shadow-soft);
  cursor: pointer;
  opacity: 0;
  pointer-events: none;
  transform: translateY(12px);
  transition: opacity 0.25s ease, transform 0.25s ease;
  z-index: 24;
}
.floating-button .icon {
  font-weight: 700;
  font-size: 1rem;
}
.floating-button.visible {
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0);
}
.floating-button:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
}
.floating-top {
  bottom: 108px;
}
.floating-menu {
  bottom: 44px;
}
body[data-theme="dark"] .floating-button {
  color: #0b1220;
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
  const scrollTopButton = document.getElementById('scrollTopButton');
  const floatingMenuButton = document.getElementById('floatingMenuButton');
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
    floatingMenuButton?.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
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

  scrollTopButton?.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  if (floatingMenuButton) {
    floatingMenuButton.addEventListener('click', () => {
      if (body.classList.contains('sidebar-open')) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });
  }

  function handleScroll() {
    const shouldShow = window.scrollY > 240;
    if (scrollTopButton) {
      scrollTopButton.classList.toggle('visible', shouldShow);
    }
    if (floatingMenuButton) {
      floatingMenuButton.classList.toggle('visible', shouldShow);
    }
  }

  window.addEventListener('scroll', handleScroll, { passive: true });
  handleScroll();
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
        #("Volumen", escape(doc.get("volume") or "N/D")),
        #("Número", escape(doc.get("issue") or "N/D")),
        #(
        #    "Páginas",
        #    escape(" - ".join(filter(None, [doc.get("fpage"), doc.get("lpage")])) or "N/D"),
        #),
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
  <script>
  document.addEventListener('DOMContentLoaded', function() {{
    document.addEventListener('click', function(e) {{
      var link = e.target.closest('a[href^="#"]');
      if (!link) return;
      var hash = link.getAttribute('href');
      if (!hash || hash === '#') return;
      e.preventDefault();
      var targetId = hash.substring(1);
      var target = document.getElementById(targetId);
      if (target) {{
        target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
      }}
    }});
  }});
  </script>
</head>
<body data-theme=\"light\" data-contrast=\"normal\">
  <div class="app">
    <header class="app-header">
      <div class="header-panel">
        <div class="branding">
          <h1>{title}</h1>
          {f'<p class="translated-title">{translated_title}</p>' if translated_title else ''}
        </div>
        <div class="control-bar">
          <button id="sidebarToggle" type="button" class="sidebar-toggle" aria-label="Mostrar índice" aria-controls="sidebar" aria-expanded="false">
            <span>Índice</span>
          </button>
          <button id="themeToggle" aria-label="Cambiar tema"><span>Modo</span><span class="state">Modo oscuro</span></button>
          <button id="contrastToggle" aria-label="Cambiar contraste"><span>Contraste</span><span class="state">Alto contraste</span></button>
        </div>
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
    <button id="scrollTopButton" class="floating-button floating-top" type="button" aria-label="Volver al inicio">
      <span class="icon" aria-hidden="true">&uarr;</span>
      <span class="label">Arriba</span>
    </button>
    <button id="floatingMenuButton" class="floating-button floating-menu" type="button" aria-label="Mostrar índice flotante" aria-controls="sidebar" aria-expanded="false">
      <span class="icon" aria-hidden="true">&#9776;</span>
      <span class="label">Índice</span>
    </button>
  </div>
  <script>{js}</script>
</body>
</html>
"""
    return html



def convert(xml_path: str, output_path: str | None = None) -> str:
    """Función de alto nivel para convertir un archivo JATS XML a HTML.

    Args:
        xml_path (str): Ruta al archivo de entrada.
        output_path (str | None, optional): Ruta de salida. Si es None, no guarda archivo.

    Returns:
        str: El contenido HTML generado.
    """
    doc = parse_jats(xml_path)
    html = build_html(doc)
    if output_path:
        Path(output_path).write_text(html, encoding="utf-8")
    return html



def main(argv: List[str]) -> int:
    """Punto de entrada para la ejecución desde línea de comandos.

    Args:
        argv (List[str]): Argumentos de la línea de comandos (sin incluir el nombre del script).

    Returns:
        int: Código de salida (0 para éxito, 1 para error).
    """
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
