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

from .transformer import invocar_gemini_cli
from . import prompts
import os

try:
    from docx import Document
except ImportError:
    pass

class MetadataExtractor:
    """Extracts and validates metadata from document files."""

    REQUIRED_FIELDS = ["article_title", "journal_title", "publication_date", "doi", "authors"]

    def __init__(self):
        pass

    @staticmethod
    def _normalize_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normaliza claves conocidas del resultado de la IA.
        
        Corrige variaciones como 'roi' → 'doi' que el modelo puede devolver.
        """
        # Normalizar roi → doi (typo histórico en prompts)
        if 'roi' in data and 'doi' not in data:
            data['doi'] = data.pop('roi')
        # Asegurar que doi existe como clave
        if 'doi' not in data:
            data['doi'] = None
        return data

    def extract_from_file(self, file_path: str, model_version: str = "gemini-2.5-flash", api_key: str = None, api_key_pro: str = None) -> Dict[str, Any]:
        """Determines file type and delegates extraction."""
        path = Path(file_path)
        if path.suffix.lower() == '.docx':
            return self.extract_from_docx(file_path, model_version, api_key, api_key_pro)
        elif path.suffix.lower() == '.pdf':
            return self.extract_from_pdf(file_path, model_version, api_key, api_key_pro)
        else:
            return {"error": "Unsupported file format"}

    def extract_from_docx(self, file_path: str, model_version: str = "gemini-2.5-flash", api_key: str = None, api_key_pro: str = None) -> Dict[str, Any]:
        """Extracts text from DOCX and uses LLM to parse metadata."""
        try:
            doc = Document(file_path)
            # Extract first 3 pages or 1500 words approx for metadata context
            full_text = []
            for para in doc.paragraphs[:50]: # First 50 paragraphs should contain header info
                full_text.append(para.text)
            
            context_text = "\n".join(full_text)
            return self._query_llm_for_metadata(context_text, model_version, api_key, api_key_pro)
        except Exception as e:
            print(f"Error reading DOCX: {e}", file=sys.stderr)
            return {}

    def extract_from_pdf(self, file_path: str, model_version: str = "gemini-2.5-flash", api_key: str = None, api_key_pro: str = None) -> Dict[str, Any]:
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
            
            return self._query_llm_for_metadata(context_text, model_version, api_key, api_key_pro)
        except Exception as e:
            print(f"Error reading PDF: {e}", file=sys.stderr)
            return {}

    def _query_llm_for_metadata(self, text_snippet: str, model_version: str = "gemini-2.5-flash", api_key: str = None, api_key_pro: str = None) -> Dict[str, Any]:
        """Uses Gemini to structure the metadata from raw text."""
        prompt = prompts.get_metadata_prompt(text_snippet)
        
        # Try to get API Key from env if not passed
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        api_key_pro = api_key_pro or os.environ.get("GEMINI_API_KEY_PRO")
        
        result = invocar_gemini_cli(prompt, model_version=model_version, api_key=api_key, api_key_pro=api_key_pro)
        if result.get('returncode') == 0 and result.get('stdout'):
            import json
            txt = result['stdout']
            # Clean markdown code blocks if present
            txt = re.sub(r'```json\s*', '', txt)
            txt = re.sub(r'```', '', txt)
            # El LLM a veces antepone texto/XML antes del JSON.
            # Extraer solo el objeto JSON buscando el primer '{' y último '}'
            first_brace = txt.find('{')
            last_brace = txt.rfind('}')
            if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                txt = txt[first_brace:last_brace + 1]
            try:
                parsed = json.loads(txt.strip())
                return self._normalize_metadata(parsed)
            except json.JSONDecodeError:
                return {"error": f"Failed to parse LLM JSON response: {txt[:500]}..."}
        
        # Si falló la llamada a la API
        error_msg = result.get('stderr', 'Unknown error') or 'No output from Gemini'
        return {"error": f"Error de Gemini AI (Code {result.get('returncode')}): {error_msg}"}

    def validate_metadata(self, metadata: Dict[str, Any]) -> List[str]:
        """Returns a list of missing required fields."""
        missing = []
        for field in self.REQUIRED_FIELDS:
            val = metadata.get(field)
            if not val or (isinstance(val, list) and len(val) == 0):
                missing.append(field)
        return missing
