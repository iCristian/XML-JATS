# -*- coding: utf-8 -*-

"""Verificador semántico de integridad usando modelos de lenguaje.

Compara texto original vs. texto extraído del XML a nivel semántico,
detectando omisiones, parafraseos, resúmenes y cambios numéricos
que un verificador programático (hash) no captura.

Typical usage::

    from modules.ai_integrity_verifier import AiIntegrityVerifier

    verifier = AiIntegrityVerifier(provider_id="gemini", model="gemini-2.5-flash")
    result = verifier.verify_section(original_text, xml_plain_text, api_key="...")
    print(result.is_complete, result.problems)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .prompts import get_integrity_verification_prompt
from .transformer import invocar_llm


# ─── Estructuras de datos ────────────────────────────────────────

@dataclass
class VerificationProblem:
    """Problema detectado en una sección."""

    type: str  # "OMISION", "PARAFRASEO", "DATO_NUMERICO", "TRUNCAMIENTO"
    description: str
    original_fragment: str = ""
    xml_fragment: str = ""


@dataclass
class VerificationResult:
    """Resultado de la verificación IA de una sección."""

    is_complete: bool
    paragraphs_reviewed: int = 0
    paragraphs_with_problems: int = 0
    problems: List[VerificationProblem] = field(default_factory=list)
    raw_response: str = ""
    error: str = ""


# ─── Clase principal ─────────────────────────────────────────────

class AiIntegrityVerifier:
    """Orquesta la verificación semántica con un modelo de lenguaje."""

    def __init__(
        self,
        provider_id: str = "gemini",
        model: str = "gemini-2.5-flash",
    ) -> None:
        """Inicializa el verificador.

        Args:
            provider_id: ID del proveedor LLM ('gemini', 'openai', etc.).
            model: Nombre del modelo a usar.
        """
        self.provider_id = provider_id
        self.model = model

    def verify_section(
        self,
        original_text: str,
        xml_plain_text: str,
        api_key: Optional[str] = None,
    ) -> VerificationResult:
        """Verifica una sección comparando original vs. XML plano.

        Args:
            original_text: Texto original de la sección.
            xml_plain_text: Texto extraído del XML (sin etiquetas).
            api_key: Clave de API del proveedor.

        Returns:
            VerificationResult con problemas detectados.
        """
        if not original_text or not original_text.strip():
            return VerificationResult(
                is_complete=True,
                paragraphs_reviewed=0,
                paragraphs_with_problems=0,
            )

        prompt = get_integrity_verification_prompt(original_text, xml_plain_text)

        try:
            response = invocar_llm(
                prompt=prompt,
                model_version=self.model,
                api_key=api_key or "",
                provider_id=self.provider_id,
            )
        except Exception as e:
            return VerificationResult(
                is_complete=False,
                error=f"Error llamando al LLM: {str(e)}",
            )

        if response.get('returncode') != 0:
            return VerificationResult(
                is_complete=False,
                error=response.get('stderr', 'Error desconocido en LLM'),
            )

        raw = response.get('stdout', '')
        return self._parse_verification_response(raw)

    @staticmethod
    def _parse_verification_response(raw_text: str) -> VerificationResult:
        """Parsea la respuesta del LLM en formato JSON.

        Args:
            raw_text: Texto crudo devuelto por el modelo.

        Returns:
            VerificationResult estructurado.
        """
        result = VerificationResult(
            is_complete=False,
            raw_response=raw_text,
        )

        if not raw_text or not raw_text.strip():
            result.error = "Respuesta vacía del modelo"
            return result

        # Extraer JSON de la respuesta
        json_text = raw_text.strip()
        # Quitar bloques markdown si existen
        md_match = re.search(r'```json\s*(.*?)\s*```', json_text, re.DOTALL)
        if md_match:
            json_text = md_match.group(1).strip()
        else:
            # Buscar primer '{' y último '}'
            first = json_text.find('{')
            last = json_text.rfind('}')
            if first != -1 and last != -1 and last > first:
                json_text = json_text[first:last + 1]

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            result.error = f"No se pudo parsear JSON: {e}"
            return result

        result.is_complete = bool(data.get('integridad_completa', False))
        result.paragraphs_reviewed = int(data.get('párrafos_revisados', 0))
        result.paragraphs_with_problems = int(
            data.get('párrafos_con_problemas', 0)
        )

        problems = data.get('problemas', [])
        if isinstance(problems, list):
            for p in problems:
                if isinstance(p, dict):
                    result.problems.append(VerificationProblem(
                        type=p.get('tipo', 'DESCONOCIDO'),
                        description=p.get('descripcion', ''),
                        original_fragment=p.get('fragmento_original', ''),
                        xml_fragment=p.get('fragmento_xml', ''),
                    ))

        return result

    def verify_all_sections(
        self,
        original_sections: Dict[str, str],
        xml_sections: Dict[str, str],
        api_key: Optional[str] = None,
    ) -> Dict[str, VerificationResult]:
        """Verifica múltiples secciones en secuencia.

        Args:
            original_sections: Dict {nombre_sección: texto_original}.
            xml_sections: Dict {nombre_sección: texto_xml_plano}.
            api_key: Clave de API.

        Returns:
            Dict {nombre_sección: VerificationResult}.
        """
        results: Dict[str, VerificationResult] = {}
        for title, orig_text in original_sections.items():
            xml_text = xml_sections.get(title, "")
            results[title] = self.verify_section(
                original_text=orig_text,
                xml_plain_text=xml_text,
                api_key=api_key,
            )
        return results
