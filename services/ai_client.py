"""Cliente ligero para llamar a un modelo de IA (Gemini o Claude) y parsear respuestas JSON.

Por defecto usa la API gratuita de Google Gemini (AI_PROVIDER=gemini). Si prefieres usar
Claude (Anthropic), configura ANTHROPIC_API_KEY y AI_PROVIDER=anthropic en el .env.
"""
import json
import re

import config


class AIConfigError(RuntimeError):
    """No hay ninguna clave de API de IA configurada correctamente."""


class AIGenerationError(RuntimeError):
    """El modelo de IA no devolvió una respuesta utilizable."""


def _provider() -> str:
    """Determina qué proveedor usar, con fallback automático si solo hay una clave configurada."""
    provider = config.AI_PROVIDER
    if provider not in ("gemini", "anthropic"):
        provider = "gemini"
    if provider == "gemini" and not config.GEMINI_API_KEY and config.ANTHROPIC_API_KEY:
        provider = "anthropic"
    elif provider == "anthropic" and not config.ANTHROPIC_API_KEY and config.GEMINI_API_KEY:
        provider = "gemini"
    return provider


def _ask_gemini(system_prompt: str, user_prompt: str, max_tokens: int, json_mode: bool) -> str:
    from google import genai
    from google.genai import types
    from google.genai import errors as genai_errors

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    try:
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=max_tokens,
                response_mime_type="application/json" if json_mode else "text/plain",
                thinking_config=types.ThinkingConfig(thinking_level="low"),
            ),
        )
    except genai_errors.APIError as exc:
        raise AIGenerationError(f"Error al contactar con la API de Gemini: {exc}") from exc

    text = (getattr(response, "text", None) or "").strip()
    if not text:
        raise AIGenerationError(
            "Gemini no ha devuelto texto (puede que el contenido se haya bloqueado por sus "
            "filtros de seguridad). Prueba a generar de nuevo o revisa el texto de origen."
        )
    return text


def _ask_anthropic(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    try:
        response = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.APIError as exc:
        raise AIGenerationError(f"Error al contactar con la API de Claude: {exc}") from exc

    text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    text = "\n".join(text_parts).strip()
    if not text:
        raise AIGenerationError("Claude devolvió una respuesta vacía.")
    return text


def ask_ai(system_prompt: str, user_prompt: str, max_tokens: int = 8000, json_mode: bool = False) -> str:
    """Envía un prompt al proveedor de IA configurado y devuelve el texto de la respuesta."""
    provider = _provider()

    if provider == "gemini":
        if not config.GEMINI_API_KEY:
            raise AIConfigError(
                "No se ha configurado GEMINI_API_KEY. Copia .env.example a .env y añade tu clave "
                "gratuita de la API de Gemini, que puedes crear en https://aistudio.google.com/apikey"
            )
        return _ask_gemini(system_prompt, user_prompt, max_tokens, json_mode)

    if not config.ANTHROPIC_API_KEY:
        raise AIConfigError(
            "No se ha configurado ANTHROPIC_API_KEY. Copia .env.example a .env y añade tu clave "
            "de la API de Anthropic, o configura GEMINI_API_KEY para usar la alternativa gratuita."
        )
    return _ask_anthropic(system_prompt, user_prompt, max_tokens)


def ask_ai_json(system_prompt: str, user_prompt: str, max_tokens: int = 8000):
    """Igual que ask_ai, pero espera y parsea un bloque JSON en la respuesta."""
    raw = ask_ai(system_prompt, user_prompt, max_tokens=max_tokens, json_mode=True)
    return extract_json(raw)


def extract_json(raw: str):
    """Extrae y parsea el primer bloque JSON válido de un texto (tolera ```json ... ```)."""
    candidate = raw.strip()

    fence_match = re.search(r"```(?:json)?\s*(.*?)```", candidate, re.DOTALL)
    if fence_match:
        candidate = fence_match.group(1).strip()

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    start_chars = "{["
    end_chars = "}]"
    for start, end in zip(start_chars, end_chars):
        start_idx = candidate.find(start)
        end_idx = candidate.rfind(end)
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            snippet = candidate[start_idx : end_idx + 1]
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                continue

    raise AIGenerationError(
        "No se pudo interpretar la respuesta de la IA como JSON. "
        "Prueba a generar de nuevo o revisa el texto de origen."
    )
