import tempfile
import os
import pytest
from unittest import mock
from swarm.blueprints.codey.blueprint_codey import CodeyBlueprint
from swarm.blueprints.common.audit import AuditLogger

def test_write_file_allow():
    policy = {"tool.fs.write": "allow"}
    logger = AuditLogger(enabled=False)
    bp = CodeyBlueprint(blueprint_id="appr-allow", approval_policy=policy, audit_logger=logger)
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        path = tf.name
    bp.write_file_with_approval(path, "hello")
    with open(path) as f:
        assert f.read() == "hello"
    os.remove(path)

def test_write_file_deny():
    policy = {"tool.fs.write": "deny"}
    logger = AuditLogger(enabled=False)
    bp = CodeyBlueprint(blueprint_id="appr-deny", approval_policy=policy, audit_logger=logger)
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        path = tf.name
    with pytest.raises(PermissionError):
        bp.write_file_with_approval(path, "fail")
    os.remove(path)

def test_write_file_ask_approve(monkeypatch):
    policy = {"tool.fs.write": "ask"}
    logger = AuditLogger(enabled=False)
    bp = CodeyBlueprint(blueprint_id="appr-ask", approval_policy=policy, audit_logger=logger)
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        path = tf.name
    monkeypatch.setattr("builtins.input", lambda _: "y")
    bp.write_file_with_approval(path, "yes")
    with open(path) as f:
        assert f.read() == "yes"
    os.remove(path)

def test_write_file_ask_deny(monkeypatch):
    policy = {"tool.fs.write": "ask"}
    logger = AuditLogger(enabled=False)
    bp = CodeyBlueprint(blueprint_id="appr-ask", approval_policy=policy, audit_logger=logger)
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        path = tf.name
    monkeypatch.setattr("builtins.input", lambda _: "n")
    with pytest.raises(PermissionError):
        bp.write_file_with_approval(path, "no")
    os.remove(path)

def test_shell_exec_deny():
    policy = {"tool.shell.exec": "deny"}
    logger = AuditLogger(enabled=False)
    bp = CodeyBlueprint(blueprint_id="appr-sh-deny", approval_policy=policy, audit_logger=logger)
    with pytest.raises(PermissionError):
        bp.shell_exec_with_approval("echo fail")

def test_shell_exec_allow():
    policy = {"tool.shell.exec": "allow"}
    logger = AuditLogger(enabled=False)
    bp = CodeyBlueprint(blueprint_id="appr-sh-allow", approval_policy=policy, audit_logger=logger)
    out = bp.shell_exec_with_approval("echo success")
    assert "success" in out
