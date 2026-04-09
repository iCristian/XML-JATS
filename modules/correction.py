# -*- coding: utf-8 -*-

"""Módulo para la corrección asistida por IA de archivos XML JATS.

Este módulo permite enviar un XML inválido junto con sus errores de validación
y feedback del usuario a un modelo de lenguaje (Gemini) para obtener una versión corregida.
"""


from typing import Any, Dict, List

from . import prompts
from .transformer import WORKSPACE_ROOT, invocar_gemini_cli, invocar_llm


def analizar_errores_inicial(
    xml_content: str, 
    validation_errors: List[str],
    model_version: str = "gemini-2.5-flash",
    api_key: str = None,
    provider_id: str = "gemini",
    **_kwargs,
) -> Dict[str, Any]:
    """Realiza el análisis inicial de errores para decidir si preguntar o corregir."""
    prompt = prompts.get_correction_analysis_prompt(xml_content, validation_errors)
    return invocar_llm(prompt, model_version=model_version, api_key=api_key, provider_id=provider_id)

def corregir_xml(
    xml_content: str, 
    validation_errors: List[str], 
    user_feedback: str = "",
    model_version: str = "gemini-2.5-flash",
    api_key: str = None,
    provider_id: str = "gemini",
    **_kwargs,
) -> Dict[str, Any]:
    """Orquesta el proceso de corrección de XML usando el LLM seleccionado."""
    prompt = prompts.get_interactive_correction_prompt(xml_content, validation_errors, user_feedback)
    return invocar_llm(prompt, model_version=model_version, api_key=api_key, provider_id=provider_id)

def generar_plan_correccion(validation_errors: List[str],
                            model_version: str = "gemini-2.5-flash", 
                            api_key: str = "",
                            provider_id: str = "gemini") -> Dict[str, Any]:
    """Genera un plan de acción sugerido basado en los errores de validación, sin retornar XML.

    Args:
        validation_errors: Lista de cadenas de error DTD.
        model_version: Modelo a usar.
        api_key: Puede ser vacía si el LLM la resuelve.
        provider_id: Proveedor de LLM.

    Returns:
        Dict con 'stdout' (el plan redactado), 'token_usage', etc.
    """
    prompt = prompts.get_correction_plan_prompt(validation_errors)
    return invocar_llm(prompt, model_version=model_version, api_key=api_key, provider_id=provider_id)
