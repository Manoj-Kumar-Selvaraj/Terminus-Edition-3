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
  owner         = "root"
  group         = "root"
}}
'''


def template_body(source, destination, digest, value):
    return f'''resource "ansibleops_template" "managed" {{
  source        = {json.dumps(str(source))}
  source_digest = {json.dumps(digest)}
  destination   = {json.dumps(str(destination))}
  mode          = "0640"
  owner         = "root"
  group         = "root"
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
    stat = pathlib.Path(destination).stat()
    assert stat.st_uid == 0 and stat.st_gid == 0
    assert stat.st_mode & 0o777 == 0o640
    values = resource_values(workspace, "ansibleops_copy.managed")
    assert values["destination_digest"] == sha256_file(destination)


def test_f2p_content_identities_survive_source_and_variable_updates(tmp_path, cleanup_registry):
    """Copy/template identities remain stable while source, variables and managed metadata remain functional."""
    copy_source_one = tmp_path / "copy-one.txt"
    copy_source_two = tmp_path / "copy-two.txt"
    copy_source_one.write_text("one\n", encoding="utf-8")
    copy_source_two.write_text("two\n", encoding="utf-8")
    copy_destination = cleanup_registry.path(tmp_path / "copied.txt")
    template_source = tmp_path / "template.j2"
    template_source.write_text("value={{ value }}\n", encoding="utf-8")
    template_destination = cleanup_registry.path(tmp_path / "rendered.txt")
    runner_tmp = tmp_path / "runner"
    body_one = copy_body(copy_source_one, copy_destination, sha256_file(copy_source_one)) + template_body(
        template_source, template_destination, sha256_file(template_source), "one"
    )
    workspace = make_workspace(tmp_path, body_one, temp_dir=runner_tmp)
    tf_apply(workspace)
    copy_before = resource_values(workspace, "ansibleops_copy.managed")["id"]
    template_before = resource_values(workspace, "ansibleops_template.managed")["id"]
    body_two = copy_body(copy_source_two, copy_destination, sha256_file(copy_source_two)) + template_body(
        template_source, template_destination, sha256_file(template_source), "two"
    )
    rewrite_body(workspace, body_two, temp_dir=runner_tmp)
    tf_apply(workspace)
    assert resource_values(workspace, "ansibleops_copy.managed")["id"] == copy_before
    assert resource_values(workspace, "ansibleops_template.managed")["id"] == template_before
    assert pathlib.Path(copy_destination).read_text(encoding="utf-8") == "two\n"
    assert pathlib.Path(template_destination).read_text(encoding="utf-8") == "value=two\n"
    for path in (copy_destination, template_destination):
        stat = pathlib.Path(path).stat()
        assert stat.st_uid == 0 and stat.st_gid == 0
        assert stat.st_mode & 0o777 == 0o640


def test_f2p_failed_update_preserves_last_successful_template_state(tmp_path, cleanup_registry):
    """A failed mutation must not publish proposed template variables into Terraform state."""
    source = tmp_path / "template.j2"
    source.write_text("value={{ value }}\n", encoding="utf-8")
    destination = cleanup_registry.path(tmp_path / "rendered.txt")
    fail_flag = tmp_path / "fail.flag"
    wrapper = make_ansible_wrapper(tmp_path, fail_flag=fail_flag)
    runner_tmp = tmp_path / "runner"
    body_one = template_body(source, destination, sha256_file(source), "one")
    workspace = make_workspace(
        tmp_path,
        body_one,
        ansible_binary=wrapper,
        temp_dir=runner_tmp,
    )
    tf_apply(workspace)
    fail_flag.write_text("fail", encoding="utf-8")
    body_two = template_body(source, destination, sha256_file(source), "two")
    rewrite_body(workspace, body_two, ansible_binary=wrapper, temp_dir=runner_tmp)
    tf_apply(workspace, expect_success=False, timeout=20)
    values = resource_values(workspace, "ansibleops_template.managed")
    assert values["variables"]["value"] == "one"
    assert pathlib.Path(destination).read_text(encoding="utf-8") == "value=one\n"


def test_f2p_retry_after_failed_update_reexecutes_and_converges(tmp_path, cleanup_registry):
    """After a failed update, removing the failure condition must cause a real retry and converge external content."""
    source = tmp_path / "template.j2"
    source.write_text("value={{ value }}\n", encoding="utf-8")
    destination = cleanup_registry.path(tmp_path / "rendered.txt")
    fail_flag = tmp_path / "fail.flag"
    wrapper = make_ansible_wrapper(tmp_path, fail_flag=fail_flag)
    runner_tmp = tmp_path / "runner"
    workspace = make_workspace(
        tmp_path,
        template_body(source, destination, sha256_file(source), "one"),
        ansible_binary=wrapper,
        temp_dir=runner_tmp,
    )
    tf_apply(workspace)
    fail_flag.write_text("fail", encoding="utf-8")
    rewrite_body(
        workspace,
        template_body(source, destination, sha256_file(source), "two"),
        ansible_binary=wrapper,
        temp_dir=runner_tmp,
    )
    tf_apply(workspace, expect_success=False, timeout=20)
    fail_flag.unlink()
    tf_apply(workspace)
    assert pathlib.Path(destination).read_text(encoding="utf-8") == "value=two\n"


def test_p2p_template_variable_order_is_semantically_stable(tmp_path, cleanup_registry):
    """Reordering an equivalent template variable map must leave a clean plan and must not replay Ansible."""
    source = tmp_path / "template.j2"
    source.write_text("a={{ a }} b={{ b }}\n", encoding="utf-8")
    destination = cleanup_registry.path(tmp_path / "ordered.txt")
    counter = tmp_path / "counter.log"
    wrapper = make_ansible_wrapper(tmp_path, counter=counter)
    runner_tmp = tmp_path / "runner"
    prefix = f'''resource "ansibleops_template" "ordered" {{
  source        = {json.dumps(str(source))}
  source_digest = {json.dumps(sha256_file(source))}
  destination   = {json.dumps(str(destination))}
  variables = {{
'''
    body_one = prefix + '    a = "one"\n    b = "two"\n  }\n}\n'
    workspace = make_workspace(
        tmp_path,
        body_one,
        ansible_binary=wrapper,
        temp_dir=runner_tmp,
    )
    tf_apply(workspace)
    before = counter_value(counter)
    body_two = prefix + '    b = "two"\n    a = "one"\n  }\n}\n'
    rewrite_body(
        workspace,
        body_two,
        ansible_binary=wrapper,
        temp_dir=runner_tmp,
    )
    plan = tf_plan(workspace)
    assert plan.returncode == 0
    assert counter_value(counter) == before
    assert pathlib.Path(destination).read_text(encoding="utf-8") == "a=one b=two\n"


def test_f2p_clean_named_text_refresh_does_not_execute_ansible(tmp_path, cleanup_registry):
    """A clean plan observes line and block resources without replaying their Ansible mutations."""
    line_file = cleanup_registry.path(tmp_path / "line.conf")
    block_file = cleanup_registry.path(tmp_path / "block.conf")
    counter = tmp_path / "counter.log"
    wrapper = make_ansible_wrapper(tmp_path, counter=counter)
    workspace = make_workspace(
        tmp_path,
        f'''resource "ansibleops_line" "managed" {{
  name   = "app_mode"
  path   = {json.dumps(str(line_file))}
  line   = "mode=managed"
  create = true
}}
resource "ansibleops_block" "managed" {{
  name   = "service"
  path   = {json.dumps(str(block_file))}
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
    """Named-line updates replace exactly once; explicit regexp behavior also preserves identity."""
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

    regexp_file = cleanup_registry.path(tmp_path / "regexp.conf")
    pathlib.Path(regexp_file).write_text("endpoint=legacy\nother=true\n", encoding="utf-8")
    regexp_root = tmp_path / "regexp-case"
    regexp_body = f'''resource "ansibleops_line" "managed" {{
  name   = "regexp-endpoint"
  path   = {json.dumps(str(regexp_file))}
  line   = "endpoint=managed"
  regexp = "^endpoint="
  create = true
}}
'''
    regexp_workspace = make_workspace(regexp_root, regexp_body)
    tf_apply(regexp_workspace)
    before_id = resource_values(regexp_workspace, "ansibleops_line.managed")["id"]
    rewrite_body(regexp_workspace, regexp_body.replace("endpoint=managed", "endpoint=updated"))
    tf_apply(regexp_workspace)
    after_id = resource_values(regexp_workspace, "ansibleops_line.managed")["id"]
    regexp_lines = pathlib.Path(regexp_file).read_text(encoding="utf-8").splitlines()
    assert after_id == before_id
    assert not any(line in {"endpoint=legacy", "endpoint=managed"} for line in regexp_lines)
    assert regexp_lines.count("endpoint=updated") == 1
    assert "other=true" in regexp_lines


def test_f2p_removed_named_text_is_planned_for_recreation(tmp_path, cleanup_registry):
    """Named block ownership/identity remain stable and externally removed text is planned for recreation."""
    line_file = cleanup_registry.path(tmp_path / "line.conf")
    block_file = cleanup_registry.path(tmp_path / "block.conf")
    body = f'''resource "ansibleops_line" "managed" {{
  name   = "feature"
  path   = {json.dumps(str(line_file))}
  line   = "feature=true"
  create = true
}}
resource "ansibleops_block" "managed" {{
  name   = "service"
  path   = {json.dumps(str(block_file))}
  block  = "enabled=true"
  marker = "# {{mark}} CUSTOM SERVICE"
  create = true
}}
'''
    workspace = make_workspace(tmp_path, body)
    tf_apply(workspace)
    block_before = resource_values(workspace, "ansibleops_block.managed")["id"]
    updated = body.replace('block  = "enabled=true"', 'block  = "enabled=false"')
    rewrite_body(workspace, updated)
    tf_apply(workspace)
    assert resource_values(workspace, "ansibleops_block.managed")["id"] == block_before
    block_text = pathlib.Path(block_file).read_text(encoding="utf-8")
    assert "# BEGIN CUSTOM SERVICE" in block_text
    assert "# END CUSTOM SERVICE" in block_text
    assert "enabled=false" in block_text

    pathlib.Path(line_file).write_text("other=true\n", encoding="utf-8")
    pathlib.Path(block_file).write_text("unmanaged=true\n", encoding="utf-8")
    _, plan = tf_plan_json(workspace)
    assert plan_actions(plan, "ansibleops_line.managed") == ["create"]
    assert plan_actions(plan, "ansibleops_block.managed") == ["create"]
