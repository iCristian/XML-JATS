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

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from . import prompts

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


def parse_model_response(text: str) -> str:
    """Extrae el contenido de un bloque de código markdown o devuelve el texto puro."""
    import re
    # Buscar bloque XML (soporta output truncado sin backticks finales)
    match_xml = re.search(r'```xml\s*(.*?)(?:```|$)', text, re.DOTALL | re.IGNORECASE)
    if match_xml:
         return match_xml.group(1).strip()
         
    # Buscar bloque JSON
    match_json = re.search(r'```json\s*(.*?)(?:```|$)', text, re.DOTALL | re.IGNORECASE)
    if match_json:
         return match_json.group(1).strip()
         
    # Fallback si no hay formato markdown
    return text.strip()


class GeminiRetryError(Exception):
    """Excepción lanzada cuando faya la ejecución de Gemini tras varios reintentos por errores recuperables (e.g. cuota)."""
    pass

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=5, min=10, max=60),
    retry=retry_if_exception_type(GeminiRetryError),
    reraise=True
)
def _attempt_gemini_call(model: genai.GenerativeModel, prompt: str, token_manager=None, chat=None) -> Any:
    """Llamada interna a Gemini con lógica de reintentos vía tenacity."""
    try:
        generation_config = genai.types.GenerationConfig(
            temperature=0.1,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
        )
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        if chat is not None:
             response = chat.send_message(prompt, generation_config=generation_config, safety_settings=safety_settings)
        else:
             response = model.generate_content(prompt, generation_config=generation_config, safety_settings=safety_settings)
        
        # Track token usage if response is successful
        if token_manager and response and hasattr(response, 'usage_metadata'):
            try:
                # Actualizar contadores globales de tokens
                usage = response.usage_metadata
                token_manager.add_usage(
                    input_tokens=usage.prompt_token_count,
                    output_tokens=usage.candidates_token_count,
                    model_name=model.model_name
                )
            except Exception as e:
                print(f"Error registrando tokens (ignorado en core flow): {e}", file=sys.stderr)
                
        return response
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "Quota exceeded" in error_str:
            print(f"Advertencia: Cuota excedida (429). Programando reintento... Detalle: {error_str}", file=sys.stderr)
            raise GeminiRetryError(f"HTTP 429: Cuota excedida o Rate Limit ({error_str})")
        
        if "Recitation" in error_str or "FinishReason.RECITATION" in error_str:
            print(f"Error de Recitation (Gemini se negó a responder por políticas de copyright).", file=sys.stderr)
            # Retornar una excepción normal que no dispara retries (o dejar que la capture the top level)
            raise Exception(f"FinishReason.RECITATION - El modelo bloqueó la respuesta por políticas de recitación/copyright. Intenta procesar fragmentos más pequeños.")
            
        raise # Reraise other errors to be caught in invocar_gemini_cli

def invocar_gemini_cli(prompt: str, max_attempts: int = 3, base_backoff: int = 20, timeout: int = 120, 
                       model_version: str = "gemini-2.5-flash", api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Función helper para llamar a la API de Gemini (CLI-friendly y modular).
    """
    if not api_key:
        api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return {'returncode': 1, 'stderr': 'No API key provided. Set it as param, st.session_state (in app) or GEMINI_API_KEY env var.'}
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_version)
    
    token_manager = None
    try:
        from .config_store import token_manager as global_token_manager
        token_manager = global_token_manager
    except ImportError:
        pass
        
    try:
        chat = model.start_chat()
        response = _attempt_gemini_call(model, prompt, token_manager=token_manager, chat=chat)
        
        full_text = response.text if response and hasattr(response, 'text') else ""
        
        tu = {}
        if hasattr(response, 'usage_metadata'):
             usage = response.usage_metadata
             tu = {
                 'prompt_tokens': getattr(usage, 'prompt_token_count', 0),
                 'completion_tokens': getattr(usage, 'candidates_token_count', 0),
                 'total_tokens': getattr(usage, 'total_token_count', 0)
             }
             
        # Lógica de auto-continuación si el output llega al límite máximo de tokens (8192)
        loop_count = 0
        while response and response.candidates and loop_count < 3:
             finish_reason = getattr(response.candidates[0], 'finish_reason', 1)
             is_max_tokens = "MAX_TOKENS" in str(finish_reason) or finish_reason == 2
             if not is_max_tokens:
                 break
                 
             print("MAX_TOKENS alcanzado (límite de salida). Solicitando continuación a Gemini...", file=sys.stderr)
             response = _attempt_gemini_call(
                 model, 
                 "Continúa generando el código XML exactamente donde te quedaste, sin repetir texto, sin saludos ni explicaciones, solo el código XML que sigue.", 
                 token_manager=token_manager, 
                 chat=chat
             )
             
             if response and hasattr(response, 'text') and response.text:
                 import re
                 chunk = response.text.strip()
                 chunk = re.sub(r"^```[a-zA-Z]*\n?", "", chunk)
                 chunk = re.sub(r"```$", "", chunk).strip()
                 full_text += "\n" + chunk
             
             if hasattr(response, 'usage_metadata'):
                 usage = response.usage_metadata
                 tu['prompt_tokens'] = tu.get('prompt_tokens', 0) + getattr(usage, 'prompt_token_count', 0)
                 tu['completion_tokens'] = tu.get('completion_tokens', 0) + getattr(usage, 'candidates_token_count', 0)
                 tu['total_tokens'] = tu.get('total_tokens', 0) + getattr(usage, 'total_token_count', 0)
                 
             loop_count += 1
        
        if full_text:
             response_text = parse_model_response(full_text)
             return {'returncode': 0, 'stdout': response_text, 'token_usage': tu}
        else:
             return {'returncode': 1, 'stderr': f'Gemini devolvió una respuesta vacía o fue bloqueada. {getattr(response, "prompt_feedback", "")}'}
             
    except Exception as e:
        return {'returncode': 1, 'stderr': f'Error en API de Gemini tras reintentos: {str(e)}'}
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