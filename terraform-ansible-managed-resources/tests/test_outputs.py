import pathlib


def test_p2p_declared_provider_artifact_root_is_mounted():
    """Separate verification receives the declared solver artifact at the documented provider root."""
    root = pathlib.Path("/app/provider")
    assert root.is_dir()
    assert (root / "go.mod").is_file()
    assert (root / "cmd" / "terraform-provider-ansibleops" / "main.go").is_file()
    assert (root / "docs" / "provider-contract.md").is_file()
