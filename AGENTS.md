# AGENTS.md — XML-JATS Transformer

High-signal context for AI agents working in this repo. Omit anything you can already infer from filenames or standard Python conventions.

---

## Project Type

Python 3.9+ Streamlit app (multi-page, registry in `streamlit_app.py`) with a desacoplado backend in `modules/`. No `pyproject.toml`, `setup.py`, or formal test framework — plain `pip` + `requirements.txt`.

---

## Entry Points

| Mode | Command |
|------|---------|
| Web UI | `streamlit run streamlit_app.py` or `./run_app.sh` (uses `.venv`) |
| CLI transform (DOCX/PDF → XML) | `python -m modules.transformer <input.docx> <output.xml>` |
| CLI convert (XML → HTML) | `python -m modules.xml_html <input.xml> <output.html>` |
| Check available models | `python check_models.py` |

---

## Pre-PR Validation (No Test Suite)

There is no `pytest` suite. Before any PR, run the exact checks from `CONTRIBUTING.md`:

```bash
# 1. Syntax check all Python files
for f in modules/*.py views/*.py streamlit_app.py; do
    python -m py_compile "$f" && echo "OK: $f"
done

# 2. Import check
python -c "from modules import transformer, metadata_processor, correction, llm_provider, config_store, prompts, xml_html; print('Imports OK')"

# 3. Manual smoke test
streamlit run streamlit_app.py
```

> **Note:** The `tests/` directory is gitignored and contains only ad-hoc utility scripts (e.g., `test_tokens.py`). Do not add real tests there.

---

## Architecture Boundaries (Critical)

1. **Backend/UI separation:** `modules/` must **never** import `streamlit` or touch `st.session_state`. All config is passed explicitly via arguments or `config_store.py`.
2. **Prompts centralized:** Every AI prompt lives in `modules/prompts.py`. Never hardcode prompts in `transformer.py`, `correction.py`, or views.
3. **LLM abstraction:** All AI calls must go through `modules/llm_provider.py` (`LLMProvider.generate()`). No direct `google.generativeai`, `openai`, or `anthropic` SDK calls outside that file.
4. **Config store:** `modules/config_store.py` owns all SQLite persistence (API keys, tokens, metrics). API keys are Fernet-encrypted; the key is at `data/.fernet.key`.

---

## Code Conventions

- **Type hints:** Mandatory on all functions/methods (args and return values).
- **Docstrings:** Google-style, mandatory on all public functions/classes/modules.
- **Style:** PEP 8, ~100 char line limit, `snake_case` for vars/funcs, `PascalCase` for classes.
- **Quota handling:** Functions that call AI and hit a 429 must **return** `{'quota_exceeded': True}` (not raise). Use `tenacity` with `stop_after_attempt(3)` + `wait_exponential()`.
- **Zero-Placeholder policy:** AI output must never contain placeholders like `<!-- Contenido... -->`. `transformer.verificar_completitud_xml()` is the final guardrail — do not weaken or remove it.
- **Single key per provider:** Do not add `api_key_pro` or secondary key parameters. One key per provider; Google handles free-to-paid tier automatically.

---

## Environment & Secrets

- **Virtual env:** `.venv/`
- **Local data:** `data/` is gitignored and must stay out of version control. It contains:
  - `config.db` — SQLite with encrypted API keys and token metrics.
  - `.fernet.key` — Fernet encryption key (permissions `0600`).
- **Env vars as fallback:** `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, `MISTRAL_API_KEY`, `GROQ_API_KEY`. The UI-persisted key in `config.db` takes precedence if both exist.
- **Runtime artifacts:** `imagenes_extraidas/` is generated during DOCX processing and is also gitignored.

---

## Operational Gotchas

- **Default model:** `gemini-2.5-flash` everywhere. Respect the user's selected model; do not hardcode others.
- **Max tokens:** `65536` (configured in `LLMConfig`).
- **Local LLM auto-start (macOS):** `llm_provider.py` attempts to launch Ollama/LM Studio via `open -a` if `localhost` endpoints are unreachable.
- **SSL on macOS:** `SSL: CERTIFICATE_VERIFY_FAILED` when downloading DTDs is handled with a programmatic fallback, but can also be fixed system-wide via `/Applications/Python\ 3.x/Install\ Certificates.command`.
- **DTD validation:** Bundled offline in `modules/dtd/` (default JATS 1.4). Dynamic version selection is supported via config.
