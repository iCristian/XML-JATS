#!/usr/bin/env python3
"""Fix JATS XML references and minor validation errors."""

import re
from lxml import etree

# Ensure xlink prefix is preserved
etree.register_namespace('xlink', 'http://www.w3.org/1999/xlink')


def parse_authors(authors_text: str):
    """Parse author string into list of (surname, given_names) or collab strings."""
    authors_text = authors_text.strip()
    if not authors_text:
        return []
    # Split by ', & ' or ' & ' or ' and '
    groups = re.split(r',?\s+&\s+', authors_text)
    authors = []
    for group in groups:
        parts = [p.strip() for p in group.split(',') if p.strip()]
        # Pair up parts
        i = 0
        while i < len(parts):
            if i + 1 < len(parts):
                surname = parts[i]
                given = parts[i + 1]
                authors.append(('name', surname, given))
                i += 2
            else:
                # Unpaired - treat as collab/institution
                authors.append(('collab', parts[i].rstrip('.')))
                i += 1
    return authors


def extract_journal_meta(text):
    """Extract volume, issue, pages from the end of a journal-like string.
    Returns (remaining_text, volume, issue, pages)."""
    pages = ''
    volume = ''
    issue = ''

    # Pages: e.g., 1035–1048 or 1035-1048
    m = re.search(r',\s*(\d+)[-–](\d+)\.?\s*$', text)
    if m:
        pages = m.group(1) + '-' + m.group(2)
        text = text[:m.start()]

    # Volume(issue): e.g., 31(5)
    m = re.search(r',\s*(\d+)\((\d+)\)\.?\s*$', text)
    if m:
        volume = m.group(1)
        issue = m.group(2)
        text = text[:m.start()]
    else:
        # Volume only: e.g., 42
        m = re.search(r',\s*(\d+)\.?\s*$', text)
        if m:
            volume = m.group(1)
            text = text[:m.start()]

    return text.rstrip('. ').strip(), volume, issue, pages


def split_title_rest(text):
    """Split text into title and rest (source/publisher) using first '. ' or '? '.
    Does not split if text contains Vol. or Núm. (report titles)."""
    if 'Vol.' in text or 'Núm.' in text:
        return text, ''
    if '. ' in text:
        parts = text.split('. ', 1)
        return parts[0], parts[1]
    if '? ' in text:
        parts = text.split('? ', 1)
        return parts[0], parts[1]
    return text, ''


def parse_citation(text: str):
    """Best-effort parse of a mixed-citation string into structured fields."""
    text = text.strip()
    result = {
        'pub_type': 'other',
        'authors': [],
        'year': None,
        'article_title': '',
        'source': '',
        'volume': '',
        'issue': '',
        'fpage': '',
        'lpage': '',
        'publisher': '',
        'doi': '',
        'url': '',
    }

    # Extract DOI
    doi_match = re.search(r'https?://(?:dx\.)?doi\.org/([^\s]+)', text)
    if doi_match:
        result['doi'] = doi_match.group(1)

    # Extract URL (non-DOI)
    url_match = re.search(r'(https?://[^\s]+)', text)
    if url_match:
        url = url_match.group(1)
        if not url.startswith('https://doi.org/'):
            result['url'] = url

    # Extract year (including suffixes like 2022a, 2022b)
    year_match = re.search(r'\((\d{4})(?:[a-z])?(?:,\s*[^)]+)?\)', text)
    if year_match:
        result['year'] = year_match.group(1)
        authors_text = text[:year_match.start()].strip()
        rest = text[year_match.end():].strip()
    else:
        sf_match = re.search(r'\((s\.\s*f\.)\)', text)
        if sf_match:
            result['year'] = 's.f.'
            authors_text = text[:sf_match.start()].strip()
            rest = text[sf_match.end():].strip()
        else:
            authors_text = ''
            rest = text

    if rest.startswith('.'):
        rest = rest[1:].strip()

    # Remove URL/DOI strings from rest for further parsing
    rest_clean = re.sub(r'https?://\S+', '', rest).strip()
    rest_clean = re.sub(r'\s+', ' ', rest_clean).strip()
    rest_clean = rest_clean.rstrip('.').strip()

    result['authors'] = parse_authors(authors_text)

    # Determine publication type and parse rest
    temp_text, vol, iss, pgs = extract_journal_meta(rest_clean)
    has_journal_meta = bool(vol or iss or pgs or result['doi'])

    # Check for publisher keywords (books)
    publisher_keywords = ['McGraw-Hill', 'SAGE Publications', 'Editorial', 'Ediciones', 'Herder']
    has_publisher = any(kw in rest_clean for kw in publisher_keywords)

    # Determine type
    if has_journal_meta:
        result['pub_type'] = 'journal'
    elif has_publisher:
        result['pub_type'] = 'book'
    elif not temp_text and result['url']:
        result['pub_type'] = 'web'
    elif not temp_text and not result['url']:
        result['pub_type'] = 'report' if any(kw in authors_text.lower() for kw in ['ministerio', 'instituto', 'organización', 'asociación']) else 'other'
    else:
        # Check if source looks like a journal
        title_part, source_part = split_title_rest(temp_text)
        journal_keywords = ['revista', 'journal', 'cadernos', 'medicine', 'plos', 'bmc', 'sociology',
                            'enfermagem', 'obstetricia', 'ginecología', 'infectología', 'psiquiatría',
                            'salud pública', 'ciencia', 'docencia', 'tecnología', 'universum', 'salud',
                            'nursing', 'behavior', 'aids care', 'public health']
        if any(kw in source_part.lower() for kw in journal_keywords):
            result['pub_type'] = 'journal'
        elif any(kw in rest_clean.lower() for kw in ['informe', 'resultados', 'boletín', 'codificación', 'anual', 'estadístic']):
            result['pub_type'] = 'report'
        else:
            result['pub_type'] = 'web' if result['url'] else 'journal'

    # Now parse based on type
    if result['pub_type'] == 'journal':
        text_after_meta, result['volume'], result['issue'], pages_str = extract_journal_meta(rest_clean)
        if pages_str:
            result['fpage'], result['lpage'] = pages_str.split('-')
        result['article_title'], result['source'] = split_title_rest(text_after_meta)
    elif result['pub_type'] == 'book':
        result['source'], result['publisher'] = split_title_rest(rest_clean)
    else:
        # web, report, other
        result['article_title'], result['source'] = split_title_rest(rest_clean)

    return result


def build_element_citation(data: dict):
    """Build an <element-citation> Element from parsed data."""
    ec = etree.Element('element-citation')
    if data['pub_type']:
        ec.set('publication-type', data['pub_type'])

    if data['authors']:
        pg = etree.SubElement(ec, 'person-group')
        pg.set('person-group-type', 'author')
        for kind, *rest in data['authors']:
            if kind == 'name':
                surname, given = rest
                name_el = etree.SubElement(pg, 'name')
                sn = etree.SubElement(name_el, 'surname')
                sn.text = surname
                gn = etree.SubElement(name_el, 'given-names')
                gn.text = given
            else:
                collab = etree.SubElement(pg, 'collab')
                collab.text = rest[0]

    if data['year']:
        year_el = etree.SubElement(ec, 'year')
        year_el.text = data['year']

    if data['article_title']:
        at = etree.SubElement(ec, 'article-title')
        at.text = data['article_title']

    if data['source']:
        src = etree.SubElement(ec, 'source')
        src.text = data['source']

    if data['volume']:
        vol = etree.SubElement(ec, 'volume')
        vol.text = data['volume']

    if data['issue']:
        iss = etree.SubElement(ec, 'issue')
        iss.text = data['issue']

    if data['fpage']:
        fp = etree.SubElement(ec, 'fpage')
        fp.text = data['fpage']
    if data['lpage']:
        lp = etree.SubElement(ec, 'lpage')
        lp.text = data['lpage']

    if data['publisher']:
        pub = etree.SubElement(ec, 'publisher-name')
        pub.text = data['publisher']

    if data['doi']:
        pid = etree.SubElement(ec, 'pub-id')
        pid.set('pub-id-type', 'doi')
        pid.text = data['doi']

    if data['url']:
        ext = etree.SubElement(ec, 'ext-link')
        ext.set('ext-link-type', 'uri')
        ext.set('{http://www.w3.org/1999/xlink}href', data['url'])

    return ec


def indent_element(element, level=0):
    """Recursively add pretty-print whitespace to an element tree."""
    indent_str = '\n' + '    ' * level
    child_indent = '\n' + '    ' * (level + 1)
    if len(element) > 0:
        if not element.text or not element.text.strip():
            element.text = child_indent
        for i, child in enumerate(element):
            indent_element(child, level + 1)
            if i == len(element) - 1:
                child.tail = indent_str
            else:
                child.tail = child_indent
    else:
        if element.text and not element.text.strip():
            element.text = None


def main():
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse('/Users/usuario/dev/XML-JATS-2/4975.xml', parser)
    root = tree.getroot()

    # Fix license
    for lic in root.iter('license'):
        lic.set('{http://www.w3.org/1999/xlink}href', 'https://creativecommons.org/licenses/by-nc-sa/4.0/')
        lic.set('{http://www.w3.org/XML/1998/namespace}lang', 'es')

    # Fix ref-count
    ref_list = root.find('.//ref-list')
    if ref_list is not None:
        actual_count = len(ref_list.findall('ref'))
        for rc in root.iter('ref-count'):
            rc.set('count', str(actual_count))

    # Fix references
    if ref_list is not None:
        for ref in ref_list.findall('ref'):
            mixed = ref.find('mixed-citation')
            if mixed is not None:
                text = ''.join(mixed.itertext())
                data = parse_citation(text)
                ec = build_element_citation(data)
                ref.remove(mixed)
                ref.append(ec)

    # Pretty-print
    indent_element(root)
    tree.write('/Users/usuario/dev/XML-JATS-2/4975.xml', encoding='utf-8', xml_declaration=True,
               doctype='<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.1 20151215//EN" "JATS-journalpublishing1.dtd">',
               pretty_print=False)
    print("Done. Fixed 4975.xml")


if __name__ == '__main__':
    main()
