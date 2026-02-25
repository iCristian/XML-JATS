# -*- coding: utf-8 -*-

"""Módulo para la corrección asistida por IA de archivos XML JATS.

Este módulo permite enviar un XML inválido junto con sus errores de validación
y feedback del usuario a un modelo de lenguaje (Gemini) para obtener una versión corregida.
"""


from typing import Dict, Any, List

from .transformer import invocar_gemini_cli, WORKSPACE_ROOT
from . import prompts

def analizar_errores_inicial(
    xml_content: str, 
    validation_errors: List[str],
    model_version: str = "gemini-2.5-flash",
    api_key: str = None
) -> Dict[str, Any]:
    """Realiza el análisis inicial de errores para decidir si preguntar o corregir."""
    prompt = prompts.get_correction_analysis_prompt(xml_content, validation_errors)
    return invocar_gemini_cli(prompt, model_version=model_version, api_key=api_key)

def corregir_xml(
    xml_content: str, 
    validation_errors: List[str], 
    user_feedback: str = "",
    model_version: str = "gemini-2.5-flash",
    api_key: str = None
) -> Dict[str, Any]:
    """Orquesta el proceso de corrección de XML usando Gemini."""
    prompt = prompts.get_interactive_correction_prompt(xml_content, validation_errors, user_feedback)
    return invocar_gemini_cli(prompt, model_version=model_version, api_key=api_key)
