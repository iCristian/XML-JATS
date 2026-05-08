# -*- coding: utf-8 -*-

"""Gestor de archivos temporales para el pipeline por fases.

Crea un directorio temporal con timestamp bajo ``data/pipeline_temp/``
y persiste todos los artefactos intermedios del pipeline para facilitar
debug, auditoría y recuperación ante fallos.

Typical usage::

    from modules.pipeline_temp_manager import PipelineTempManager

    with PipelineTempManager() as tmp:
        tmp.save_raw_text("texto extraído...")
        tmp.save_prompt("front", "prompt...")
        tmp.save_output("front", "<front>...</front>")
        tmp.save_validation({"is_valid": True, "errors": []})
        print(tmp.base_dir)
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


_DEFAULT_TEMP_DIR = Path("data") / "pipeline_temp"


class PipelineTempManager:
    """Administra archivos temporales de una ejecución del pipeline.

    El directorio se crea con un timestamp único. Cada fase del pipeline
    puede guardar sus prompts, salidas y metadatos. El manager se puede
    usar como context manager para limpieza automática, o de forma
    persistente para debug.
    """

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        cleanup_on_exit: bool = False,
    ) -> None:
        """Inicializa el directorio temporal.

        Args:
            base_dir: Directorio raíz para temporales. Por defecto
                ``data/pipeline_temp/``.
            cleanup_on_exit: Si es True, elimina el directorio al cerrar
                el context manager. Útil para tests.
        """
        self._base = base_dir or _DEFAULT_TEMP_DIR
        self._cleanup = cleanup_on_exit
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.base_dir = self._base / f"run_{timestamp}"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(str(self.base_dir), 0o700)

    def __enter__(self) -> PipelineTempManager:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._cleanup and self.base_dir.exists():
            shutil.rmtree(str(self.base_dir), ignore_errors=True)

    def _write(self, filename: str, content: str) -> Path:
        """Escribe texto plano a un archivo en el directorio temporal.

        Args:
            filename: Nombre del archivo (ej. ``00_raw_text.txt``).
            content: Contenido a escribir.

        Returns:
            Path al archivo escrito.
        """
        path = self.base_dir / filename
        path.write_text(content, encoding="utf-8")
        return path

    def save_raw_text(self, text: str) -> Path:
        """Guarda el texto crudo extraído del documento.

        Args:
            text: Texto plano del documento.

        Returns:
            Path al archivo guardado.
        """
        return self._write("00_raw_text.txt", text)

    def save_segments(self, segments_data: Dict[str, Any]) -> Path:
        """Guarda la salida del segmentador como JSON.

        Args:
            segments_data: Diccionario serializable con los segmentos.

        Returns:
            Path al archivo guardado.
        """
        path = self.base_dir / "01_segments.json"
        path.write_text(
            json.dumps(segments_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def save_prompt(self, stage: str, prompt: str) -> Path:
        """Guarda el prompt enviado a un LLM para una fase.

        Args:
            stage: Identificador de la fase (ej. ``front``, ``body_sec_0``).
            prompt: Texto del prompt.

        Returns:
            Path al archivo guardado.
        """
        filename = f"02_{stage}_prompt.txt"
        return self._write(filename, prompt)

    def save_output(self, stage: str, xml_output: str) -> Path:
        """Guarda la salida XML cruda del LLM para una fase.

        Args:
            stage: Identificador de la fase.
            xml_output: Fragmento XML generado.

        Returns:
            Path al archivo guardado.
        """
        filename = f"03_{stage}_output.xml"
        return self._write(filename, xml_output)

    def save_sanitized(self, stage: str, xml_output: str) -> Path:
        """Guarda la salida XML tras pasar por el sanitizer.

        Args:
            stage: Identificador de la fase.
            xml_output: Fragmento XML sanitizado.

        Returns:
            Path al archivo guardado.
        """
        filename = f"04_{stage}_sanitized.xml"
        return self._write(filename, xml_output)

    def save_assembled(self, xml_string: str) -> Path:
        """Guarda el XML ensamblado antes de post-procesamiento.

        Args:
            xml_string: XML completo ensamblado.

        Returns:
            Path al archivo guardado.
        """
        return self._write("05_assembled.xml", xml_string)

    def save_postprocessed(self, xml_string: str) -> Path:
        """Guarda el XML tras correcciones estructurales automáticas.

        Args:
            xml_string: XML post-procesado.

        Returns:
            Path al archivo guardado.
        """
        return self._write("06_postprocessed.xml", xml_string)

    def save_validation(self, result: Dict[str, Any]) -> Path:
        """Guarda el resultado de la validación DTD e integridad.

        Args:
            result: Diccionario serializable con ``is_valid``, ``errors``, etc.

        Returns:
            Path al archivo guardado.
        """
        path = self.base_dir / "07_validation.json"
        path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def save_pipeline_config(self, config: Dict[str, Any]) -> Path:
        """Guarda la configuración usada para esta ejecución.

        Args:
            config: Diccionario con provider_id, model, max_tokens, etc.

        Returns:
            Path al archivo guardado.
        """
        path = self.base_dir / "99_config.json"
        path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def list_stages(self) -> List[str]:
        """Lista las fases que tienen al menos un artefacto guardado.

        Returns:
            Lista de nombres de fase detectados.
        """
        stages: set[str] = set()
        for f in self.base_dir.iterdir():
            if f.is_file() and "_" in f.name:
                parts = f.name.split("_", 2)
                if len(parts) >= 3:
                    stages.add(parts[2])
        return sorted(stages)

    @staticmethod
    def list_runs(base_dir: Optional[Path] = None) -> List[Path]:
        """Lista todos los directorios de ejecuciones previas.

        Args:
            base_dir: Directorio raíz de temporales.

        Returns:
            Lista de Paths ordenados por fecha (más reciente primero).
        """
        bd = base_dir or _DEFAULT_TEMP_DIR
        if not bd.exists():
            return []
        runs = [p for p in bd.iterdir() if p.is_dir() and p.name.startswith("run_")]
        runs.sort(key=lambda p: p.name, reverse=True)
        return runs
