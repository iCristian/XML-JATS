# xml_html.py

Script para convertir un archivo XML (por ejemplo JATS) a un único archivo HTML
profesional y responsivo. Usa la CLI `gemini` si está disponible; si no, aplica
un XSLT local como fallback.

Uso rápido:

```bash
# activar virtualenv
source .venv/bin/activate

python xml_html.py entrada.xml salida.html
```

Notas:
- El script intentará invocar `gemini` y pedir la conversión por IA.
- Si `gemini` no está instalado o no produce HTML, el script usa un XSLT
  sencillo para generar una versión funcional del HTML.
- Si quieres que gemini devuelva metadatos (por ejemplo tokens), considera
  modificar la invocación a `-o json` en `xml_html.py`.
