import base64
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st
from fpdf import FPDF

from modules.theme import render_sidebar_footer

# --- CONTENIDO MANUAL DE USUARIO (Hardcoded + Images) ---
MANUAL_SECTIONS = [
    {
        "type": "text",
        "title": "Introducción",
        "content": """
El **Transformador XML JATS** es una herramienta especializada diseñada para optimizar y automatizar el flujo de trabajo editorial de la **Universidad de Valparaíso**. 

Esta solución convierte manuscritos en formato Microsoft Word (`.docx`) o PDF al estándar **JATS XML (Journal Article Tag Suite)**, asegurando el cumplimiento con los requisitos de indexación y preservación digital de revistas científicas (OJS, PubMed Central, SciELO, Latindex, etc.).

**Características principales:**
- Extracción automática de metadatos con IA (título, autores, DOI, fechas, ORCID, afiliaciones).
- Arquitectura Multi-Agente: genera múltiples versiones del XML con distintos modelos de IA y selecciona la mejor.
- Validación automática contra el DTD oficial JATS 1.3 / 1.4 (ANSI/NISO Z39.96-2024).
- Corrección asistida por IA cuando se detectan errores de estructura XML.
- Generación de HTML5 responsivo con DOIs clickeables y tabla de contenidos interactiva.
- Soporte para múltiples proveedores de IA: Google Gemini, OpenAI, Anthropic, DeepSeek, Mistral, Groq y modelos locales (Ollama, LM Studio).
"""
    },
    {
        "type": "step",
        "title": "Paso 1 — Configurar la Clave de API",
        "content": """
Antes de usar el Transformador, necesitas configurar al menos una clave de API de un proveedor de IA.

**Cómo configurar tu API Key:**

1. En el menú lateral izquierdo, haz clic en **"⚙️ API y Tokens"**.
2. En la sección **"🤖 Proveedor de IA Activo"**, selecciona tu proveedor preferido (se recomienda **Google Gemini** para empezar, ya que ofrece tier gratuito generoso).
3. Haz clic en la pestaña de tu proveedor dentro de **"🔑 Claves de API"**.
4. Pega tu API Key en el campo de texto y presiona **"💾 Guardar"**.
5. Una vez guardada, la clave desaparece de la interfaz y se muestra enmascarada (ej. `AIza••••••xY4Z`).

**¿Dónde obtener una API Key gratuita?**

- **Google Gemini:** [aistudio.google.com/apikey](https://aistudio.google.com/apikey) — 500 requests/día gratuitas con `gemini-2.5-flash`.
- **OpenAI:** [platform.openai.com/api-keys](https://platform.openai.com/api-keys) — pay-as-you-go.
- **Groq:** [console.groq.com/keys](https://console.groq.com/keys) — tier gratuito disponible.
- **Ollama (local):** No requiere clave. Instala desde [ollama.com](https://ollama.com) y ejecuta localmente sin costo.

> 🔒 **Seguridad:** Tu clave se almacena localmente en `data/config.db` con ofuscación Base64. Nunca se envía a servidores externos distintos al proveedor de IA seleccionado.
""",
        "image": "resources/manual_images/01.png",
        "caption": "Figura 1: Panel de Configuración de API Keys con proveedor activo y estado de cada clave configurada."
    },
    {
        "type": "step",
        "title": "Paso 2 — Configurar los Datos de la Revista",
        "content": """
Para evitar reescribir los mismos datos en cada artículo, configura los metadatos persistentes de tu revista.

**Cómo configurar los datos de la revista:**

1. En **"⚙️ API y Tokens"**, baja hasta la sección **"📄 Datos por Defecto y Estándar JATS"**.
2. Rellena los campos:
   - **Título de la Revista**: nombre oficial completo (ej. `Revista Médica de Chile`).
   - **Editorial (Publisher)**: institución que publica la revista (ej. `Universidad de Valparaíso`).
   - **ISSN**: número ISSN de la revista (ej. `0034-9887`).
3. Selecciona la **Versión JATS** a generar:
   - **JATS 1.4** (recomendado): soporte mejorado para accesibilidad y matemáticas.
   - **JATS 1.3**: usa solo si tu sistema editorial (OJS legacy) lo requiere específicamente.
4. Presiona **"💾 Guardar Datos"**.

Estos datos se inyectarán automáticamente en el XML de cada artículo que proceses, sin necesidad de ingresarlos manualmente cada vez.
""",
        "image": "resources/manual_images/02.png",
        "caption": "Figura 2: Configuración de los datos permanentes de la revista y selección del estándar JATS a generar."
    },
    {
        "type": "step",
        "title": "Paso 3 — Monitorear tu Cuota de Tokens",
        "content": """
El panel de consumo te permite controlar el uso de tu cuota gratuita y evitar interrupciones.

**Cómo usar el panel de consumo:**

1. En **"⚙️ API y Tokens"**, desplázate hasta la sección **"📊 Consumo de Tokens"**.
2. Verás 4 métricas clave:
   - **Requests hoy**: cuántas solicitudes has hecho hoy vs. el límite diario del tier gratuito.
   - **Tokens hoy**: cantidad total de tokens procesados en el día.
   - **Total histórico**: acumulado de todos los tokens desde que empezaste a usar la herramienta.
   - **Operaciones totales**: número total de transformaciones y correcciones realizadas.
3. La **barra de progreso** muestra visualmente el porcentaje de cuota consumida:
   - 🟢 Verde: menos del 80% consumido — estás bien.
   - 🟡 Amarillo: entre 80% y 100% — precaución, estás cerca del límite.
   - 🔴 Rojo: cuota agotada — las solicitudes fallarán hasta que se renueve (00:00 UTC).
4. Los gráficos de **uso diario** muestran el historial de los últimos 30 días.

**Tip:** Si tu cuota se agota con frecuencia, considera cambiar al modelo `gemini-2.0-flash` (1500 requests/día gratuitas) o activar la facturación en Google Cloud para uso ilimitado Pay-as-you-go.
""",
        "image": "resources/manual_images/03.png",
        "caption": "Figura 3: Panel de consumo de tokens con métricas diarias, históricas y gráfico de uso de los últimos 30 días."
    },
    {
        "type": "step",
        "title": "Paso 4 — Preparar el Documento Word",
        "content": """
La calidad del XML generado depende directamente de la estructura del documento fuente. Sigue estas recomendaciones antes de cargar tu archivo.

**Buenas prácticas para el documento Word (.docx):**

✅ **Estructura recomendada:**
- Usa estilos de Word (Título 1, Título 2, etc.) para marcar secciones — el sistema los detecta automáticamente.
- El título del artículo debe estar al inicio, en una línea sola, con letra grande o estilo "Título".
- Los nombres de autores deben aparecer bajo el título, idealmente con ORCID y afiliación.
- El DOI debe estar visible (ej. `DOI: 10.1234/revista.2024.001`).
- Las secciones estándar (Introducción, Métodos, Resultados, Discusión, Conclusiones) deben tener título explícito.
- Las referencias deben estar al final, numeradas o en formato APA/Vancouver.

✅ **Tablas:**
- Usa las herramientas de tabla de Word (no tablas dibujadas manualmente).
- La primera fila debe ser el encabezado de la tabla.
- Evita celdas combinadas complejas que puedan dificultar la extracción.

⚠️ **Qué evitar:**
- Tablas anidadas (tablas dentro de tablas).
- Texto en cuadros de texto flotantes — el sistema puede no extraerlos.
- Imágenes con texto incrustado (prefiere texto real en el documento).
- Ecuaciones como imágenes — las ecuaciones de Word (editor de ecuaciones) se extraen mejor.

> **Soporte PDF:** También puedes subir `.pdf`, pero el formato `.docx` es siempre preferible ya que permite una extracción más completa y estructurada.
""",
        "image": None,
        "caption": ""
    },
    {
        "type": "step",
        "title": "Paso 5 — Cargar el Archivo",
        "content": """
Una vez que tu documento está listo, es momento de cargarlo en el Transformador.

**Cómo cargar el archivo:**

1. En el menú lateral, navega a **"📄 Transformador"**.
2. Verás el área de carga de archivos con el texto **"Arrastra y suelta tu archivo aquí"** o el botón **"Browse files"**.
3. Selecciona o arrastra tu archivo `.docx` o `.pdf`.
4. El sistema comenzará automáticamente a:
   - Extraer el texto completo del documento.
   - Detectar y extraer las tablas.
   - Identificar imágenes (en el caso de DOCX).
   - Invocar la IA para extraer los metadatos del artículo.
5. Mientras se procesa, verás un indicador de progreso.

**Formatos soportados:**
- `.docx` — Microsoft Word (recomendado)
- `.pdf` — Documento PDF

> ⏱️ El tiempo de procesamiento varía según el tamaño del artículo: un artículo típico de 8-12 páginas tarda entre 15 y 45 segundos dependiendo del proveedor de IA y la conexión a internet.
""",
        "image": "resources/manual_images/05.png",
        "caption": "Figura 5: Área de carga de documentos. El sistema extrae automáticamente el contenido y los metadatos."
    },
    {
        "type": "step",
        "title": "Paso 6 — Revisar y Completar los Metadatos",
        "content": """
Tras la extracción, el sistema muestra los metadatos detectados para que los revises y completes antes de generar el XML.

**Metadatos que se extraen automáticamente:**

| Campo | Descripción |
|-------|-------------|
| **Título** | Título completo del artículo |
| **Autores** | Nombre y apellido de cada autor |
| **DOI** | Identificador digital del artículo |
| **Fecha de publicación** | Año, mes y día de publicación |
| **Fecha de recepción** | Cuándo se recibió el manuscrito |
| **Fecha de aceptación** | Cuándo fue aceptado para publicación |
| **Afiliaciones** | Institución de cada autor |
| **Resumen (Abstract)** | Resumen del artículo |
| **Palabras clave** | Keywords del artículo |

**Qué hacer si faltan datos:**

- Haz clic en cualquier campo editable y modifica el valor directamente.
- Si el **DOI** o la **fecha de publicación** no se detectaron automáticamente, el **Chatbot Asistente** se activará para pedírtelos. Puedes responder en el chat con el valor correspondiente.
- Revisa la sección de **texto extraído** para verificar que el contenido del artículo se capturó correctamente.
- Revisa las **tablas detectadas** al pie de la sección para confirmar que las tablas se extrajeron con todos sus datos.

> ⚠️ El **DOI** y la **fecha de publicación** son **obligatorios** para generar el XML JATS. Si no los tienes, el sistema no permitirá avanzar al siguiente paso.
""",
        "image": "resources/manual_images/06.png",
        "caption": "Figura 6: Formulario de metadatos extraídos automáticamente. Todos los campos son editables antes de continuar."
    },
    {
        "type": "step",
        "title": "Paso 7 — Usar el Chatbot Asistente",
        "content": """
Si hay información faltante o quieres ajustar los metadatos, el Chatbot Asistente te guía de forma conversacional.

**Cuándo se activa el Chatbot:**
- Automáticamente cuando el DOI o la fecha de publicación no se detectaron.
- Cuando quieres modificar o añadir información que el sistema no encontró.

**Cómo interactuar con el Chatbot:**

1. El chatbot aparece debajo del formulario de metadatos si detecta información faltante.
2. Lee el mensaje del chatbot — te preguntará específicamente qué información necesita.
3. Escribe tu respuesta en el campo de texto (ej. `10.1234/revista.2024.001` para el DOI).
4. Presiona **Enter** o el botón de enviar.
5. El chatbot confirmará que recibió la información y actualizará los metadatos automáticamente.
6. Puedes continuar el diálogo si hay más datos incompletos.

**Ejemplos de interacción:**

```
🤖 Chatbot: No encontré el DOI del artículo. ¿Puedes proporcionarlo?
👤 Tú: El DOI es 10.1234/rev.uv.2024.001
🤖 Chatbot: ✅ DOI registrado: 10.1234/rev.uv.2024.001

🤖 Chatbot: ¿Cuál es la fecha de publicación? (formato: día/mes/año)
👤 Tú: 15 de marzo de 2024
🤖 Chatbot: ✅ Fecha de publicación: 15/03/2024
```

> 💡 También puedes usar el chatbot para pedir al asistente que reformule el resumen, corrija un nombre de autor o añada afiliaciones faltantes.
""",
        "image": None,
        "caption": ""
    },
    {
        "type": "step",
        "title": "Paso 8 — Seleccionar Modelos y Generar el XML JATS",
        "content": """
Con los metadatos confirmados, es momento de generar el XML JATS. Puedes usar uno o múltiples modelos de IA simultáneamente.

**Cómo generar el XML:**

1. En la pestaña **"Generación"** del Transformador, verás el selector de modelos.
2. Selecciona uno o más modelos de IA de la lista desplegable:
   - **Modo simple:** selecciona un solo modelo para una generación rápida.
   - **Modo Multi-Agente:** selecciona 2-3 modelos para generar múltiples versiones en paralelo y elegir la mejor.
3. Presiona el botón **"🚀 Generar XML JATS"**.
4. El sistema procesará el artículo aplicando el estándar JATS 1.4:
   - Etiquetará todas las secciones (`<sec>`, `<title>`, `<p>`).
   - Convertirá las tablas a `<table-wrap>` con `<thead>`/`<tbody>`.
   - Estructurará los metadatos en `<article-meta>`.
   - Formateará las referencias bibliográficas en `<ref-list>`.
5. Una barra de progreso mostrará el avance en tiempo real.

> ⏱️ La generación típicamente toma 30-90 segundos por modelo. Con múltiples modelos en paralelo, el tiempo total es similar al del modelo más lento.

> 🔢 El sistema soporta artículos de hasta 65 536 tokens de salida — equivalente a artículos de ~50 páginas sin truncamiento.
""",
        "image": "resources/manual_images/08.png",
        "caption": "Figura 8: Interfaz de generación XML JATS. Selecciona los modelos de IA que competirán en la generación simultánea."
    },
    {
        "type": "step",
        "title": "Paso 9 — Leaderboard: Seleccionar el Mejor XML",
        "content": """
Cuando generas XML con múltiples modelos, el Leaderboard te ayuda a comparar y seleccionar el resultado de mayor calidad.

**Cómo funciona el Leaderboard:**

1. Tras la generación, aparece un panel con una tabla comparativa de todos los modelos utilizados.
2. Cada modelo recibe:
   - **Puntaje DTD (%):** porcentaje de precisión estructural contra el DTD JATS oficial. Un 100% significa que el XML es perfectamente válido.
   - **Auditoría Semántica:** indicador de si el XML contiene placeholders (`<!-- ... -->`) o secciones vacías.
   - **Densidad de texto:** métrica que compara la cantidad de texto en el XML vs. el documento original.
3. El modelo con mayor puntaje es marcado automáticamente como **"🏆 Ganador"**.
4. Puedes revisar el XML de cualquier modelo haciendo clic en **"Ver XML"** junto a su nombre.
5. Si prefieres usar un modelo diferente al ganador automático, selecciónalo manualmente.
6. Confirma tu selección con **"Usar este XML"** para proceder a la validación.

**¿Qué hace que un XML sea de mejor calidad?**

- Mayor cobertura del DTD (menos errores estructurales).
- Sin placeholders ni comentarios de IA en el contenido.
- Texto del artículo completamente transcrito (no resumido).
- Tablas correctamente estructuradas con todos los datos.
- Referencias bibliográficas completas y bien formateadas.
""",
        "image": "resources/manual_images/09.png",
        "caption": "Figura 9: Leaderboard Multi-Agente con puntajes de calidad JATS. El ganador se determina automáticamente."
    },
    {
        "type": "step",
        "title": "Paso 10 — Validar el XML contra el DTD JATS",
        "content": """
La validación DTD garantiza que el XML generado cumple con el estándar oficial JATS y puede ser procesado por sistemas de publicación como OJS.

**Cómo ejecutar la validación:**

1. En la pestaña **"Validación"**, presiona el botón **"✅ Ejecutar Validación DTD"**.
2. El sistema valida el XML contra el DTD JATS 1.3 o 1.4 (según tu configuración) usando el DTD oficial empaquetado localmente — sin necesidad de conexión a internet para esta etapa.
3. Los resultados pueden ser:
   - **✅ Validación exitosa:** el XML cumple con el estándar JATS al 100%. Puedes proceder directamente a la descarga.
   - **⚠️ Errores encontrados:** el sistema lista cada error con su línea y descripción. Se habilita el botón de corrección automática.

**Errores comunes y sus causas:**

| Error | Causa probable |
|-------|---------------|
| `Element 'xxx' not expected` | Etiqueta JATS no válida o mal anidada |
| `Attribute 'xxx' not allowed` | Atributo no soportado en esa versión JATS |
| `Content model error` | Orden incorrecto de elementos hijos |
| `ID 'xxx' is not unique` | Dos elementos con el mismo atributo `id` |
| `IDREF error` | Una referencia apunta a un ID que no existe |

> 💡 No todos los errores impiden la publicación. Algunos son advertencias menores que el Agente Editorial puede corregir automáticamente.
""",
        "image": "resources/manual_images/10.png",
        "caption": "Figura 10: Resultado de la validación DTD JATS. Un XML válido al 100% puede descargarse y publicarse directamente."
    },
    {
        "type": "step",
        "title": "Paso 11 — Corregir Errores con el Agente Editorial",
        "content": """
Si la validación encuentra errores, el Agente Editorial IA puede analizarlos y proponer correcciones automáticamente.

**Cómo usar el Agente Editorial:**

1. Tras una validación fallida, haz clic en **"🔧 Intentar Solucionar con IA"**.
2. El sistema envía el XML con errores y el informe de errores DTD al Agente Editorial.
3. El Agente analiza cada error y genera una versión corregida del XML, **preservando completamente el texto original** del artículo — solo modifica la estructura de etiquetas.
4. Una vez generada la corrección, el sistema ejecuta automáticamente una segunda validación.
5. Si quedan errores menores, puedes repetir el proceso (se recomiendan máximo 3 iteraciones).

**Corrección manual alternativa:**

Si prefieres corregir el XML manualmente:
1. Haz clic en **"✏️ Editar XML"** para abrir el editor de texto integrado.
2. Modifica las líneas con error según el informe de validación.
3. Presiona **"💾 Aplicar cambios"** para guardar y volver a validar.

**El Chatbot de Corrección:**

También puedes dialogar directamente con la IA para correcciones específicas:
```
👤 Tú: La tabla de resultados no tiene thead, solo tbody. ¿Puedes añadirlo?
🤖 Agente: He añadido el elemento <thead> con los encabezados detectados...
```

> ⚠️ Si después de 3 iteraciones de corrección automática persisten errores, revisa el documento Word original — puede tener estructuras inusuales que requieren edición manual del XML.
""",
        "image": None,
        "caption": ""
    },
    {
        "type": "step",
        "title": "Paso 12 — Vista Previa HTML y Exportación",
        "content": """
Una vez validado el XML, puedes generar una vista previa HTML y descargar los archivos finales.

**Generar la Vista Previa HTML:**

1. En la sección **"Resultados"**, presiona **"🌐 Generar HTML"**.
2. El sistema convierte el XML JATS a un archivo HTML5 responsivo con:
   - Logo de la universidad incrustado (Base64).
   - Tabla de contenidos interactiva con anclas a cada sección.
   - Referencias bibliográficas con DOIs clickeables que enlazan a doi.org.
   - Soporte para modo claro y oscuro.
   - Diseño responsivo para móviles y escritorio.
3. Haz clic en **"🔍 Ver vista previa en nueva pestaña"** para abrir el HTML en el navegador.
   - Los enlaces internos (citas `[1]`, `[2]`) navegan correctamente dentro del artículo.
   - Los DOIs en las referencias son clickeables y abren doi.org.
4. Revisa el HTML y confirma que el artículo se ve correctamente antes de descargarlo.

**Descargar los archivos:**

Presiona los botones de descarga para obtener:
- **📥 Descargar XML JATS**: el archivo `.xml` validado, listo para subir a OJS u otro sistema editorial.
- **📥 Descargar HTML**: la vista web del artículo para publicación o archivo.
- **📥 Descargar Manual PDF**: el manual de usuario completo en formato PDF.

> 💡 El archivo XML descargado incluye la declaración `<!DOCTYPE>` correcta para la versión JATS seleccionada (1.3 o 1.4), lista para ser importada directamente en Open Journal Systems (OJS).
""",
        "image": "resources/manual_images/12.png",
        "caption": "Figura 12: Vista previa HTML del artículo con tabla de contenidos interactiva y referencias con DOIs clickeables."
    }
]

FAQ_CONTENT = """
**¿Qué formatos de documento soporta la herramienta?**
Soporta archivos Microsoft Word (`.docx`) y documentos PDF (`.pdf`). El formato `.docx` es preferido ya que permite una extracción más estructurada del contenido, tablas e imágenes. Los PDFs con texto seleccionable funcionan bien; los PDFs escaneados (imágenes) tienen extracción limitada.

**¿Necesito conocimientos de XML o JATS para usar la herramienta?**
No. La herramienta está diseñada para usuarios editoriales sin conocimientos técnicos en XML. La IA se encarga de todo el etiquetado. Sin embargo, si deseas editar el XML manualmente, el editor integrado y el chatbot pueden guiarte.

**¿Qué hago si falla la validación DTD?**
Usa el botón **"🔧 Intentar Solucionar con IA"** para que el Agente Editorial corrija los errores automáticamente. Si persisten tras 3 intentos, revisa que el documento Word no tenga tablas anidadas complejas ni cuadros de texto flotantes. También puedes editar el XML manualmente usando el editor integrado.

**¿Las tablas del documento se incluyen en el XML?**
Sí. Las tablas se extraen automáticamente y se convierten a formato JATS (`<table-wrap>`) con encabezados (`<thead>`) y cuerpo (`<tbody>`) correctamente estructurados, preservando todas las filas y columnas del original. Las tablas muy complejas con celdas combinadas pueden requerir revisión manual.

**¿Se incluye el DOI y la fecha de publicación en el XML?**
Sí. El DOI y la fecha de publicación son campos obligatorios que se extraen automáticamente. Si el sistema no los detecta en el documento, el Chatbot Asistente te los pedirá antes de permitir la generación del XML.

**¿Los caracteres especiales (tildes, ñ, etc.) se preservan correctamente?**
Sí. El sistema usa codificación UTF-8 en todo el flujo (extracción, generación XML y conversión HTML). Los caracteres acentuados, la ñ, el ü y otros caracteres especiales del español se preservan correctamente.

**¿Los enlaces del HTML funcionan correctamente?**
Sí. Los enlaces de citas (ej. `[1]`, `[2]`) y la tabla de contenidos navegan correctamente dentro de la página HTML. Los DOIs en las referencias bibliográficas son clickeables y enlazan directamente a `doi.org`. Usa siempre el botón **"Ver vista previa en nueva pestaña"** para la mejor experiencia de navegación.

**¿Es seguro subir mis archivos?**
Los archivos se procesan temporalmente en memoria del servidor y **no se almacenan permanentemente**. El texto del artículo se envía a la API del proveedor de IA seleccionado (ej. Google Gemini) bajo los términos de servicio de ese proveedor. Para máxima privacidad, usa **Ollama** (inferencia local) — el contenido no sale del servidor.

**¿Mi API Key está segura?**
Sí. La clave se almacena localmente en `data/config.db` (carpeta excluida de Git) con ofuscación Base64. Una vez guardada, desaparece de la interfaz y solo se muestra enmascarada (ej. `AIza••••••xY4Z`). La clave nunca se envía a ningún servidor externo distinto al proveedor de IA correspondiente.

**¿Qué pasa si alcanzo el límite de tokens gratuitos de Gemini?**
El panel de consumo en **"⚙️ API y Tokens"** muestra tu consumo actual vs. los límites del tier gratuito. Al alcanzar el 80%% se muestra una advertencia; al 100%% los requests fallarán con error 429. Puedes:
- Esperar a las 00:00 UTC para que el límite diario se renueve.
- Cambiar a `gemini-2.0-flash` (1500 req/día gratuitas).
- Activar facturación en Google Cloud para uso Pay-as-you-go con la misma clave.
- Configurar otro proveedor (OpenAI, Groq, etc.) como alternativa.

**¿Puedo usar el sistema sin conexión a internet?**
Parcialmente. Si usas **Ollama** o **LM Studio** (proveedores locales), la generación de XML funciona sin internet. Sin embargo, la validación DTD usa el DTD empaquetado localmente, por lo que también funciona offline. Solo la interfaz web y la descarga del manual PDF requieren conexión.

**¿Qué versión de JATS debo usar: 1.3 o 1.4?**
Usa **JATS 1.4** a menos que tu sistema editorial (OJS, etc.) especifique explícitamente que requiere 1.3. JATS 1.4 añade mejoras en accesibilidad, matemáticas estructuradas y afiliaciones. La versión se configura en **"⚙️ API y Tokens"** → **"Estándar XML JATS"**.

**¿Puedo procesar múltiples artículos a la vez?**
La interfaz web procesa un artículo a la vez. Para procesamiento por lotes, usa la interfaz de línea de comandos (CLI):
```bash
python -m modules.transformer articulo1.docx salida1.xml
python -m modules.transformer articulo2.docx salida2.xml
```
"""

def get_documentation_content():
    """Lee README y CONTRIBUTING."""
    docs = []
    
    # README
    readme_path = Path("README.md")
    if readme_path.exists():
        docs.append({"title": "Documentación General (README)", "content": readme_path.read_text(encoding='utf-8')})
    
    # CONTRIBUTING
    contrib_path = Path("CONTRIBUTING.md")
    if contrib_path.exists():
        docs.append({"title": "Guía de Contribución", "content": contrib_path.read_text(encoding='utf-8')})
        
    return docs

def get_credits_content():
    """Retorna contenido de créditos como texto."""
    return """
Esta herramienta ha sido desarrollada para optimizar el flujo editorial de las Revistas UV, automatizando la conversión de manuscritos a XML JATS validado.

Desarrollador Principal:
Cristian Carreño León (cristian.carreno@uv.cl)
Escuela de Obstetricia y Puericultura
Facultad de Medicina
Universidad de Valparaíso, Chile

Tecnologías Utilizadas:
- Python 3.9+: Lenguaje base.
- Streamlit 1.51+: Framework de interfaz de usuario web.
- Google Gemini 2.5 Flash: Modelo de lenguaje (LLM) principal para etiquetado inteligente.
- OpenAI / Anthropic / DeepSeek / Mistral / Groq: Proveedores alternativos de IA.
- Ollama / LM Studio: Inferencia local sin costo.
- lxml 6.0+: Procesamiento, validación y parsing de XML/HTML.
- python-docx 1.2+: Extracción de contenido desde archivos Word.
- pdfplumber 0.10+: Extracción de texto desde PDFs.
- tenacity 9.1+: Reintentos robustos con backoff exponencial.
- FPDF2: Generación de manuales en PDF.
- SQLite + Fernet: Persistencia local de configuración y API keys cifradas.
- JATS 1.3 / 1.4 (ANSI/NISO Z39.96-2024): Estándar de etiquetado XML.

Privacidad y Tratamiento de Datos:
1. Procesamiento por Demanda: Los artículos se procesan durante la ejecución y no se incorporan a un repositorio persistente de manuscritos.
2. Custodia Local de Credenciales: Las API keys se almacenan cifradas en data/config.db mediante Fernet; la clave criptográfica reside en data/.fernet.key.
3. Proveedor Activo Controlado: El texto se envía únicamente al proveedor de IA seleccionado por el usuario.
4. Inferencia Local: Con Ollama/LM Studio, el procesamiento puede realizarse sin salida de datos a servicios cloud.
5. Recomendación Institucional: Para documentos sensibles, anonimizar previamente y aplicar políticas de protección de datos vigentes.

Seguridad:
1. Secretos fuera de control de versiones: data/ permanece excluido por .gitignore.
2. Reporte responsable de vulnerabilidades: contacto directo con el responsable del proyecto antes de divulgar públicamente.
3. Dependencias y riesgo: toda librería nueva debe revisarse por vulnerabilidades conocidas (CVE) antes de su adopción.
4. Evidencia segura: no compartir capturas o logs que incluyan datos de manuscritos reales.

Licencia:
Software de uso exclusivo para la Universidad de Valparaíso. Todos los derechos reservados.
El código y la documentación son propiedad de la Universidad de Valparaíso y su autor.
El uso de servicios de terceros está sujeto a términos de cada proveedor (cloud o local) seleccionado por el usuario.

Version: 0.7.5
"""

class ProfessionalPDF(FPDF):
    def header(self):
        # Logo
        logo_path = "resources/UV_color.png"
        if os.path.exists(logo_path):
            self.image(logo_path, 10, 8, 33)
        
        self.set_font('Arial', 'B', 10)
        self.cell(80) # Move to right
        self.cell(100, 10, 'Manual de Usuario - Transformador XML JATS', 0, 0, 'R')
        self.ln(20)
        # Line break
        self.line(10, 25, 200, 25)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Generado el {datetime.now().strftime("%d/%m/%Y")} | Página ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')

def clean_text_for_pdf(text):
    """Limpia caracteres markdown básicos y elimina caracteres no soportados por latin-1 (emojis)."""
    # Remove bold/italic markers only if they are not part of a header structure we parse later?
    # Actually for simple FPDF text, we want to strip them usually.
    # But let's leave proper headers (#) alone here so we can detect them in the loop.
    text = text.replace('**', '').replace('__', '').replace('`', '').strip()
    return text.encode('latin-1', 'ignore').decode('latin-1')


def _is_markdown_table_separator(line: str) -> bool:
    """Detecta separadores de tabla markdown como |---|:---:|."""
    stripped = line.replace('|', '').replace(':', '').replace('-', '').strip()
    return stripped == '' and '-' in line


def _parse_markdown_table(lines, start_idx: int):
    """Parsea bloque de tabla markdown y retorna (headers, rows, next_idx)."""
    headers = [c.strip() for c in lines[start_idx].strip().strip('|').split('|')]
    rows = []
    i = start_idx + 2  # Skip separator line

    while i < len(lines):
        raw = lines[i].strip()
        if not raw or '|' not in raw:
            break
        row = [c.strip() for c in raw.strip('|').split('|')]
        rows.append(row)
        i += 1

    return headers, rows, i


def _render_markdown_table(pdf, headers, rows):
    """Renderiza tabla markdown con ancho dinámico y salto de página seguro."""
    if not headers:
        return

    col_count = len(headers)
    available_width = pdf.w - pdf.l_margin - pdf.r_margin
    col_width = available_width / col_count
    row_height = 7

    required = row_height * (2 + len(rows))
    _ensure_pdf_space(pdf, required)

    # Header row
    pdf.set_font('Arial', 'B', 10)
    pdf.set_fill_color(230, 237, 248)
    for header in headers:
        pdf.cell(col_width, row_height, clean_text_for_pdf(header), border=1, align='C', fill=True)
    pdf.ln(row_height)

    # Body rows
    pdf.set_font('Arial', '', 10)
    for row in rows:
        if len(row) < col_count:
            row.extend([''] * (col_count - len(row)))
        elif len(row) > col_count:
            row = row[:col_count]

        _ensure_pdf_space(pdf, row_height + 2)
        for cell in row:
            pdf.cell(col_width, row_height, clean_text_for_pdf(cell), border=1, align='L')
        pdf.ln(row_height)

    pdf.ln(3)

def add_markdown_section_to_pdf(pdf, text):
    """Parsea markdown simple (encabezados/listas/tablas) y lo agrega al PDF."""
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if not line:
            pdf.ln(3)
            i += 1
            continue

        # Tabla markdown: encabezado + separador
        if (
            '|' in line
            and i + 1 < len(lines)
            and _is_markdown_table_separator(lines[i + 1].strip())
        ):
            headers, rows, next_idx = _parse_markdown_table(lines, i)
            _render_markdown_table(pdf, headers, rows)
            i = next_idx
            continue

        # Headers
        if line.startswith('# '):
            _ensure_pdf_space(pdf, 14)
            pdf.ln(3)
            pdf.set_font('Arial', 'B', 16)
            pdf.set_text_color(0, 51, 102)
            pdf.cell(0, 10, clean_text_for_pdf(line.replace('# ', '')), 0, 1, 'L')
            pdf.set_text_color(0)
            pdf.set_font('Arial', '', 11)

        elif line.startswith('## '):
            _ensure_pdf_space(pdf, 13)
            pdf.ln(2)
            pdf.set_font('Arial', 'B', 14)
            pdf.set_text_color(0, 51, 102)
            pdf.cell(0, 9, clean_text_for_pdf(line.replace('## ', '')), 0, 1, 'L')
            pdf.set_text_color(0)
            pdf.set_font('Arial', '', 11)

        elif line.startswith('### '):
            _ensure_pdf_space(pdf, 11)
            pdf.ln(1)
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, clean_text_for_pdf(line.replace('### ', '')), 0, 1, 'L')
            pdf.set_font('Arial', '', 11)

        # Lists
        elif line.startswith('- ') or line.startswith('* '):
            _ensure_pdf_space(pdf, 8)
            pdf.set_font('Arial', '', 11)
            pdf.cell(5)
            content = clean_text_for_pdf(line[2:])
            pdf.multi_cell(0, 6, chr(149) + ' ' + content)

        # Numbered Lists (simple detection "1. ")
        elif len(line) > 2 and line[0].isdigit() and line[1] == '.' and line[2] == ' ':
            _ensure_pdf_space(pdf, 8)
            pdf.set_font('Arial', '', 11)
            pdf.cell(5)
            pdf.multi_cell(0, 6, clean_text_for_pdf(line))

        # Code blocks (simple detection)
        elif line.startswith('```'):
            pass

        # Normal text
        else:
            _ensure_pdf_space(pdf, 8)
            pdf.set_font('Arial', '', 11)
            pdf.multi_cell(0, 6, clean_text_for_pdf(line))

        i += 1


def _extract_step_number(step_title: str) -> str:
    """Extrae el número de paso desde títulos como 'Paso 8 — ...'."""
    match = re.search(r"Paso\s+(\d+)", step_title, flags=re.IGNORECASE)
    return match.group(1) if match else "?"


def _ensure_pdf_space(pdf, required_height: float):
    """Agrega página cuando no hay espacio vertical suficiente para el siguiente bloque."""
    if pdf.get_y() + required_height > pdf.page_break_trigger:
        pdf.add_page()

def create_professional_pdf():
    pdf = ProfessionalPDF()
    pdf.alias_nb_pages()
    
    # --- PORTADA ---
    pdf.add_page()
    
    # Logo Grande
    logo_path = "resources/UV_color.png"
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=65, y=60, w=80)
    
    pdf.set_y(100)
    pdf.set_font('Arial', 'B', 24)
    pdf.cell(0, 10, 'Manual de Usuario', 0, 1, 'C')
    pdf.ln(5)
    pdf.set_font('Arial', '', 16)
    pdf.set_text_color(100)
    pdf.cell(0, 10, 'Transformador XML-JATS', 0, 1, 'C')
    
    pdf.set_y(130)
    pdf.set_font('Arial', '', 12)
    pdf.set_text_color(0)
    pdf.cell(0, 10, 'Universidad de Valparaíso', 0, 1, 'C')
    pdf.cell(0, 10, 'Facultad de Medicina', 0, 1, 'C')
    
    pdf.set_y(180)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 10, 'Autor: Cristian Carreño León', 0, 1, 'C')
    pdf.cell(0, 10, f'Fecha: {datetime.now().strftime("%d-%m-%Y")}', 0, 1, 'C')
    pdf.cell(0, 10, 'Versión: 0.7.5', 0, 1, 'C')
    pdf.cell(0, 10, 'Contacto: cristian.carreno@uv.cl', 0, 1, 'C')
    
    # --- SECCIÓN 1: DOCUMENTACIÓN ---
    docs = get_documentation_content()
    for doc in docs:
        pdf.add_page()
        # Title of the section (e.g. "Documentación General")
        pdf.set_font('Arial', 'B', 16)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 10, doc["title"], 0, 1, 'L', 1)
        pdf.ln(5)
        
        # Render Markdown content properly
        add_markdown_section_to_pdf(pdf, doc["content"])
            
    # --- SECCIÓN 2: MANUAL DE USUARIO ---
    pdf.add_page()
    
    # Intro
    pdf.set_font('Arial', 'B', 16)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, 'Manual de Usuario', 0, 1, 'L', 1)
    pdf.ln(5)
    
    pdf.set_font('Arial', '', 11)
    intro_text = clean_text_for_pdf(MANUAL_SECTIONS[0]["content"])
    pdf.multi_cell(0, 6, intro_text)
    pdf.ln(10)
    
    # Pasos
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Flujo de Trabajo', 0, 1, 'L')
    pdf.ln(5)
    
    for section in MANUAL_SECTIONS:
        if section["type"] == "step":
            # Mantener bloque de título siempre visible y separado.
            _ensure_pdf_space(pdf, 20)

            # Title
            pdf.set_font('Arial', 'B', 13)
            pdf.set_text_color(0, 51, 102) # Dark Blue
            pdf.cell(0, 10, clean_text_for_pdf(section["title"]), 0, 1, 'L')
            pdf.set_text_color(0)
            
            # Content (using markdown parser logic slightly adapted or reuse)
            # The manual sections are simple, mostly lines. Let's use clean_text_for_pdf logic directly
            # but allow bullet points if any exist in the manual content.
            # Actually, let's use the new parser for consistency!
            add_markdown_section_to_pdf(pdf, section["content"])
            pdf.ln(2)
            
            # Image
            image_path = section.get("image")
            if image_path and os.path.exists(image_path):
                # Reservar espacio para imagen + caption; si no cabe, saltar de página
                # y dejar indicador explícito del paso para evitar confusiones.
                _ensure_pdf_space(pdf, 105)
                step_number = _extract_step_number(section["title"])

                pdf.set_font('Arial', 'B', 10)
                pdf.set_text_color(75)
                pdf.cell(0, 6, clean_text_for_pdf(f"Imagen correspondiente al Paso {step_number}"), 0, 1, 'C')
                pdf.set_text_color(0)

                image_width = 140
                image_x = (pdf.w - image_width) / 2
                pdf.image(image_path, w=image_width, x=image_x)

                if "caption" in section:
                    pdf.set_font('Arial', 'I', 9)
                    pdf.cell(0, 8, clean_text_for_pdf(section["caption"]), 0, 1, 'C')
            
            pdf.ln(10)
            
    # FAQ
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Preguntas Frecuentes', 0, 1, 'L')
    pdf.ln(5)
    
    # Use parser for FAQ too to handle bold headers if they were properly markdown 
    # (Currently FAQ_CONTENT uses ** for bold which clean_text strips, 
    # but we can improve FAQ_CONTENT to use ## if we want headers, or just rely on the existing logic there).
    # Since FAQ_CONTENT uses simple **Question?** format, the previous logic was fine. 
    # Let's clean it up to use standard markdown ## for questions if possible, 
    # or just stick to the manual parsing for FAQ which was working okay. 
    # The previous code handled "?" detection. Let's keep a simple loop for FAQ or adapt it.
    
    faq_lines = FAQ_CONTENT.strip().split('\n')
    for line in faq_lines:
        line = clean_text_for_pdf(line)
        if not line:
            pdf.ln(5)
            continue
        if "?" in line and line.endswith("?"): 
            pdf.set_font('Arial', 'B', 11)
            pdf.multi_cell(0, 6, line)
            pdf.set_font('Arial', '', 11)
        else:
            pdf.multi_cell(0, 6, line)
            
    # --- SECCIÓN 3: CRÉDITOS Y LICENCIAS ---
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, 'Créditos y Licencias', 0, 1, 'L', 1)
    pdf.ln(10)
    
    pdf.set_font('Arial', '', 11)
    # Using parser for credits? Credits is simple text.
    credits_text = get_credits_content()
    add_markdown_section_to_pdf(pdf, credits_text)

    return pdf

@st.cache_data(show_spinner="Generando PDF...")
def generate_pdf_bytes(_assets_signature: tuple):
    """Genera el PDF y devuelve los bytes, cacheado para optimizar."""
    try:
        pdf = create_professional_pdf()
        # Use temp file to get bytes safely across platforms/versions
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            pdf.output(tmp_file.name)
            tmp_path = tmp_file.name
        
        with open(tmp_path, "rb") as f:
            pdf_bytes = f.read()
            
        os.unlink(tmp_path)
        return pdf_bytes
    except Exception as e:
        st.error(f"Error generando PDF: {e}")
        return None


def get_assets_signature():
    """Firma simple para invalidar caché si cambian docs o capturas del manual."""
    tracked_paths = [
        Path("README.md"),
        Path("CONTRIBUTING.md"),
        Path(__file__),
    ]

    for section in MANUAL_SECTIONS:
        image_path = section.get("image")
        if image_path:
            tracked_paths.append(Path(image_path))

    signature = []
    for path in tracked_paths:
        if path.exists():
            stat = path.stat()
            signature.append((str(path), int(stat.st_mtime_ns), stat.st_size))
        else:
            signature.append((str(path), -1, -1))

    # Incluye estructura del manual para que cambios de orden, títulos,
    # captions o mapeo de imágenes invaliden la caché del PDF.
    manual_signature = tuple(
        (
            section.get("type", ""),
            section.get("title", ""),
            section.get("image", ""),
            section.get("caption", ""),
            section.get("content", "")[:200],
        )
        for section in MANUAL_SECTIONS
    )
    signature.append(("MANUAL_SECTIONS", manual_signature))

    return tuple(signature)


# ── CSS inyectado una vez por render para el sistema de lightbox ──────────────
_LIGHTBOX_CSS = """<style>
a.ml-t {
    display:block; width:210px; margin:14px 0 6px auto;
    border-radius:10px; overflow:hidden; cursor:zoom-in;
    box-shadow:0 3px 16px rgba(0,51,102,.2); border:1.5px solid #c4d7ee;
    text-decoration:none; transition:transform .22s,box-shadow .22s;
    position:relative;
}
a.ml-t:hover {
    transform:translateY(-3px) scale(1.03);
    box-shadow:0 8px 30px rgba(0,51,102,.32);
}
a.ml-t img { width:100%; display:block; }
.ml-t-badge {
    position:absolute; bottom:0; left:0; right:0;
    padding:22px 8px 7px;
    background:linear-gradient(transparent,rgba(0,20,55,.8));
    color:#fff; font-size:.65em; font-style:italic;
    text-align:center; line-height:1.4; pointer-events:none;
}
.ml-t-zoom {
    position:absolute; top:7px; right:7px;
    background:rgba(255,255,255,.87); border-radius:50%;
    width:26px; height:26px; display:flex; align-items:center;
    justify-content:center; font-size:.75em;
    box-shadow:0 1px 5px rgba(0,0,0,.2); pointer-events:none;
}
.ml-lb {
    display:none;
    position:fixed !important;
    left:0; top:0; width:100vw; height:100vh;
    z-index:2147483000 !important;
}
.ml-lb:target {
    display:flex; align-items:center; justify-content:center;
    animation:ml-fd .22s ease;
}
@keyframes ml-fd {
    from { opacity:0; transform:scale(.96); }
    to   { opacity:1; transform:scale(1); }
}
a.ml-lb-bg {
    position:fixed !important; inset:0; background:rgba(6,16,40,.9);
    z-index:1; cursor:zoom-out; text-decoration:none;
}
.ml-lb-box {
    position:relative; z-index:2;
    max-width:90vw; text-align:center;
}
.ml-lb-box img {
    max-width:100%; max-height:84vh; display:block;
    border-radius:10px; box-shadow:0 10px 52px rgba(0,0,0,.65);
    margin:0 auto;
}
.ml-lb-cap {
    color:#b4cceb; font-size:.78em; font-style:italic;
    padding:10px 0 0; line-height:1.5;
    max-width:620px; margin:0 auto;
}
a.ml-lb-x {
    position:absolute; top:-13px; right:-13px;
    background:#2e7bcf; color:#fff; text-decoration:none;
    border-radius:999px; min-width:110px; height:34px; padding:0 12px;
    display:flex; align-items:center; justify-content:center;
    font-weight:700; font-size:.8em; letter-spacing:.2px;
    box-shadow:0 2px 10px rgba(0,0,0,.38);
    transition:background .15s; z-index:3;
}
a.ml-lb-x:hover { background:#1a5aa0; color:#fff; text-decoration:none; }
.ml-lb-help {
    color:#d7e8ff; font-size:.74em; text-align:center;
    margin-top:7px; letter-spacing:.2px;
}
</style>"""


def _build_lightbox_html(image_path: str, caption: str, lb_id: str) -> str:
    """Construye thumbnail clicable + overlay lightbox CSS puro."""
    if not image_path or not os.path.exists(image_path):
        return ""
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
    ext = Path(image_path).suffix.lstrip(".").lower()
    if ext == "jpg":
        ext = "jpeg"
    src = f"data:image/{ext};base64,{img_b64}"
    short = caption.split(":")[0].strip() if ":" in caption else caption[:42]
    return (
        f'<a href="#{lb_id}" class="ml-t" title="Clic para ampliar">'
        f'<img src="{src}" alt="{short}"/>'
        f'<span class="ml-t-zoom">🔍</span>'
        f'<span class="ml-t-badge">{short}</span>'
        f'</a>'
        f'<div id="{lb_id}" class="ml-lb">'
        f'<a href="#0" class="ml-lb-bg"></a>'
        f'<div class="ml-lb-box">'
        f'<a href="#0" class="ml-lb-x" title="Cerrar">&#x2715; Cerrar</a>'
        f'<img src="{src}" alt="{caption}"/>'
        f'<p class="ml-lb-cap">{caption}</p>'
        f'<p class="ml-lb-help">Clic fuera de la imagen para cerrar</p>'
        f'</div></div>'
    )


def main():
    st.title("📖 Manual de Usuario")
    st.markdown("---")

    # Layout: Intro wide
    st.markdown(MANUAL_SECTIONS[0]["content"])
    
    st.subheader("📍 Flujo de Trabajo Completo")
    
    st.graphviz_chart('''
        digraph Flujo {
            rankdir=LR;
            node [shape=rect, style=filled, color="#2e7bcf", fontcolor=white, fontname="Helvetica", margin="0.2,0.1"];
            edge [color="#666666", fontname="Helvetica", fontsize=9];
            
            Config [label="1-3. Configuración\\n(API Key + Revista + Cuota)"];
            Prepare [label="4. Preparar\\nDocumento"];
            Carga [label="5. Cargar Archivo\\n(.docx o .pdf)"];
            Metadatos [label="6. Revisar\\nMetadatos"];
            Chatbot [label="7. Chatbot\\nAsistente"];
            Generacion [label="8. Seleccionar Modelos\\ny Generar XML"];
            Leaderboard [label="9. Leaderboard\\nMulti-Agente"];
            Validacion [label="10. Validación\\nDTD JATS"];
            Correccion [label="11. Corrección\\nAgente Editorial"];
            Resultados [label="12. Vista Previa HTML\\ny Exportación"];
            
            Config -> Prepare;
            Prepare -> Carga;
            Carga -> Metadatos;
            Metadatos -> Chatbot [label=" si faltan\\n datos"];
            Chatbot -> Generacion [label=" completar"];
            Metadatos -> Generacion [label=" datos OK"];
            Generacion -> Leaderboard [label=" multi-modelo"];
            Leaderboard -> Validacion [label=" seleccionar\\n ganador"];
            Validacion -> Resultados [label=" ✅ éxito", color="green", fontcolor="green"];
            Validacion -> Correccion [label=" ❌ errores", color="red", fontcolor="red"];
            Correccion -> Validacion [label=" re-validar"];
        }
    ''')
    
    st.markdown("<br>", unsafe_allow_html=True)  # safe: static HTML

    # Inyectar CSS lightbox (se aplica en cada render)
    st.markdown(_LIGHTBOX_CSS, unsafe_allow_html=True)  # safe: CSS estático

    # Un paso por bloque — texto full-width + thumbnail compacto clicable
    for i, section in enumerate(MANUAL_SECTIONS):
        if section["type"] == "step":
            with st.container():
                st.markdown(
                    f'<h3 style="color:#1a3a5c;border-left:4px solid #2e7bcf;'
                    f'padding-left:12px;margin:8px 0 6px;">'
                    f'{section["title"]}</h3>',
                    unsafe_allow_html=True,  # safe: contenido estático
                )
                st.markdown(section["content"])

                lb_html = _build_lightbox_html(
                    section.get("image", ""),
                    section.get("caption", ""),
                    f"ml-lb-{i}",
                )
                if lb_html:
                    st.markdown(lb_html, unsafe_allow_html=True)  # safe: base64 + CSS estático

                st.divider()

    with st.expander("❓ Preguntas Frecuentes (FAQ)", expanded=False):
        st.markdown(FAQ_CONTENT)
    
    st.markdown("---")
    
    col_center = st.columns([1, 2, 1])
    with col_center[1]:
        st.info("Obtenga el manual completo en PDF, incluyendo documentación técnica y créditos.")
        
        # Pre-generate or get from cache
        pdf_bytes = generate_pdf_bytes(get_assets_signature())
        
        if pdf_bytes:
            st.download_button(
                label="📄 Descargar Manual Completo PDF",
                data=pdf_bytes,
                file_name="Manual_Usuario_Completo_UV.pdf",
                mime="application/pdf",
                type="primary",
                width="stretch"
            )

    # Sidebar Footer
    with st.sidebar:
        render_sidebar_footer()

if __name__ == "__main__":
    main()
