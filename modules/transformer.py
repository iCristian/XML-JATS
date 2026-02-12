# -*- coding: utf-8 -*-

"""Script para convertir documentos Word a JATS XML usando IA.

Este módulo orquesta la extracción de contenido de archivos .docx, la generación
de XML JATS mediante un modelo de lenguaje (Gemini), y la validación del resultado.
Cumple con las normas de documentación de Google.

Attributes:
    DTD_ZIP_URL (str): URL para descargar el DTD de JATS 1.3.
    WORKSPACE_ROOT (Path): Ruta base del espacio de trabajo actual.
    DTD_FILENAME (str): Nombre del archivo DTD local.
    IMAGE_OUTPUT_DIR (Path): Directorio para guardar imágenes extraídas.
"""

import os
import re

import sys
import time
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from docx import Document
from lxml import etree

# --- Constantes ---
DTD_ZIP_URL = "https://ftp.ncbi.nlm.nih.gov/pub/jats/publishing/1.3/JATS-Publishing-1-3-MathML3-DTD.zip"
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
# Ruta relativa al directorio de módulos donde se descargó
DTD_DIR_INTERNAL = WORKSPACE_ROOT / "modules" / "dtd" / "JATS-Publishing-1-3-MathML3-DTD"
DTD_FILENAME = "JATS-journalpublishing1-3-mathml3.dtd"
DTD_LOCAL_FILE = DTD_DIR_INTERNAL / DTD_FILENAME
IMAGE_OUTPUT_DIR = WORKSPACE_ROOT / "imagenes_extraidas"


def validar_jats_xml(xml_content: str) -> Tuple[bool, List[str]]:
    """
    Valida el contenido XML contra el DTD JATS 1.3 local.
    """
    # Asegurar que el DTD existe (se debe haber descargado/instalado previamente)
    if not DTD_LOCAL_FILE.exists():
        return False, [f"Error crítico: No se encuentra el archivo DTD local en {DTD_LOCAL_FILE}. Por favor, reinstale los componentes o verifique la carpeta 'modules/dtd'."]

    try:
        # Parsear con lxml y validar
        parser = etree.XMLParser(dtd_validation=True, no_network=False)
        
        # Necesitamos establecer el base_url para que encuentre las entidades relativas
        # El base_url debe ser el directorio donde está el DTD
        base_url = str(DTD_DIR_INTERNAL) + os.sep
        
        # Inyectar DTD si no tiene DOCTYPE o si queremos forzar el nuestro
        # Para validación simple, cargamos el DTD explícitamente y validamos el objeto ElementTree
        dtd = etree.DTD(str(DTD_LOCAL_FILE))
        
        # Parsear XML (sin validación automática al parsear para controlar errores mejor)
        root = etree.fromstring(xml_content.encode('utf-8'))
        
        if dtd.validate(root):
            return True, []
        else:
            # Formatear errores
            errores = []
            for error in dtd.error_log:
                errores.append(f"Línea {error.line}: {error.message}")
            return False, errores

    except etree.XMLSyntaxError as e:
        return False, [f"Error de Sintaxis XML: {str(e)}"]
    except Exception as e:
        return False, [f"Error inesperado validando XML: {str(e)}"]

# Función antigua de descarga eliminada/simplificada ya que usamos bundle local
def descargar_y_extraer_dtd(url: str, extract_to: Path):
    pass

def extraer_contenido_estructurado(docx_path: str) -> Optional[str]:
    """Extrae contenido de un .docx, incluyendo texto, tablas e imágenes.

    Las imágenes se guardan en el disco y se insertan placeholders en el texto.
    Las tablas se convierten a una representación de texto con delimitadores.

    Args:
        docx_path (str): Ruta absoluta o relativa al archivo .docx.

    Returns:
        Optional[str]: El contenido extraído como texto con placeholders, o
            None si ocurre un error crítico (archivo no encontrado, etc.).
    """
    try:
        doc = Document(docx_path)
        content_parts: List[str] = []
        image_counter = 1

        # Crear directorio para imágenes si no existe
        IMAGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Usamos un iterador para procesar elementos del cuerpo (párrafos y tablas)
        for element in doc.element.body:
            if element.tag.endswith('p'):
                # Encontrar el párrafo correspondiente en el objeto doc.paragraphs
                # Nota: Este método de búsqueda por XPath puede ser lento en docs muy grandes
                # pero es necesario para mantener el orden estricto entre tablas y texto.
                para = doc.paragraphs[int(element.xpath('count(preceding-sibling::w:p)'))]
                
                # Manejo de imágenes (inline shapes)
                if 'graphicData' in para._p.xml:
                    for shape in para._p.xpath('.//pic:pic'):
                        # Extraer la relación de la imagen
                        embeds = shape.xpath('.//a:blip/@r:embed')
                        if not embeds:
                            continue
                        rel_id = embeds[0]
                        image_part = doc.part.related_parts[rel_id]
                        
                        # Guardar la imagen
                        content_type = image_part.content_type.split('/')[-1]
                        image_filename = f"imagen_{image_counter}.{content_type}"
                        image_path = IMAGE_OUTPUT_DIR / image_filename
                        with open(image_path, "wb") as f:
                            f.write(image_part.blob)
                        
                        # Añadir placeholder
                        caption = para.text.strip()
                        content_parts.append(f'\n[IMAGEN-PLACEHOLDER file="{image_filename}" caption="{caption}"]\n')
                        image_counter += 1
                else:
                    content_parts.append(para.text)

            elif element.tag.endswith('tbl'):
                table = doc.tables[int(element.xpath('count(preceding-sibling::w:tbl)'))]
                table_content: List[str] = []
                for row in table.rows:
                    row_content = [cell.text.strip().replace('\n', ' ') for cell in row.cells]
                    table_content.append(" | ".join(row_content))
                
                # Intentar usar el párrafo anterior como caption si parece serlo
                caption = ""
                if content_parts and content_parts[-1].strip():
                    caption = content_parts[-1].strip()
                    content_parts[-1] = ""  # Eliminarlo para no duplicar

                content_parts.append(f'\n[TABLA-PLACEHOLDER caption="{caption}" content="{"; ".join(table_content)}"]\n')

        return '\n'.join(content_parts)

    except FileNotFoundError:
        print(f"Error: El archivo '{docx_path}' no fue encontrado.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error al leer o procesar el archivo Word: {e}", file=sys.stderr)
        return None


def construir_prompt_avanzado(texto_articulo: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """Construye un prompt de sistema detallado para la generación de JATS XML.

    Args:
        texto_articulo (str): El texto crudo del artículo con placeholders.
        metadata (Optional[Dict[str, Any]]): Metadatos validados y corregidos por el usuario.

    Returns:
        str: El prompt completo formateado para el modelo de IA.
    """
    
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

    prompt = f"""
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
        *   Incluye `<article-title>` y, si está disponible en el texto, `<article-id pub-id-type="doi">`.
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
    return prompt


def _should_retry_gemini(stderr: str, stdout: str) -> bool:
    """Determina si se debe reintentar la llamada a Gemini basada en la salida de error.

    Args:
        stderr (str): Salida de error estándar del proceso.
        stdout (str): Salida estándar del proceso.

    Returns:
        bool: True si el error indica un problema transitorio (ej. rate limit).
    """
    combined = f"{stderr}\n{stdout}".lower()
    retry_tokens = (
        "429",
        "ratelimit",
        "resource has been exhausted",
        "resource exhausted",
        "error when talking to gemini api",
    )
    return any(token in combined for token in retry_tokens)


try:
    import google.generativeai as genai
except ImportError as _import_err:
    genai = None
    print(f"ADVERTENCIA: No se pudo importar google.generativeai: {_import_err}", file=sys.stderr)
except Exception as _import_err:
    genai = None
    print(f"ERROR INESPERADO al importar google.generativeai: {_import_err}", file=sys.stderr)

def invocar_gemini_cli(prompt: str, max_attempts: int = 3, base_backoff: int = 20, timeout: int = 120, 
                       model_version: str = "gemini-2.5-flash", api_key: Optional[str] = None) -> Dict[str, Any]:
    """Invoca a Gemini usando la librería oficial de Python.

    Args:
        prompt (str): El prompt a enviar.
        max_attempts (int, optional): Máximo de reintentos. Defaults to 3.
        base_backoff (int, optional): Tiempo base de espera. Defaults to 20.
        timeout (int, optional): (No usado directamente por la lib, pero mantenido por compatibilidad).
        model_version (str, optional): Modelo a usar. Defaults to "gemini-1.5-flash".
        api_key (str, optional): API Key. Si es None, busca en variable de entorno GEMINI_API_KEY.

    Returns:
        Dict[str, Any]: {'stdout': respuesta, 'stderr': error, 'returncode': 0 o 1}
    """
    if not genai:
        msg = "Error: La librería 'google-generativeai' no está instalada en el entorno virtual activo."
        print(msg, file=sys.stderr)
        return {'stdout': '', 'stderr': msg, 'returncode': 1, 'elapsed': 0.0}

    # Configurar API Key
    final_api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not final_api_key:
        msg = "Error: No se encontró la API Key de Gemini. Configúrala en la interfaz o en la variable de entorno GEMINI_API_KEY."
        print(msg, file=sys.stderr)
        return {'stdout': '', 'stderr': msg, 'returncode': 1, 'elapsed': 0.0}
    
    genai.configure(api_key=final_api_key.strip())

    # Configuración de generación
    # max_output_tokens alto para no truncar artículos largos (tablas, refs, etc.)
    generation_config = {
        "temperature": 0.2,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 65536,
        "response_mime_type": "text/plain",
    }
    
    last_result = {'stdout': '', 'stderr': '', 'returncode': 1, 'elapsed': 0.0}

    for attempt in range(1, max_attempts + 1):
        try:
            start = time.time()
            
            # Desactivar TODOS los filtros de seguridad.
            # Trabajamos con artículos científicos publicados y revisados por pares.
            # No hay razón para filtrar contenido académico legítimo.
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            
            model = genai.GenerativeModel(
                model_name=model_version,
                generation_config=generation_config,
                safety_settings=safety_settings,
            )
            
            # Generar contenido
            response = model.generate_content(prompt)
            elapsed = time.time() - start
            
            # Extraer métricas de tokens del SDK (usage_metadata)
            token_data = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
            try:
                um = getattr(response, 'usage_metadata', None)
                if um:
                    token_data['prompt_tokens'] = getattr(um, 'prompt_token_count', 0) or 0
                    token_data['completion_tokens'] = getattr(um, 'candidates_token_count', 0) or 0
                    token_data['total_tokens'] = getattr(um, 'total_token_count', 0) or 0
            except Exception:
                pass  # Token data no disponible, no es crítico
            
            # NUNCA usar response.text — lanza ValueError si finish_reason != STOP
            # Siempre extraer texto manualmente de los candidatos
            if not response.candidates:
                last_result = {'stdout': '', 'stderr': 'Gemini no retornó candidatos.', 'returncode': 1, 'elapsed': elapsed}
                continue
            
            candidate = response.candidates[0]
            finish_reason = getattr(candidate, 'finish_reason', None)
            
            # Extraer texto de las partes (seguro, sin excepciones)
            extracted_text = ""
            try:
                if candidate.content and candidate.content.parts:
                    extracted_text = "".join(
                        part.text for part in candidate.content.parts 
                        if hasattr(part, 'text')
                    )
            except (ValueError, AttributeError):
                extracted_text = ""
            
            # finish_reason 1 = STOP (normal, exitoso)
            if finish_reason == 1 and extracted_text:
                return {'stdout': extracted_text, 'stderr': '', 'returncode': 0, 'elapsed': elapsed, 'token_usage': token_data}
            
            # finish_reason 4 = RECITATION (filtro de copyright)
            if finish_reason == 4:
                if extracted_text and len(extracted_text) > 500:
                    # Hay contenido parcial útil — usarlo directamente
                    print("Aviso: Respuesta parcial (filtro recitación), usando contenido disponible.", file=sys.stderr)
                    return {'stdout': extracted_text, 'stderr': '', 'returncode': 0, 'elapsed': elapsed, 'token_usage': token_data}
                else:
                    # Reintentar con temperatura más alta para diversificar
                    print(f"Aviso: Filtro de recitación (intento {attempt}/{max_attempts}). Subiendo temperatura...", file=sys.stderr)
                    generation_config["temperature"] = min(0.4 + (attempt * 0.2), 0.9)
                    last_result = {
                        'stdout': '', 
                        'stderr': f'Filtro de recitación activado (intento {attempt}/{max_attempts}). Reintentando con temperatura {generation_config["temperature"]}...', 
                        'returncode': 1, 'elapsed': elapsed
                    }
                    time.sleep(2)  # Pausa breve antes de reintentar
                    continue
            
            # finish_reason 3 = SAFETY
            if finish_reason == 3:
                if extracted_text and len(extracted_text) > 500:
                    print("Aviso: Respuesta parcial (filtro seguridad), usando contenido disponible.", file=sys.stderr)
                    return {'stdout': extracted_text, 'stderr': '', 'returncode': 0, 'elapsed': elapsed, 'token_usage': token_data}
                else:
                    last_result = {'stdout': '', 'stderr': 'Filtro de seguridad activado.', 'returncode': 1, 'elapsed': elapsed}
                    continue
            
            # Cualquier otro caso con texto
            if extracted_text:
                return {'stdout': extracted_text, 'stderr': '', 'returncode': 0, 'elapsed': elapsed, 'token_usage': token_data}
            else:
                last_result = {'stdout': '', 'stderr': f'Respuesta vacía (finish_reason={finish_reason}).', 'returncode': 1, 'elapsed': elapsed}

        except Exception as e:
            elapsed = time.time() - start
            error_msg = str(e)
            
            # Detectar errores de cuota para reintentar
            if "429" in error_msg or "Resource has been exhausted" in error_msg:
                wait_time = base_backoff * attempt
                print(f"Aviso: Límite de recursos (429). Reintentando en {wait_time}s...", file=sys.stderr)
                last_result = {'stdout': '', 'stderr': error_msg, 'returncode': 1, 'elapsed': elapsed}
                time.sleep(wait_time)
                continue
            # Detectar error de recitación que llegó como excepción
            elif "finish_reason" in error_msg and ("4" in error_msg or "RECITATION" in error_msg.upper()):
                print(f"Aviso: Excepción por filtro de recitación (intento {attempt}). Subiendo temperatura...", file=sys.stderr)
                generation_config["temperature"] = min(0.4 + (attempt * 0.2), 0.9)
                last_result = {'stdout': '', 'stderr': f'Filtro de recitación (intento {attempt}/{max_attempts}).', 'returncode': 1, 'elapsed': elapsed}
                time.sleep(2)
                continue
            else:
                msg = f"Gemini AI Error: {error_msg}"
                print(msg, file=sys.stderr)
                return {'stdout': '', 'stderr': msg, 'returncode': 1, 'elapsed': elapsed}
    
    return last_result


def extraer_resumen_tokens(gemini_meta: Dict[str, Any]) -> Dict[str, Any]:
    """Extrae métricas de uso de tokens de la salida de Gemini.

    Args:
        gemini_meta (Dict[str, Any]): Resultado de `invocar_gemini_cli`.

    Returns:
        Dict[str, Any]: Diccionario con 'total', 'prompt_tokens', etc.
    """
    search_text = (gemini_meta.get('stderr', '') or '') + "\n" + (gemini_meta.get('stdout', '') or '')
    tokens_info: Dict[str, Any] = {
        'found': False, 'total': None, 'prompt_tokens': None,
        'completion_tokens': None, 'raw': ''
    }

    # Estrategia 1: Buscar bloque JSON
    try:
        m = re.search(r"\{[^\}]*token[^\}]*\}", search_text)
        if m:
            tokens_info['raw'] = m.group(0)
            total = re.search(r"total[_\s-]*tokens\D*(\d+)", m.group(0), re.I)
            pt = re.search(r"prompt[_\s-]*tokens\D*(\d+)", m.group(0), re.I)
            ct = re.search(r"completion[_\s-]*tokens\D*(\d+)", m.group(0), re.I)
            if total:
                tokens_info['total'] = int(total.group(1))
            if pt:
                tokens_info['prompt_tokens'] = int(pt.group(1))
            if ct:
                tokens_info['completion_tokens'] = int(ct.group(1))
            if tokens_info['total'] or tokens_info['prompt_tokens']:
                tokens_info['found'] = True
                return tokens_info
    except Exception:
        pass

    # Estrategia 2: Patrones simples
    total_m = re.search(r"total\s*tokens\D*(\d+)", search_text, re.I)
    pt_m = re.search(r"prompt\s*tokens\D*(\d+)", search_text, re.I)
    ct_m = re.search(r"completion\s*tokens\D*(\d+)", search_text, re.I)
    
    if total_m or pt_m or ct_m:
        tokens_info['found'] = True
        tokens_info['raw'] = search_text
        if total_m:
            tokens_info['total'] = int(total_m.group(1))
        if pt_m:
            tokens_info['prompt_tokens'] = int(pt_m.group(1))
        if ct_m:
            tokens_info['completion_tokens'] = int(ct_m.group(1))
        return tokens_info

    tokens_info['raw'] = search_text
    return tokens_info


def validar_jats_xml(xml_content: str) -> Tuple[bool, List[str]]:
    """Valida el contenido XML contra el DTD JATS 1.3 local.

    Args:
        xml_content (str): Cadena con el XML completo.

    Returns:
        Tuple[bool, List[str]]: (es_valido, lista_de_errores).
    """
    possible_dtd_locations = [
        WORKSPACE_ROOT / DTD_FILENAME,
        WORKSPACE_ROOT / "JATS-Publishing-1-4-MathML3-DTD" / DTD_FILENAME,
        WORKSPACE_ROOT / "JATS-Publishing-1-3-MathML3-DTD" / DTD_FILENAME # Fallback
    ]
    
    dtd_path = None
    for path in possible_dtd_locations:
        if path.exists():
            dtd_path = path
            break
            
    if not dtd_path:
        # Intento de descarga automática si no existe
        try:
            zip_path = WORKSPACE_ROOT / "jats_dtd.zip"
            if not zip_path.exists():
                print(f"Descargando DTD JATS desde {DTD_ZIP_URL}...")
                urllib.request.urlretrieve(DTD_ZIP_URL, str(zip_path))
                print("Descarga completada.")

            print("Extrayendo DTD...")
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(WORKSPACE_ROOT)
            
            for path in possible_dtd_locations:
                if path.exists():
                    dtd_path = path
                    break
        except Exception as e:
            return False, [f"Fallo crítico al descargar/extraer DTD: {e}"]

    if not dtd_path:
         return False, [f"No se encontró {DTD_FILENAME} incluso después de intentar descargar."]

    print(f"Usando DTD: {dtd_path}")

    try:
        # Ajustar DOCTYPE para que apunte al DTD local si es necesario, 
        # o asegurar que el validador lo encuentre.
        # Aquí reemplazamos cualquier DOCTYPE existente con uno que apunte al archivo local.
        xml_content_patched = re.sub(
            r'<!DOCTYPE.*?>',
            f'<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD with MathML3 v1.4 2024//EN" "{DTD_FILENAME}">',
            xml_content,
            flags=re.DOTALL
        )
        
        xml_bytes = xml_content_patched.encode('utf-8')
        parser = etree.XMLParser(dtd_validation=False, no_network=False)
        xml_tree = etree.fromstring(xml_bytes, parser)
        dtd = etree.DTD(str(dtd_path))

        is_valid = dtd.validate(xml_tree)
        errors = [str(err) for err in dtd.error_log.filter_from_errors()]
        return is_valid, errors

    except etree.XMLSyntaxError as e:
        return False, [f"Error de sintaxis XML (mal formado): {e}"]
    except Exception as e:
        return False, [f"Error inesperado durante validación: {e}"]


def guardar_salida_xml(xml_content: str, output_path: str) -> None:
    """Guarda el XML en disco con la declaración DOCTYPE correcta.

    Args:
        xml_content (str): Contenido XML.
        output_path (str): Ruta de destino.
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            dtd_decl = f'<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.4 2024//EN" "{DTD_FILENAME}">' 
            # Eliminar declaración XML duplicada si existe
            if xml_content.startswith('<?xml'):
                parts = xml_content.split('?>', 1)
                if len(parts) > 1:
                    xml_content = parts[-1].strip()

            final_content = f'<?xml version="1.0" encoding="UTF-8"?>\n{dtd_decl}\n{xml_content}'
            f.write(final_content)
        print(f"XML guardado en: {output_path}")
    except Exception as e:
        print(f"Error al escribir archivo: {e}", file=sys.stderr)


def main() -> None:
    """Función principal CLI."""
    if len(sys.argv) != 3:
        print("Uso: python transformer.py <entrada.docx> <salida.xml>", file=sys.stderr)
        sys.exit(1)

    input_path, output_path = sys.argv[1], sys.argv[2]
    base_name = os.path.splitext(output_path)[0]
    log_path = f"{base_name}.txt"

    def log(msg: str, error: bool = False) -> None:
        """Helper para logging a archivo y consola."""
        ts = datetime.now().isoformat(sep=' ', timespec='seconds')
        line = f"[{ts}] {msg}\n"
        try:
            with open(log_path, 'a', encoding='utf-8') as lf:
                lf.write(line)
        except IOError:
            pass # Ignorar errores de log
            
        if error:
            print(msg, file=sys.stderr)
        else:
            print(msg)

    log(f"Iniciando conversión: {input_path} -> {output_path}")
    
    # 1. Extracción
    log("Paso 1: Extrayendo contenido...")
    structured_text = extraer_contenido_estructurado(input_path)
    if not structured_text:
        log("Falló la extracción.", error=True)
        sys.exit(1)
    
    # 2. Construcción de Prompt
    prompt = construir_prompt_avanzado(structured_text)

    # 3. Invocación IA
    log("Paso 2: Consultando a Gemini AI...")
    gemini_result = invocar_gemini_cli(prompt)
    if gemini_result.get('returncode') != 0 or not gemini_result.get('stdout'):
        log("Error en Gemini AI.", error=True)
        log(f"Stderr: {gemini_result.get('stderr')}", error=True)
        sys.exit(1)
    
    generated_xml = gemini_result.get('stdout', '')

    # 4. Limpieza
    match = re.search(r"```xml\s*(.*?)\s*```", generated_xml, re.DOTALL)
    if match:
        generated_xml = match.group(1)
    else:
        # Fallback para encontrar inicio de XML
        match_xml = re.search(r"(<\?xml|<!DOCTYPE|<article).*", generated_xml, re.DOTALL)
        if match_xml:
            generated_xml = match_xml.group(0)
            if generated_xml.endswith("```"):
                generated_xml = generated_xml[:-3]
    
    generated_xml = generated_xml.strip()

    # 5. Validación
    log("Paso 3: Validando XML...")
    is_valid, errors = validar_jats_xml(generated_xml)
    if is_valid:
        log("XML Válido según DTD.")
    else:
        log("XML Inválido (se guardará igual para revisión).", error=True)
        for err in errors:
            log(f"- {err}", error=True)

    # 6. Guardado
    guardar_salida_xml(generated_xml, output_path)
    log("Proceso terminado.")

if __name__ == "__main__":
    main()