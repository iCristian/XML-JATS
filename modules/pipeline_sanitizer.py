# -*- coding: utf-8 -*-

"""Sanitizador de fragmentos XML para el pipeline por fases.

Valida que cada fragmento generado por el LLM (front, body section, back)
sea XML bien formado antes de pasarlo al ensamblaje. Si un fragmento está
roto, intenta repararlo con ``lxml`` (recover=True) o lo envuelve en una
estructura segura para no romper el documento global.

Typical usage::

    from modules.pipeline_sanitizer import PipelineSanitizer

    sanitizer = PipelineSanitizer()
    clean_front = sanitizer.sanitize_front(raw_front_xml)
    clean_body = sanitizer.sanitize_body_section(raw_body_xml, "Introducción")
    clean_back = sanitizer.sanitize_back(raw_back_xml)
"""

from __future__ import annotations

import re
from typing import Optional

from lxml import etree


class PipelineSanitizer:
    """Repara fragmentos XML generados por modelos de lenguaje."""

    # Patrones para detectar comentarios placeholder comunes de LLMs
    _LAZY_COMMENT_RE = re.compile(
        r'<!--\s*(?:contenido|cuerpo|texto|referencias|inserte|...|'
        r'placeholder|todo el contenido|sección|section|body|back|front)'
        r'[^>]*?-->',
        re.IGNORECASE,
    )

    @staticmethod
    def _repair_with_lxml(fragment: str, root_tag_hint: Optional[str] = None) -> str:
        """Intenta parsear y re-serializar un fragmento XML con lxml recover.

        Args:
            fragment: Texto XML potencialmente roto.
            root_tag_hint: Tag raíz esperado (ej. ``front``, ``sec``).

        Returns:
            Fragmento reparado, o texto vacío si es irrecuperable.
        """
        if not fragment or not fragment.strip():
            return ""

        try:
            parser = etree.XMLParser(
                recover=True,
                encoding="utf-8",
                resolve_entities=False,
                no_network=True,
            )
            # Envolvemos en un dummy root para que lxml no exija un solo root
            wrapped = f"<dummy-root>{fragment}</dummy-root>"
            tree = etree.fromstring(wrapped.encode("utf-8"), parser=parser)
            # Extraer solo los hijos del dummy root
            children = list(tree)
            if not children:
                # Puede que haya texto plano mezclado; serializar todo el contenido
                return "".join(tree.itertext())
            parts: list[str] = []
            for child in children:
                parts.append(etree.tostring(child, encoding="unicode"))
            return "\n".join(parts)
        except Exception:
            return fragment.strip()

    @staticmethod
    def _remove_lazy_comments(xml: str) -> str:
        """Elimina comentarios XML que sugieren omisión de contenido.

        Args:
            xml: Fragmento XML.

        Returns:
            XML sin comentarios perezosos.
        """
        return PipelineSanitizer._LAZY_COMMENT_RE.sub("", xml)

    @staticmethod
    def _ensure_tag_bounds(xml: str, open_tag: str, close_tag: str) -> str:
        """Asegura que un fragmento empiece con open_tag y termine con close_tag.

        Si el fragmento ya contiene el tag, lo deja intacto. Si no, lo envuelve.

        Args:
            xml: Fragmento XML.
            open_tag: Tag de apertura (ej. ``<front>``).
            close_tag: Tag de cierre (ej. ``</front>``).

        Returns:
            Fragmento envuelto correctamente.
        """
        xml = xml.strip()
        if not xml.startswith(open_tag):
            xml = f"{open_tag}\n{xml}"
        if not xml.endswith(close_tag):
            xml = f"{xml}\n{close_tag}"
        return xml

    @staticmethod
    def _extract_tag(xml: str, tag: str) -> str:
        """Extrae el contenido de un tag específico, manejando anidación en <article>.

        Args:
            xml: XML que puede contener el tag envuelto en <article>.
            tag: Tag a extraer (ej. 'front', 'sec', 'back').

        Returns:
            Contenido del tag encontrado, o cadena vacía.
        """
        # Buscar <tag> o <tag ...>
        pattern = rf'<{tag}\b[^>]*>(.*?)</{tag}>'
        match = re.search(pattern, xml, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(0)
        return ""

    @staticmethod
    def _extract_all_tags(xml: str, tag: str) -> List[str]:
        """Extrae TODAS las ocurrencias de un tag.

        Args:
            xml: XML a escanear.
            tag: Tag a extraer.

        Returns:
            Lista de strings con cada ocurrencia completa.
        """
        pattern = rf'<{tag}\b[^>]*>.*?</{tag}>'
        return re.findall(pattern, xml, re.DOTALL | re.IGNORECASE)

    def sanitize_front(self, xml: str) -> str:
        """Sanitiza el fragmento <front>.

        Args:
            xml: XML crudo del front.

        Returns:
            XML well-formed del front.
        """
        xml = self._remove_lazy_comments(xml)
        # Si el modelo envolvió front en <article>, extraer solo <front>
        extracted = self._extract_tag(xml, "front")
        if extracted:
            xml = extracted
        else:
            xml = self._ensure_tag_bounds(xml, "<front>", "</front>")
        repaired = self._repair_with_lxml(xml, "front")
        # Si lxml devolvió algo sin <front>, reenvolver
        if repaired and "<front>" not in repaired and "<front " not in repaired:
            repaired = f"<front>\n{repaired}\n</front>"
        return repaired or "<front></front>"

    def sanitize_body_section(self, xml: str, title: str) -> str:
        """Sanitiza un fragmento de sección del body.

        Si el fragmento no tiene estructura <sec>, intenta crear una válida
        a partir del contenido. Elimina comentarios placeholder.
        Maneja múltiples <sec> si el modelo generó varias.

        Args:
            xml: XML crudo de la sección.
            title: Título esperado de la sección.

        Returns:
            XML well-formed de la sección (o múltiples secciones concatenadas).
        """
        xml = self._remove_lazy_comments(xml)
        xml = xml.strip()

        if not xml:
            # Fragmento vacío: crear sección placeholder
            return (
                f'<sec>\n'
                f'  <title>{title}</title>\n'
                f'  <p>[Error: el modelo no generó contenido para esta sección]</p>\n'
                f'</sec>'
            )

        # Si el modelo envolvió todo en <article>, extraer las <sec> internas
        sec_blocks = self._extract_all_tags(xml, "sec")
        if sec_blocks:
            # Reparar cada bloque y concatenar
            repaired_blocks: List[str] = []
            for block in sec_blocks:
                rep = self._repair_with_lxml(block)
                if rep and ("<sec>" in rep or "<sec " in rep):
                    repaired_blocks.append(rep)
            if repaired_blocks:
                return "\n".join(repaired_blocks)

        # Si el fragmento no tiene <sec>, intentar envolverlo
        has_sec = xml.startswith("<sec")
        if not has_sec:
            # Intentar reparar con lxml envolviendo en dummy-root
            repaired = self._repair_with_lxml(xml)
            if repaired and ("<sec>" in repaired or "<sec " in repaired):
                xml = repaired
            else:
                # Envolver todo en <sec><title>...</title>...
                xml = (
                    f'<sec>\n'
                    f'  <title>{title}</title>\n'
                    f'  {repaired or xml}\n'
                    f'</sec>'
                )
        else:
            # Tiene <sec>, reparar con lxml
            xml = self._repair_with_lxml(xml)

        # Asegurar que tenga <title>
        if "<title>" not in xml and "<title " not in xml:
            # Insertar título justo después de <sec> o <sec ...>
            xml = re.sub(
                r'(<sec[^>]*>)',
                r'\1\n  <title>' + re.escape(title) + '</title>',
                xml,
                count=1,
            )

        return xml

    def sanitize_back(self, xml: str) -> str:
        """Sanitiza el fragmento <back> (referencias).

        Args:
            xml: XML crudo del back.

        Returns:
            XML well-formed del back.
        """
        xml = self._remove_lazy_comments(xml)
        # Extraer <back> si está anidado en <article>
        extracted = self._extract_tag(xml, "back")
        if extracted:
            xml = extracted
        else:
            # Si no hay <back> pero hay <ref-list>, envolver
            if "<ref-list>" in xml.lower():
                xml = f"<back>\n{xml}\n</back>"
            else:
                xml = self._ensure_tag_bounds(xml, "<back>", "</back>")
        repaired = self._repair_with_lxml(xml, "back")
        if repaired and "<back>" not in repaired and "<back " not in repaired:
            repaired = f"<back>\n{repaired}\n</back>"
        return repaired or "<back><ref-list></ref-list></back>"

    def sanitize_table(self, xml: str) -> str:
        """Sanitiza un fragmento <table-wrap>.

        Args:
            xml: XML crudo de la tabla.

        Returns:
            XML well-formed del table-wrap.
        """
        xml = self._remove_lazy_comments(xml)
        xml = xml.strip()
        if not xml:
            return ""
        repaired = self._repair_with_lxml(xml)
        return repaired or ""

    def create_placeholder_section(self, title: str, reason: str = "") -> str:
        """Crea una sección <sec> placeholder segura para ensamblaje.

        Args:
            title: Título de la sección.
            reason: Razón del placeholder (opcional).

        Returns:
            XML placeholder well-formed.
        """
        msg = f"[Error al generar esta sección]"
        if reason:
            msg = f"[Error: {reason}]"
        return (
            f'<sec>\n'
            f'  <title>{title}</title>\n'
            f'  <p>{msg}</p>\n'
            f'</sec>'
        )
