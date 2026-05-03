# Propuesta de Mejora: Arquitectura Pipeline por Fases para XML-JATS Transformer

**Rama:** `experimento4`  
**Versión base:** 0.7.5  
**Fecha:** 2026-05-03  
**Meta:** Transformar artículos científicos al estándar XML-JATS 1.4 de forma **100% íntegra** (sin resumir, sin modificar, sin truncar), con soporte optimizado para modelos pequeños y ejecutables en dispositivos móviles vía Ollama.

---

## 1. Resumen Ejecutivo

El sistema actual envía el documento completo en un **único prompt monolítico** al modelo de lenguaje. Esto funciona con modelos cloud de gran contexto (Gemini 2.5 Flash, GPT-4o), pero presenta tres fallas estructurales graves:

1. **Truncamiento silencioso**: Artículos extensos (>15-20 páginas) exceden la ventana de contexto o el límite de tokens de salida, generando XML incompleto.
2. **Imposibilidad con modelos pequeños**: Ollama en celulares (Phi-3-mini 3.8B, Qwen2.5-3B, Llama 3.2 3B) tiene ventanas de 4K-8K tokens. El prompt actual de ~8.000-20.000 tokens (instrucciones + texto completo) no cabe.
3. **Falta de verificación estructurada de integridad**: No existe un mecanismo robusto que compare el texto original contra el XML generado para detectar omisiones sección por sección.

Esta propuesta redefine el flujo como un **pipeline de 5 fases**, donde cada fase subdivide la tarea en unidades mínimas procesables por modelos pequeños, con validación intermedia y ensamblaje orquestado.

---

## 2. Análisis del Estado Actual (Evidencia de Código)

### 2.1 Flujo Monolítico de Generación

```
extraer_contenido_estructurado(docx) → string gigante
    ↓
get_generation_prompt(texto_completo, metadata) → prompt único
    ↓
invocar_llm(prompt) → XML completo en una sola respuesta
    ↓
sanitize_generated_xml() → validación DTD
```

**Archivo:** `modules/transformer.py:799-822` (CLI) y `views/transformador.py:599-601` (UI)

- El prompt incluye: instrucciones generales (~3.000 tokens) + metadatos (~500 tokens) + texto del artículo completo + tablas en markdown.
- Para un artículo de 30 páginas (~15.000 palabras ≈ 20.000 tokens), el prompt total puede superar los **25.000-30.000 tokens**.

### 2.2 Mecanismo de Continuación (Insuficiente)

En `transformer.py:288-315`, existe un loop de auto-continuación cuando `finish_reason == MAX_TOKENS`:

```python
while loop_count < 3:
    continuation = _attempt_llm_call(prompt="Continúa generando...")
```

**Problemas:**
- Solo reacciona al truncamiento de **salida**, no al de **entrada** (context window overflow).
- La continuación pierde frecuentemente el contexto estructural (cierra etiquetas incorrectamente, repite secciones).
- No divide el problema; solo pide "seguir escribiendo".

### 2.3 Extracción sin Segmentación Semántica

`extraer_contenido_estructurado()` en `transformer.py:57-136` produce un único string plano con placeholders de imágenes/tablas. No identifica dónde empieza la Introducción, Métodos, Resultados, etc. Esta segmentación se delega enteramente al modelo, aumentando su carga cognitiva.

### 2.4 Validación de Integridad Débil

`verificar_completitud_xml()` en `transformer.py:692-729`:
- Detecta comentarios tipo `<!-- Contenido... -->`.
- Revisa que el `<body>` tenga >500 caracteres.
- **No compara el texto original contra el XML sección por sección.**
- No detecta si el modelo omitió párrafos intermedios o resumió una sección completa.

### 2.5 Corrección como Monolito

Cuando hay errores DTD, `correction.py` envía el **XML completo + lista de errores** en un solo prompt. Para XMLs grandes, esto reproduce el mismo problema de contexto.

---

## 3. Problemas Críticos Identificados

| # | Problema | Impacto | Evidencia |
|---|----------|---------|-----------|
| 1 | **Prompt monolítico** | Truncamiento, omisiones, imposibilidad con contextos pequeños | `prompts.py:67-187`, `transformer.py:799` |
| 2 | **Sin segmentación semántica previa** | El modelo debe adivinar la estructura; mayor tasa de error | `transformer.py:57` |
| 3 | **Validación de integridad insuficiente** | XMLs "válidos" pero vacíos o resumidos pasan el control | `transformer.py:692` |
| 4 | **Corrección monolítica** | Re-corrección de XML grande reproduce el problema de contexto | `correction.py:28-39` |
| 5 | **Sin optimización para Ollama móvil** | Contextos de 4K-8K hacen imposible el uso; sin detección de límite | `llm_provider.py:306-353` |
| 6 | **Tablas grandes en texto plano** | Tablas complejas consumen miles de tokens en el prompt | `transformer.py:114-127` |
| 7 | **Referencias bibliográficas en bloque** | Lista de 50+ referencias en un solo bloque sobrecarga el modelo | `prompts.py:166-169` |
| 8 | **Ausencia de caché por sección** | Si falla una sección, se re-procesa todo el artículo | `views/transformador.py:589-671` |

---

## 4. Objetivos de la Mejora

1. **Integridad 100%**: Cada palabra del documento original debe estar presente en el XML JATS final. Cero resúmenes, cero omisiones, cero placeholders.
2. **Compatibilidad con modelos pequeños**: Funcionar con modelos de 3B-7B parámetros y ventanas de 4K-8K tokens (Ollama en celulares, Raspberry Pi, etc.).
3. **Validación intermedia**: Cada unidad de trabajo debe validarse antes de ensamblarse.
4. **Corrección granular**: Re-procesar solo la sección fallida, no el documento completo.
5. **Transparencia**: El usuario debe poder ver qué secciones se procesaron, cuáles fallaron y por qué.
6. **Cumplimiento fiel JATS 1.4**: Mantener la validación DTD actual como guardrail final.

---

## 5. Propuesta Arquitectónica: Pipeline por Fases

La arquitectura propuesta abandona el modelo "Un Prompt para Todo" en favor de un **pipeline secuencial de micro-tareas**, donde cada tarea tiene un prompt mínimo y un scope acotado.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FASE 0: PRE-PROCESAMIENTO                         │
│  extraer_contenido_estructurado() + SEGMENTACIÓN SEMÁNTICA          │
│  (heurística, sin IA: divide en Front, BodySections, Back)          │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    FASE 1: GENERACIÓN DEL FRONT                      │
│  Input: metadatos ya extraídos + configuración de revista           │
│  Output: XML del <front> completo                                   │
│  Modelo: Cualquiera (prompt muy corto, ~500 tokens)                 │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    FASE 2: GENERACIÓN DEL BODY (por chunks)          │
│  Input: cada sección del body (Intro, Métodos, Resultados...)       │
│  Output: lista de fragmentos XML <sec>...</sec>                     │
│  Modelo: Pequeño o grande; cada prompt es independiente             │
│  Paralelizable: Sí (cada sección es independiente)                  │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    FASE 3: GENERACIÓN DEL BACK                       │
│  Input: lista de referencias en batches de N elementos              │
│  Output: <ref-list> completo                                        │
│  Modelo: Cualquiera; batches permiten contexto pequeño              │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    FASE 4: ENSAMBLAJE Y VALIDACIÓN GLOBAL            │
│  Input: front + body_chunks + back                                  │
│  Output: XML completo <article>...</article>                        │
│  Verificación: integridad textual 100% + validación DTD             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. Estrategia de Chunking y Subdivisión de Tareas

### 6.1 Segmentación Semántica Heurística (Fase 0)

Implementar un nuevo módulo `document_segmenter.py` que analice el texto extraído y lo divida en bloques lógicos **sin usar IA**:

- **Front zone**: Primeros N párrafos (hasta encontrar "Resumen", "Abstract", "Introducción" o similar).
- **Body sections**: Detectar por palabras clave de encabezado ("Introducción", "Métodos", "Resultados", "Discusión", "Conclusión", "Agradecimientos").
- **Back zone**: Todo lo que venga después de "Referencias", "Bibliografía", "References".
- **Tablas**: Cada tabla se segmenta como unidad independiente con su caption.
- **Figuras**: Cada figura como unidad independiente.

**Ejemplo de salida:**
```python
{
  "front_text": "Título\nAutores\nResumen...",
  "body_sections": [
    {"title": "Introducción", "content": "..."},
    {"title": "Métodos", "content": "..."},
    {"title": "Resultados", "content": "..."}
  ],
  "tables": [
    {"id": "t1", "caption": "...", "content": "..."}
  ],
  "figures": [
    {"id": "f1", "caption": "...", "file": "..."}
  ],
  "references_raw": [
    "1. Autor A...",
    "2. Autor B..."
  ]
}
```

**Ventaja**: El modelo ya no tiene que "adivinar" la estructura; solo tiene que etiquetar el bloque que recibe.

### 6.2 Prompts Especializados por Fase

Cada fase tendrá su propio prompt mínimo en `prompts.py`:

#### Prompt de Front (`prompt_front.xml`)
- Tamaño estimado: ~800-1.200 tokens (instrucciones + metadatos JSON).
- Instrucciones: "Genera SOLO la sección `<front>` de un JATS XML. Usa EXACTAMENTE estos metadatos..."
- No incluye texto del artículo.

#### Prompt de Body Section (`prompt_body_section.xml`)
- Tamaño estimado: instrucciones (~600 tokens) + una sola sección (~1.000-4.000 tokens).
- Instrucciones: "Etiqueta SOLO esta sección como `<sec>` con `<title>` y `<p>`. NO omitas párrafos. NO resumas. Transcribe íntegramente..."
- Incluye contexto mínimo: "Esta sección pertenece a un artículo científico. El título de la sección es: X"

#### Prompt de Tabla (`prompt_table.xml`)
- Tamaño estimado: instrucciones (~400 tokens) + datos de la tabla.
- Instrucciones: "Genera un `<table-wrap>` con `<table>`, `<thead>`, `<tbody>` para estos datos..."

#### Prompt de Referencias Batch (`prompt_references_batch.xml`)
- Tamaño estimado: instrucciones (~500 tokens) + batch de 10 referencias (~1.000 tokens).
- Instrucciones: "Genera `<ref>` elementos para estas 10 referencias. Separa autores, título, fuente, año, DOI..."

### 6.3 Paralelización de Body Sections

Las secciones del body son independientes entre sí (salvo por cross-references de figuras/tablas, que se resuelven en ensamblaje). Por tanto:

- Se pueden enviar **en paralelo** a múltiples instancias de Ollama o a batches del mismo modelo.
- Cada sección se procesa en ~2-5 segundos con un modelo 3B en CPU.
- Un artículo de 6 secciones se procesa en el tiempo de la sección más larga, no en la suma.

### 6.4 Batching de Referencias

En lugar de enviar 50 referencias de una vez:
- Dividir en batches de 5-10 referencias.
- Cada batch genera un fragmento `<ref-list>` parcial.
- Ensamblar manteniendo el orden numérico.

---

## 7. Optimización para Modelos Pequeños / Ollama Móvil

### 7.1 Detección y Adaptación de Context Window

Implementar en `llm_provider.py` una función `estimate_context_window(provider_id, model)`:

| Modelo | Context Window | Estrategia |
|--------|---------------|------------|
| gemini-2.5-flash | 1M tokens | Modo monolítico (actual) o pipeline |
| gemini-2.5-pro | 1M tokens | Modo monolítico o pipeline |
| gpt-4o | 128K | Modo monolítico o pipeline |
| ollama/llama3.2:3b | 8K-128K* | Pipeline obligatorio; chunks de 2K-4K |
| ollama/phi3:3.8b | 4K-128K* | Pipeline obligatorio; chunks de 2K |
| ollama/qwen2.5:3b | 32K | Pipeline recomendado |

\* Ollama permite configurar context window, pero en móviles suele limitarse a 2K-4K por RAM.

**Implementación**: Añadir un campo `context_window` en cada proveedor/modelo, y un parámetro `chunk_size` configurable en la UI (con autodetección para Ollama vía endpoint `/api/show`).

### 7.2 Prompts Híbridos: Instrucciones vs. Contenido

Para modelos pequeños, usar la técnica de **"System Prompt Liviano + User Content"**:
- Reducir las instrucciones a lo esencial (modelos 3B confunden con muchas reglas).
- Usar ejemplos few-shot de 1-2 ejemplos máximo.
- Separar claramente "qué hacer" (etiquetar) de "qué NO hacer" (resumir).

### 7.3 Streaming de Resultados y Memoria

En dispositivos móviles:
- Procesar secciones una a una (secuencial) si la RAM es <4GB.
- Liberar memoria GPU/CPU entre chunks (`gc.collect()`).
- No mantener todos los prompts en memoria simultáneamente.

### 7.4 Degradación Graceful

Si un modelo local falla por timeout o OOM:
1. Reducir el tamaño del chunk a la mitad.
2. Reintentar con el chunk más pequeño.
3. Si persiste, marcar la sección como "requiere modelo cloud" y notificar al usuario.

---

## 8. Sistema de Integridad Textual 100%

Este es el guardrail más crítico. Debe ser **independiente del modelo** y **verificable programáticamente**.

### 8.1 Métricas de Extracción Pre-XML

Antes de enviar a la IA, calcular:
- `total_paragraphs_original`: cantidad de párrafos de texto plano.
- `total_words_original`: cantidad de palabras.
- `total_sentences_original`: cantidad de oraciones.
- `section_hashes`: hash MD5 del texto de cada sección detectada.

### 8.2 Métricas de Extracción Post-XML

Una vez ensamblado el XML, extraer todo el texto plano del `<body>` y `<back>` usando `lxml` (sin etiquetas) y calcular:
- `total_paragraphs_xml`: cantidad de `<p>` en body + `<mixed-citation>` en back.
- `total_words_xml`: cantidad de palabras.
- `section_hashes_xml`: hash del texto plano de cada `<sec>`.

### 8.3 Comparación y Rechazo

```python
def verificar_integridad_100(original_stats, xml_string) -> Tuple[bool, List[str]]:
    warnings = []
    
    # Comparación global
    if xml_words < original_words * 0.95:  # Umbral del 5% por espacios/XML markup
        warnings.append(f"Pérdida de texto: {original_words} palabras → {xml_words} palabras")
    
    # Comparación por sección
    for sec_title, orig_hash in original_stats['section_hashes'].items():
        xml_hash = extract_section_hash(xml_string, sec_title)
        if xml_hash != orig_hash:
            warnings.append(f"Sección '{sec_title}' fue modificada, resumida o truncada")
    
    return len(warnings) == 0, warnings
```

**Regla de oro**: Si `verificar_integridad_100` falla, el XML **no puede pasar** a validación DTD. Se debe re-procesar la sección fallida.

### 8.4 Diff Visual para el Usuario

Si una sección no coincide, generar un diff (como `difflib.unified_diff`) mostrando:
- Texto original de la sección.
- Texto extraído del XML de esa sección.
- Líneas omitidas resaltadas en rojo.

Esto permite al usuario ver exactamente qué perdió la IA.

---

## 9. Nuevos Módulos Propuestos

### 9.1 `modules/document_segmenter.py`
Responsabilidad: Dividir el texto extraído en front, body sections, tables, figures, references.
- Sin dependencias de IA.
- Usa expresiones regulares y heurísticas de lenguaje.
- Exporta: `DocumentSegments` dataclass.

### 9.2 `modules/pipeline_orchestrator.py`
Responsabilidad: Coordinar las 5 fases del pipeline.
- Recibe `DocumentSegments`.
- Llama a los prompts especializados en orden.
- Maneja paralelización con `ThreadPoolExecutor`.
- Ensambla el XML final.
- Exporta: `run_pipeline(segments, config) -> Tuple[str, PipelineReport]`.

### 9.3 `modules/integrity_checker.py`
Responsabilidad: Verificación textual 100%.
- `compute_original_stats(docx_path) -> DocumentStats`
- `verify_xml_integrity(xml_string, stats) -> IntegrityReport`
- Exporta estadísticas de diff por sección.

### 9.4 `modules/chunk_manager.py`
Responsabilidad: Calcular tamaños de chunks según modelo y dividir contenido.
- `estimate_tokens(text: str) -> int` (usando conteo aproximado: palabras * 1.3).
- `split_section_if_needed(section_text, max_tokens) -> List[str]`
- Divide párrafos en sub-chunks respetando límites de oración.

### 9.5 Refactorización de `prompts.py`

Añadir funciones:
- `get_front_prompt(metadata: dict, journal_config: dict) -> str`
- `get_body_section_prompt(section_title: str, section_text: str, metadata: dict) -> str`
- `get_table_prompt(table_data: dict) -> str`
- `get_reference_batch_prompt(batch: List[str], start_index: int) -> str`
- `get_assembly_prompt(front_xml: str, body_sections_xml: List[str], back_xml: str) -> str` (opcional; ensamblaje puede ser programático)

---

## 10. Plan de Implementación (Fases de Desarrollo)

### Fase A: Cimientos (Semanas 1-2)
- [ ] Implementar `document_segmenter.py` con heurísticas robustas para español e inglés.
- [ ] Implementar `chunk_manager.py` con estimación de tokens.
- [ ] Implementar `integrity_checker.py` con hash por sección.
- [ ] Tests manuales: comparar segmentación contra 10 artículos reales.

### Fase B: Pipeline Secuencial (Semanas 3-4)
- [ ] Crear prompts especializados (`front`, `body_section`, `table`, `references_batch`).
- [ ] Implementar `pipeline_orchestrator.py` en modo **secuencial** (no paralelo).
- [ ] Integrar en la UI como modo alternativo: "Modo Pipeline (Beta)".
- [ ] Comparar salida del modo Pipeline vs. Modo Monolítico en 10 artículos.

### Fase C: Paralelización y Optimización (Semanas 5-6)
- [ ] Implementar paralelización de body sections con `ThreadPoolExecutor`.
- [ ] Implementar detección de context window para Ollama/LM Studio.
- [ ] Implementar degradación graceful (reducción de chunk + reintento).
- [ ] Optimizar prompts para modelos 3B (reducción de instrucciones).

### Fase D: Validación y Refinamiento (Semanas 7-8)
- [ ] Integrar `integrity_checker` como gate obligatorio antes de DTD.
- [ ] Implementar diff visual en la UI para secciones fallidas.
- [ ] Pruebas con Ollama en celular (Android Termux / iOS).
- [ ] Benchmark: tiempo de procesamiento y tasa de éxito vs. modo monolítico.

### Fase E: Consolidación (Semana 9)
- [ ] Si el modo Pipeline supera al Monolítico en integridad y soporta modelos pequeños, hacerlo el modo por defecto.
- [ ] Actualizar `AGENTS.md` y documentación.
- [ ] Preparar PR a `main`.

---

## 11. Cambios en la Interfaz de Usuario (Streamlit)

### Nueva Pestaña: "Configuración Avanzada del Pipeline"
- **Modo de procesamiento**:
  - "Monolítico (modelos grandes)"
  - "Pipeline por fases (modelos pequeños)"
- **Tamaño máximo de chunk**: Slider (1K - 16K tokens), con autodetección.
- **Paralelización**: Toggle (on/off). Off recomendado para móviles.
- **Integridad estricta**: Toggle. Si está on, rechaza XMLs con pérdida de texto >2%.

### En la Pestaña "Generación" (Modo Pipeline)
- Mostrar progreso visual por fase:
  ```
  [✅] Front         [✅] Introducción    [⏳] Métodos
  [✅] Tabla 1       [⏳] Resultados      [⏳] Discusión
  [⏳] Referencias   [⏳] Ensamblaje      [⏳] Validación
  ```
- Botón "Re-procesar sección X" si falla integridad.
- Panel de diff si una sección fue truncada.

---

## 12. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| Segmentación heurística falla en artículos con estructura atípica | Media | Alto | Fallback: si no detecta secciones, usar modo monolítico. Permitir edición manual de segmentos antes del pipeline. |
| Ensamblaje deja etiquetas mal anidadas entre chunks | Media | Alto | Validar cada chunk con `lxml` antes de ensamblar. Usar parser con `recover=True`. |
| Cross-references (figuras/tablas citadas en texto) se rompen | Media | Medio | Generar placeholders de IDs en Fase 0. Resolver xref en Fase 4 con regex programático. |
| Modelos pequeños generan XML sintácticamente inválido por chunk | Alta | Medio | Post-procesar cada chunk con `sanitize_generated_xml` antes de ensamblar. |
| Pipeline es más lento que monolítico para artículos cortos | Alta | Bajo | Usar monolítico por defecto para artículos <5 páginas. Automatizar selección. |
| Usuario no entiende el modo Pipeline | Baja | Medio | UI con explicaciones inline. Mantener modo Monolítico como opción. |

---

## 13. Métricas de Éxito

| Métrica | Valor Actual (Estimado) | Meta |
|---------|------------------------|------|
| Tasa de XMLs con truncamiento silencioso (artículos >20 pág.) | ~30-50% | <5% |
| Palabras del texto original presentes en XML final | ~85-95%* | 100% |
| Soporte de modelos con contexto ≤8K tokens | 0% | 100% |
| Tiempo de procesamiento con Ollama 3B en CPU (artículo 10 pág.) | N/A (no funciona) | <60s |
| Tasa de validación DTD exitosa a la primera | ~40-60% | >80% |
| Tasa de re-intento por sección (vs. re-intento de artículo completo) | 100% re-intento completo | <20% re-intento completo |

\* Basado en observaciones de `verificar_completitud_xml` y reportes de usuarios.

---

## 14. Conclusión

La arquitectura monolítica actual es el cuello de botella fundamental que impide:
1. Garantizar integridad textual en artículos extensos.
2. Utilizar modelos locales pequeños y económicos.
3. Escalar el procesamiento de manera eficiente.

La transición a un **Pipeline por Fases con Chunking Inteligente** no solo resuelve estos problemas, sino que también introduce un marco de validación robusto (`integrity_checker`) que hace explícita una promesa que hoy solo es implícita: **que el artículo se transforma íntegramente**.

Esta propuesta está diseñada para ser implementada de forma incremental, sin romper el modo Monolítico existente, permitiendo validación A/B y adopción controlada.

**Próximo paso recomendado**: Aprobación de esta propuesta para iniciar la Fase A (Implementación de `document_segmenter.py` y `integrity_checker.py`).

---

*Documento generado para la rama `experimento4` del proyecto XML-JATS Transformer.*
