"""REST API — system settings (credentials, instances, capabilities, prompts)."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.config.paths import config_dir
from app.config.system_config import SystemConfig

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _cfg() -> SystemConfig:
    return SystemConfig(config_dir())


# ── System config ──────────────────────────────────────


@router.get("/system")
async def get_system_config():
    cfg = _cfg()
    storage = cfg.get_storage_config_public()
    creds = cfg.list_credentials()
    instances = cfg.list_instances()
    caps = cfg.list_capabilities()
    from app.storage.file_store import get_store
    store = get_store()
    sessions = store.list_sessions()
    return {
        "status": "success",
        "data": {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "data_dir": str(Path("data").resolve()),
            "storage_mode": storage.get("backend", "local"),
            "credential_count": len(creds),
            "instance_count": len(instances),
            "capability_count": len(caps),
            "library_count": 0,
            "session_count": len(sessions),
            **storage,
        },
    }


@router.put("/system")
async def update_system_config(body: dict):
    cfg = _cfg()
    result = cfg.update_storage_config(body)
    return {"status": "success", "data": result}


# ── Credentials ────────────────────────────────────────


@router.get("/credentials")
async def get_credentials():
    cfg = _cfg()
    creds = cfg.list_credentials()
    mapped = {}
    for c in creds:
        mapped[c["id"]] = {"masked": c["masked_secret"]}
    return {"status": "success", "data": mapped}


@router.put("/credentials")
async def update_credentials(body: dict):
    cfg = _cfg()
    existing = _cfg().list_credentials()
    for key, secret in body.items():
        found = False
        for c in existing:
            if c["id"] == key or c.get("type") == key:
                cfg.update_credential(c["id"], {"secret": secret})
                found = True
                break
        if not found:
            cfg.create_credential({"type": key, "name": key, "secret": secret})
    return {"status": "success"}


@router.post("/credentials/{key:path}/test")
async def test_credential(key: str):
    return {
        "status": "success",
        "data": {"ok": True, "message": "连接测试通过（模拟）"},
    }


# ── Instances ──────────────────────────────────────────


@router.get("/instances")
async def get_instances():
    cfg = _cfg()
    instances = cfg.list_instances()
    return {"status": "success", "data": {"instances": instances}}


@router.post("/instances", status_code=201)
async def create_instance(body: dict):
    cfg = _cfg()
    inst = cfg.create_instance(body)
    return {"status": "success", "data": inst}


@router.patch("/instances/{inst_id}")
async def update_instance(inst_id: str, body: dict):
    cfg = _cfg()
    try:
        inst = cfg.update_instance(inst_id, body)
    except KeyError:
        raise HTTPException(404, "Instance not found")
    return {"status": "success", "data": inst}


@router.delete("/instances/{inst_id}")
async def delete_instance(inst_id: str):
    cfg = _cfg()
    try:
        cfg.delete_instance(inst_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "success"}


@router.post("/instances/{inst_id}/test")
async def test_instance(inst_id: str):
    return {
        "status": "success",
        "data": {"ok": True, "message": "连接测试通过（模拟）"},
    }


# ── Capabilities ───────────────────────────────────────


@router.get("/capabilities")
async def get_capabilities():
    cfg = _cfg()
    caps = cfg.list_capabilities()
    return {
        "status": "success",
        "data": {
            "bindings": [
                {
                    "capability": c.get("capability_id", ""),
                    "instance_id": (c.get("primary_ref") or {}).get("id", ""),
                    "instance_name": (c.get("primary_ref") or {}).get("name", ""),
                }
                for c in caps
            ]
        },
    }


@router.put("/capabilities/{capability}")
async def update_capability(capability: str, body: dict):
    cfg = _cfg()
    instance_id = body.get("instance_id", "")
    primary_ref = {"id": instance_id} if instance_id else None
    cfg.update_capability(capability, {"primary_ref": primary_ref})
    return {"status": "success"}


# ── Prompts ────────────────────────────────────────────


@router.get("/prompts")
async def get_prompts():
    from app.agents.prompt_settings import load_all_prompts
    prompts = load_all_prompts()
    return {
        "status": "success",
        "data": {
            "prompts": [
                {"name": k, "system_prompt": v}
                for k, v in prompts.items()
            ]
        },
    }


@router.put("/prompts/{name:path}")
async def update_prompt(name: str, body: dict):
    return {"status": "success"}
