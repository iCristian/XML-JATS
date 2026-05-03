# -*- coding: utf-8 -*-

"""Gestor de chunks para procesamiento con modelos de lenguaje.

Estima tamaños de tokens, calcula límites según el modelo objetivo
y divide texto largo en sub-unidades que quepan en la ventana de
contexto del LLM seleccionado.

Typical usage::

    from modules.chunk_manager import ChunkManager

    cm = ChunkManager(max_input_tokens=2048, max_output_tokens=2048)
    chunks = cm.split_section(section_text)
    print(f"Dividido en {len(chunks)} chunks")
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


# ─── Constantes ──────────────────────────────────────────────────

# Estimación conservadora: ~1.3 tokens por palabra en promedio
# para textos académicos en español/inglés con puntuación.
_TOKENS_PER_WORD: float = 1.35

# Tokens adicionales que consume el propio prompt de instrucciones
# por chunk (depende del prompt especializado usado).
_PROMPT_OVERHEAD_TOKENS: int = 400


@dataclass
class ChunkConfig:
    """Configuración de chunking para un modelo específico."""

    max_input_tokens: int = 8192
    max_output_tokens: int = 4096
    prompt_overhead: int = _PROMPT_OVERHEAD_TOKENS
    reserve_tokens: int = 256  # Margen de seguridad

    @property
    def max_content_tokens(self) -> int:
        """Tokens disponibles para el contenido del usuario."""
        available = (
            self.max_input_tokens
            - self.prompt_overhead
            - self.reserve_tokens
        )
        return max(available, 512)


# ─── Clase principal ─────────────────────────────────────────────

class ChunkManager:
    """Calcula y ejecuta la división de texto en chunks viables."""

    def __init__(
        self,
        max_input_tokens: int = 8192,
        max_output_tokens: int = 4096,
        prompt_overhead: int = _PROMPT_OVERHEAD_TOKENS,
        reserve_tokens: int = 256,
    ) -> None:
        """Inicializa el gestor con los límites del modelo.

        Args:
            max_input_tokens: Límite de la ventana de contexto del modelo.
            max_output_tokens: Límite de tokens de salida del modelo.
            prompt_overhead: Tokens estimados del prompt de instrucciones.
            reserve_tokens: Margen de seguridad adicional.
        """
        self.config = ChunkConfig(
            max_input_tokens=max_input_tokens,
            max_output_tokens=max_output_tokens,
            prompt_overhead=prompt_overhead,
            reserve_tokens=reserve_tokens,
        )

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estima la cantidad de tokens de un texto.

        Usa una heurística basada en palabras + puntuación.
        Es aproximada pero suficiente para chunking.

        Args:
            text: Texto a estimar.

        Returns:
            Número estimado de tokens (int).
        """
        if not text:
            return 0
        # Contar palabras alfanuméricas
        words = len(re.findall(r'\b\w+\b', text))
        # Contar signos de puntuación y símbolos como tokens separados
        punct = len(re.findall(r'[^\w\s]', text))
        # Cifras y números largos suelen tokenizarse en múltiples tokens
        numbers = len(re.findall(r'\d+', text))
        raw = int((words + punct * 0.5 + numbers * 0.3) * _TOKENS_PER_WORD)
        return max(raw, 1)

    def fits_in_one_chunk(self, text: str) -> bool:
        """Determina si un texto cabe en un único prompt.

        Args:
            text: Texto candidato.

        Returns:
            True si cabe dentro del límite configurado.
        """
        return self.estimate_tokens(text) <= self.config.max_content_tokens

    def split_section(self, text: str) -> List[str]:
        """Divide una sección de texto en chunks que quepan en el modelo.

        Respeta límites de párrafo y, si es necesario, de oración
        para no cortar en medio de una idea.

        Args:
            text: Texto de la sección (puede ser muy largo).

        Returns:
            Lista de strings, cada uno un chunk válido.
        """
        if not text or not text.strip():
            return []

        if self.fits_in_one_chunk(text):
            return [text.strip()]

        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        if not paragraphs:
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        chunks: List[str] = []
        current_chunk = ""
        max_tokens = self.config.max_content_tokens

        for para in paragraphs:
            para_tokens = self.estimate_tokens(para)
            current_tokens = self.estimate_tokens(current_chunk)

            if para_tokens > max_tokens:
                # Párrafo gigante: hay que partirlo por oraciones
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                sentence_chunks = self._split_by_sentences(para, max_tokens)
                chunks.extend(sentence_chunks)
                continue

            if current_tokens + para_tokens > max_tokens:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _split_by_sentences(self, text: str, max_tokens: int) -> List[str]:
        """Divide un texto largo por oraciones respetando el límite de tokens.

        Args:
            text: Texto largo (generalmente un párrafo enorme).
            max_tokens: Límite de tokens por chunk.

        Returns:
            Lista de chunks generados por oraciones.
        """
        # Regex simple para fin de oración en español/inglés
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks: List[str] = []
        current = ""
        for sentence in sentences:
            sent_tokens = self.estimate_tokens(sentence)
            current_tokens = self.estimate_tokens(current)

            if sent_tokens > max_tokens:
                # Oración extremadamente larga (tabla o lista): cortar por comas
                if current:
                    chunks.append(current.strip())
                    current = ""
                comma_chunks = self._split_by_commas(sentence, max_tokens)
                chunks.extend(comma_chunks)
                continue

            if current_tokens + sent_tokens > max_tokens:
                if current:
                    chunks.append(current.strip())
                current = sentence
            else:
                current += " " + sentence if current else sentence

        if current:
            chunks.append(current.strip())
        return chunks

    def _split_by_commas(self, text: str, max_tokens: int) -> List[str]:
        """Último recurso: divide por comas si una oración es demasiado larga.

        Args:
            text: Texto extremadamente largo.
            max_tokens: Límite de tokens por chunk.

        Returns:
            Lista de chunks.
        """
        parts = [p.strip() for p in text.split(',') if p.strip()]
        chunks: List[str] = []
        current = ""
        for part in parts:
            part_tokens = self.estimate_tokens(part)
            current_tokens = self.estimate_tokens(current)
            if current_tokens + part_tokens > max_tokens:
                if current:
                    chunks.append(current.strip() + ",")
                current = part
            else:
                current += ", " + part if current else part
        if current:
            chunks.append(current.strip() + ",")
        return chunks
