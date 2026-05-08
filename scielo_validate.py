# -*- coding: utf-8 -*-
"""Validador rápido de SciELO SPS 1.8 (reglas estructurales comunes)."""

from lxml import etree
from typing import List, Tuple

def validate_scielo_sps(xml_string: str) -> Tuple[bool, List[str]]:
    """Valida reglas SciELO SPS 1.8 básicas."""
    errors: List[str] = []
    try:
        parser = etree.XMLParser(recover=True, encoding='utf-8')
        root = etree.fromstring(xml_string.encode('utf-8'), parser=parser)
    except Exception as e:
        return False, [f"XML mal formado: {e}"]

    ns = {'xlink': 'http://www.w3.org/1999/xlink'}

    # 1. article attributes
    if root.get('specific-use') != 'sps-1.8':
        errors.append("@specific-use debe ser 'sps-1.8'")
    if root.get('dtd-version') != '1.0':
        errors.append("@dtd-version debe ser '1.0'")

    # 2. journal-meta / issn
    issn = root.find('.//journal-meta/issn')
    if issn is None:
        errors.append("Falta <issn> en <journal-meta>")
    else:
        issn_text = (issn.text or '').strip()
        if issn_text in ('0000-0000', 'XXXX-XXXX', ''):
            errors.append("ISSN no configurado. Ve a 'Configuración de Revista' e ingresa el ISSN impreso real de la revista.")
        if not issn.get('pub-type'):
            errors.append("<issn> debe tener @pub-type")

    # 3. article-meta counts
    article_meta = root.find('.//article-meta')
    if article_meta is not None:
        counts = article_meta.find('counts')
        if counts is None:
            errors.append("Falta <counts> en <article-meta> (obligatorio SPS)")
        else:
            for child_name in ['fig-count', 'table-count', 'ref-count', 'page-count']:
                if counts.find(child_name) is None:
                    errors.append(f"Falta <{child_name}> dentro de <counts>")

    # 4. history dates iso-8601-date
    for date_el in root.findall('.//history/date'):
        if not date_el.get('iso-8601-date'):
            errors.append(f"Fecha <date date-type='{date_el.get('date-type')}'> falta @iso-8601-date")

    # 5. fn types in author-notes
    valid_fn_types = {'coi-statement', 'conflict', 'corresp', 'presented-at', 'supplementary-material', 'supported-by'}
    for fn in root.findall('.//author-notes/fn'):
        fnt = fn.get('fn-type')
        if fnt and fnt not in valid_fn_types:
            errors.append(f"<fn fn-type='{fnt}'> no es un valor SPS 1.8 válido. Usar: {valid_fn_types}")

    # 6. permissions: license href required
    license_el = root.find('.//permissions/license')
    if license_el is not None:
        href = license_el.get('{http://www.w3.org/1999/xlink}href')
        if not href:
            errors.append("<license> debe tener @xlink:href")

    # 7. mixed-citation in refs
    for ref in root.findall('.//back/ref-list/ref'):
        if ref.find('mixed-citation') is None and ref.find('element-citation') is None:
            errors.append(f"<ref id='{ref.get('id')}'> falta <mixed-citation>")

    # 8. table-wrap id
    for tw in root.findall('.//table-wrap'):
        if not tw.get('id'):
            errors.append("<table-wrap> debe tener @id")

    # 9. fig id
    for fig in root.findall('.//fig'):
        if not fig.get('id'):
            errors.append("<fig> debe tener @id")

    # 10. aff id and label
    for aff in root.findall('.//aff'):
        if not aff.get('id'):
            errors.append("<aff> debe tener @id")

    return len(errors) == 0, errors


if __name__ == '__main__':
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else '4975.xml'
    with open(path, 'rb') as f:
        xml_bytes = f.read()
    ok, errs = validate_scielo_sps(xml_bytes.decode('utf-8'))
    print(f"Valid: {ok}")
    for e in errs:
        print(f"  - {e}")
