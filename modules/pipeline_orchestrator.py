# -*- coding: utf-8 -*-

"""Orquestador del pipeline por fases para generación JATS XML.

Coordina la segmentación, generación por chunks, ensamblaje DOM,
validación y verificación del XML JATS. Diseñado para funcionar
con modelos grandes y pequeños mediante degradación progresiva
de complejidad de prompts (L1→L2→L3→L4).

Typical usage::

    from modules.pipeline_orchestrator import PipelineOrchestrator

    orchestrator = PipelineOrchestrator(provider_id="gemini", model="gemini-2.5-flash")
    result = orchestrator.run(docx_path="articulo.docx", api_key="...")
    print(result.xml_string)
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from lxml import etree

from . import prompts
from .ai_integrity_verifier import AiIntegrityVerifier, VerificationResult
from .chunk_manager import ChunkManager
from .document_segmenter import BodySection, DocumentSegmenter, DocumentSegments
from .integrity_checker import IntegrityChecker, IntegrityReport
from .llm_provider import estimate_context_window, get_model_tier
from .metadata_processor import MetadataExtractor
from .pipeline_sanitizer import PipelineSanitizer
from .pipeline_temp_manager import PipelineTempManager
from .transformer import invocar_llm, validar_jats_xml


# ─── Estructuras de datos ────────────────────────────────────────

@dataclass
class PipelineStage:
    """Representa el estado de una fase del pipeline."""

    name: str
    status: str  # "pending", "running", "success", "failed", "warning"
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
    temp_dir: Optional[str] = None


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
        parallel: bool = False,
        max_workers: int = 4,
        use_light_prompts: bool = False,
        enable_ai_verification: bool = True,
        temp_manager: Optional[PipelineTempManager] = None,
    ) -> None:
        """Inicializa el orquestador.

        Args:
            provider_id: ID del proveedor LLM.
            model: Modelo específico.
            api_key: Clave de API.
            max_input_tokens: Ventana de contexto del modelo.
            max_output_tokens: Límite de tokens de salida del modelo.
            parallel: Si es True, procesa body sections en paralelo.
            max_workers: Número máximo de hilos para paralelización.
            use_light_prompts: Usar prompts reducidos para modelos pequeños.
            enable_ai_verification: Ejecutar verificación semántica con LLM.
            temp_manager: Instancia de PipelineTempManager para persistencia.
        """
        self.provider_id = provider_id
        self.model = model
        self.api_key = api_key or ""
        self.parallel = parallel
        self.max_workers = max_workers
        self.use_light_prompts = use_light_prompts
        self.enable_ai_verification = enable_ai_verification
        self.temp_manager = temp_manager or PipelineTempManager()
        self.sanitizer = PipelineSanitizer()

        # Determinar nivel de degradación inicial según tier del modelo
        self.model_tier = get_model_tier(model)
        if self.model_tier == "small":
            self.degradation_level = 2  # L2 por defecto para small
        elif self.model_tier == "medium":
            self.degradation_level = 1  # L1 por defecto para medium
        else:
            self.degradation_level = 0  # L0 = prompts normales

        # Autodetección de context window si no se especificó explícitamente
        if max_input_tokens == 8192:  # Valor por defecto
            detected = estimate_context_window(provider_id, model, api_key or "")
            max_input_tokens = min(detected, max_input_tokens)

        self.chunk_manager = ChunkManager(
            max_input_tokens=max_input_tokens,
            max_output_tokens=max_output_tokens,
        )
        self.segmenter = DocumentSegmenter()
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

        # Guardar configuración
        self.temp_manager.save_pipeline_config({
            "provider_id": self.provider_id,
            "model": self.model,
            "tier": self.model_tier,
            "degradation_level": self.degradation_level,
            "max_input_tokens": self.chunk_manager.config.max_input_tokens,
            "max_output_tokens": self.chunk_manager.config.max_output_tokens,
            "parallel": self.parallel,
            "use_light_prompts": self.use_light_prompts,
        })

        # ── FASE 0: Segmentación ─────────────────────────────────
        self._add_stage("Segmentación", "running")
        try:
            from .transformer import extraer_contenido_estructurado
            raw_text = extraer_contenido_estructurado(docx_path)
            if not raw_text:
                self._add_stage("Segmentación", "failed", "No se pudo extraer texto")
                result.error = "Extracción de texto fallida"
                return result
            self.temp_manager.save_raw_text(raw_text)
            segments = self.segmenter.segment(raw_text)
            self.temp_manager.save_segments(self._segments_to_dict(segments))
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
            front_sanitized = self.sanitizer.sanitize_front(front_xml)
            self.temp_manager.save_output("front", front_xml)
            self.temp_manager.save_sanitized("front", front_sanitized)
            front_xml = front_sanitized
            self._add_stage("Front", "success")
        except Exception as e:
            self._add_stage("Front", "failed", str(e))
            result.error = f"Error generando front: {e}"
            return result

        # ── FASE 2: Body Sections ────────────────────────────────
        self._add_stage("Body", "running")
        body_sections_xml: List[str] = []
        body_errors: List[str] = []
        try:
            if self.parallel and len(segments.body_sections) > 1 and self.model_tier != "small":
                # Paralelización solo para modelos medium/large
                section_results: Dict[int, str] = {}
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = {
                        executor.submit(
                            self._generate_body_section, sec, metadata
                        ): idx
                        for idx, sec in enumerate(segments.body_sections)
                    }
                    for future in as_completed(futures):
                        idx = futures[future]
                        try:
                            section_results[idx] = future.result()
                        except Exception as exc:
                            sec_title = segments.body_sections[idx].title
                            body_errors.append(f"'{sec_title}': {exc}")
                            section_results[idx] = self.sanitizer.create_placeholder_section(
                                sec_title, str(exc)
                            )
                # Reconstruir en orden
                body_sections_xml = [
                    section_results[i] for i in range(len(segments.body_sections))
                ]
            else:
                # Modo secuencial (default, recomendado para modelos pequeños)
                for sec in segments.body_sections:
                    try:
                        sec_xml = self._generate_body_section(sec, metadata)
                        body_sections_xml.append(sec_xml)
                    except Exception as exc:
                        body_errors.append(f"'{sec.title}': {exc}")
                        body_sections_xml.append(
                            self.sanitizer.create_placeholder_section(sec.title, str(exc))
                        )

            if body_errors:
                self._add_stage("Body", "warning", f"{len(body_errors)} sección(es) con errores")
            else:
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
            back_sanitized = self.sanitizer.sanitize_back(back_xml)
            self.temp_manager.save_output("back", back_xml)
            self.temp_manager.save_sanitized("back", back_sanitized)
            back_xml = back_sanitized
            self._add_stage("Referencias", "success")
        except Exception as e:
            self._add_stage("Referencias", "failed", str(e))
            result.error = f"Error generando back: {e}"
            return result

        # ── FASE 4: Ensamblaje DOM ───────────────────────────────
        self._add_stage("Ensamblaje DOM", "running")
        try:
            full_xml = self._assemble_xml_dom(front_xml, body_sections_xml, back_xml)
            self.temp_manager.save_assembled(full_xml)
            self._add_stage("Ensamblaje DOM", "success")
        except Exception as e:
            self._add_stage("Ensamblaje DOM", "failed", str(e))
            result.error = f"Error ensamblando XML: {e}"
            return result

        # ── FASE 5: Post-procesamiento estructural ───────────────
        self._add_stage("Post-procesamiento", "running")
        try:
            full_xml = self._postprocess_xml(full_xml)
            self.temp_manager.save_postprocessed(full_xml)
            self._add_stage("Post-procesamiento", "success")
        except Exception as e:
            self._add_stage("Post-procesamiento", "failed", str(e))
            # No abortamos: el XML ensamblado sigue siendo usable

        # ── FASE 6: Validación DTD ───────────────────────────────
        self._add_stage("Validación DTD", "running")
        try:
            is_valid, errors = validar_jats_xml(full_xml)
            result.is_valid_dtd = is_valid
            result.dtd_errors = errors
            status = "success" if is_valid else "warning"
            self._add_stage("Validación DTD", status)
        except Exception as e:
            self._add_stage("Validación DTD", "failed", str(e))

        # ── FASE 7: Integridad Programática ──────────────────────
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

        # ── FASE 8: Verificación IA (condicional) ────────────────
        if self.enable_ai_verification and self.model_tier != "small":
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
        else:
            self._add_stage("Verificación IA", "success",
                            "Omitida (modelo pequeño o desactivada)")

        result.xml_string = full_xml
        result.stages = self.stages
        result.temp_dir = str(self.temp_manager.base_dir)

        # Guardar resultado de validación
        self.temp_manager.save_validation({
            "is_valid_dtd": result.is_valid_dtd,
            "dtd_errors": result.dtd_errors,
            "integrity_complete": result.integrity_report.is_complete if result.integrity_report else False,
            "integrity_warnings": result.integrity_report.warnings if result.integrity_report else [],
        })

        return result

    # ─── Generación por fases ────────────────────────────────────

    def _generate_front(
        self,
        metadata: Dict[str, Any],
        journal_config: Dict[str, str],
    ) -> str:
        """Genera el XML del <front>."""
        prompt = prompts.get_front_prompt(metadata, journal_config)
        self.temp_manager.save_prompt("front", prompt)
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
        sec: BodySection,
        metadata: Optional[Dict[str, Any]],
    ) -> str:
        """Genera el XML de una sección del body con degradación progresiva.

        Intenta L1 → L2 → L3 → L4 según la configuración y los fallos.
        """
        chunks = self.chunk_manager.split_section(sec.content)
        chunk_xmls: List[str] = []

        for chunk in chunks:
            xml_part = self._call_llm_with_degradation(
                section_title=sec.title,
                section_text=chunk,
                metadata=metadata,
            )
            chunk_xmls.append(xml_part)

        combined = "\n".join(chunk_xmls)
        sanitized = self.sanitizer.sanitize_body_section(combined, sec.title)
        self.temp_manager.save_output(f"body_sec_{sec.order}_{sec.title}", combined)
        self.temp_manager.save_sanitized(f"body_sec_{sec.order}_{sec.title}", sanitized)
        return sanitized

    def _call_llm_with_degradation(
        self,
        section_title: str,
        section_text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Llama al LLM con degradación progresiva L1→L2→L3→L4.

        Args:
            section_title: Título de la sección.
            section_text: Texto plano del chunk.
            metadata: Metadatos para contexto.

        Returns:
            Fragmento XML generado.

        Raises:
            RuntimeError: Si se agotan todos los niveles.
        """
        levels = [
            (0, lambda: prompts.get_body_section_prompt(
                section_title=section_title,
                section_text=section_text,
                metadata=metadata,
            )),
            (1, lambda: prompts.get_body_section_prompt_light(
                section_title=section_title,
                section_text=section_text,
            )),
            (2, lambda: prompts.get_body_section_prompt_ultra_light(
                section_title=section_title,
                section_text=section_text,
            )),
            (3, lambda: prompts.get_body_section_prompt_marked(
                section_title=section_title,
                section_text=section_text,
            )),
        ]

        # Empezar desde el nivel configurado (o inferior si el usuario forzó light)
        start_level = self.degradation_level
        if self.use_light_prompts and start_level < 1:
            start_level = 1

        last_error = ""
        for level_idx, prompt_factory in levels[start_level:]:
            prompt = prompt_factory()
            response = invocar_llm(
                prompt=prompt,
                model_version=self.model,
                api_key=self.api_key,
                provider_id=self.provider_id,
            )
            if response.get('returncode') == 0:
                stdout = response.get('stdout', '').strip()
                # Nivel 3 (marked) requiere conversión manual a XML
                if level_idx == 3:
                    stdout = prompts.convert_marked_to_xml(stdout, section_title)
                return stdout
            last_error = response.get('stderr', 'unknown')

        raise RuntimeError(
            f"Error generando sección '{section_title}': {last_error} "
            f"(agotados todos los niveles de degradación)"
        )

    def _call_llm_with_fallback(
        self,
        prompt_factory: Callable[[], str],
        fallback_text: str,
        context: str = "",
        max_retries: int = 2,
    ) -> str:
        """Llama al LLM con degradación graceful por chunk halving.

        DEPRECATED: Usar _call_llm_with_degradation para body sections.
        Mantenido para compatibilidad con referencias.
        """
        current_text = fallback_text
        attempt = 0
        last_error = ""

        while attempt <= max_retries:
            prompt = prompt_factory()
            response = invocar_llm(
                prompt=prompt,
                model_version=self.model,
                api_key=self.api_key,
                provider_id=self.provider_id,
            )
            if response.get('returncode') == 0:
                return response.get('stdout', '').strip()

            error_msg = response.get('stderr', 'unknown').lower()
            last_error = response.get('stderr', 'unknown')

            size_related = any(k in error_msg for k in [
                "context", "too long", "maximum", "exceed", "overflow",
                "tokens", "length", "truncated", "oom", "out of memory",
                "timeout", "tiempo de espera",
            ])

            if not size_related or attempt >= max_retries:
                break

            halves = self.chunk_manager.halve_chunk(current_text)
            if len(halves) < 2:
                break

            # Procesar ambas mitades con prompts correctos
            results: List[str] = []
            for half in halves:
                half_response = invocar_llm(
                    prompt=prompt_factory(),
                    model_version=self.model,
                    api_key=self.api_key,
                    provider_id=self.provider_id,
                )
                if half_response.get('returncode') == 0:
                    results.append(half_response.get('stdout', '').strip())
                else:
                    results.append("")
            if all(results):
                return "\n".join(results)

            current_text = halves[0] if len(halves) > 0 else current_text
            attempt += 1

        raise RuntimeError(
            f"Error generando {context}: {last_error} "
            f"(agotados {max_retries} reintentos de degradación)"
        )

    def _generate_back(self, segments: DocumentSegments) -> str:
        """Genera el XML del <back> (referencias)."""
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
            prompt_fn = (
                prompts.get_reference_batch_prompt_light
                if self.use_light_prompts
                else prompts.get_reference_batch_prompt
            )
            prompt = prompt_fn(batch, start_idx)
            self.temp_manager.save_prompt(f"back_batch_{start_idx}", prompt)
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

    # ─── Ensamblaje DOM ──────────────────────────────────────────

    def _assemble_xml_dom(
        self,
        front_xml: str,
        body_sections_xml: List[str],
        back_xml: str,
    ) -> str:
        """Ensambla las partes en un XML JATS completo usando DOM.

        Args:
            front_xml: XML del front.
            body_sections_xml: Lista de XMLs de secciones.
            back_xml: XML del back.

        Returns:
            XML completo well-formed.
        """
        from . import config_store
        _ = config_store.get_jats_version()  # no se usa para el DOCTYPE del pipeline
        sps_version = "1.1"  # SciELO SPS 1.8 requiere JATS 1.1
        dtd_public_id = f"-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v{sps_version} 20151215//EN"
        dtd_system_id = "JATS-journalpublishing1.dtd"

        # Crear raíz
        nsmap = {
            "xlink": "http://www.w3.org/1999/xlink",
            "xml": "http://www.w3.org/XML/1998/namespace",
        }
        root = etree.Element(
            "article",
            nsmap=nsmap,
            attrib={
                "dtd-version": "1.0",
                "article-type": "research-article",
                "{http://www.w3.org/XML/1998/namespace}lang": "es",
                "specific-use": "sps-1.8",
            },
        )

        # Parsear front (buscar tag <front> específicamente)
        front_parsed = self._parse_fragment(front_xml, target_tag="front")
        if front_parsed is not None:
            root.append(front_parsed)
        else:
            # Crear front vacío mínimo
            front_el = etree.SubElement(root, "front")
            etree.SubElement(front_el, "journal-meta")
            etree.SubElement(front_el, "article-meta")

        # Crear body y añadir secciones (buscar <sec> específicamente)
        body_el = etree.SubElement(root, "body")
        for sec_xml in body_sections_xml:
            sec_parsed = self._parse_fragment(sec_xml, target_tag="sec")
            if sec_parsed is not None:
                body_el.append(sec_parsed)
            else:
                # Fallback: intentar sin target_tag
                sec_parsed = self._parse_fragment(sec_xml)
                if sec_parsed is not None:
                    body_el.append(sec_parsed)

        # Asegurar que todo contenido suelto en body esté dentro de sec
        self._ensure_body_structure(body_el)

        # Parsear back (buscar <back> específicamente)
        back_parsed = self._parse_fragment(back_xml, target_tag="back")
        if back_parsed is not None:
            root.append(back_parsed)
        else:
            back_el = etree.SubElement(root, "back")
            etree.SubElement(back_el, "ref-list")

        # Serializar
        xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>'
        doctype = (
            f'<!DOCTYPE article PUBLIC "{dtd_public_id}" '
            f'"{dtd_system_id}">'
        )
        xml_string = etree.tostring(
            root,
            encoding="unicode",
            xml_declaration=False,
            pretty_print=True,
        )
        return f"{xml_declaration}\n{doctype}\n{xml_string}"

    @staticmethod
    def _parse_fragment(xml_fragment: str, target_tag: Optional[str] = None) -> Optional[etree.Element]:
        """Parsea un fragmento XML con recover=True.

        Si target_tag se especifica, busca y devuelve ese tag específico
        (útil cuando el modelo envuelve el fragmento en <article>).

        Args:
            xml_fragment: Texto XML.
            target_tag: Tag a buscar dentro del fragmento (ej. 'front', 'sec', 'back').

        Returns:
            Elemento raíz del fragmento, o None si es irrecuperable.
        """
        if not xml_fragment or not xml_fragment.strip():
            return None

        # Si se busca un tag específico y existe en el texto, extraerlo
        if target_tag:
            pattern = rf'<{target_tag}\b[^>]*>.*?</{target_tag}>'
            match = re.search(pattern, xml_fragment, re.DOTALL | re.IGNORECASE)
            if match:
                xml_fragment = match.group(0)

        try:
            parser = etree.XMLParser(
                recover=True,
                encoding="utf-8",
                resolve_entities=False,
                no_network=True,
            )
            # Envolver para que lxml no exija un solo root
            wrapped = f"<dummy-root>{xml_fragment}</dummy-root>"
            tree = etree.fromstring(wrapped.encode("utf-8"), parser=parser)
            children = list(tree)
            if children:
                # Devolver el primer elemento significativo
                return children[0]
            return None
        except Exception:
            return None

    @staticmethod
    def _ensure_body_structure(body_el: etree.Element) -> None:
        """Asegura que todo contenido directo de <body> esté dentro de <sec>.

        Mueve <p>, <table-wrap>, <fig> sueltos a una <sec> auxiliar.

        Args:
            body_el: Elemento <body> del árbol DOM.
        """
        orphan_tags = {"p", "table-wrap", "fig", "list", "disp-quote"}
        orphans: List[etree.Element] = []

        for child in list(body_el):
            tag = child.tag if isinstance(child.tag, str) else ""
            if tag in orphan_tags:
                orphans.append(child)

        if orphans:
            # Remover del body y crear sec auxiliar
            for el in orphans:
                body_el.remove(el)
            aux_sec = etree.SubElement(body_el, "sec")
            aux_sec.set("sec-type", "supplementary-material")
            title_el = etree.SubElement(aux_sec, "title")
            title_el.text = "Material Suplementario"
            for el in orphans:
                aux_sec.append(el)

    def _postprocess_xml(self, xml_string: str) -> str:
        """Aplica correcciones estructurales programáticas al XML ensamblado.

        Args:
            xml_string: XML completo.

        Returns:
            XML corregido.
        """
        from .transformer import sanitize_generated_xml
        return sanitize_generated_xml(xml_string)

    # ─── Verificación ────────────────────────────────────────────

    def _run_ai_verification(
        self,
        segments: DocumentSegments,
        xml_string: str,
    ) -> Dict[str, VerificationResult]:
        """Ejecuta verificación semántica IA por secciones."""
        xml_sections: Dict[str, str] = {}
        try:
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

        original_sections: Dict[str, str] = {}
        for sec in segments.body_sections:
            original_sections[sec.title] = sec.content

        return self.ai_verifier.verify_all_sections(
            original_sections=original_sections,
            xml_sections=xml_sections,
            api_key=self.api_key,
        )

    # ─── Utilidades ──────────────────────────────────────────────

    @staticmethod
    def _segments_to_dict(segments: DocumentSegments) -> Dict[str, Any]:
        """Serializa DocumentSegments a dict para JSON.

        Args:
            segments: Instancia de DocumentSegments.

        Returns:
            Diccionario serializable.
        """
        return {
            "front_text": segments.front_text,
            "body_sections": [
                {
                    "title": s.title,
                    "content": s.content,
                    "order": s.order,
                }
                for s in segments.body_sections
            ],
            "tables": [
                {
                    "id": t.id,
                    "caption": t.caption,
                    "content": t.content,
                }
                for t in segments.tables
            ],
            "figures": [
                {
                    "id": f.id,
                    "caption": f.caption,
                    "file": f.file,
                }
                for f in segments.figures
            ],
            "references_raw": segments.references_raw,
        }
