"""Jev Decisions transport with private config and environment overrides."""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys
import ssl
import time
import urllib.error
import urllib.request
from .model import BokkioError


def config_path() -> Path:
    override = os.environ.get("BOKKIO_JEV_CONFIG")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "Bokkio/jev.json"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/Bokkio/jev.json"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "bokkio/jev.json"


class JevProvider:
    ENDPOINTS = {"typesafe": "https://api.typesafe.ai/v1/systemone",
                 "openrouter": "https://openrouter.ai/api/alpha/decisions"}

    def __init__(self, api_key=None, model=None, timeout=30, opener=None, source=None):
        settings = {}
        environment_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("TYPESAFE_API_KEY")
        if api_key is None and not environment_key:
            path = config_path()
            if path.is_file():
                try:
                    settings = json.loads(path.read_text(encoding="utf-8"))
                    if not isinstance(settings, dict): raise ValueError()
                except (OSError, ValueError):
                    raise BokkioError("Invalid private Jev configuration") from None
        self._key = api_key or environment_key or settings.get("api_key")
        if not isinstance(self._key, str) or not self._key.strip():
            raise BokkioError("Jev key is not configured; set OPENROUTER_API_KEY or private Bokkio jev.json")
        self.source = source or os.environ.get("BOKKIO_JEV_SOURCE") or settings.get("source") or (
            "openrouter" if self._key.startswith("sk-or-") or (api_key is None and os.environ.get("OPENROUTER_API_KEY")) else "typesafe")
        if self.source not in self.ENDPOINTS:
            raise BokkioError("Jev source must be openrouter or typesafe")
        if self._key.startswith("sk-or-") and self.source != "openrouter":
            raise BokkioError("OpenRouter keys require the OpenRouter Decisions endpoint")
        self.endpoint = self.ENDPOINTS[self.source]
        self.model = model or os.environ.get("BOKKIO_JEV_MODEL") or settings.get("model") or (
            "typesafe/jev-1.13" if self.source == "openrouter" else "jev-latest")
        self.timeout = timeout
        if opener is None:
            import certifi
            context = ssl.create_default_context(cafile=certifi.where())
            self._opener = lambda request, timeout: urllib.request.urlopen(request, timeout=timeout, context=context)
        else:
            self._opener = opener

    def ask(self, state, questions):
        payload = json.dumps({"model": self.model, "state": state, "questions": questions}, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(self.endpoint, data=payload, headers={"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}, method="POST")
        started = time.monotonic()
        try:
            with self._opener(request, timeout=self.timeout) as response:
                data = response.read(4 * 1024 * 1024 + 1)
                if len(data) > 4 * 1024 * 1024: raise BokkioError("Jev response exceeds 4 MiB")
                result = json.loads(data)
        except urllib.error.HTTPError as error:
            raise BokkioError(f"Jev HTTP request failed with status {error.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise BokkioError("Jev connection failed or timed out") from None
        except (ValueError, UnicodeDecodeError):
            raise BokkioError("Jev returned invalid JSON") from None
        if not isinstance(result, dict): raise BokkioError("Jev response must be an object")
        result["elapsed_seconds"] = round(time.monotonic() - started, 6)
        result["source"] = self.source
        return result
