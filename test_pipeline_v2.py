import sys
from modules.pipeline_orchestrator import PipelineOrchestrator
from modules import config_store

# Configurar Ollama
config_store.save_ollama_host('http://localhost:11434')

print('🚀 Iniciando Pipeline v2 con Ollama (qwen-jats:latest)...')
print('📄 Documento: 4975.docx (6,182 palabras)')
print()

# Crear orquestador con modelo pequeño (simulando condiciones de 3B-7B)
orchestrator = PipelineOrchestrator(
    provider_id='ollama',
    model='qwen-jats:latest',
    api_key='ollama',
    max_input_tokens=4096,
    max_output_tokens=2048,
    parallel=False,
    use_light_prompts=True,
    enable_ai_verification=False,
)

# Metadatos mínimos (simulando extracción previa)
metadata = {
    'article_title': 'PERCEPCIONES DE PERSONAS DE SEXO MASCULINO HOMOSEXUALES QUE VIVEN CON VIH SOBRE LA PATERNIDAD',
    'journal_title': 'Revista de Enfermería',
    'publication_date': '2024',
    'doi': '10.1234/example',
    'authors': [
        {'given_names': 'Camila', 'surname': 'Rojas-Cáceres', 'aff_id': '1'},
        {'given_names': 'Gabriela', 'surname': 'Oyarzún-Pizarro', 'aff_id': '1'},
    ],
    'abstract': 'Resumen del artículo sobre percepciones de paternidad en personas VIH+',
    'keywords': ['VIH', 'paternidad', 'homosexualidad', 'percepciones'],
}

journal_config = {
    'title': 'Revista de Enfermería',
    'publisher': 'Universidad de Chile',
    'issn_print': '1234-5678',
}

try:
    result = orchestrator.run(
        docx_path='/Users/usuario/dev/XML-JATS-2/4975.docx',
        metadata=metadata,
        journal_config=journal_config,
    )
    
    print('=== RESULTADO DEL PIPELINE ===')
    print(f'Error: {result.error or "Ninguno"}')
    print(f'DTD Valido: {result.is_valid_dtd}')
    print(f'Errores DTD: {len(result.dtd_errors)}')
    if result.dtd_errors:
        for e in result.dtd_errors[:5]:
            print(f'  - {e}')
    
    print(f'\nIntegridad: {result.integrity_report.is_complete if result.integrity_report else "N/A"}')
    if result.integrity_report and result.integrity_report.warnings:
        for w in result.integrity_report.warnings[:5]:
            print(f'  - {w}')
    
    print(f'\nFases ejecutadas:')
    for s in result.stages:
        print(f'  [{s.status.upper()}] {s.name}: {s.message or "OK"}')
    
    print(f'\nDirectorio temporal: {result.temp_dir}')
    
    # Guardar XML final
    output_path = '/Users/usuario/dev/XML-JATS-2/4975_output.xml'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result.xml_string)
    print(f'\n💾 XML guardado en: {output_path}')
    print(f'📏 Tamaño XML: {len(result.xml_string)} chars')
    
    # Preview del XML
    print('\n=== PREVIEW XML (primeras 1500 chars) ===')
    print(result.xml_string[:1500])
    
except Exception as e:
    print(f'❌ ERROR: {e}')
    import traceback
    traceback.print_exc()
