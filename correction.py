# -*- coding: utf-8 -*-

"""Módulo para la corrección asistida por IA de archivos XML JATS.

Este módulo permite enviar un XML inválido junto con sus errores de validación
y feedback del usuario a un modelo de lenguaje (Gemini) para obtener una versión corregida.
"""

import subprocess
import sys
import time
from typing import Dict, Any, List

from transformer import invocar_gemini_cli, WORKSPACE_ROOT

def construir_prompt_correccion(
    xml_content: str, 
    validation_errors: List[str], 
    user_feedback: str = ""
) -> str:
    """Construye el prompt para solicitar correcciones al modelo.

    Args:
        xml_content (str): El contenido XML actual (posiblemente inválido).
        validation_errors (List[str]): Lista de errores reportados por el validador DTD.
        user_feedback (str, optional): Instrucciones adicionales del usuario.

    Returns:
        str: El prompt completo.
    """
    errores_str = "\n".join(f"- {err}" for err in validation_errors)
    
    extra_instructions = ""
    if user_feedback:
        extra_instructions = f"""
    INSTRUCCIONES ADICIONALES DEL USUARIO:
    "{user_feedback}"
    Asegúrate de atender específicamente solicitud del usuario.
        """

    prompt = f"""
    Actúa como un experto en depuración de XML JATS 1.3 interactivo.

    SITUACIÓN:
    Tengo un archivo XML que NO valida contra el DTD JATS 1.3 o tiene datos incompletos.

    ERRORES DE VALIDACIÓN REPORTADOS O PREGUNTA DEL USUARIO:
    {errores_str}

    {extra_instructions}

    TAREA:
    1. Analiza el problema.
    2. SI TIENES INFORMACIÓN SUFICIENTE para corregir:
       - Genera el XML corregido completo.
       - Envuelve el XML en un bloque de código markdown: ```xml ... ```.
    3. SI FALTA INFORMACIÓN CRÍTICA (por ejemplo, correos de autores, fechas exactas, afiliaciones requeridas por DTD):
       - NO inventes datos fake si no son obvios.
       - PREGUNTA al usuario qué dato falta.
       - Responde con texto plano (sin bloques de código xml) explicando qué necesitas.

    ENTRADA XML ACTUAL:
    ```xml
    {xml_content}
    ```

    TU RESPUESTA:
    """
    return prompt

def corregir_xml(
    xml_content: str, 
    validation_errors: List[str], 
    user_feedback: str = ""
) -> Dict[str, Any]:
    """Orquesta el proceso de corrección de XML usando Gemini.

    Args:
        xml_content (str): XML original.
        validation_errors (List[str]): Errores de validación.
        user_feedback (str): Feedback opcional.

    Returns:
        Dict[str, Any]: Resultado similar a invocar_gemini_cli (stdout, stderr, etc.).
    """
    prompt = construir_prompt_correccion(xml_content, validation_errors, user_feedback)
    return invocar_gemini_cli(prompt)
