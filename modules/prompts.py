# -*- coding: utf-8 -*-

"""Módulo centralizado para la gestión de Prompts de IA.

Contiene las plantillas de instrucciones utilizadas por el modelo de lenguaje
(Gemini) para las distintas fases del procesamiento de documentos:
extracción de metadatos, generación JATS XML y corrección de validaciones.
"""

from typing import Dict, Any, List, Optional


def get_metadata_prompt(text_snippet: str) -> str:
    """Prompt para estructurar metadatos a partir de un fragmento de texto."""
    return f"""
    Actúa como un bibliotecario experto. Analiza el siguiente texto inicial de un artículo científico y extrae los metadatos en formato JSON estricto.

    TEXTO:
    {text_snippet[:3000]} 

    TIPOS DE DATOS REQUERIDOS (Devuelve null si no lo encuentras):
    - article_title (string)
    - journal_title (string)
    - publication_date (string, formato YYYY-MM-DD o YYYY)
    - roi (string, DOI del artículo)
    - authors (lista de objetos: {{ "given_names": "", "surname": "", "email": "", "aff_id": "1" }})
    - affiliations (lista de objetos: {{ "id": "1", "institution": "", "country": "" }})
    - abstract (string)
    - keywords (lista de strings)

    RESPUESTA SOLO JSON:
    """


def get_generation_prompt(texto_articulo: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """Prompt avanzado para la generación de la estructura inicial JATS XML."""
    
    metadata_instructions = ""
    if metadata:
        metadata_instructions = f"""
    INFORMACIÓN DE METADATOS OBLIGATORIA (ÚSALA TAL CUAL):
    - Título del Artículo: {metadata.get('article_title', 'Determinar del texto')}
    - Revista: {metadata.get('journal_title', 'Determinar del texto')}
    - Fecha de Publicación: {metadata.get('publication_date', 'Determinar del texto')}
    - DOI: {metadata.get('doi', 'Determinar del texto')}
    - Autores: {metadata.get('authors', [])}
    - Afiliaciones: {metadata.get('affiliations', [])}
    - Resumen: {metadata.get('abstract', 'Determinar del texto')}
    - Palabras Clave: {metadata.get('keywords', 'Determinar del texto')}
    
    Usa estos datos EXACTOS en la sección <front> del XML.
        """

    return f"""
    Actúa como un maquetador XML JATS (Journal Article Tag Suite), versión 1.4 (ANSI/NISO Z39.96-2024), para SciELO.

    CONTEXTO PROFESIONAL:
    Este es un trabajo de maquetación editorial. El texto del artículo ya pasó por revisión por pares y corrección de estilo profesional. Tu tarea es aplicar el marcado XML JATS estructural al contenido proporcionado.
    
    PRINCIPIO DE MAQUETACIÓN:
    - Un maquetador NO edita, NO resume, NO parafrasea el contenido del autor.
    - Un maquetador aplica formato y estructura al texto existente.
    - El contenido textual dentro de cada etiqueta XML debe ser el contenido original del artículo.
    - NO condenses párrafos ni secciones. Cada párrafo del original = un <p> en el XML.
    - NO omitas secciones, tablas, datos ni referencias.
    
    {metadata_instructions}

    INSTRUCCIONES DE ETIQUETADO:
    1.  **Estructura General:** Raíz `<article>` con `xmlns:xlink="http://www.w3.org/1999/xlink"` y `xml:lang="es"`. Debe contener `<front>`, `<body>`, y `<back>`.
    2.  **Sección <front>:**
        *   **OBLIGATORIO - Nodos vacíos:** Debes incluir SIEMPRE las siguientes etiquetas en sus posiciones correctas, incluso si la información no está en el texto original (déjalas completamente vacías si no hay datos): `<trans-title>`, `<journal-title>`, `<publisher-name>`, `<issn>`, `<volume>`, `<issue>`, `<fpage>`, `<lpage>`, `<year>`, `<abstract>`, `<kwd-group>`.
        *   Incluye `<article-title>` y `<article-id pub-id-type="doi">`.
        *   **IMPORTANTE - Orden de elementos en <contrib>:** Dentro de cada `<contrib contrib-type="author">`, sigue ESTRICTAMENTE este orden:
            1.  `<contrib-id contrib-id-type="orcid">` (si existe ORCID).
            2.  `<name>` (con `<surname>` y `<given-names>`).
            3.  `<xref ref-type="aff" rid="affX">` (referencias a afiliaciones).
            4.  `<xref ref-type="corresp" rid="cor1">` (si es autor de correspondencia).
            5.  `<email>` (correo electrónico).
        *   Crea un `<aff>` por cada filiación con `id` (`aff1`, `aff2`, ...) y `<label>` numérico.
        *   Marca correspondencia con `corresp="yes"` y `<author-notes><corresp id="cor1"><email>...</email></corresp></author-notes>`.
        *   El `<abstract>` debe contener el resumen completo del original.
        *   `<kwd-group>` debe incluir todas las palabras clave.
    3.  **Sección <body>:** 
        *   Usa `<sec>` para secciones con `<title>`. Cada párrafo va en `<p>`.
        *   Mantén la estructura y extensión original de cada sección y párrafo.
        *   **Citas:** Etiqueta las citas bibliográficas con `<xref ref-type="bibr" rid="refN">`.
        *   **Placeholders de imágenes:** `[IMAGEN-PLACEHOLDER file="..." caption="..."]` →
            `<fig id="fN"><label>Figura N</label><caption><p>caption</p></caption><graphic mimetype="image" xlink:href="file"/></fig>`
        *   **Placeholders de tablas:** `[TABLA-PLACEHOLDER caption="..." content="..."]` →
            `<table-wrap>` con `<table>`, `<thead>`, `<tbody>`. Incluir TODAS las filas y columnas.
    4.  **Sección <back>:** `<ref-list>` con `<ref>` y `<element-citation>` para cada referencia bibliográfica. Incluir TODAS las referencias del texto.
        *   Cada `<ref>` debe tener un `<label>` con el número de referencia.
        *   **IMPORTANTE:** El número de referencia debe ir SOLO en el `<label>`. NO repetir el número dentro de `<element-citation>`. Ejemplo correcto:
            `<ref id="ref1"><label>1</label><element-citation>Aldrete MG, Navarro C...</element-citation></ref>`
        *   Separar los componentes de la cita en sub-elementos: `<person-group>`, `<article-title>`, `<source>`, `<year>`, `<volume>`, `<fpage>`, `<lpage>`, `<pub-id pub-id-type="doi">`.
    5.  **Completitud:** Todas las secciones, tablas, referencias y anexos deben estar presentes.
    6.  **Reglas:** XML bien formado. Solo código XML en la salida. Caracteres especiales codificados.

    TEXTO DEL ARTÍCULO A ETIQUETAR:
    ---
    {texto_articulo}
    ---

    RECORDATORIO: Genera el XML JATS completo desde `<article>` hasta `</article>`. Mantén la extensión y contenido original de cada sección. No omitas contenido.
    """


def get_correction_analysis_prompt(xml_content: str, validation_errors: List[str]) -> str:
    """Prompt para analizar los errores XML e intentar una autocorrección profunda."""
    errores_str = "\n".join(f"- {err}" for err in validation_errors)
    
    return f"""
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

    INSTRUCCIONES CRÍTICAS (DE CUMPLIMIENTO OBLIGATORIO):
    1. TU RESPUESTA DEBE INCLUIR EL CÓDIGO XML CORREGIDO COMPLETO. 
       - Está ESTRICTAMENTE PROHIBIDO responder únicamente con una explicación del error.
       - INCLUSO SI el "XML Actual" parece un mensaje de error, un texto truncado o basura, NO TE QUEJES NI PIDAS AL USUARIO EL "XML REAL". Asume que eso es todo lo que hay y RECONSTRUYE un documento XML válido desde cero utilizando la información disponible.
       - Si detectas que falta un tag de apertura como `<article>`, u otro error de sintaxis ("Start tag expected"), AGREGA los tags faltantes y devuelve el documento completo y estructurado.
       - Siempre debes comenzar y terminar con la estructura raíz JATS válida (desde `<article>` hasta `</article>`).
       
    2. PRIORIDAD MÁXIMA: Corregir errores TÉCNICOS y ESTRUCTURALES directamente:
       - Tags mal anidados, atributos inválidos, orden incorrecto de elementos.
       - Elementos faltantes requeridos por el DTD (ej: `<ref-list>` vacío si no hay refs, `<body>` incompleto).
       - Secciones truncadas que terminan abruptamente (cierra los tags correctamente).
       
    3. Si la corrección requiere inventar contenido real que NO existe en el XML (ej: el nombre de un autor, una fecha que realmente falta), SOLO ENTONCES agrega un comentario XML y pregunta al usuario.

    4. Envuelve el XML en un bloque: ```xml ... ```. 
       Agrega una breve nota fuera del bloque explicando qué arreglaste, pero JAMÁS omitas el bloque de código XML.
       NO omitas secciones ni contenido existente. Reproduce TODO el contenido textual IDÉNTICO con las correcciones estructurales.

    IMPORTANTE: 
    - NO pidas al usuario información que ya está en el XML.
    - NO pidas al usuario "el XML original" o "el XML completo". Trabaja y repara el texto provisto.
    - NO modifiques, resumas ni parafrasees el texto del artículo.
    - ¡ESTÁS OBLIGADO A DEVOLVER EL XML CORREGIDO!

    TU RESPUESTA:
    """


def get_interactive_correction_prompt(xml_content: str, validation_errors: List[str], user_feedback: str = "") -> str:
    """Prompt para orquestar la corrección XML iterativa asistida por feedback humano."""
    errores_str = "\n".join(f"- {err}" for err in validation_errors)
    
    extra_instructions = ""
    if user_feedback:
        extra_instructions = f"""
    INSTRUCCIONES ADICIONALES DEL USUARIO:
    "{user_feedback}"
    Asegúrate de atender específicamente solicitud del usuario.
        """

    return f"""
    Actúa como un experto en depuración de XML JATS 1.3 interactivo.

    CONTEXTO: Este es un trabajo de maquetación editorial. El contenido textual del artículo ya fue aprobado.
    Solo debes corregir la ESTRUCTURA XML (tags, atributos, orden de elementos), no el contenido textual.

    SITUACIÓN:
    Tengo un archivo XML que NO valida contra el DTD JATS 1.3 o tiene datos incompletos.

    ERRORES DE VALIDACIÓN REPORTADOS O PREGUNTA DEL USUARIO:
    {errores_str}

    {extra_instructions}

    TAREA CRÍTICA (DE CUMPLIMIENTO OBLIGATORIO):
    1. Analiza el problema.
    2. SI TIENES INFORMACIÓN SUFICIENTE para corregir con lo que el usuario ha dado:
       - Genera el XML corregido COMPLETO (desde `<article>` hasta `</article>`).
       - INCLUYE TODAS las secciones, tablas, referencias y contenido existente. NO omitas ni recortes nada.
       - Envuelve el XML en un bloque de código markdown: ```xml ... ```.
       - Agrega una breve nota FUERA del bloque XML explicando los cambios.
    3. SI AÚN FALTA INFORMACIÓN CRÍTICA o el XML de entrada de por sí no parece XML válido (ej: está truncado o malformado desde la raíz):
       - ¡NO PIDAS AL USUARIO QUE TE ENVÍE EL "XML VERDADERO"!
       - Asume que el bloque corrupto que recibes es todo lo que existe y RECONSTRUYE un cascarón válido de XML envuelto en ```xml ... ``` (por ejemplo, asegurando que existan `<article>` y `</article>`), infiriendo lo que puedas.
       
    IMPORTANTE: 
    - NO generes un documento a medias. El resultado principal que procesará el sistema es tu bloque ```xml ... ```. 
    - Está PROHIBIDO responder únicamente con explicaciones quejándote del input recibido. Siempre devuelve el código reparado.
       
    ENTRADA XML ACTUAL:
    ```xml
    {xml_content}
    ```

    TU RESPUESTA:
    """
