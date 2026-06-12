"""Tests for app.config.system_config — atomic write, masking, CRUD."""
import json

import pytest

from app.config.system_config import SystemConfig


@pytest.fixture
def sc(tmp_path):
    return SystemConfig(config_dir=tmp_path)


def test_mask_secret():
    from app.config.system_config import mask_secret
    assert mask_secret("sk-abcdef1234") == "··· 1234"
    assert mask_secret("ab") == "····"
    assert mask_secret("") == ""
    assert mask_secret("x" * 100) == "··· xxxx"


def test_atomic_write_json(tmp_path):
    from app.config.system_config import atomic_write_json
    target = tmp_path / "test.json"
    data = {"hello": "world", "num": 42}
    atomic_write_json(target, data)
    assert json.loads(target.read_text(encoding="utf-8")) == data


def test_crud_credential(sc):
    c = sc.create_credential({"type": "tavily", "name": "my-tavily", "secret": "sk-abc123"})
    assert c["id"]
    assert c["type"] == "tavily"
    assert c["has_secret"] is True
    assert c["masked_secret"] == "··· c123"
    assert c["status"] == "unknown"

    got = sc.get_credential(c["id"])
    assert got["secret"] == "sk-abc123"

    listed = sc.list_credentials()
    assert len(listed) == 1
    assert "secret" not in listed[0]
    assert listed[0]["has_secret"] is True

    sc.update_credential(c["id"], {"name": "tavily-renamed"})
    updated = sc.get_credential(c["id"])
    assert updated["name"] == "tavily-renamed"
    assert updated["secret"] == "sk-abc123"

    sc.delete_credential(c["id"])
    assert sc.list_credentials() == []


def test_clear_secret_sets_unknown(sc):
    c = sc.create_credential({"type": "jina", "name": "j1", "secret": "jinakey"})
    sc.update_credential(c["id"], {"secret": ""})
    got = sc.get_credential(c["id"])
    assert got["secret"] == ""
    assert got["status"] == "unknown"
    assert got["last_verified_at"] is None


def test_delete_credential_conflict_with_instance(sc):
    cred = sc.create_credential({"type": "llm:openai", "name": "c1", "secret": "sk-x"})
    sc.create_instance({"name": "inst1", "credential_id": cred["id"], "model_name": "gpt-4o"})
    with pytest.raises(ValueError, match="被实例引用"):
        sc.delete_credential(cred["id"])


def test_crud_instance(sc):
    cred = sc.create_credential({"type": "llm:openai", "name": "c1", "secret": "sk-x"})
    inst = sc.create_instance({"name": "main", "credential_id": cred["id"], "model_name": "gpt-4o"})
    assert inst["id"]
    assert inst["provider"] == "openai"
    assert inst["model_name"] == "gpt-4o"

    sc.update_instance(inst["id"], {"model_name": "deepseek-chat"})
    assert sc.get_instance(inst["id"])["model_name"] == "deepseek-chat"

    sc.delete_instance(inst["id"])
    assert sc.list_instances() == []


def test_delete_instance_conflict_with_capability(sc):
    cred = sc.create_credential({"type": "llm:openai", "name": "c1", "secret": "sk-x"})
    inst = sc.create_instance({"name": "i1", "credential_id": cred["id"], "model_name": "gpt-4o"})
    sc.update_capability("review_main", {"primary_ref": {"kind": "instance", "id": inst["id"]}})
    with pytest.raises(ValueError, match="被能力引用"):
        sc.delete_instance(inst["id"])


def test_capability_crud(sc):
    cap = sc.update_capability("web_search", {"params": {"search_max_results": 30}})
    assert cap["capability_id"] == "web_search"
    assert cap["params"]["search_max_results"] == 30

    caps = sc.list_capabilities()
    assert any(c["capability_id"] == "web_search" for c in caps)


def test_storage_config(sc):
    sc.update_storage_config({"database_url": "libsql://test.turso.io", "auth_token": "tok123"})
    raw = sc.get_storage_config()
    assert raw["auth_token"] == "tok123"
    assert raw["database_url"] == "libsql://test.turso.io"

    pub = sc.get_storage_config_public()
    assert "auth_token" not in pub
    assert pub["has_auth_token"] is True
    assert pub["masked_auth_token"] == "··· k123"


def test_storage_clear_token(sc):
    sc.update_storage_config({"database_url": "libsql://test.turso.io", "auth_token": "tok123"})
    sc.update_storage_config({"auth_token": ""})
    pub = sc.get_storage_config_public()
    assert pub["has_auth_token"] is False
    raw = sc.get_storage_config()
    assert raw["auth_token"] == ""
