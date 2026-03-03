# srt_translator/core/services/language_detection.py

from srt_translator.prompts.detection import build_language_detection_prompt


def detect_source_language(
    text: str,
    *,
    chat,  # object exposing .chat.completions.create(...)
    model: str,
    language_config: object | None = None,
    sample_chars: int = 2000,
) -> dict[str, object]:
    """
    Returns:
      {
        "detected_code": str|None,     # raw BCP-47 guess (e.g., "en", "es", "zh-Hans", "pt-BR")
        "normalized_code": str|None,   # mapped to app-supported code if language_config provided
        "normalized_name": str|None,   # human-readable name (via language_config)
        "confidence": float,           # 0..1 (model self-report)
        "mixed": bool                  # true if multiple sources detected
      }
    Never raises; returns a safe empty structure on failure.
    """
    text = (text or "")[:sample_chars]
    if not text.strip():
        return {
            "detected_code": None,
            "normalized_code": None,
            "normalized_name": None,
            "confidence": 0.0,
            "mixed": False,
        }

    prompt = build_language_detection_prompt(text)

    try:
        resp = chat.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=1,
            max_completion_tokens=120,
            response_format={"type": "json_object"},
        )
        import json

        data = json.loads((resp.choices[0].message.content or "").strip() or "{}")
        detected = (data.get("detected_code") or "").strip()
        confidence = float(data.get("confidence") or 0.0)
        mixed = bool(data.get("mixed") or False)

        norm = name = None
        if language_config and detected:
            try:
                if hasattr(language_config, "closest_supported_code"):
                    norm = language_config.closest_supported_code(detected)  # type: ignore
                else:
                    supported = set(language_config.get_language_codes())  # type: ignore
                    if detected in supported:
                        norm = detected
                    else:
                        lowered = {c.lower(): c for c in supported}
                        norm = lowered.get(detected.lower())
                        if not norm and detected.lower().startswith("zh"):
                            norm = "zh-Hans" if "zh-Hans" in supported else lowered.get("zh-hans")
                        if not norm and detected.lower().startswith("pt"):
                            norm = "pt-BR" if "pt-BR" in supported else lowered.get("pt-br")
                if norm:
                    name = language_config.get_language_name(norm)  # type: ignore
            except Exception:
                norm, name = None, None

        return {
            "detected_code": detected or None,
            "normalized_code": norm,
            "normalized_name": name,
            "confidence": confidence,
            "mixed": mixed,
        }
    except Exception:
        return {
            "detected_code": None,
            "normalized_code": None,
            "normalized_name": None,
            "confidence": 0.0,
            "mixed": False,
        }
