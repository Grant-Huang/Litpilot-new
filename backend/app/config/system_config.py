"""System configuration storage — atomic JSON read/write with masking."""
from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from filelock import FileLock

from app.config.paths import ensure_dir

_log = logging.getLogger(__name__)

_CREDENTIALS_FILE = "system.credentials.json"
_INSTANCES_FILE = "system.instances.json"
_CAPABILITIES_FILE = "system.capabilities.json"
_STORAGE_FILE = "system.storage.json"


def mask_secret(secret: str) -> str:
    s = secret or ""
    if not s:
        return ""
    if len(s) >= 4:
        return f"··· {s[-4:]}"
    return "····"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gen_id() -> str:
    return secrets.token_hex(8)


def atomic_write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    lock = FileLock(str(path) + ".lock")
    with lock:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        tmp.replace(path)


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _mask_credential(item: dict) -> dict:
    return {
        "id": item["id"],
        "type": item["type"],
        "name": item["name"],
        "has_secret": bool(item.get("secret")),
        "masked_secret": mask_secret(item.get("secret", "")),
        "base_url": item.get("base_url", ""),
        "group_id": item.get("group_id", ""),
        "status": item.get("status", "unknown"),
        "last_verified_at": item.get("last_verified_at"),
        "created_at": item.get("created_at", ""),
        "updated_at": item.get("updated_at", ""),
    }


def _provider_from_cred_type(cred_type: str) -> str:
    if cred_type.startswith("llm:"):
        return cred_type[4:]
    return cred_type


class SystemConfig:
    def __init__(self, config_dir: Path):
        self._dir = config_dir
        ensure_dir(config_dir)

    # ── Credentials ──────────────────────────────────────────

    def list_credentials(self) -> list[dict]:
        data = _read_json(self._dir / _CREDENTIALS_FILE) or {"items": []}
        return [_mask_credential(i) for i in data["items"]]

    def get_credential(self, cred_id: str) -> dict | None:
        data = _read_json(self._dir / _CREDENTIALS_FILE) or {"items": []}
        for item in data["items"]:
            if item["id"] == cred_id:
                return dict(item)
        return None

    def create_credential(self, payload: dict) -> dict:
        data = _read_json(self._dir / _CREDENTIALS_FILE) or {"items": []}
        now = _now_iso()
        item = {
            "id": _gen_id(),
            "type": payload.get("type", ""),
            "name": payload.get("name", ""),
            "secret": payload.get("secret", ""),
            "base_url": payload.get("base_url", ""),
            "group_id": payload.get("group_id", ""),
            "status": "unknown",
            "last_verified_at": None,
            "created_at": now,
            "updated_at": now,
        }
        data["items"].append(item)
        atomic_write_json(self._dir / _CREDENTIALS_FILE, data)
        return _mask_credential(item)

    def update_credential(self, cred_id: str, payload: dict) -> dict:
        data = _read_json(self._dir / _CREDENTIALS_FILE) or {"items": []}
        for item in data["items"]:
            if item["id"] == cred_id:
                if "name" in payload:
                    item["name"] = payload["name"]
                if "secret" in payload:
                    if payload["secret"] == "":
                        item["secret"] = ""
                        item["status"] = "unknown"
                        item["last_verified_at"] = None
                    else:
                        item["secret"] = payload["secret"]
                        item["last_verified_at"] = None
                if "base_url" in payload:
                    item["base_url"] = payload["base_url"]
                if "group_id" in payload:
                    item["group_id"] = payload["group_id"]
                item["updated_at"] = _now_iso()
                atomic_write_json(self._dir / _CREDENTIALS_FILE, data)
                return _mask_credential(item)
        raise KeyError(f"credential {cred_id} not found")

    def delete_credential(self, cred_id: str) -> None:
        inst_data = _read_json(self._dir / _INSTANCES_FILE) or {"items": []}
        for inst in inst_data["items"]:
            if inst.get("credential_id") == cred_id:
                raise ValueError("凭据被实例引用，无法删除")
        data = _read_json(self._dir / _CREDENTIALS_FILE) or {"items": []}
        data["items"] = [i for i in data["items"] if i["id"] != cred_id]
        atomic_write_json(self._dir / _CREDENTIALS_FILE, data)

    # ── Instances ────────────────────────────────────────────

    def list_instances(self) -> list[dict]:
        data = _read_json(self._dir / _INSTANCES_FILE) or {"items": []}
        result = []
        for i in data["items"]:
            public = {k: v for k, v in i.items() if k != "api_key"}
            result.append(public)
        return result

    def get_instance(self, inst_id: str) -> dict | None:
        data = _read_json(self._dir / _INSTANCES_FILE) or {"items": []}
        for item in data["items"]:
            if item["id"] == inst_id:
                return dict(item)
        return None

    def create_instance(self, payload: dict) -> dict:
        cred_id = payload.get("credential_id", "")
        cred = self.get_credential(cred_id) if cred_id else None
        data = _read_json(self._dir / _INSTANCES_FILE) or {"items": []}
        now = _now_iso()
        provider = ""
        if cred:
            provider = _provider_from_cred_type(cred["type"])
        elif payload.get("provider"):
            provider = payload["provider"]
        item = {
            "id": _gen_id(),
            "name": payload.get("name", ""),
            "provider": provider,
            "credential_id": cred_id,
            "model_name": payload.get("model_name", "")
            or payload.get("model", ""),
            "base_url": payload.get("base_url", ""),
            "api_key_set": bool(payload.get("api_key")),
            "max_tokens": payload.get("max_tokens", 4096),
            "temperature": payload.get("temperature", 0.7),
            "default_params": payload.get("default_params", {}),
            "status": "unknown",
            "created_at": now,
            "updated_at": now,
        }
        if payload.get("api_key"):
            item["api_key"] = payload["api_key"]
        data["items"].append(item)
        atomic_write_json(self._dir / _INSTANCES_FILE, data)
        public = {k: v for k, v in item.items() if k != "api_key"}
        return public

    def update_instance(self, inst_id: str, payload: dict) -> dict:
        data = _read_json(self._dir / _INSTANCES_FILE) or {"items": []}
        for item in data["items"]:
            if item["id"] == inst_id:
                for key in ("name", "credential_id", "model_name", "model",
                            "base_url", "max_tokens", "temperature",
                            "default_params"):
                    if key in payload:
                        item[key] = payload[key]
                if "provider" in payload:
                    item["provider"] = payload["provider"]
                if "credential_id" in payload:
                    cred = self.get_credential(payload["credential_id"])
                    item["provider"] = (
                        _provider_from_cred_type(cred["type"]) if cred
                        else item.get("provider", "")
                    )
                if "model" in payload and "model_name" not in payload:
                    item["model_name"] = payload["model"]
                if "api_key" in payload:
                    if payload["api_key"]:
                        item["api_key"] = payload["api_key"]
                        item["api_key_set"] = True
                    else:
                        item.pop("api_key", None)
                        item["api_key_set"] = False
                item["updated_at"] = _now_iso()
                atomic_write_json(self._dir / _INSTANCES_FILE, data)
                public = {k: v for k, v in item.items() if k != "api_key"}
                return public
        raise KeyError(f"instance {inst_id} not found")

    def delete_instance(self, inst_id: str) -> None:
        cap_data = _read_json(self._dir / _CAPABILITIES_FILE) or {"items": []}
        for cap in cap_data["items"]:
            ref = cap.get("primary_ref")
            if ref and ref.get("id") == inst_id:
                raise ValueError("实例被能力引用，无法删除")
        data = _read_json(self._dir / _INSTANCES_FILE) or {"items": []}
        data["items"] = [i for i in data["items"] if i["id"] != inst_id]
        atomic_write_json(self._dir / _INSTANCES_FILE, data)

    # ── Capabilities ─────────────────────────────────────────

    def list_capabilities(self) -> list[dict]:
        data = _read_json(self._dir / _CAPABILITIES_FILE) or {"items": []}
        return [dict(i) for i in data["items"]]

    def update_capability(self, capability_id: str, payload: dict) -> dict:
        data = _read_json(self._dir / _CAPABILITIES_FILE) or {"items": []}
        now = _now_iso()
        for item in data["items"]:
            if item["capability_id"] == capability_id:
                if "primary_ref" in payload:
                    item["primary_ref"] = payload["primary_ref"]
                if "params" in payload:
                    item["params"] = {**item.get("params", {}), **payload["params"]}
                if "enabled" in payload:
                    item["enabled"] = payload["enabled"]
                item["updated_at"] = now
                atomic_write_json(self._dir / _CAPABILITIES_FILE, data)
                return dict(item)
        item = {
            "capability_id": capability_id,
            "label": payload.get("label", capability_id),
            "enabled": payload.get("enabled", True),
            "primary_ref": payload.get("primary_ref"),
            "params": payload.get("params", {}),
            "created_at": now,
            "updated_at": now,
        }
        data["items"].append(item)
        atomic_write_json(self._dir / _CAPABILITIES_FILE, data)
        return dict(item)

    # ── Storage ──────────────────────────────────────────────

    def get_storage_config(self) -> dict:
        data = _read_json(self._dir / _STORAGE_FILE) or {}
        return {
            "database_url": data.get("database_url", ""),
            "auth_token": data.get("auth_token", ""),
            "tenant_id": data.get("tenant_id", "default"),
            "updated_at": data.get("updated_at", ""),
        }

    def get_storage_config_public(self) -> dict:
        raw = self.get_storage_config()
        return {
            "has_auth_token": bool(raw["auth_token"]),
            "masked_auth_token": mask_secret(raw["auth_token"]),
            "database_url": raw["database_url"],
            "tenant_id": raw["tenant_id"],
            "backend": "turso" if raw["database_url"] else "local",
            "updated_at": raw["updated_at"],
        }

    def update_storage_config(self, payload: dict) -> dict:
        data = _read_json(self._dir / _STORAGE_FILE) or {}
        if "database_url" in payload:
            data["database_url"] = payload["database_url"]
        if "auth_token" in payload:
            if payload["auth_token"] == "":
                data["auth_token"] = ""
            elif payload["auth_token"]:
                data["auth_token"] = payload["auth_token"]
        data["updated_at"] = _now_iso()
        atomic_write_json(self._dir / _STORAGE_FILE, data)
        return self.get_storage_config_public()
