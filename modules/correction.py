# -*- coding: utf-8 -*-

"""Módulo para la corrección asistida por IA de archivos XML JATS.

Este módulo permite enviar un XML inválido junto con sus errores de validación
y feedback del usuario a un modelo de lenguaje (Gemini) para obtener una versión corregida.
"""


import sys
import time
from typing import Dict, Any, List

import streamlit as st
from .transformer import invocar_gemini_cli, WORKSPACE_ROOT

def construir_prompt_analisis_inicial(xml_content: str, validation_errors: List[str]) -> str:
    """Construye el prompt para el análisis inicial de errores."""
    errores_str = "\n".join(f"- {err}" for err in validation_errors)
    
    prompt = f"""
    Actúa como un validador experto de XML JATS 1.3.

    CONTEXTO: Este es un trabajo de maquetación editorial. El contenido textual del artículo ya fue aprobado.
    Solo debes corregir la ESTRUCTURA XML (tags, atributos, orden de elementos), no el contenido textual.

    FINALIDAD:
    Analizar los errores de validación y corregir el XML. La mayoría de los errores se deben a PROBLEMAS ESTRUCTURALES o XML INCOMPLETO generado por la transformación anterior. Tu trabajo es CORREGIRLOS directamente.

    ERRORES REPORTADOS:
    {errores_str}

    XML ACTUAL:
    ```xml
    {xml_content}
    ```

    INSTRUCCIONES:
    1. PRIORIDAD MÁXIMA: Corregir errores TÉCNICOS y ESTRUCTURALES directamente:
       - Tags mal anidados, atributos inválidos, orden incorrecto de elementos.
       - Elementos faltantes requeridos por el DTD (ej: `<ref-list>` vacío si no hay refs, `<body>` incompleto).
       - Secciones truncadas que terminan abruptamente (cierra los tags correctamente).
       
    2. Si la corrección requiere inventar contenido real que NO existe en el XML (ej: el nombre de un autor, una fecha que realmente falta), SOLO ENTONCES pregunta al usuario.

    3. Genera SIEMPRE el XML corregido COMPLETO (desde `<article>` hasta `</article>`).
       - Envuelve el XML en un bloque: ```xml ... ```
       - Agrega una breve nota fuera del bloque explicando qué arreglaste.
       - NO omitas secciones ni contenido existente. Reproduce TODO el contenido textual IDÉNTICO con las correcciones estructurales.

    IMPORTANTE: 
    - NO pidas al usuario información que ya está en el XML.
    - NO modifiques, resumas ni parafrasees el texto del artículo.
    - Solo corrige TAGS y ESTRUCTURA, nunca el contenido textual.

    TU RESPUESTA:
    """
    return prompt

def analizar_errores_inicial(
    xml_content: str, 
    validation_errors: List[str]
) -> Dict[str, Any]:
    """Realiza el análisis inicial de errores para decidir si preguntar o corregir."""
    prompt = construir_prompt_analisis_inicial(xml_content, validation_errors)
    
    # Retrieve config from session state
    model_version = st.session_state.get("selected_model", "gemini-2.5-flash")
    api_key = st.session_state.get("gemini_api_key_input")
    
    return invocar_gemini_cli(prompt, model_version=model_version, api_key=api_key)

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

    CONTEXTO: Este es un trabajo de maquetación editorial. El contenido textual del artículo ya fue aprobado.
    Solo debes corregir la ESTRUCTURA XML (tags, atributos, orden de elementos), no el contenido textual.

    SITUACIÓN:
    Tengo un archivo XML que NO valida contra el DTD JATS 1.3 o tiene datos incompletos.

    ERRORES DE VALIDACIÓN REPORTADOS O PREGUNTA DEL USUARIO:
    {errores_str}

    {extra_instructions}

    TAREA:
    1. Analiza el problema.
    2. SI TIENES INFORMACIÓN SUFICIENTE para corregir con lo que el usuario ha dado:
       - Genera el XML corregido COMPLETO (desde `<article>` hasta `</article>`).
       - INCLUYE TODAS las secciones, tablas, referencias y contenido existente. NO omitas ni recortes nada.
       - Envuelve el XML en un bloque de código markdown: ```xml ... ```.
       - Agrega una breve nota FUERA del bloque XML explicando los cambios.
    3. SI AÚN FALTA INFORMACIÓN CRÍTICA:
       - PREGUNTA nuevamente, pero sé específico sobre qué datos necesitas.
       
    IMPORTANTE: NO generes un XML parcial. El resultado debe ser el documento COMPLETO corregido.
       
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
    
    # Retrieve config from session state
    model_version = st.session_state.get("selected_model", "gemini-1.5-flash")
    api_key = st.session_state.get("gemini_api_key_input")
    
    return invocar_gemini_cli(prompt, model_version=model_version, api_key=api_key)
