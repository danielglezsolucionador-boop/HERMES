"""
base.py - Subfase 3.6.7
Interfaz abstracta para providers IA.
Todo provider debe implementar esta interfaz.
Hermes NO está acoplado a ningún provider específico.
"""
from abc import ABC, abstractmethod


class AIProvider(ABC):
    """
    Interfaz base para todos los providers IA de Hermes.
    Claude, DeepSeek, OpenAI, Ollama — todos implementan esta clase.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nombre del provider. Ej: 'claude', 'deepseek', 'openai'."""

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str | None = None, max_tokens: int = 1024) -> dict:
        """
        Genera respuesta desde el provider.

        Retorna contrato normalizado:
        {
            "success": bool,
            "content": str,
            "model": str,
            "usage": {"input_tokens": int, "output_tokens": int},
            "duration_ms": int,
            "error": str | None,
            "error_type": str | None,
        }
        """

    @abstractmethod
    async def healthcheck(self) -> dict:
        """
        Verifica estado del provider.

        Retorna:
        {
            "available": bool,
            "configured": bool,
            "last_error": str | None,
            "timeout_support": bool,
        }
        """