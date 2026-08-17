import json
import pathlib

from conftest import (
    counter_value,
    make_ansible_wrapper,
    make_workspace,
    plan_actions,
    resource_values,
    rewrite_body,
    sha256_file,
    tf_apply,
    tf_plan,
    tf_plan_json,
)


def copy_body(source, destination, digest, mode="0640"):
    return f'''resource "ansibleops_copy" "managed" {{
  source        = {json.dumps(str(source))}
  source_digest = {json.dumps(digest)}
  destination   = {json.dumps(str(destination))}
  mode          = {json.dumps(mode)}
}}
'''


def template_body(source, destination, digest, value):
    return f'''resource "ansibleops_template" "managed" {{
  source        = {json.dumps(str(source))}
  source_digest = {json.dumps(digest)}
  destination   = {json.dumps(str(destination))}
  variables = {{
    value = {json.dumps(value)}
  }}
}}
'''


def test_f2p_copy_destination_content_drift_requires_reconciliation(tmp_path, cleanup_registry):
    """A copied destination modified out of band must plan an update back to the configured source digest."""
    source = tmp_path / "source.txt"
    source.write_text("expected\n", encoding="utf-8")
    destination = cleanup_registry.path(tmp_path / "destination.txt")
    workspace = make_workspace(tmp_path, copy_body(source, destination, sha256_file(source)))
    tf_apply(workspace)
    pathlib.Path(destination).write_text("drifted\n", encoding="utf-8")
    _, plan = tf_plan_json(workspace)
    assert plan_actions(plan, "ansibleops_copy.managed") == ["update"]


def test_f2p_copy_source_digest_change_executes_content_update(tmp_path, cleanup_registry):
    """Changing source content plus its declared digest must execute one copy update rather than only advancing state."""
    source = tmp_path / "source.txt"
    source.write_text("version-one\n", encoding="utf-8")
    destination = cleanup_registry.path(tmp_path / "destination.txt")
    runner_tmp = tmp_path / "runner"
    workspace = make_workspace(tmp_path, copy_body(source, destination, sha256_file(source)), temp_dir=runner_tmp)
    tf_apply(workspace)
    source.write_text("version-two\n", encoding="utf-8")
    rewrite_body(workspace, copy_body(source, destination, sha256_file(source)), temp_dir=runner_tmp)
    tf_apply(workspace)
    assert pathlib.Path(destination).read_text(encoding="utf-8") == "version-two\n"
    values = resource_values(workspace, "ansibleops_copy.managed")
    assert values["destination_digest"] == sha256_file(destination)


def test_f2p_copy_identity_is_destination_key_not_source_path(tmp_path, cleanup_registry):
    """Switching the source file for the same managed destination must preserve the resource identity."""
    source1 = tmp_path / "source-one.txt"
    source2 = tmp_path / "source-two.txt"
    source1.write_text("one\n", encoding="utf-8")
    source2.write_text("two\n", encoding="utf-8")
    destination = cleanup_registry.path(tmp_path / "destination.txt")
    runner_tmp = tmp_path / "runner"
    workspace = make_workspace(tmp_path, copy_body(source1, destination, sha256_file(source1)), temp_dir=runner_tmp)
    tf_apply(workspace)
    before = resource_values(workspace, "ansibleops_copy.managed")["id"]
    rewrite_body(workspace, copy_body(source2, destination, sha256_file(source2)), temp_dir=runner_tmp)
    tf_apply(workspace)
    after = resource_values(workspace, "ansibleops_copy.managed")["id"]
    assert after == before
    assert pathlib.Path(destination).read_text(encoding="utf-8") == "two\n"


def test_f2p_failed_update_preserves_last_successful_template_state(tmp_path, cleanup_registry):
    """A timed-out mutation must not publish the proposed template variables into Terraform state."""
    source = tmp_path / "template.j2"
    source.write_text("value={{ value }}\n", encoding="utf-8")
    destination = cleanup_registry.path(tmp_path / "rendered.txt")
    sleep_flag = tmp_path / "sleep.flag"
    wrapper = make_ansible_wrapper(tmp_path, sleep_flag=sleep_flag)
    runner_tmp = tmp_path / "runner"
    body_one = template_body(source, destination, sha256_file(source), "one")
    workspace = make_workspace(
        tmp_path,
        body_one,
        ansible_binary=wrapper,
        timeout_seconds=1,
        temp_dir=runner_tmp,
    )
    tf_apply(workspace)
    sleep_flag.write_text("sleep", encoding="utf-8")
    body_two = template_body(source, destination, sha256_file(source), "two")
    rewrite_body(workspace, body_two, ansible_binary=wrapper, timeout_seconds=1, temp_dir=runner_tmp)
    tf_apply(workspace, expect_success=False, timeout=20)
    values = resource_values(workspace, "ansibleops_template.managed")
    assert values["variables"]["value"] == "one"
    assert pathlib.Path(destination).read_text(encoding="utf-8") == "value=one\n"


def test_f2p_retry_after_failed_update_reexecutes_and_converges(tmp_path, cleanup_registry):
    """After a failed update, removing the failure condition must cause a real retry and converge external content."""
    source = tmp_path / "template.j2"
    source.write_text("value={{ value }}\n", encoding="utf-8")
    destination = cleanup_registry.path(tmp_path / "rendered.txt")
    sleep_flag = tmp_path / "sleep.flag"
    wrapper = make_ansible_wrapper(tmp_path, sleep_flag=sleep_flag)
    runner_tmp = tmp_path / "runner"
    workspace = make_workspace(
        tmp_path,
        template_body(source, destination, sha256_file(source), "one"),
        ansible_binary=wrapper,
        timeout_seconds=1,
        temp_dir=runner_tmp,
    )
    tf_apply(workspace)
    sleep_flag.write_text("sleep", encoding="utf-8")
    rewrite_body(
        workspace,
        template_body(source, destination, sha256_file(source), "two"),
        ansible_binary=wrapper,
        timeout_seconds=1,
        temp_dir=runner_tmp,
    )
    tf_apply(workspace, expect_success=False, timeout=20)
    sleep_flag.unlink()
    tf_apply(workspace)
    assert pathlib.Path(destination).read_text(encoding="utf-8") == "value=two\n"


def test_f2p_template_identity_survives_variable_update(tmp_path, cleanup_registry):
    """Template variables are mutable desired data and must not participate in destination identity."""
    source = tmp_path / "template.j2"
    source.write_text("value={{ value }}\n", encoding="utf-8")
    destination = cleanup_registry.path(tmp_path / "rendered.txt")
    runner_tmp = tmp_path / "runner"
    workspace = make_workspace(
        tmp_path,
        template_body(source, destination, sha256_file(source), "one"),
        temp_dir=runner_tmp,
    )
    tf_apply(workspace)
    before = resource_values(workspace, "ansibleops_template.managed")["id"]
    rewrite_body(
        workspace,
        template_body(source, destination, sha256_file(source), "two"),
        temp_dir=runner_tmp,
    )
    tf_apply(workspace)
    after = resource_values(workspace, "ansibleops_template.managed")["id"]
    assert after == before


def test_f2p_clean_line_refresh_does_not_execute_ansible(tmp_path, cleanup_registry):
    """A clean Terraform plan must observe a managed line without replaying lineinfile."""
    managed = cleanup_registry.path(tmp_path / "app.conf")
    counter = tmp_path / "counter.log"
    wrapper = make_ansible_wrapper(tmp_path, counter=counter)
    workspace = make_workspace(
        tmp_path,
        f'''resource "ansibleops_line" "managed" {{
  name   = "app_mode"
  path   = {json.dumps(str(managed))}
  line   = "mode=managed"
  create = true
}}
''',
        ansible_binary=wrapper,
    )
    tf_apply(workspace)
    before = counter_value(counter)
    plan = tf_plan(workspace)
    assert plan.returncode == 0
    assert counter_value(counter) == before


def test_f2p_clean_block_refresh_does_not_execute_ansible(tmp_path, cleanup_registry):
    """A clean Terraform plan must parse a managed block without replaying blockinfile."""
    managed = cleanup_registry.path(tmp_path / "app.conf")
    counter = tmp_path / "counter.log"
    wrapper = make_ansible_wrapper(tmp_path, counter=counter)
    workspace = make_workspace(
        tmp_path,
        f'''resource "ansibleops_block" "managed" {{
  name   = "service"
  path   = {json.dumps(str(managed))}
  block  = "enabled=true\\nworkers=2"
  create = true
}}
''',
        ansible_binary=wrapper,
    )
    tf_apply(workspace)
    before = counter_value(counter)
    plan = tf_plan(workspace)
    assert plan.returncode == 0
    assert counter_value(counter) == before


def test_f2p_line_update_replaces_previous_value_exactly_once(tmp_path, cleanup_registry):
    """Updating a named line without an explicit regexp must replace its prior value instead of appending a duplicate."""
    managed = cleanup_registry.path(tmp_path / "app.conf")
    runner_tmp = tmp_path / "runner"
    body_one = f'''resource "ansibleops_line" "managed" {{
  name   = "endpoint"
  path   = {json.dumps(str(managed))}
  line   = "endpoint=one"
  create = true
}}
'''
    workspace = make_workspace(tmp_path, body_one, temp_dir=runner_tmp)
    tf_apply(workspace)
    rewrite_body(workspace, body_one.replace("endpoint=one", "endpoint=two"), temp_dir=runner_tmp)
    tf_apply(workspace)
    lines = pathlib.Path(managed).read_text(encoding="utf-8").splitlines()
    assert "endpoint=one" not in lines
    assert lines.count("endpoint=two") == 1


def test_f2p_removed_managed_line_is_planned_for_recreation(tmp_path, cleanup_registry):
    """If the owned line disappears externally, Read must report it missing rather than silently recreating it during plan."""
    managed = cleanup_registry.path(tmp_path / "app.conf")
    workspace = make_workspace(
        tmp_path,
        f'''resource "ansibleops_line" "managed" {{
  name   = "feature"
  path   = {json.dumps(str(managed))}
  line   = "feature=true"
  create = true
}}
''',
    )
    tf_apply(workspace)
    pathlib.Path(managed).write_text("other=true\n", encoding="utf-8")
    _, plan = tf_plan_json(workspace)
    assert plan_actions(plan, "ansibleops_line.managed") == ["create"]


def test_f2p_removed_managed_block_is_planned_for_recreation(tmp_path, cleanup_registry):
    """If a named block disappears externally, plan must show recreation without mutating during refresh."""
    managed = cleanup_registry.path(tmp_path / "app.conf")
    workspace = make_workspace(
        tmp_path,
        f'''resource "ansibleops_block" "managed" {{
  name   = "service"
  path   = {json.dumps(str(managed))}
  block  = "enabled=true"
  create = true
}}
''',
    )
    tf_apply(workspace)
    pathlib.Path(managed).write_text("unmanaged=true\n", encoding="utf-8")
    _, plan = tf_plan_json(workspace)
    assert plan_actions(plan, "ansibleops_block.managed") == ["create"]
