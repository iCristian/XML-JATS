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
import subprocess
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
DTD_ZIP_URL = "https://public.nlm.nih.gov/projects/jats/publishing/1.3/JATS-Publishing-1-3-MathML3-DTD.zip"
WORKSPACE_ROOT = Path(__file__).resolve().parent
DTD_FILENAME = "JATS-journalpublishing1-3-mathml3.dtd"
DTD_LOCAL_FILE = WORKSPACE_ROOT / DTD_FILENAME
IMAGE_OUTPUT_DIR = WORKSPACE_ROOT / "imagenes_extraidas"


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


def construir_prompt_avanzado(texto_articulo: str) -> str:
    """Construye un prompt de sistema detallado para la generación de JATS XML.

    Args:
        texto_articulo (str): El texto crudo del artículo con placeholders.

    Returns:
        str: El prompt completo formateado para el modelo de IA.
    """
    prompt = f"""
    Actúa como un experto en etiquetado JATS (Journal Article Tag Suite) XML, versión 1.3, para SciELO.

    TAREA:
    Convierte el siguiente texto de un artículo científico, que contiene placeholders especiales para imágenes y tablas, a un archivo XML bien formado que cumpla con el estándar JATS.

    INSTRUCCIONES Y MEJORES PRÁCTICAS:
    1.  **Estructura General:** Raíz `<article>` con `xmlns:xlink="http://www.w3.org/1999/xlink"` y `xml:lang="es"`. Debe contener `<front>`, `<body>`, y `<back>`.
    2.  **Sección <front>:**
        *   Incluye `<article-title>` y, si está disponible en el texto, `<article-id pub-id-type="doi">`.
        *   **IMPORTANTE - Orden de elementos en <contrib>:** Dentro de cada `<contrib contrib-type="author">`, debes seguir ESTRICTAMENTE este orden de elementos (si están presentes):
            1.  `<contrib-id contrib-id-type="orcid">` (si existe ORCID).
            2.  `<name>` (con `<surname>` y `<given-names>`).
            3.  `<xref ref-type="aff" rid="affX">` (referencias a afiliaciones).
            4.  `<xref ref-type="corresp" rid="cor1">` (si es autor de correspondencia).
            5.  `<email>` (correo electrónico).
            NO coloques `contrib-id` después del nombre. NO coloques `xref` antes del nombre. El orden es CRÍTICO para la validación.
        *   Crea un `<aff>` por cada filiación en `<contrib-group>`, con `id` (`aff1`, `aff2`, ...) y un `<label>` numérico.
        *   Marca al responsable de correspondencia con `corresp="yes"` en el atributo de `<contrib>`, y registra el dato completo en `<author-notes><corresp id="cor1"><email>...</email></corresp></author-notes>`.
        *   Mantén `<abstract>` y `<kwd-group>` como en la especificación original.
    3.  **Sección <body>:**
        *   Usa `<sec>` para secciones con un `<title>`. Los párrafos deben ir en `<p>`.
        *   **Referencias en el cuerpo:** Identifica citas bibliográficas en formato numérico (Vancouver: `1`, `[1]`, `1-3`, etc.) y en formato autor-fecha (APA: `(Apellido, 2020)`, `(Apellido & Otro, 2019)`, etc.). Normaliza la cita reemplazando el texto original por elementos `<xref ref-type="bibr" rid="ID_DE_REFERENCIA">`. El contenido textual del `<xref>` debe reflejar el estilo original (por ejemplo, `[1]` o `(Apellido, 2020)`). Cada `<xref>` debe apuntar al `id` del `<ref>` correspondiente en la sección de bibliografía.
        *   **Manejo de Placeholders:**
            *   **Imágenes:** Si encuentras `[IMAGEN-PLACEHOLDER file="..." caption="..."]`, conviértelo a la siguiente estructura JATS:
                ```xml
                <fig id="f_ID_UNICO">
                  <label>Figura X</label>
                  <caption><p>Texto del pie de foto aquí</p></caption>
                  <graphic mimetype="image" xlink:href="NOMBRE_DEL_ARCHIVO_AQUI"/>
                </fig>
                ```
                Reemplaza los valores correspondientes. Genera un `id` único y una `label` secuencial.
            *   **Tablas:** Si encuentras `[TABLA-PLACEHOLDER caption="..." content="..."]`, donde el contenido es texto delimitado por `|` para columnas y `;` para filas, conviértelo a:
                ```xml
                <table-wrap id="t_ID_UNICO">
                  <label>Tabla X</label>
                  <caption><p>Título de la tabla aquí</p></caption>
                  <table>
                    <thead>
                      <tr>
                        <th>Encabezado 1</th>
                        <th>Encabezado 2</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>Dato fila 1, col 1</td>
                        <td>Dato fila 1, col 2</td>
                      </tr>
                      <tr>
                        <td>Dato fila 2, col 1</td>
                        <td>Dato fila 2, col 2</td>
                      </tr>
                    </tbody>
                  </table>
                </table-wrap>
                ```
                Interpreta la primera fila del contenido como `<thead>` con `<th>` y las siguientes como `<tbody>` con `<td>`.
    4.  **Sección <back>:** Usa `<ref-list>` y `<ref>` para la bibliografía, desglosando con `<element-citation>`. Asegúrate de que cada `<ref>` tenga un `id` único (por ejemplo `ref1`, `ref2`, …) y que coincida con los atributos `rid` utilizados en los `<xref>` del cuerpo. Si detectas múltiples citas que apuntan a la misma referencia, reutiliza el mismo `id`.
    5.  **Reglas Finales:**
        *   El XML debe ser perfectamente bien formado.
        *   No incluyas explicaciones en la salida, solo el código XML.
        *   Codifica caracteres especiales (`&` como `&amp;`, etc.).

    TEXTO DEL ARTÍCULO A CONVERTIR:
    ---
    {texto_articulo}
    ---
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


def invocar_gemini_cli(prompt: str, max_attempts: int = 3, base_backoff: int = 20) -> Dict[str, Any]:
    """Invoca la CLI de Gemini para procesar el prompt, con lógica de reintentos.

    Args:
        prompt (str): El prompt a enviar a Gemini.
        max_attempts (int, optional): Número máximo de intentos. Por defecto 3.
        base_backoff (int, optional): Segundos base para esperar entre reintentos. Por defecto 20.

    Returns:
        Dict[str, Any]: Diccionario con 'stdout', 'stderr', 'returncode', y 'elapsed'.
    """
    command = ["gemini", "-p", prompt, "-o", "text"]
    last_result: Dict[str, Any] = {'stdout': '', 'stderr': '', 'returncode': 1, 'elapsed': 0.0}

    for attempt in range(1, max_attempts + 1):
        try:
            start = time.time()
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                encoding="utf-8",
                cwd=str(WORKSPACE_ROOT),
            )
            elapsed = time.time() - start
        except FileNotFoundError:
            msg = "Error: El comando 'gemini' no se encontró. Verifica tu instalación."
            print(msg, file=sys.stderr)
            return {'stdout': '', 'stderr': msg, 'returncode': 127, 'elapsed': 0.0}
        except Exception as exc:
            msg = f"Error inesperado al invocar a Gemini: {exc}"
            print(msg, file=sys.stderr)
            return {'stdout': '', 'stderr': msg, 'returncode': 1, 'elapsed': 0.0}

        stdout = result.stdout.strip() if result.stdout else ''
        stderr = result.stderr.strip() if result.stderr else ''
        last_result = {'stdout': stdout, 'stderr': stderr, 'returncode': result.returncode, 'elapsed': elapsed}

        # Si tenemos éxito y no hay error de rate limit, retornamos
        if stdout and not _should_retry_gemini(stderr, stdout):
            return last_result

        # Detener si llegamos al máximo
        if attempt >= max_attempts:
            break

        # Si hay error de cuota, esperar y reintentar
        if _should_retry_gemini(stderr, stdout):
            wait_time = base_backoff * attempt
            print(f"Aviso: Límite de recursos en Gemini. Reintentando en {wait_time}s...", file=sys.stderr)
            time.sleep(wait_time)
            continue

        break

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
        WORKSPACE_ROOT / "JATS-Publishing-1-3-MathML3-DTD" / DTD_FILENAME
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
            f'<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD with MathML3 v1.3 20210610//EN" "{DTD_FILENAME}">',
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
            dtd_decl = f'<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.3 20210610//EN" "{DTD_FILENAME}">' 
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