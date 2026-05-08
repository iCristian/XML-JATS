# -*- coding: utf-8 -*-

"""Script para convertir documentos Word a JATS XML usando IA.

Este módulo orquesta la extracción de contenido de archivos .docx, la generación
de XML JATS mediante un modelo de lenguaje, y la validación del resultado.
Cumple con las normas de documentación de Google.

Attributes:
    DTD_ZIP_URLS (dict): URLs para descargar los DTDs de JATS por versión.
    WORKSPACE_ROOT (Path): Ruta base del espacio de trabajo actual.
    DTD_BASE_DIR (Path): Directorio base centralizado de DTDs (modules/dtd/).
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
from typing import Any, Dict, List, Optional, Tuple

from docx import Document
from lxml import etree
from tenacity import (retry, retry_if_exception_type, stop_after_attempt,
                      wait_exponential)

from . import prompts
from .llm_provider import (PROVIDER_REGISTRY, LLMConfig, LLMResponse,
                           get_provider)

# --- Constantes ---
# URLs de descarga para cada versión JATS (NCBI FTP)
DTD_ZIP_URLS = {
    "1.3": "https://ftp.ncbi.nlm.nih.gov/pub/jats/publishing/1.3/JATS-Publishing-1-3-MathML3-DTD.zip",
    "1.4": "https://public.nlm.nih.gov/projects/jats/publishing/1.4/JATS-Publishing-1-4-MathML3-DTD.zip",
}
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
# Directorio base para todos los DTDs (centralizado en modules/dtd/)
DTD_BASE_DIR = WORKSPACE_ROOT / "modules" / "dtd"
IMAGE_OUTPUT_DIR = WORKSPACE_ROOT / "imagenes_extraidas"


def _get_dtd_dir(version: str) -> Path:
    """Devuelve la ruta al directorio DTD para una versión JATS dada."""
    folder = f"JATS-Publishing-{version.replace('.', '-')}-MathML3-DTD"
    return DTD_BASE_DIR / folder


def _get_dtd_filename(version: str) -> str:
    """Devuelve el nombre del archivo DTD principal para una versión JATS dada."""
    return f"JATS-journalpublishing{version.replace('.', '-')}-mathml3.dtd"

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
        os.chmod(str(IMAGE_OUTPUT_DIR), 0o700)

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
                        _ALLOWED_IMAGE_EXT = {'png', 'jpeg', 'jpg', 'gif', 'tiff', 'bmp', 'svg+xml'}
                        if content_type not in _ALLOWED_IMAGE_EXT:
                            content_type = 'png'
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


class LLMRetryError(Exception):
    """Excepción lanzada cuando falla la ejecución del LLM tras varios reintentos por errores recuperables (e.g. cuota)."""
    pass

# Alias de compatibilidad
GeminiRetryError = LLMRetryError

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=5, min=10, max=60),
    retry=retry_if_exception_type(LLMRetryError),
    reraise=True
)
def _attempt_llm_call(
    provider_id: str,
    prompt: str,
    model: str,
    api_key: str,
    config: LLMConfig | None = None,
    chat_history: list | None = None,
) -> LLMResponse:
    """Llamada interna al LLM con lógica de reintentos vía tenacity."""
    try:
        provider = get_provider(provider_id)
        return provider.generate(
            prompt=prompt,
            model=model,
            api_key=api_key,
            config=config,
            chat_history=chat_history,
        )
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "Quota exceeded" in error_str or "rate_limit" in error_str.lower():
            print(f"Advertencia: Cuota excedida (429). Programando reintento... Detalle: {error_str}", file=sys.stderr)
            raise LLMRetryError(f"HTTP 429: Cuota excedida o Rate Limit ({error_str})")

        if "Recitation" in error_str or "FinishReason.RECITATION" in error_str:
            print(f"Error de Recitation (modelo se negó a responder por políticas de copyright).", file=sys.stderr)
            raise Exception(f"FinishReason.RECITATION - El modelo bloqueó la respuesta por políticas de recitación/copyright. Intenta procesar fragmentos más pequeños.")

        raise


def invocar_llm(
    prompt: str,
    max_attempts: int = 3,
    base_backoff: int = 20,
    timeout: int = 120,
    model_version: str = "gemini-2.5-flash",
    api_key: str | None = None,
    provider_id: str = "gemini",
    **_kwargs,
) -> Dict[str, Any]:
    """
    Función principal para llamar a cualquier proveedor de LLM.

    Soporta Google Gemini, OpenAI, Anthropic y proveedores compatibles
    con la API de OpenAI (DeepSeek, Mistral, Groq, Ollama).

    Args:
        prompt: Texto del prompt a enviar.
        model_version: Nombre/ID del modelo.
        api_key: Clave de API del proveedor.
        provider_id: Identificador del proveedor ('gemini', 'openai', 'anthropic', etc.).

    Returns:
        Dict con claves 'returncode', 'stdout', 'stderr', 'token_usage', 'quota_exceeded'.
    """
    if not api_key:
        provider = get_provider(provider_id)
        env_var = provider.get_api_key_env_var()
        api_key = os.environ.get(env_var, "") if env_var else ""

    # Sanitización robusta: ignorar placeholders o keys muy cortas (< 20 chars)
    # Ollama no requiere API key real
    def _is_valid_key_format(k: str | None) -> bool:
        if not k:
            return False
        k = k.strip()
        if len(k) < 20 or "tu_api_key" in k.lower() or k.lower() == "aiza...":
            return False
        return True

    if provider_id not in ("ollama", "lmstudio") and not _is_valid_key_format(api_key):
        return {
            'returncode': 1,
            'stderr': f'No se encontró una API Key válida para {provider_id}. Ve a ⚙️ Configuración y guarda tu clave.',
        }

    # Para Ollama, usar una key dummy si no hay
    if provider_id == "ollama" and not api_key:
        api_key = "ollama"

    token_manager = None
    try:
        from .config_store import token_manager as global_token_manager
        token_manager = global_token_manager
    except ImportError:
        pass

    config = LLMConfig()

    try:
        response = _attempt_llm_call(
            provider_id=provider_id,
            prompt=prompt,
            model=model_version,
            api_key=api_key,
            config=config,
        )

        full_text = response.text

        tu = {
            'prompt_tokens': response.prompt_tokens,
            'completion_tokens': response.completion_tokens,
            'total_tokens': response.total_tokens,
        }

        # Track token usage
        if token_manager and tu.get('total_tokens', 0) > 0:
            try:
                token_manager.add_usage(
                    input_tokens=response.prompt_tokens,
                    output_tokens=response.completion_tokens,
                    model_name=model_version,
                )
            except Exception as e:
                print(f"Error registrando tokens (ignorado): {e}", file=sys.stderr)

        # Lógica de auto-continuación si el output llega al límite máximo de tokens
        loop_count = 0
        while loop_count < 3:
            is_max_tokens = "MAX_TOKENS" in response.finish_reason.upper() or "length" in response.finish_reason.lower()
            if not is_max_tokens:
                break

            print("MAX_TOKENS alcanzado. Solicitando continuación...", file=sys.stderr)
            continuation = _attempt_llm_call(
                provider_id=provider_id,
                prompt="Continúa generando el código XML exactamente donde te quedaste, sin repetir texto, sin saludos ni explicaciones, solo el código XML que sigue.",
                model=model_version,
                api_key=api_key,
                config=config,
            )

            if continuation.text:
                chunk = continuation.text.strip()
                chunk = re.sub(r"^```[a-zA-Z]*\n?", "", chunk)
                chunk = re.sub(r"```$", "", chunk).strip()
                full_text += "\n" + chunk

            tu['prompt_tokens'] = tu.get('prompt_tokens', 0) + continuation.prompt_tokens
            tu['completion_tokens'] = tu.get('completion_tokens', 0) + continuation.completion_tokens
            tu['total_tokens'] = tu.get('total_tokens', 0) + continuation.total_tokens

            response = continuation
            loop_count += 1

        if full_text:
            response_text = parse_model_response(full_text)
            response_text = sanitize_generated_xml(response_text)
            return {'returncode': 0, 'stdout': response_text, 'token_usage': tu}
        else:
            return {'returncode': 1, 'stderr': 'El modelo devolvió una respuesta vacía o fue bloqueada.'}

    except LLMRetryError as e:
        print(f"Cuota de API agotada tras reintentos. Detalles: {e}", file=sys.stderr)
        return {
            'returncode': 1,
            'quota_exceeded': True,
            'stderr': (
                f'Cuota gratuita agotada (HTTP 429 tras {max_attempts} reintentos). '
                'Si tu cuenta tiene facturación habilitada, la misma clave seguirá '
                'funcionando en el tier de pago. Espera unos minutos o revisa '
                'tu cuota en el panel de tu proveedor de IA.'
            ),
        }
    except Exception as e:
        return {'returncode': 1, 'stderr': f'Error en API de LLM tras reintentos: {str(e)}'}


# Alias de compatibilidad hacia atrás — código existente puede seguir usando invocar_gemini_cli
def invocar_gemini_cli(
    prompt: str,
    max_attempts: int = 3,
    base_backoff: int = 20,
    timeout: int = 120,
    model_version: str = "gemini-2.5-flash",
    api_key: Optional[str] = None,
    **_kwargs,
) -> Dict[str, Any]:
    """Alias de compatibilidad. Delega a ``invocar_llm`` con provider_id='gemini'."""
    return invocar_llm(
        prompt=prompt,
        max_attempts=max_attempts,
        base_backoff=base_backoff,
        timeout=timeout,
        model_version=model_version,
        api_key=api_key,
        provider_id="gemini",
        **_kwargs,
    )


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


def _fix_unclosed_tags(xml_string: str) -> str:
    """Intento de emergencia para cerrar etiquetas huérfanas o arreglar desajustes básicos dejados por la IA."""
    import re

    # 1. Asegurar que empiece y termine con <article>
    if not xml_string.strip().startswith("<article") and not xml_string.strip().startswith("<?xml"):
        xml_string = f"<article>\n{xml_string}"
    
    if not xml_string.strip().endswith("</article>"):
        xml_string = f"{xml_string}\n</article>"
    
    return xml_string


def sanitize_generated_xml(xml_string: str) -> str:
    """
    Post-procesamiento exhaustivo del XML generado por la IA.
    
    Corrige errores recurrentes del modelo antes de pasar a validación DTD:
      - Etiquetas truncadas/malformadas (ej. <publisher\\n<publisher-name>)
      - <align="..."> sueltos que debían ser <td align="...">
      - <break/> (no válido en JATS)
      - <table-wrap> huérfanos a nivel de <body> (deben ir dentro de <sec>)
      - <table-wrap-foot> fuera de su <table-wrap>
      - <collab>et al.</collab> → <etal/> si procede (opcional, no forzado)
    """
    import re

    # ── 0. Quitar BOM y espacios iniciales ──────────────────────────
    xml_string = xml_string.strip().lstrip('\ufeff')

    # ── 1. Etiquetas truncadas / malformadas ────────────────────────
    # Patrón: <tag_name  (sin cerrar con '>') seguido inmediatamente de otra etiqueta
    # Ejemplo real: <publisher\n<publisher-name>  →  <publisher-name>
    # Detectamos <word  seguido de \n o espacio y luego <  (sin > intermedio)
    xml_string = re.sub(
        r'<([a-zA-Z][\w-]*)\s*\n\s*(<[a-zA-Z])',
        r'\2',
        xml_string
    )

    # ── 2. <align="...">texto</align> → <td align="...">texto</td> ──
    # La IA a veces escribe <align="left"> en vez de <td align="left">
    xml_string = re.sub(
        r'<align="([^"]*)">(.*?)</align>',
        r'<td align="\1">\2</td>',
        xml_string,
        flags=re.DOTALL
    )

    # ── 3. Quitar <break/> (no válido en JATS) ─────────────────────
    xml_string = re.sub(r'<break\s*/>', '', xml_string)

    # ── 4. Quitar <?xml...?> duplicada si hay más de una ────────────
    # Mantener solo la primera
    parts = xml_string.split('<?xml')
    if len(parts) > 2:
        xml_string = '<?xml' + parts[1]
        for p in parts[2:]:
            # Quitar la declaración, conservar el resto
            idx = p.find('?>')
            if idx >= 0:
                xml_string += p[idx+2:]

    # ── 5. Asegurar <article> y </article> ──────────────────────────
    xml_string = _fix_unclosed_tags(xml_string)

    # ── 6. Mover <table-wrap> huérfanos (hijos directos de <body>)
    #        adentro de la sección que los referencia, o crear una <sec>
    #        auxiliar si es necesario. ────────────────────────────────
    # Esto es crítico porque el DTD dice: body = (block-stuff*, sec*, sig-block?)
    # Una vez que aparecen <sec>, no puede haber más <table-wrap> sueltos.
    try:
        xml_string = _move_orphan_table_wraps(xml_string)
    except Exception:
        pass  # Si falla, dejamos el XML sin cambiar en este paso

    # ── 7. Limpiar <table-wrap-foot> si quedó fuera de su <table-wrap>
    # Por robustez, lo envolvemos en un <sec> si está suelto en <body>
    # (esto generalmente ya se resuelve con el paso 6)

    # ── 8. SciELO: element-citation → mixed-citation ───────────
    xml_string = xml_string.replace("<element-citation", "<mixed-citation")
    xml_string = xml_string.replace("</element-citation>", "</mixed-citation>")

    # ── 9. SciELO: volumen/issue vacíos → placeholder ──────────
    xml_string = re.sub(r'<volume>\s*</volume>', '<volume>1</volume>', xml_string)
    xml_string = re.sub(r'<issue>\s*</issue>', '<issue>1</issue>', xml_string)

    # ── 10. SciELO: <fig><caption><p> → <caption><title> ──────
    # Reemplazar <caption><p>texto</p></caption> → <caption><title>texto</title></caption>
    xml_string = re.sub(
        r'<caption>\s*<p>(.*?)</p>\s*</caption>',
        r'<caption>\n<title>\1</title>\n</caption>',
        xml_string,
        flags=re.DOTALL,
    )

    # ── 11. SciELO: generar <counts> si falta ────────────────────
    try:
        xml_string = _inject_counts(xml_string)
    except Exception:
        pass

    # ── 12. SciELO: agregar @iso-8601-date a fechas de history ───
    xml_string = _add_iso_dates_to_history(xml_string)

    # ── 13. SciELO: fn-type="other" → "supported-by" ─────────────
    xml_string = xml_string.replace('fn-type="other"', 'fn-type="supported-by"')

    # ── 14. SciELO: ISSN placeholder genérico ────────────────────
    xml_string = xml_string.replace('<issn pub-type="ppub">0000-0000</issn>', '<issn pub-type="ppub">XXXX-XXXX</issn>')

    return xml_string


def _move_orphan_table_wraps(xml_string: str) -> str:
    """
    Detecta <table-wrap> que son hijos directos de <body> (fuera de cualquier <sec>)
    y los envuelve en una <sec sec-type="supplementary-material"> al final del body,
    justo ANTES del primer </body>.
    
    Usa lxml con recover=True para manejar XML levemente roto.
    """
    try:
        parser = etree.XMLParser(recover=True, encoding='utf-8', resolve_entities=False, no_network=True)
        root = etree.fromstring(xml_string.encode('utf-8'), parser=parser)
    except Exception:
        return xml_string  # No podemos parsear, devolver sin tocar

    body = root.find('.//body')
    if body is None:
        return xml_string

    # Encontrar table-wrap que sean hijos directos de body (NO dentro de sec)
    orphans = []
    for child in list(body):
        tag = child.tag if isinstance(child.tag, str) else ''
        if tag == 'table-wrap':
            orphans.append(child)
        elif tag == 'table-wrap-foot':
            # table-wrap-foot suelto en body, lo quitamos (debería estar dentro de table-wrap)
            body.remove(child)

    if not orphans:
        return xml_string

    # Intentar mover cada table-wrap a la sección que lo referencia via <xref rid="...">
    for tw in orphans:
        tw_id = tw.get('id', '')
        if not tw_id:
            continue
        
        # Buscar la <sec> que contiene un <xref ref-type="table" rid="tw_id">
        placed = False
        for xref in root.iter('xref'):
            if xref.get('rid') == tw_id and xref.get('ref-type') == 'table':
                # Subir hasta encontrar la <sec> padre
                parent = xref.getparent()
                while parent is not None and parent.tag != 'sec':
                    parent = parent.getparent()
                if parent is not None and parent.tag == 'sec':
                    # Remover del body y añadir al final de esa sec
                    body.remove(tw)
                    parent.append(tw)
                    placed = True
                    break
        
        if not placed:
            # No encontramos la sec que lo referencia — crear una sec auxiliar
            body.remove(tw)
            aux_sec = etree.SubElement(body, 'sec')
            aux_sec.set('sec-type', 'supplementary-material')
            title_el = etree.SubElement(aux_sec, 'title')
            title_el.text = 'Material Suplementario'
            aux_sec.append(tw)

    # Serializar de vuelta
    result = etree.tostring(root, encoding='unicode', xml_declaration=False)
    
    # Re-añadir la declaración XML si la tenía al inicio
    if xml_string.strip().startswith('<?xml'):
        import re
        match = re.match(r'(<\?xml[^?]*\?>)', xml_string.strip())
        if match:
            result = match.group(1) + '\n' + result
    
    return result


def _inject_counts(xml_string: str) -> str:
    """Inserta <counts> dentro de <article-meta> si falta.

    Cuenta figuras, tablas, referencias y páginas del XML parseado.
    """
    import re
    try:
        parser = etree.XMLParser(recover=True, encoding='utf-8', resolve_entities=False, no_network=True)
        root = etree.fromstring(xml_string.encode('utf-8'), parser=parser)
    except Exception:
        return xml_string

    article_meta = root.find('.//article-meta')
    if article_meta is None:
        return xml_string

    # Si ya existe <counts>, no tocar
    if article_meta.find('counts') is not None:
        return xml_string

    # Contar elementos
    fig_count = len(root.findall('.//fig'))
    table_count = len(root.findall('.//table-wrap'))
    ref_count = len(root.findall('.//back//ref'))

    # Páginas: lpage - fpage + 1
    fpage_el = article_meta.find('fpage')
    lpage_el = article_meta.find('lpage')
    try:
        fpage = int(fpage_el.text) if fpage_el is not None and fpage_el.text else 1
        lpage = int(lpage_el.text) if lpage_el is not None and lpage_el.text else fpage
        page_count = max(1, lpage - fpage + 1)
    except (ValueError, TypeError):
        page_count = 1

    counts = etree.Element('counts')
    etree.SubElement(counts, 'fig-count', count=str(fig_count))
    etree.SubElement(counts, 'table-count', count=str(table_count))
    etree.SubElement(counts, 'ref-count', count=str(ref_count))
    etree.SubElement(counts, 'page-count', count=str(page_count))

    # Insertar justo antes del primer <abstract> o al final de <article-meta>
    abstract = article_meta.find('abstract')
    if abstract is not None:
        idx = list(article_meta).index(abstract)
        article_meta.insert(idx, counts)
    else:
        article_meta.append(counts)

    return etree.tostring(root, encoding='unicode', xml_declaration=False)


def _add_iso_dates_to_history(xml_string: str) -> str:
    """Agrega @iso-8601-date a cada <date> dentro de <history>.

    El formato ISO esperado es YYYY-MM-DD. Si falta día o mes, se usa
    YYYY-MM o YYYY según corresponda.
    """
    import re

    def _patch_date(match: 're.Match') -> str:
        tag = match.group(1)
        day = (match.group(2) or '').strip()
        month = (match.group(3) or '').strip()
        year = (match.group(4) or '').strip()

        if not year:
            return match.group(0)

        # Construir ISO según disponibilidad
        iso = year
        if month and month.isdigit():
            iso = f"{year}-{int(month):02d}"
            if day and day.isdigit():
                iso = f"{year}-{int(month):02d}-{int(day):02d}"
        elif month:
            # Mes textual — intentar mapeo básico
            meses = {
                'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
                'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
                'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12',
                'january': '01', 'february': '02', 'march': '03', 'april': '04',
                'may': '05', 'june': '06', 'july': '07', 'august': '08',
                'september': '09', 'october': '10', 'november': '11', 'december': '12',
            }
            m = meses.get(month.lower(), '')
            if m:
                iso = f"{year}-{m}"
                if day and day.isdigit():
                    iso = f"{year}-{m}-{int(day):02d}"

        return f'<date date-type="{tag}" iso-8601-date="{iso}">{match.group(5)}</date>'

    # Patrón robusto para <date date-type="...">...<day>..</day><month>..</month><year>..</year>...</date>
    pattern = re.compile(
        r'<date\s+date-type="([^"]+)"(?![^>]*iso-8601-date)>(.*?)<year>([^<]+)</year>(.*?)</date>',
        re.DOTALL
    )

    # Necesitamos capturar day y month que pueden estar antes o después del year
    def _patch_date_v2(match: 're.Match') -> str:
        date_type = match.group(1)
        inner = match.group(2)
        year = match.group(3).strip()
        rest = match.group(4)

        day_match = re.search(r'<day>([^<]+)</day>', inner)
        month_match = re.search(r'<month>([^<]+)</month>', inner)
        day = day_match.group(1).strip() if day_match else ''
        month = month_match.group(1).strip() if month_match else ''

        if not year:
            return match.group(0)

        iso = year
        if month and month.isdigit():
            iso = f"{year}-{int(month):02d}"
            if day and day.isdigit():
                iso = f"{year}-{int(month):02d}-{int(day):02d}"
        elif month:
            meses = {
                'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
                'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
                'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12',
                'january': '01', 'february': '02', 'march': '03', 'april': '04',
                'may': '05', 'june': '06', 'july': '07', 'august': '08',
                'september': '09', 'october': '10', 'november': '11', 'december': '12',
            }
            m = meses.get(month.lower(), '')
            if m:
                iso = f"{year}-{m}"
                if day and day.isdigit():
                    iso = f"{year}-{m}-{int(day):02d}"

        return f'<date date-type="{date_type}" iso-8601-date="{iso}">{inner}<year>{year}</year>{rest}</date>'

    return pattern.sub(_patch_date_v2, xml_string)


def validar_jats_xml(xml_content: str) -> Tuple[bool, List[str]]:
    """Valida el contenido XML contra el DTD JATS local.

    Busca el DTD en ``modules/dtd/`` según la versión configurada
    (1.4 por defecto). Si no existe, intenta descargarlo desde NCBI.

    Args:
        xml_content (str): Cadena con el XML completo.

    Returns:
        Tuple[bool, List[str]]: (es_valido, lista_de_errores).
    """
    from . import config_store
    version = config_store.get_jats_version()
    dtd_filename = _get_dtd_filename(version)
    dtd_dir = _get_dtd_dir(version)

    # Búsqueda ordenada: primero la versión configurada en modules/dtd/,
    # luego fallback a la otra versión disponible.
    fallback_version = "1.3" if version == "1.4" else "1.4"
    possible_dtd_locations = [
        # 1. Versión configurada en modules/dtd/ (ubicación canónica)
        dtd_dir / dtd_filename,
        # 2. Fallback: otra versión en modules/dtd/
        _get_dtd_dir(fallback_version) / _get_dtd_filename(fallback_version),
    ]

    dtd_path = None
    used_fallback = False
    for i, path in enumerate(possible_dtd_locations):
        if path.exists():
            dtd_path = path
            used_fallback = (i > 0)
            break

    if not dtd_path:
        # Intento de descarga automática si no existe
        download_url = DTD_ZIP_URLS.get(version, DTD_ZIP_URLS["1.4"])
        try:
            zip_path = DTD_BASE_DIR / f"jats_{version.replace('.', '')}_temp.zip"
            if not zip_path.exists():
                print(f"📥 Descargando DTD JATS {version} desde {download_url}...")
                import ssl
                try:
                    import certifi
                    ctx = ssl.create_default_context(cafile=certifi.where())
                except ImportError:
                    ctx = ssl.create_default_context()

                req = urllib.request.Request(download_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, context=ctx, timeout=30) as response, \
                     open(zip_path, 'wb') as out_file:
                    out_file.write(response.read())
                print("   ✓ Descarga completada.")

            print("📦 Extrayendo DTD...")
            with zipfile.ZipFile(zip_path, 'r') as z:
                # Extraer a modules/dtd/ (no a la raíz del proyecto)
                for member in z.namelist():
                    if not member.startswith('__MACOSX'):
                        z.extract(member, DTD_BASE_DIR)

            # Limpiar ZIP temporal
            if zip_path.exists():
                zip_path.unlink()

            # Re-buscar
            for path in possible_dtd_locations:
                if path.exists():
                    dtd_path = path
                    break
        except Exception as e:
            return False, [f"Fallo crítico al descargar/extraer DTD: {e}"]

    if not dtd_path:
        return False, [
            f"No se encontró el DTD JATS {version} ({dtd_filename}).",
            f"Ejecuta: python modules/dtd/download_jats14.py",
        ]

    if used_fallback:
        actual_v = fallback_version
        print(f"⚠️  DTD JATS {version} no disponible, usando fallback {actual_v}: {dtd_path}")
    else:
        print(f"✅ Usando DTD JATS {version}: {dtd_path}")

    # La versión real del DTD cargado (puede diferir si hubo fallback)
    dtd_actual_version = fallback_version if used_fallback else version
    dtd_actual_filename = _get_dtd_filename(dtd_actual_version)

    try:
        # Reemplazar DOCTYPE para apuntar al DTD local correcto
        xml_content_patched = re.sub(
            r'<!DOCTYPE.*?>',
            f'<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD with MathML3 v{dtd_actual_version} 2024//EN" "{dtd_actual_filename}">',
            xml_content,
            flags=re.DOTALL
        )

        xml_bytes = xml_content_patched.encode('utf-8')

        # Activar modo de recuperación para intentar parsear a pesar de etiquetas mal cerradas
        parser = etree.XMLParser(dtd_validation=False, recover=True, no_network=True, resolve_entities=False)
        xml_tree = etree.fromstring(xml_bytes, parser)
        dtd = etree.DTD(str(dtd_path))

        is_valid = dtd.validate(xml_tree)
        errors = [str(err) for err in dtd.error_log.filter_from_errors()]
        return is_valid, errors

    except etree.XMLSyntaxError as e:
        return False, [f"Error de sintaxis XML (mal formado): {e}"]
    except Exception as e:
        return False, [f"Error inesperado durante validación: {e}"]


def verificar_completitud_xml(xml_content: str, original_text: str = None) -> Tuple[bool, List[str]]:
    """Verifica heurísticamente que el XML no sea un cascarón vacío y contenga el texto real.

    Args:
        xml_content (str): Cadena con el XML completo a evaluar.
        original_text (str, optional): Texto original extraído del docx para comparar densidad.

    Returns:
        Tuple[bool, List[str]]: (es_completo, lista_de_advertencias)
    """
    import re
    warnings = []
    is_complete = True

    # 1. Búsqueda de comentarios perezosos típicos de LLMs
    # Ej: <!-- Contenido de la introducción -->
    lazy_comments = re.findall(r'<!--\s*(?i:contenido|cuerpo|texto|referencias|inserte|...\s*).*?-->', xml_content)
    if lazy_comments:
        warnings.append(f"Se detectaron comentarios que sugieren omisión de texto: {lazy_comments[:2]}...")
        is_complete = False

    # Extraer texto visible del body
    try:
        parser = etree.XMLParser(recover=True, encoding='utf-8', resolve_entities=False, no_network=True)
        root = etree.fromstring(xml_content.encode('utf-8'), parser=parser)
        body = root.find('.//body')
        body_text = "".join(body.itertext()) if body is not None else ""
        
        # 2. Verificación básica: un artículo académico debe tener un body sustancial
        if len(body_text.strip()) < 500:
            warnings.append("El cuerpo del documento (<body>) es peligrosamente corto (menos de 500 caracteres). El modelo probablemente omitió el contenido de la investigación.")
            is_complete = False
            
    except Exception as e:
        # Falla el parseo crudo
        pass

    return is_complete, warnings


def guardar_salida_xml(xml_content: str, output_path: str) -> None:
    """Guarda el XML en disco con la declaración DOCTYPE correcta.

    Utiliza la versión JATS configurada en config_store (1.4 por defecto)
    para generar el DOCTYPE y el nombre de archivo DTD correspondiente.

    Args:
        xml_content (str): Contenido XML.
        output_path (str): Ruta de destino.
    """
    from . import config_store
    version = config_store.get_jats_version()
    dtd_filename = _get_dtd_filename(version)

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            dtd_decl = f'<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD with MathML3 v{version} 2024//EN" "{dtd_filename}">'

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
    prompt = prompts.get_generation_prompt(structured_text)

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