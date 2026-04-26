#!/usr/bin/env python3
"""Descarga e instala el DTD JATS Publishing 1.4 con MathML3 desde NCBI.

Uso:
    python modules/dtd/download_jats14.py

Requisitos:
    - Conexión a internet con acceso a jats.nlm.nih.gov
    - Python 3.8+

El paquete se descarga como ZIP desde:
    https://public.nlm.nih.gov/projects/jats/publishing/1.4/JATS-Publishing-1-4-MathML3-DTD.zip
y se extrae en modules/dtd/JATS-Publishing-1-4-MathML3-DTD/
"""
import os
import ssl
import sys
import urllib.request
import zipfile
from pathlib import Path

# URLs de descarga (en orden de preferencia)
URLS = [
    "https://public.nlm.nih.gov/projects/jats/publishing/1.4/JATS-Publishing-1-4-MathML3-DTD.zip",
    "https://ftp.ncbi.nlm.nih.gov/pub/jats/publishing/1.4/JATS-Publishing-1-4-MathML3-DTD.zip",
]

DTD_DIR = Path(__file__).resolve().parent
TARGET_DIR = DTD_DIR / "JATS-Publishing-1-4-MathML3-DTD"
EXPECTED_DTD = TARGET_DIR / "JATS-journalpublishing1-4-mathml3.dtd"


def download_and_extract():
    """Descarga y extrae el DTD JATS 1.4."""
    # Verificar si ya existe
    if EXPECTED_DTD.exists():
        print(f"✅ DTD JATS 1.4 ya existe en: {TARGET_DIR}")
        return True

    # Intentar certifi para SSL, fallback a contexto sin verificar
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()

    zip_path = DTD_DIR / "jats14_temp.zip"

    for url in URLS:
        print(f"📥 Intentando descargar desde: {url}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                data = resp.read()
                with open(zip_path, "wb") as f:
                    f.write(data)
            print(f"   ✓ Descarga completada ({len(data):,} bytes)")
            break
        except Exception as e:
            print(f"   ✗ Error: {e}")
            continue
    else:
        print("\n❌ No se pudo descargar desde ninguna URL.")
        print("   Descarga manualmente desde:")
        print("   https://public.nlm.nih.gov/projects/jats/publishing/1.4/JATS-Publishing-1-4-MathML3-DTD.zip")
        print(f"   y extrae en: {TARGET_DIR}")
        return False

    # Extraer
    print("📦 Extrayendo archivos...")
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            # Extraer solo el directorio del DTD, no __MACOSX
            for member in z.namelist():
                if member.startswith("JATS-Publishing-1-4-MathML3-DTD/"):
                    z.extract(member, DTD_DIR)
        print(f"   ✓ Extraído en: {TARGET_DIR}")
    except Exception as e:
        print(f"   ✗ Error al extraer: {e}")
        return False
    finally:
        # Limpiar ZIP temporal
        if zip_path.exists():
            zip_path.unlink()

    # Verificar
    if EXPECTED_DTD.exists():
        file_count = len(list(TARGET_DIR.glob("*")))
        print(f"\n✅ DTD JATS 1.4 instalado correctamente ({file_count} archivos)")
        return True
    else:
        print("\n❌ El archivo DTD principal no se encontró después de la extracción.")
        return False


if __name__ == "__main__":
    success = download_and_extract()
    sys.exit(0 if success else 1)
