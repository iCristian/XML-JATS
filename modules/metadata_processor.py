# -*- coding: utf-8 -*-

"""Module for extracting metadata from documents (DOCX, PDF) using heuristics and AI.

This module handles the extraction of critical metadata (Title, Authors, Abstract, etc.)
from uploaded files to ensure high-quality JATS XML generation.
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import sys

# Try importing PDF libraries, handle if missing
try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from docx import Document
from .transformer import invocar_gemini_cli

class MetadataExtractor:
    """Extracts and validates metadata from document files."""

    REQUIRED_FIELDS = ["article_title", "journal_title", "publication_date", "authors"]

    def __init__(self):
        pass

    def extract_from_file(self, file_path: str) -> Dict[str, Any]:
        """Determines file type and delegates extraction."""
        path = Path(file_path)
        if path.suffix.lower() == '.docx':
            return self.extract_from_docx(file_path)
        elif path.suffix.lower() == '.pdf':
            return self.extract_from_pdf(file_path)
        else:
            return {"error": "Unsupported file format"}

    def extract_from_docx(self, file_path: str) -> Dict[str, Any]:
        """Extracts text from DOCX and uses LLM to parse metadata."""
        try:
            doc = Document(file_path)
            # Extract first 3 pages or 1500 words approx for metadata context
            full_text = []
            for para in doc.paragraphs[:50]: # First 50 paragraphs should contain header info
                full_text.append(para.text)
            
            context_text = "\n".join(full_text)
            return self._query_llm_for_metadata(context_text)
        except Exception as e:
            print(f"Error reading DOCX: {e}", file=sys.stderr)
            return {}

    def extract_from_pdf(self, file_path: str) -> Dict[str, Any]:
        """Extracts text from PDF and uses LLM to parse metadata."""
        if not pdfplumber:
            return {"error": "pdfplumber not installed"}
        
        try:
            context_text = ""
            with pdfplumber.open(file_path) as pdf:
                # Extract first 2 pages
                for page in pdf.pages[:2]:
                    text = page.extract_text()
                    if text:
                        context_text += text + "\n"
            
            return self._query_llm_for_metadata(context_text)
        except Exception as e:
            print(f"Error reading PDF: {e}", file=sys.stderr)
            return {}

    def _query_llm_for_metadata(self, text_snippet: str) -> Dict[str, Any]:
        """Uses Gemini to structure the metadata from raw text."""
        prompt = f"""
        Actúa como un bibliotecario experto. Analiza el siguiente texto inicial de un artículo científico y extrae los metadatos en formato JSON estricto.

        TEXTO:
        {text_snippet[:3000]} 

        TIPOS DE DATOS REQUERIDOS (Devuelve null si no lo encuentras):
        - article_title (string)
        - journal_title (string)
        - publication_date (string, formato YYYY-MM-DD o YYYY)
        - roi (string, DOI del artículo)
        - authors (lista de objetos: {{ "given_names": "", "surname": "", "email": "", "aff_id": "1" }})
        - affiliations (lista de objetos: {{ "id": "1", "institution": "", "country": "" }})
        - abstract (string)
        - keywords (lista de strings)

        RESPUESTA SOLO JSON:
        """
        
        result = invocar_gemini_cli(prompt)
        if result.get('returncode') == 0 and result.get('stdout'):
            import json
            txt = result['stdout']
            # Clean markdown code blocks if present
            txt = re.sub(r'```json\s*', '', txt)
            txt = re.sub(r'```', '', txt)
            try:
                return json.loads(txt.strip())
            except json.JSONDecodeError:
                return {"error": f"Failed to parse LLM JSON response: {txt[:500]}..."}
        
        # Si falló la llamada CLI
        error_msg = result.get('stderr', 'Unknown error') or 'No output from Gemini'
        return {"error": f"Gemini CLI error (Code {result.get('returncode')}): {error_msg}"}

    def validate_metadata(self, metadata: Dict[str, Any]) -> List[str]:
        """Returns a list of missing required fields."""
        missing = []
        for field in self.REQUIRED_FIELDS:
            val = metadata.get(field)
            if not val or (isinstance(val, list) and len(val) == 0):
                missing.append(field)
        return missing
