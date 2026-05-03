# -*- coding: utf-8 -*-

"""Orquestador del pipeline por fases para generación JATS XML.

Coordina la segmentación, generación por chunks, ensamblaje y
validación del XML JATS siguiendo la arquitectura propuesta en
`propuesta.md` (rama experimento4).

Typical usage::

    from modules.pipeline_orchestrator import PipelineOrchestrator

    orchestrator = PipelineOrchestrator(provider_id="gemini", model="gemini-2.5-flash")
    result = orchestrator.run(docx_path="articulo.docx", api_key="...")
    print(result.xml_string)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .document_segmenter import DocumentSegmenter, DocumentSegments
from .chunk_manager import ChunkManager
from .integrity_checker import IntegrityChecker, OriginalStats, IntegrityReport
from .ai_integrity_verifier import AiIntegrityVerifier, VerificationResult
from .transformer import validar_jats_xml, invocar_llm
from .metadata_processor import MetadataExtractor
from . import prompts


# ─── Estructuras de datos ────────────────────────────────────────

@dataclass
class PipelineStage:
    """Representa el estado de una fase del pipeline."""

    name: str
    status: str  # "pending", "running", "success", "failed"
    message: str = ""


@dataclass
class PipelineResult:
    """Resultado completo de la ejecución del pipeline."""

    xml_string: str = ""
    is_valid_dtd: bool = False
    dtd_errors: List[str] = field(default_factory=list)
    integrity_report: Optional[IntegrityReport] = None
    ai_verification: Optional[Dict[str, VerificationResult]] = None
    stages: List[PipelineStage] = field(default_factory=list)
    error: str = ""


# ─── Clase principal ─────────────────────────────────────────────

class PipelineOrchestrator:
    """Orquesta el flujo completo de generación JATS por fases."""

    def __init__(
        self,
        provider_id: str = "gemini",
        model: str = "gemini-2.5-flash",
        api_key: Optional[str] = None,
        max_input_tokens: int = 8192,
        max_output_tokens: int = 4096,
    ) -> None:
        """Inicializa el orquestador.

        Args:
            provider_id: ID del proveedor LLM.
            model: Modelo específico.
            api_key: Clave de API.
            max_input_tokens: Ventana de contexto del modelo.
            max_output_tokens: Límite de salida del modelo.
        """
        self.provider_id = provider_id
        self.model = model
        self.api_key = api_key or ""
        self.segmenter = DocumentSegmenter()
        self.chunk_manager = ChunkManager(
            max_input_tokens=max_input_tokens,
            max_output_tokens=max_output_tokens,
        )
        self.integrity_checker = IntegrityChecker()
        self.ai_verifier = AiIntegrityVerifier(
            provider_id=provider_id,
            model=model,
        )
        self.stages: List[PipelineStage] = []

    def _add_stage(self, name: str, status: str, message: str = "") -> None:
        """Registra una fase en el log de ejecución."""
        self.stages.append(PipelineStage(
            name=name, status=status, message=message,
        ))

    def run(
        self,
        docx_path: str,
        metadata: Optional[Dict[str, Any]] = None,
        journal_config: Optional[Dict[str, str]] = None,
    ) -> PipelineResult:
        """Ejecuta el pipeline completo.

        Args:
            docx_path: Ruta al archivo DOCX (o PDF en futuro).
            metadata: Metadatos pre-extraídos (opcional).
            journal_config: Configuración de la revista.

        Returns:
            PipelineResult con el XML y todos los reportes.
        """
        result = PipelineResult()
        self.stages = []

        # ── FASE 0: Segmentación ─────────────────────────────────
        self._add_stage("Segmentación", "running")
        try:
            from .transformer import extraer_contenido_estructurado
            raw_text = extraer_contenido_estructurado(docx_path)
            if not raw_text:
                self._add_stage("Segmentación", "failed", "No se pudo extraer texto")
                result.error = "Extracción de texto fallida"
                return result
            segments = self.segmenter.segment(raw_text)
            self._add_stage("Segmentación", "success")
        except Exception as e:
            self._add_stage("Segmentación", "failed", str(e))
            result.error = f"Error en segmentación: {e}"
            return result

        # Extraer metadatos si no se proporcionaron
        if not metadata:
            self._add_stage("Metadatos", "running")
            try:
                extractor = MetadataExtractor()
                metadata = extractor.extract_from_file(
                    docx_path,
                    model_version=self.model,
                    api_key=self.api_key,
                    provider_id=self.provider_id,
                )
                self._add_stage("Metadatos", "success")
            except Exception as e:
                self._add_stage("Metadatos", "failed", str(e))
                result.error = f"Error extrayendo metadatos: {e}"
                return result

        # ── FASE 1: Front ────────────────────────────────────────
        self._add_stage("Front", "running")
        front_xml = ""
        try:
            front_xml = self._generate_front(metadata, journal_config or {})
            self._add_stage("Front", "success")
        except Exception as e:
            self._add_stage("Front", "failed", str(e))
            result.error = f"Error generando front: {e}"
            return result

        # ── FASE 2: Body Sections ────────────────────────────────
        self._add_stage("Body", "running")
        body_sections_xml: List[str] = []
        try:
            for sec in segments.body_sections:
                sec_xml = self._generate_body_section(sec, metadata)
                body_sections_xml.append(sec_xml)
            self._add_stage("Body", "success")
        except Exception as e:
            self._add_stage("Body", "failed", str(e))
            result.error = f"Error generando body: {e}"
            return result

        # ── FASE 3: Back (Referencias) ───────────────────────────
        self._add_stage("Referencias", "running")
        back_xml = ""
        try:
            back_xml = self._generate_back(segments)
            self._add_stage("Referencias", "success")
        except Exception as e:
            self._add_stage("Referencias", "failed", str(e))
            result.error = f"Error generando back: {e}"
            return result

        # ── FASE 4: Ensamblaje ───────────────────────────────────
        self._add_stage("Ensamblaje", "running")
        try:
            full_xml = self._assemble_xml(front_xml, body_sections_xml, back_xml)
            self._add_stage("Ensamblaje", "success")
        except Exception as e:
            self._add_stage("Ensamblaje", "failed", str(e))
            result.error = f"Error ensamblando XML: {e}"
            return result

        # ── Validación DTD ───────────────────────────────────────
        self._add_stage("Validación DTD", "running")
        try:
            is_valid, errors = validar_jats_xml(full_xml)
            result.is_valid_dtd = is_valid
            result.dtd_errors = errors
            status = "success" if is_valid else "failed"
            self._add_stage("Validación DTD", status)
        except Exception as e:
            self._add_stage("Validación DTD", "failed", str(e))

        # ── Verificación de Integridad Programática ──────────────
        self._add_stage("Integridad Programática", "running")
        try:
            orig_stats = self.integrity_checker.compute_original_stats(segments)
            integrity = self.integrity_checker.verify_xml_integrity(
                full_xml, orig_stats,
            )
            result.integrity_report = integrity
            status = "success" if integrity.is_complete else "warning"
            self._add_stage("Integridad Programática", status)
        except Exception as e:
            self._add_stage("Integridad Programática", "failed", str(e))

        # ── Verificación IA ──────────────────────────────────────
        self._add_stage("Verificación IA", "running")
        try:
            ai_results = self._run_ai_verification(segments, full_xml)
            result.ai_verification = ai_results
            any_problems = any(
                not r.is_complete for r in ai_results.values()
            )
            status = "warning" if any_problems else "success"
            self._add_stage("Verificación IA", status)
        except Exception as e:
            self._add_stage("Verificación IA", "failed", str(e))

        result.xml_string = full_xml
        result.stages = self.stages
        return result

    def _generate_front(
        self,
        metadata: Dict[str, Any],
        journal_config: Dict[str, str],
    ) -> str:
        """Genera el XML del <front>.

        Args:
            metadata: Metadatos del artículo.
            journal_config: Configuración de la revista.

        Returns:
            String XML del front.
        """
        prompt = prompts.get_front_prompt(metadata, journal_config)
        response = invocar_llm(
            prompt=prompt,
            model_version=self.model,
            api_key=self.api_key,
            provider_id=self.provider_id,
        )
        if response.get('returncode') != 0:
            raise RuntimeError(response.get('stderr', 'Error generando front'))
        return response.get('stdout', '').strip()

    def _generate_body_section(
        self,
        sec,
        metadata: Optional[Dict[str, Any]],
    ) -> str:
        """Genera el XML de una sección del body.

        Args:
            sec: Instancia de BodySection.
            metadata: Metadatos para contexto.

        Returns:
            String XML de la sección.
        """
        chunks = self.chunk_manager.split_section(sec.content)
        chunk_xmls: List[str] = []
        for chunk in chunks:
            prompt = prompts.get_body_section_prompt(
                section_title=sec.title,
                section_text=chunk,
                metadata=metadata,
            )
            response = invocar_llm(
                prompt=prompt,
                model_version=self.model,
                api_key=self.api_key,
                provider_id=self.provider_id,
            )
            if response.get('returncode') != 0:
                raise RuntimeError(
                    f"Error en sección '{sec.title}': "
                    f"{response.get('stderr', 'unknown')}"
                )
            xml_part = response.get('stdout', '').strip()
            chunk_xmls.append(xml_part)
        return "\n".join(chunk_xmls)

    def _generate_back(self, segments: DocumentSegments) -> str:
        """Genera el XML del <back> (referencias).

        Args:
            segments: DocumentSegments con referencias.

        Returns:
            String XML del back.
        """
        if not segments.references_raw:
            return "<back><ref-list></ref-list></back>"

        batch_size = 10
        ref_batches = [
            segments.references_raw[i:i + batch_size]
            for i in range(0, len(segments.references_raw), batch_size)
        ]

        all_refs_xml: List[str] = []
        start_idx = 1
        for batch in ref_batches:
            prompt = prompts.get_reference_batch_prompt(batch, start_idx)
            response = invocar_llm(
                prompt=prompt,
                model_version=self.model,
                api_key=self.api_key,
                provider_id=self.provider_id,
            )
            if response.get('returncode') != 0:
                raise RuntimeError(
                    f"Error en batch de referencias: "
                    f"{response.get('stderr', 'unknown')}"
                )
            all_refs_xml.append(response.get('stdout', '').strip())
            start_idx += len(batch)

        refs_content = "\n".join(all_refs_xml)
        return f"<back><ref-list>\n{refs_content}\n</ref-list></back>"

    @staticmethod
    def _assemble_xml(
        front_xml: str,
        body_sections_xml: List[str],
        back_xml: str,
    ) -> str:
        """Ensambla las partes en un XML JATS completo.

        Args:
            front_xml: XML del front.
            body_sections_xml: Lista de XMLs de secciones.
            back_xml: XML del back.

        Returns:
            XML completo.
        """
        from . import config_store
        version = config_store.get_jats_version()
        dtd_filename = f"JATS-journalpublishing{version.replace('.', '-')}-mathml3.dtd"

        body_content = "\n".join(body_sections_xml)
        xml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD with MathML3 v{version} 2024//EN" "{dtd_filename}">',
            f'<article xmlns:xlink="http://www.w3.org/1999/xlink" dtd-version="{version}" article-type="research-article" xml:lang="es">',
            front_xml,
            "<body>",
            body_content,
            "</body>",
            back_xml,
            "</article>",
        ]
        return "\n".join(xml_parts)

    def _run_ai_verification(
        self,
        segments: DocumentSegments,
        xml_string: str,
    ) -> Dict[str, VerificationResult]:
        """Ejecuta verificación semántica IA por secciones.

        Args:
            segments: Segmentos originales.
            xml_string: XML ensamblado.

        Returns:
            Dict de resultados por sección.
        """
        # Extraer texto plano del XML por secciones
        xml_sections: Dict[str, str] = {}
        try:
            from lxml import etree
            parser = etree.XMLParser(recover=True)
            root = etree.fromstring(xml_string.encode('utf-8'), parser)
            body = root.find('.//body')
            if body is not None:
                for sec in body.findall('sec'):
                    title_el = sec.find('title')
                    title = (
                        title_el.text
                        if title_el is not None and title_el.text
                        else "Sin título"
                    )
                    text = "".join(sec.itertext())
                    xml_sections[title] = text
        except Exception:
            pass

        # Mapear secciones originales a texto plano
        original_sections: Dict[str, str] = {}
        for sec in segments.body_sections:
            original_sections[sec.title] = sec.content

        return self.ai_verifier.verify_all_sections(
            original_sections=original_sections,
            xml_sections=xml_sections,
            api_key=self.api_key,
        )
