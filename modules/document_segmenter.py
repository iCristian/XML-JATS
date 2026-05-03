# -*- coding: utf-8 -*-

"""Segmentador semántico heurístico de documentos académicos.

Divide el texto extraído de un DOCX/PDF en bloques lógicos
(front, body sections, tablas, figuras, referencias) usando
heurísticas de lenguaje y expresiones regulares, sin depender
de llamadas a modelos de lenguaje.

Typical usage::

    from modules.document_segmenter import DocumentSegmenter

    segmenter = DocumentSegmenter()
    segments = segmenter.segment(texto_extraido)
    print(segments.body_sections[0].title)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ─── Constantes de configuración ─────────────────────────────────

# Encabezados típicos de secciones del body en español e inglés.
# Ordenados por frecuencia de aparición para mejor matching.
_KNOWN_BODY_SECTIONS: List[Tuple[str, ...]] = [
    # Español
    ("introducción", "introduccion"),
    ("antecedentes",),
    ("marco teórico", "marco teorico", "marco conceptual"),
    ("objetivos", "objetivo", "objetivo general", "objetivos generales"),
    ("hipótesis", "hipotesis"),
    ("métodos", "metodos", "metodología", "metodologia",
     "material y métodos", "material y metodos",
     "materiales y métodos", "materiales y metodos",
     "sujetos y métodos", "sujetos y metodos",
     "diseño metodológico", "diseño metodologico"),
    ("resultados",),
    ("discusión", "discusion", "discusión y conclusiones",
     "discusion y conclusiones"),
    ("conclusiones", "conclusión", "conclusion"),
    ("agradecimientos", "agradecimiento", "acknowledgments",
     "acknowledgements", "agradecimientos"),
    ("financiamiento", "conflictos de interés", "conflictos de interes",
     "conflict of interest"),
    # Inglés
    ("introduction",),
    ("background",),
    ("theoretical framework", "conceptual framework"),
    ("objectives", "objective", "aim", "aims"),
    ("hypothesis", "hypotheses"),
    ("methods", "methodology", "materials and methods",
     "material and methods", "subjects and methods",
     "study design", "experimental design"),
    ("results", "findings"),
    ("discussion", "discussion and conclusions"),
    ("conclusions", "conclusion"),
    ("acknowledgments", "acknowledgements"),
    ("funding", "conflict of interest", "conflicts of interest",
     "ethical considerations", "ethics statement"),
]

# Palabras clave que marcan el inicio de la zona de referencias.
_KNOWN_REFERENCE_HEADERS: Tuple[str, ...] = (
    "referencias",
    "referencias bibliográficas",
    "bibliografía",
    "bibliografia",
    "references",
    "literature cited",
)

# Marcadores de placeholders en el texto extraído.
_TABLE_PLACEHOLDER_RE = re.compile(
    r'\[TABLA-PLACEHOLDER\s+[^\]]*\]',
    re.IGNORECASE,
)
_IMAGE_PLACEHOLDER_RE = re.compile(
    r'\[IMAGEN-PLACEHOLDER\s+[^\]]*\]',
    re.IGNORECASE,
)


# ─── Estructuras de datos ────────────────────────────────────────

@dataclass
class BodySection:
    """Representa una sección del cuerpo del artículo."""

    title: str
    content: str
    order: int = 0


@dataclass
class TableSegment:
    """Representa una tabla detectada en el texto."""

    id: str
    caption: str
    content: str
    raw_placeholder: str = ""


@dataclass
class FigureSegment:
    """Representa una figura detectada en el texto."""

    id: str
    caption: str
    file: str
    raw_placeholder: str = ""


@dataclass
class DocumentSegments:
    """Contenedor con todos los segmentos de un documento."""

    front_text: str = ""
    body_sections: List[BodySection] = field(default_factory=list)
    tables: List[TableSegment] = field(default_factory=list)
    figures: List[FigureSegment] = field(default_factory=list)
    references_raw: List[str] = field(default_factory=list)


# ─── Clase principal ─────────────────────────────────────────────

class DocumentSegmenter:
    """Divide texto plano extraído en segmentos semánticos."""

    def __init__(self) -> None:
        """Inicializa compilación de expresiones regulares."""
        self._section_patterns = self._compile_section_patterns()
        self._ref_patterns = self._compile_reference_patterns()

    @staticmethod
    def _compile_section_patterns() -> List[re.Pattern]:
        """Compila regex para detectar encabezados de sección.

        Returns:
            Lista de patrones regex compilados.
        """
        patterns: List[re.Pattern] = []
        for variants in _KNOWN_BODY_SECTIONS:
            # Construir alternancia: palabra1|palabra2|...
            escaped = [re.escape(v) for v in variants]
            # Permitir numeración opcional al inicio: "1. Introducción", "I. Métodos"
            pattern_str = (
                r'^(?:\s*(?:\d+[.\)]?\s*|\(?[IVXivx]+\)?[.\)]?\s*)?)?'
                r'(' + "|".join(escaped) + r')'
                r'(?:\s*[:.\-–—)]|$)'
            )
            patterns.append(re.compile(pattern_str, re.IGNORECASE | re.MULTILINE))
        return patterns

    @staticmethod
    def _compile_reference_patterns() -> List[re.Pattern]:
        """Compila regex para detectar encabezado de referencias.

        Returns:
            Lista de patrones regex compilados.
        """
        patterns: List[re.Pattern] = []
        for header in _KNOWN_REFERENCE_HEADERS:
            pattern_str = (
                r'^(?:\s*(?:\d+[.\)]?\s*|\(?[IVXivx]+\)?[.\)]?\s*)?)?'
                r'(' + re.escape(header) + r')'
                r'(?:\s*[:.\-–—)]|$)'
            )
            patterns.append(re.compile(pattern_str, re.IGNORECASE | re.MULTILINE))
        return patterns

    def segment(self, raw_text: str) -> DocumentSegments:
        """Segmenta el texto completo en partes lógicas.

        Args:
            raw_text: Texto plano extraído del documento (puede contener
                placeholders de imágenes y tablas).

        Returns:
            Instancia de DocumentSegments con todas las partes identificadas.
        """
        if not raw_text or not raw_text.strip():
            return DocumentSegments()

        # 1. Extraer placeholders de tablas e imágenes ANTES de segmentar
        tables = self._extract_tables(raw_text)
        figures = self._extract_figures(raw_text)

        # 2. Limpiar texto de placeholders para facilitar segmentación
        #    (conservamos una copia con saltos de línea para no romper párrafos)
        clean_text = _TABLE_PLACEHOLDER_RE.sub("", raw_text)
        clean_text = _IMAGE_PLACEHOLDER_RE.sub("", clean_text)

        # 3. Detectar todas las secciones del body
        section_matches = self._find_all_section_matches(clean_text)

        # 4. Separar front, body y back
        front_text, body_text, back_text = self._split_zones(
            clean_text, section_matches
        )

        # 5. Dividir body en secciones individuales
        body_sections = self._split_body_sections(body_text, section_matches)

        # 6. Extraer referencias del back
        references = self._extract_references(back_text)

        return DocumentSegments(
            front_text=front_text.strip(),
            body_sections=body_sections,
            tables=tables,
            figures=figures,
            references_raw=references,
        )

    def _extract_tables(self, text: str) -> List[TableSegment]:
        """Extrae placeholders de tablas del texto.

        Args:
            text: Texto original con placeholders.

        Returns:
            Lista de TableSegment identificados.
        """
        tables: List[TableSegment] = []
        counter = 1
        for match in _TABLE_PLACEHOLDER_RE.finditer(text):
            raw = match.group(0)
            caption = ""
            content = ""
            # Extraer atributos del placeholder
            cap_match = re.search(r'caption="([^"]*)"', raw)
            if cap_match:
                caption = cap_match.group(1)
            cont_match = re.search(r'content="([^"]*)"', raw)
            if cont_match:
                content = cont_match.group(1)
            tables.append(TableSegment(
                id=f"t{counter}",
                caption=caption,
                content=content,
                raw_placeholder=raw,
            ))
            counter += 1
        return tables

    def _extract_figures(self, text: str) -> List[FigureSegment]:
        """Extrae placeholders de imágenes del texto.

        Args:
            text: Texto original con placeholders.

        Returns:
            Lista de FigureSegment identificados.
        """
        figures: List[FigureSegment] = []
        counter = 1
        for match in _IMAGE_PLACEHOLDER_RE.finditer(text):
            raw = match.group(0)
            caption = ""
            file_name = ""
            cap_match = re.search(r'caption="([^"]*)"', raw)
            if cap_match:
                caption = cap_match.group(1)
            file_match = re.search(r'file="([^"]*)"', raw)
            if file_match:
                file_name = file_match.group(1)
            figures.append(FigureSegment(
                id=f"f{counter}",
                caption=caption,
                file=file_name,
                raw_placeholder=raw,
            ))
            counter += 1
        return figures

    def _find_all_section_matches(
        self, text: str
    ) -> List[Tuple[int, int, str]]:
        """Encuentra todos los encabezados de sección en el texto.

        Args:
            text: Texto limpio (sin placeholders).

        Returns:
            Lista de tuplas (start, end, title) ordenadas por posición.
        """
        matches: List[Tuple[int, int, str]] = []
        for pattern in self._section_patterns:
            for m in pattern.finditer(text):
                # Evitar falsos positivos en medio de una oración
                if self._is_likely_heading(text, m.start()):
                    matches.append((m.start(), m.end(), m.group(1).strip()))
        # Ordenar por posición y eliminar duplicados cercanos
        matches.sort(key=lambda x: x[0])
        return self._deduplicate_matches(matches)

    @staticmethod
    def _is_likely_heading(text: str, pos: int) -> bool:
        """Heurística para verificar si un match está en un encabezado real.

        Revisa que el match esté al inicio de una línea o precedido solo
        por espacios/numeración.

        Args:
            text: Texto completo.
            pos: Posición del match.

        Returns:
            True si parece un encabezado real.
        """
        # Buscar el inicio de la línea actual
        line_start = text.rfind('\n', 0, pos)
        if line_start == -1:
            line_start = 0
        else:
            line_start += 1
        prefix = text[line_start:pos]
        # El prefijo debe estar vacío o ser solo espacios/numeración romana/decimal
        return bool(re.match(r'^[\s]*(?:\d+[.\)]?\s*|\(?[IVXivx]+\)?[.\)]?\s*)?$', prefix))

    @staticmethod
    def _deduplicate_matches(
        matches: List[Tuple[int, int, str]]
    ) -> List[Tuple[int, int, str]]:
        """Elimina matches solapados o muy cercanos (< 3 caracteres).

        Args:
            matches: Lista de matches ordenados.

        Returns:
            Lista filtrada.
        """
        if not matches:
            return []
        result = [matches[0]]
        for start, end, title in matches[1:]:
            last_start, last_end, _ = result[-1]
            # Si se solapan o están a menos de 3 chars, ignorar el segundo
            if start < last_end + 3:
                continue
            result.append((start, end, title))
        return result

    def _split_zones(
        self,
        text: str,
        section_matches: List[Tuple[int, int, str]],
    ) -> Tuple[str, str, str]:
        """Divide el texto en front, body y back.

        Args:
            text: Texto limpio completo.
            section_matches: Matches de secciones detectadas.

        Returns:
            Tupla (front_text, body_text, back_text).
        """
        if not section_matches:
            # No se detectaron secciones: todo es front (fallback)
            return text, "", ""

        first_section_start = section_matches[0][0]
        front_text = text[:first_section_start]

        # Detectar dónde empieza la zona de referencias
        ref_start = self._find_references_start(text)
        if ref_start is not None and ref_start > first_section_start:
            body_text = text[first_section_start:ref_start]
            back_text = text[ref_start:]
        else:
            body_text = text[first_section_start:]
            back_text = ""

        return front_text, body_text, back_text

    def _find_references_start(self, text: str) -> Optional[int]:
        """Busca el encabezado de referencias en el texto.

        Args:
            text: Texto completo.

        Returns:
            Posición del inicio del encabezado, o None si no se encuentra.
        """
        for pattern in self._ref_patterns:
            for m in pattern.finditer(text):
                if self._is_likely_heading(text, m.start()):
                    return m.start()
        return None

    def _split_body_sections(
        self,
        body_text: str,
        section_matches: List[Tuple[int, int, str]],
    ) -> List[BodySection]:
        """Divide el texto del body en secciones individuales.

        Args:
            body_text: Texto correspondiente al body (sin front ni back).
            section_matches: Matches de secciones detectadas en el texto original.

        Returns:
            Lista de BodySection.
        """
        sections: List[BodySection] = []
        if not body_text.strip():
            return sections

        # Filtrar solo los matches que caen dentro del body_text
        # body_text empieza en offset = len(front_text) dentro del texto original
        # Pero como body_text es un slice, necesitamos recalcular los offsets
        # relative_to_body = original_start - body_start_offset
        # Esto es complejo; en su lugar, re-detectamos matches dentro de body_text.
        body_matches = self._find_all_section_matches(body_text)

        if not body_matches:
            # Si no hay matches en el body, todo es una sección genérica
            sections.append(BodySection(
                title="Contenido Principal",
                content=body_text.strip(),
                order=1,
            ))
            return sections

        for i, (start, end, title) in enumerate(body_matches, start=1):
            if i < len(body_matches):
                next_start = body_matches[i][0]
                content = body_text[end:next_start]
            else:
                content = body_text[end:]
            sections.append(BodySection(
                title=title,
                content=content.strip(),
                order=i,
            ))
        return sections

    @staticmethod
    def _extract_references(back_text: str) -> List[str]:
        """Extrae la lista de referencias del texto del back.

        Args:
            back_text: Texto de la zona posterior al encabezado de referencias.

        Returns:
            Lista de strings, cada uno representando una referencia.
        """
        if not back_text.strip():
            return []

        # Eliminar el encabezado de referencias de la primera línea
        lines = back_text.splitlines()
        if lines:
            first_line = lines[0].strip()
            if any(
                first_line.lower().startswith(h.lower())
                for h in _KNOWN_REFERENCE_HEADERS
            ):
                lines = lines[1:]

        # Estrategia 1: Buscar numeración al inicio de línea (1. o [1] o 1)
        refs: List[str] = []
        current_ref = ""
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            # Detectar inicio de nueva referencia
            if re.match(r'^(?:\[?\d+\]?[.\)]\s+|\d+\s+)', stripped):
                if current_ref:
                    refs.append(current_ref.strip())
                current_ref = stripped
            else:
                current_ref += " " + stripped
        if current_ref:
            refs.append(current_ref.strip())

        # Estrategia 2: Si no se encontraron referencias numeradas,
        # dividir por líneas en blanco dobles
        if not refs:
            refs = [r.strip() for r in back_text.split('\n\n') if r.strip()]

        return refs
