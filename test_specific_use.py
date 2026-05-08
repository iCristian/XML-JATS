from modules.pipeline_orchestrator import PipelineOrchestrator
from modules.pipeline_temp_manager import PipelineTempManager

orchestrator = PipelineOrchestrator(provider_id='openai', model='gpt-4o', api_key='test')
orchestrator.temp_manager = PipelineTempManager(cleanup_on_exit=True)

front = '<front><journal-meta></journal-meta><article-meta></article-meta></front>'
body = ['<sec><title>Intro</title><p>Test</p></sec>']
back = '<back><ref-list></ref-list></back>'

xml = orchestrator._assemble_xml_dom(front, body, back)
print('Has specific-use:', 'specific-use="sps-1.10"' in xml)
print('Has xml:lang:', 'xml:lang="es"' in xml)
print('Has dtd-version:', 'dtd-version=' in xml)
print('Article tag line:')
for line in xml.split('\n'):
    if '<article' in line:
        print(' ', line)
