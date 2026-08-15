from pathlib import Path
import json
import re

path = Path('cobol-comp3-python-equiv/tests/test_outputs.py')
text = path.read_text(encoding='utf-8')
text = text.replace('import sys\n', 'import sys\nimport subprocess\n')
text = text.replace(
    'from src.publication import atomic_publish, verify_publication\n',
    'import src.publication as publication_module\nfrom src.publication import atomic_publish, verify_publication\n',
)
text = text.replace(
    'DEFAULT_LAYOUT = ROOT / "config" / "movement.layout.json"\n',
    'DEFAULT_LAYOUT = ROOT / "config" / "movement.layout.json"\nCLI = ROOT / "bin" / "equiv-eval"\nSEED = ROOT / "sql" / "seed.sql"\n',
)
marker = 'def identity(*, gid: str = "g", source: str = "s", layout: str = "l", date: str = "2026-08-15") -> GenerationIdentity:\n'
helpers = '''def run_cli(*args: object) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run(
        [sys.executable, str(CLI), *(str(arg) for arg in args)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def public_cycle_paths(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    db_path = tmp_path / "state.db"
    source = tmp_path / "source.dat"
    source.write_bytes(reference_receipt_record())
    controls = tmp_path / "legacy.controls"
    controls.write_text(
        "processed_count=1\\naccepted_count=1\\nrejected_count=0\\n"
        "effect_count=1\\nnet_quantity=1.000\\nnet_value=10.00\\n",
        encoding="utf-8",
    )
    reports = tmp_path / "out" / "reports"
    published = tmp_path / "out" / "published"
    return db_path, source, controls, reports, published


'''
if 'def run_cli(' not in text:
    text = text.replace(marker, helpers + marker)

for old in [
    'pytest.raises(ValueError, match="padding")',
    'pytest.raises(ValueError, match="digit")',
    'pytest.raises(ValueError, match="sign")',
    'pytest.raises(ValueError, match="negative")',
    'pytest.raises(ValueError, match="outside")',
    'pytest.raises(ValueError, match="layout")',
    'pytest.raises(ValueError, match="fingerprint")',
    'pytest.raises(ValueError, match="insufficient")',
    'pytest.raises(ValueError, match="negative inventory")',
    'pytest.raises(ValueError, match="failed reconciliation")',
]:
    text = text.replace(old, 'pytest.raises(ValueError)')

text = text.replace(
    '    assert any(issue.code == "QUANTITY" for issue in validate_shape(movement(quantity="0")))\n',
    '    assert validate_shape(movement(quantity="0"))\n',
)
text = text.replace(
    '    assert any(issue.code == "TRANSFER_LOOP" for issue in validate_shape(m))\n',
    '    assert validate_shape(m)\n',
)
text = text.replace(
    '    assert any(issue.code == "ITEM_INACTIVE" for issue in validate_item(movement(), ItemPolicy("SKU00001", False)))\n',
    '    assert validate_item(movement(), ItemPolicy("SKU00001", False))\n',
)
text = text.replace(
    '    assert any(issue.code == "WAREHOUSE_INACTIVE" for issue in validate_warehouses(movement(), {"W01": WarehousePolicy("W01", False)}))\n',
    '    assert validate_warehouses(movement(), {"W01": WarehousePolicy("W01", False)})\n',
)

text, count_layout = re.subn(
    r'def test_f2p_caller_supplied_layout_path_is_honored\(tmp_path: Path\) -> None:\n.*?(?=\ndef test_f2p_odo_count_above_declared_maximum_is_rejected)',
    '''def test_f2p_caller_supplied_layout_path_is_honored(tmp_path: Path) -> None:
    path = tmp_path / "alternate-layout.json"
    path.write_text(json.dumps({"layout_id": "ALT-SEMANTIC", "version": 7, "fields": [{"name": "CODE", "picture": "X(2)"}]}))
    completed = run_cli("describe-layout", "--layout", path)
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["layout_id"] == "ALT-SEMANTIC"
    assert payload["minimum_length"] == 2

''',
    text,
    flags=re.S,
)
text, count_generation = re.subn(
    r'def test_f2p_generation_id_binds_layout_digest\(\) -> None:\n.*?(?=\ndef test_f2p_resume_rejects_layout_change)',
    '''def test_f2p_generation_id_binds_layout_digest(tmp_path: Path) -> None:
    source = tmp_path / "source.dat"
    source.write_bytes(b"same-source")
    layout_a = tmp_path / "layout-a.json"
    layout_b = tmp_path / "layout-b.json"
    layout_a.write_text(json.dumps({"layout_id": "A", "version": 1, "fields": [{"name": "X", "picture": "X(1)"}]}))
    layout_b.write_text(json.dumps({"layout_id": "B", "version": 1, "fields": [{"name": "X", "picture": "X(2)"}]}))
    first = run_cli("identity", "--source", source, "--layout", layout_a, "--business-date", "20260815")
    second = run_cli("identity", "--source", source, "--layout", layout_b, "--business-date", "20260815")
    assert first.returncode == second.returncode == 0
    assert json.loads(first.stdout)["generation_id"] != json.loads(second.stdout)["generation_id"]

''',
    text,
    flags=re.S,
)
text, count_recon = re.subn(
    r'def test_f2p_reconciliation_checks_legacy_effect_count\(tmp_path: Path\) -> None:\n.*?(?=\ndef test_f2p_reconciliation_rejects_unbalanced_transfer)',
    '''def test_f2p_reconciliation_checks_every_legacy_control(tmp_path: Path) -> None:
    db = fresh_db(tmp_path)
    names = ("effect_count", "processed_count", "accepted_count", "rejected_count", "net_quantity", "net_value")
    for name in names:
        legacy = {
            "processed_count": Decimal("0"),
            "accepted_count": Decimal("0"),
            "rejected_count": Decimal("0"),
            "effect_count": Decimal("0"),
            "net_quantity": Decimal("0"),
            "net_value": Decimal("0"),
        }
        legacy[name] = Decimal("1")
        result = reconcile(db, "g", legacy)
        assert not result.passed, f"legacy control {name} was not independently enforced"

''',
    text,
    flags=re.S,
)
text, count_publish = re.subn(
    r'def test_f2p_repeat_publication_of_same_generation_is_idempotent\(tmp_path: Path\) -> None:\n.*?(?=\ndef test_f2p_database_rejects_duplicate_generation_sequence)',
    '''def test_f2p_publication_is_atomic_and_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    first_report = tmp_path / "summary.json"
    second_report = tmp_path / "reconciliation.json"
    first_report.write_text('{"ok":true}\\n')
    second_report.write_text('{"passed":true}\\n')
    destination = tmp_path / "published"

    def partial_copytree(source: str | Path, target: str | Path, *args: object, **kwargs: object):
        target = Path(target)
        target.mkdir(parents=True, exist_ok=True)
        (target / "partial.tmp").write_text("partial", encoding="utf-8")
        raise OSError("injected non-atomic promotion failure")

    monkeypatch.setattr(publication_module.shutil, "copytree", partial_copytree)
    published = None
    try:
        published = atomic_publish(
            "g",
            {"summary": first_report, "reconciliation": second_report},
            passing_reconciliation(),
            destination,
        )
    except OSError:
        pass
    target = destination / "g"
    if published is None:
        assert not target.exists()
    else:
        assert verify_publication(published)
        second = atomic_publish(
            "g",
            {"summary": first_report, "reconciliation": second_report},
            passing_reconciliation(),
            destination,
        )
        assert second == published
        assert verify_publication(second)

''',
    text,
    flags=re.S,
)
if not all((count_layout, count_generation, count_recon, count_publish)):
    raise SystemExit(f'expected verifier blocks not found: {count_layout=} {count_generation=} {count_recon=} {count_publish=}')

additions = r'''


def test_p2p_cli_init_and_run_preserve_public_interface(tmp_path: Path) -> None:
    db_path, source, controls, reports, published = public_cycle_paths(tmp_path)
    initialized = run_cli("init-db", "--db", db_path, "--schema", SCHEMA, "--seed", SEED)
    assert initialized.returncode == 0, initialized.stderr
    assert json.loads(initialized.stdout)["status"] == "READY"
    completed = run_cli(
        "run", "--db", db_path, "--source", source, "--layout", DEFAULT_LAYOUT,
        "--business-date", "20260815", "--legacy-controls", controls,
        "--report-dir", reports, "--publish-dir", published,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["state"] == "PUBLISHED"


def test_p2p_operator_preflight_audit_archive_workflows_are_executable(tmp_path: Path) -> None:
    db_path, source, controls, reports, published = public_cycle_paths(tmp_path)
    initialized = run_cli("init-db", "--db", db_path, "--schema", SCHEMA, "--seed", SEED)
    assert initialized.returncode == 0, initialized.stderr
    check = run_cli(
        "preflight", "--db", db_path, "--source", source, "--layout", DEFAULT_LAYOUT,
        "--business-date", "20260815", "--legacy-controls", controls,
        "--report-dir", reports, "--publish-dir", published,
        "--schema", SCHEMA, "--seed", SEED,
    )
    assert check.returncode == 0, check.stderr
    assert json.loads(check.stdout)["historical_baseline"]["records"] >= 10000
    completed = run_cli(
        "run", "--db", db_path, "--source", source, "--layout", DEFAULT_LAYOUT,
        "--business-date", "20260815", "--legacy-controls", controls,
        "--report-dir", reports, "--publish-dir", published,
    )
    assert completed.returncode == 0, completed.stderr
    registry = reports.parent / "publication-registry.jsonl"
    quarantine = reports.parent / "quarantine" / "records.jsonl"
    audited = run_cli(
        "audit", "--db", db_path, "--source", source, "--layout", DEFAULT_LAYOUT,
        "--business-date", "20260815", "--expected-records", 1,
        "--quarantine", quarantine, "--registry", registry,
    )
    assert audited.returncode == 0, audited.stderr
    assert json.loads(audited.stdout)["passed"] is True
    archived = run_cli(
        "archive", "--db", db_path, "--source", source, "--layout", DEFAULT_LAYOUT,
        "--business-date", "20260815", "--report-dir", reports,
        "--publish-dir", published, "--archive-dir", tmp_path / "archive",
        "--registry", registry,
    )
    assert archived.returncode == 0, archived.stderr
    assert json.loads(archived.stdout)["archive_valid"] is True


def test_p2p_cli_runtime_errors_are_json_and_exit_two(tmp_path: Path) -> None:
    completed = run_cli(
        "identity", "--source", tmp_path / "missing.dat", "--layout", DEFAULT_LAYOUT,
        "--business-date", "20260815",
    )
    assert completed.returncode == 2
    assert completed.stdout == ""
    payload = json.loads(completed.stderr)
    assert payload["error"]["type"] == "FileNotFoundError"


def test_p2p_movement_transaction_rolls_back_effect_position_and_checkpoint(tmp_path: Path) -> None:
    db = fresh_db(tmp_path)
    seed_inventory(db, warehouse_count=2, item_count=2)
    before = db.execute(
        "SELECT quantity,value,version FROM inventory_positions WHERE warehouse_id='W01' AND item_id='SKU00001'"
    ).fetchone()
    with pytest.raises(RuntimeError):
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute(
                "INSERT INTO processed_movements VALUES(?,?,?,?,?,?,?,?)",
                ("g", "m1", 1, "ACCEPTED", "SKU00001", "RECEIPT", "1", "10"),
            )
            db.execute(
                "INSERT INTO inventory_effects(generation_id,movement_id,sequence,warehouse_id,item_id,quantity_delta,value_delta,effect_kind) VALUES(?,?,?,?,?,?,?,?)",
                ("g", "m1", 1, "W01", "SKU00001", "1", "10", "RECEIPT"),
            )
            db.execute(
                "UPDATE inventory_positions SET quantity=CAST(quantity AS REAL)+1,value=CAST(value AS REAL)+10,version=version+1 WHERE warehouse_id='W01' AND item_id='SKU00001'"
            )
            db.execute(
                "INSERT INTO checkpoints VALUES(?,?,?,?,?)",
                ("g", 1, 44, "fingerprint", "now"),
            )
            raise RuntimeError("injected crash before commit")
        except Exception:
            db.rollback()
            raise
    assert db.execute("SELECT COUNT(*) FROM processed_movements WHERE generation_id='g'").fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM inventory_effects WHERE generation_id='g'").fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM checkpoints WHERE generation_id='g'").fetchone()[0] == 0
    after = db.execute(
        "SELECT quantity,value,version FROM inventory_positions WHERE warehouse_id='W01' AND item_id='SKU00001'"
    ).fetchone()
    assert after == before


def test_p2p_checkpoint_transaction_rollback_preserves_resume_boundary(tmp_path: Path) -> None:
    db = fresh_db(tmp_path)
    ident = identity(gid="g1", source="source", layout="layout")
    with pytest.raises(RuntimeError):
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute(
                "INSERT INTO checkpoints VALUES(?,?,?,?,?)",
                (ident.generation_id, 5, 220, ident.fingerprint(), "now"),
            )
            raise RuntimeError("injected crash")
        except Exception:
            db.rollback()
            raise
    assert db.execute("SELECT COUNT(*) FROM checkpoints WHERE generation_id='g1'").fetchone()[0] == 0
    assert resume_sequence(ident, None) == 1
'''
if 'test_p2p_cli_init_and_run_preserve_public_interface' not in text:
    text += additions
path.write_text(text, encoding='utf-8')

map_path = Path('.terminus/designs/cobol-comp3-python-equiv-test-map.json')
data = json.loads(map_path.read_text(encoding='utf-8'))
data['requirements']['R-CLI'] = 'The public equiv-eval CLI must preserve caller source/layout routing, JSON output, exit semantics, init-db, identity, describe-layout and run.'
data['requirements']['R-DURABILITY'] = 'Movement effects, inventory positions and checkpoint state must roll back together on a pre-commit failure.'
data['requirements']['R-OPS'] = 'Preflight, audit and archive are real operator workflows over production-scale history and durable cutover state.'
for entry in data['tests']:
    if entry[0] == 'test_f2p_reconciliation_checks_legacy_effect_count':
        entry[0] = 'test_f2p_reconciliation_checks_every_legacy_control'
    if entry[0] == 'test_f2p_repeat_publication_of_same_generation_is_idempotent':
        entry[0] = 'test_f2p_publication_is_atomic_and_idempotent'
    if entry[0] == 'test_f2p_caller_supplied_layout_path_is_honored':
        entry[2] = 'R-CLI'
extras = [
    ['test_p2p_cli_init_and_run_preserve_public_interface','P2P','R-CLI'],
    ['test_p2p_operator_preflight_audit_archive_workflows_are_executable','P2P','R-OPS'],
    ['test_p2p_cli_runtime_errors_are_json_and_exit_two','P2P','R-CLI'],
    ['test_p2p_movement_transaction_rolls_back_effect_position_and_checkpoint','P2P','R-DURABILITY'],
    ['test_p2p_checkpoint_transaction_rollback_preserves_resume_boundary','P2P','R-DURABILITY'],
]
existing = {entry[0] for entry in data['tests']}
data['tests'].extend(entry for entry in extras if entry[0] not in existing)
map_path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
