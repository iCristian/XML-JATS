# -*- coding: utf-8 -*-

"""Verificador de integridad textual 100% entre documento original y XML JATS.

Compara el texto extraído del documento fuente contra el texto plano
extraído del XML generado, calculando métricas por sección y global.

Typical usage::

    from modules.integrity_checker import IntegrityChecker, OriginalStats

    checker = IntegrityChecker()
    stats = checker.compute_original_stats(segments)
    report = checker.verify_xml_integrity(xml_string, stats)
    print(report.is_complete, report.warnings)
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from difflib import unified_diff
from typing import Dict, List, Optional, Tuple

from lxml import etree

from .document_segmenter import DocumentSegments


# ─── Constantes ──────────────────────────────────────────────────

# Umbral mínimo de palabras para considerar una sección sustancial
_MIN_SECTION_WORDS: int = 10

# Umbral de tolerancia para diferencias por markup/encoding (5%)
_INTEGRITY_THRESHOLD: float = 0.95


# ─── Estructuras de datos ────────────────────────────────────────

@dataclass
class SectionStats:
    """Estadísticas de una sección del documento original."""

    title: str
    word_count: int
    paragraph_count: int
    text_hash: str
    raw_text: str = ""


@dataclass
class OriginalStats:
    """Estadísticas globales del documento original."""

    total_words: int = 0
    total_paragraphs: int = 0
    sections: Dict[str, SectionStats] = field(default_factory=dict)


@dataclass
class SectionDiff:
    """Resultado de comparación para una sección específica."""

    title: str
    original_hash: str
    xml_hash: str
    original_words: int
    xml_words: int
    match: bool
    diff_html: str = ""  # Representación del diff en HTML simple


@dataclass
class IntegrityReport:
    """Reporte completo de verificación de integridad."""

    is_complete: bool
    global_ratio: float  # Palabras XML / Palabras original
    warnings: List[str] = field(default_factory=list)
    section_diffs: List[SectionDiff] = field(default_factory=list)
    missing_sections: List[str] = field(default_factory=list)


# ─── Clase principal ─────────────────────────────────────────────

class IntegrityChecker:
    """Calcula y compara estadísticas textuales original vs. XML."""

    def __init__(self, threshold: float = _INTEGRITY_THRESHOLD) -> None:
        """Inicializa el verificador.

        Args:
            threshold: Ratio mínimo aceptable (0.0 - 1.0).
        """
        self.threshold = threshold

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normaliza texto para comparación justa.

        Elimina espacios extra, saltos de línea múltiples y
        convierte a minúsculas para hash.

        Args:
            text: Texto crudo.

        Returns:
            Texto normalizado.
        """
        text = text.replace('\r', '\n')
        text = re.sub(r'\s+', ' ', text)
        return text.strip().lower()

    @staticmethod
    def _compute_hash(text: str) -> str:
        """Calcula hash MD5 de un texto normalizado.

        Args:
            text: Texto a hashear.

        Returns:
            Hash hexadecimal de 32 caracteres.
        """
        normalized = IntegrityChecker._normalize_text(text)
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()

    @staticmethod
    def _count_words(text: str) -> int:
        """Cuenta palabras aproximadas en un texto.

        Args:
            text: Texto a contar.

        Returns:
            Cantidad de palabras.
        """
        if not text:
            return 0
        return len(re.findall(r'\b\w+\b', text))

    @staticmethod
    def _count_paragraphs(text: str) -> int:
        """Cuenta párrafos no vacíos.

        Args:
            text: Texto a contar.

        Returns:
            Cantidad de párrafos.
        """
        if not text:
            return 0
        return len([p for p in text.split('\n') if p.strip()])

    def compute_original_stats(
        self, segments: DocumentSegments
    ) -> OriginalStats:
        """Calcula estadísticas del documento original segmentado.

        Args:
            segments: DocumentSegments producido por DocumentSegmenter.

        Returns:
            OriginalStats con hashes y conteos.
        """
        stats = OriginalStats()

        # Front
        if segments.front_text.strip():
            words = self._count_words(segments.front_text)
            paras = self._count_paragraphs(segments.front_text)
            stats.total_words += words
            stats.total_paragraphs += paras
            stats.sections["front"] = SectionStats(
                title="Front (Metadatos + Resumen)",
                word_count=words,
                paragraph_count=paras,
                text_hash=self._compute_hash(segments.front_text),
                raw_text=segments.front_text,
            )

        # Body sections
        for sec in segments.body_sections:
            words = self._count_words(sec.content)
            paras = self._count_paragraphs(sec.content)
            stats.total_words += words
            stats.total_paragraphs += paras
            key = f"body_{sec.order}_{self._normalize_text(sec.title)}"
            stats.sections[key] = SectionStats(
                title=sec.title,
                word_count=words,
                paragraph_count=paras,
                text_hash=self._compute_hash(sec.content),
                raw_text=sec.content,
            )

        # References (contamos como zona back)
        if segments.references_raw:
            ref_text = "\n".join(segments.references_raw)
            words = self._count_words(ref_text)
            paras = len(segments.references_raw)
            stats.total_words += words
            stats.total_paragraphs += paras
            stats.sections["back_references"] = SectionStats(
                title="Referencias Bibliográficas",
                word_count=words,
                paragraph_count=paras,
                text_hash=self._compute_hash(ref_text),
                raw_text=ref_text,
            )

        return stats

    def verify_xml_integrity(
        self,
        xml_string: str,
        original_stats: OriginalStats,
    ) -> IntegrityReport:
        """Compara el XML ensamblado contra las estadísticas originales.

        Args:
            xml_string: XML JATS completo generado.
            original_stats: Estadísticas pre-calculadas del original.

        Returns:
            IntegrityReport con resultado de la comparación.
        """
        warnings: List[str] = []
        section_diffs: List[SectionDiff] = []

        # Extraer texto plano del XML por zonas
        xml_sections = self._extract_xml_sections(xml_string)
        xml_total_words = sum(s.word_count for s in xml_sections.values())

        # Comparación global
        global_ratio = (
            xml_total_words / max(original_stats.total_words, 1)
        )
        if global_ratio < self.threshold:
            warnings.append(
                f"Pérdida de texto global: {original_stats.total_words} "
                f"palabras originales → {xml_total_words} palabras en XML "
                f"(ratio {global_ratio:.2%})"
            )

        # Comparación por sección
        missing_sections: List[str] = []
        for key, orig_sec in original_stats.sections.items():
            xml_sec = xml_sections.get(key)
            if xml_sec is None:
                missing_sections.append(orig_sec.title)
                warnings.append(
                    f"Sección '{orig_sec.title}' no encontrada en el XML"
                )
                section_diffs.append(SectionDiff(
                    title=orig_sec.title,
                    original_hash=orig_sec.text_hash,
                    xml_hash="",
                    original_words=orig_sec.word_count,
                    xml_words=0,
                    match=False,
                ))
                continue

            match = orig_sec.text_hash == xml_sec.text_hash
            ratio = (
                xml_sec.word_count / max(orig_sec.word_count, 1)
            )

            diff_html = ""
            if not match and orig_sec.raw_text and xml_sec.raw_text:
                diff_html = self._generate_diff_html(
                    orig_sec.raw_text, xml_sec.raw_text
                )

            section_diffs.append(SectionDiff(
                title=orig_sec.title,
                original_hash=orig_sec.text_hash,
                xml_hash=xml_sec.text_hash,
                original_words=orig_sec.word_count,
                xml_words=xml_sec.word_count,
                match=match,
                diff_html=diff_html,
            ))

            if not match:
                if ratio < self.threshold:
                    warnings.append(
                        f"Sección '{orig_sec.title}' truncada o resumida: "
                        f"{orig_sec.word_count} → {xml_sec.word_count} palabras "
                        f"(ratio {ratio:.2%})"
                    )
                else:
                    warnings.append(
                        f"Sección '{orig_sec.title}' modificada (posible "
                        f"parafraseo o reordenamiento). Hash no coincide."
                    )

        is_complete = (
            len(warnings) == 0
            and global_ratio >= self.threshold
            and not missing_sections
        )

        return IntegrityReport(
            is_complete=is_complete,
            global_ratio=global_ratio,
            warnings=warnings,
            section_diffs=section_diffs,
            missing_sections=missing_sections,
        )

    def _extract_xml_sections(
        self, xml_string: str
    ) -> Dict[str, SectionStats]:
        """Extrae texto plano del XML agrupado por secciones.

        Args:
            xml_string: XML JATS completo.

        Returns:
            Dict mapeando claves de sección a SectionStats del XML.
        """
        result: Dict[str, SectionStats] = {}
        if not xml_string or not xml_string.strip():
            return result

        try:
            parser = etree.XMLParser(
                recover=True,
                encoding='utf-8',
                resolve_entities=False,
                no_network=True,
            )
            root = etree.fromstring(xml_string.encode('utf-8'), parser=parser)
        except Exception:
            # XML irrecuperable: no podemos extraer secciones
            return result

        # Extraer front (article-meta)
        front = root.find('.//front')
        if front is not None:
            front_text = "".join(front.itertext())
            result["front"] = SectionStats(
                title="Front (Metadatos + Resumen)",
                word_count=self._count_words(front_text),
                paragraph_count=self._count_paragraphs(front_text),
                text_hash=self._compute_hash(front_text),
                raw_text=front_text,
            )

        # Extraer body sections
        body = root.find('.//body')
        if body is not None:
            for idx, sec in enumerate(body.findall('sec'), start=1):
                title_el = sec.find('title')
                title = (
                    title_el.text if title_el is not None and title_el.text
                    else f"Sección {idx}"
                )
                sec_text = "".join(sec.itertext())
                key = f"body_{idx}_{self._normalize_text(title)}"
                result[key] = SectionStats(
                    title=title,
                    word_count=self._count_words(sec_text),
                    paragraph_count=len(sec.findall('p')),
                    text_hash=self._compute_hash(sec_text),
                    raw_text=sec_text,
                )

        # Extraer referencias
        back = root.find('.//back')
        if back is not None:
            ref_list = back.find('.//ref-list')
            if ref_list is not None:
                ref_texts: List[str] = []
                for ref in ref_list.findall('ref'):
                    ref_text = "".join(ref.itertext())
                    ref_texts.append(ref_text)
                full_ref_text = "\n".join(ref_texts)
                result["back_references"] = SectionStats(
                    title="Referencias Bibliográficas",
                    word_count=self._count_words(full_ref_text),
                    paragraph_count=len(ref_texts),
                    text_hash=self._compute_hash(full_ref_text),
                    raw_text=full_ref_text,
                )

        return result

    @staticmethod
    def _generate_diff_html(original: str, xml_text: str) -> str:
        """Genera un diff HTML simple entre dos textos.

        Args:
            original: Texto original.
            xml_text: Texto extraído del XML.

        Returns:
            String HTML con el diff resaltado.
        """
        orig_lines = original.splitlines()
        xml_lines = xml_text.splitlines()
        diff = unified_diff(
            orig_lines,
            xml_lines,
            fromfile='original',
            tofile='xml',
            lineterm='',
        )
        lines = list(diff)
        if not lines:
            return "<p>Sin diferencias detectadas (posible reordenamiento).</p>"

        html_parts = ["<div style='font-family: monospace; font-size: 0.9rem;'>"]
        for line in lines:
            if line.startswith('+'):
                html_parts.append(
                    f"<div style='background: #dcfce7; color: #166534;'>"
                    f"{line}</div>"
                )
            elif line.startswith('-'):
                html_parts.append(
                    f"<div style='background: #fee2e2; color: #991b1b;'>"
                    f"{line}</div>"
                )
            elif line.startswith('@@'):
                html_parts.append(
                    f"<div style='background: #e0e7ff; color: #3730a3;'>"
                    f"{line}</div>"
                )
            else:
                html_parts.append(f"<div>{line}</div>")
        html_parts.append("</div>")
        return "\n".join(html_parts)
