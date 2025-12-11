# -*- coding: utf-8 -*-

"""Módulo para la corrección asistida por IA de archivos XML JATS.

Este módulo permite enviar un XML inválido junto con sus errores de validación
y feedback del usuario a un modelo de lenguaje (Gemini) para obtener una versión corregida.
"""

import subprocess
import sys
import time
from typing import Dict, Any, List

from .transformer import invocar_gemini_cli, WORKSPACE_ROOT

def construir_prompt_analisis_inicial(xml_content: str, validation_errors: List[str]) -> str:
    """Construye el prompt para el análisis inicial de errores."""
    errores_str = "\n".join(f"- {err}" for err in validation_errors)
    
    prompt = f"""
    Actúa como un validador experto de XML JATS 1.3.

    FINALIDAD:
    Determinar si los errores de validación se deben a DATOS FALTANTES (que requieren input del usuario) o a ERRORES ESTRUCTURALES/SINTÁCTICOS (que puedes corregir tú mismo).

    ERRORES REPORTADOS:
    {errores_str}

    XML ACTUAL:
    ```xml
    {xml_content}
    ```

    INSTRUCCIONES:
    1. Si detectas que FALTA INFORMACIÓN ESPECÍFICA necesaria para validar (ej: falta apellido del autor, falta año de publicación, falta título de la revista, faltan referencias), TU RESPUESTA DEBE SER UNA PREGUNTA CLARA AL USUARIO pidiendo esos datos exacta y amablemente. NO GENERES XML.

    2. Si los errores son puramente TÉCNICOS o ESTRUCTURALES (ej: tag mal anidado, atributo inválido, orden incorrecto de elementos conocidos) y NO necesitas información nueva:
       - Genera el XML corregido completo.
       - Envuelve el XML en un bloque: ```xml ... ```
       - Agrega una breve nota fuera del bloque explicando qué arreglaste.

    PRIORIDAD: Si hay mezcla de errores, PRIORIZA PREGUNTAR POR LOS DATOS FALTANTES antes de intentar corregir la estructura. No inventes datos.

    TU RESPUESTA:
    """
    return prompt

def analizar_errores_inicial(
    xml_content: str, 
    validation_errors: List[str]
) -> Dict[str, Any]:
    """Realiza el análisis inicial de errores para decidir si preguntar o corregir."""
    prompt = construir_prompt_analisis_inicial(xml_content, validation_errors)
    return invocar_gemini_cli(prompt)

def construir_prompt_correccion(
    xml_content: str, 
    validation_errors: List[str], 
    user_feedback: str = ""
) -> str:
    """Construye el prompt para solicitar correcciones al modelo (flujo normal)."""
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
    2. SI TIENES INFORMACIÓN SUFICIENTE para corregir con lo que el usuario ha dado:
       - Genera el XML corregido completo.
       - Envuelve el XML en un bloque de código markdown: ```xml ... ```.
    3. SI AÚN FALTA INFORMACIÓN CRÍTICA:
       - PREGUNTA nuevamente.
       
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
    """Orquesta el proceso de corrección de XML usando Gemini."""
    prompt = construir_prompt_correccion(xml_content, validation_errors, user_feedback)
    return invocar_gemini_cli(prompt)
