from pathlib import Path

env = Path("codecommit-iam-merge-fence/environment/codecommit/lib/cc")
fixed = Path("codecommit-iam-merge-fence/solution/fixed")
fixed.mkdir(parents=True, exist_ok=True)
(env / "force.py").unlink(missing_ok=True)

mapping = {
    "actions.py": env / "iam" / "actions.py",
    "conditions.py": env / "iam" / "conditions.py",
    "eval.py": env / "iam" / "eval.py",
    "approvals.py": env / "prs" / "approvals.py",
    "merge.py": env / "prs" / "merge.py",
    "deliver.py": env / "pipelines" / "deliver.py",
    "event_id.py": env / "pipelines" / "event_id.py",
    "log.py": env / "audit" / "log.py",
    "retry.py": env / "webhooks" / "retry.py",
    "app.py": env / "api" / "app.py",
    "authz_gateway.py": env / "services" / "authz_gateway.py",
    "cli.py": env / "cli.py",
    "gitops.py": env / "repos" / "gitops.py",
}

for name, src in mapping.items():
    text = src.read_text(encoding="utf-8")
    ft = text
    ft = ft.replace("from cc.force import force_fixed\n", "")
    ft = ft.replace("fixed = force_fixed(fixed)\n", "fixed = True\n")
    ft = ft.replace(
        '    from cc.force import force_fixed\n\n    parser = build_parser()\n    ns = parser.parse_args(argv)\n    ns.fixed = force_fixed(bool(getattr(ns, "fixed", False)))\n',
        "    parser = build_parser()\n    ns = parser.parse_args(argv)\n    ns.fixed = True\n",
    )
    ft = ft.replace("    from cc.force import force_fixed\n\n    Handler.fixed = force_fixed(fixed)\n", "    Handler.fixed = True\n")
    ft = ft.replace(
        '    from cc.force import force_fixed\n\n    host = os.environ.get("CC_API_HOST", "127.0.0.1")\n    port = int(os.environ.get("CC_API_PORT", "8080"))\n    fixed = force_fixed(os.environ.get("CC_FIXED", "").lower() in ("1", "true", "yes"))\n',
        '    host = os.environ.get("CC_API_HOST", "127.0.0.1")\n    port = int(os.environ.get("CC_API_PORT", "8080"))\n    fixed = True\n',
    )
    ft = ft.replace("    from cc.force import force_fixed\n\n    fixed = force_fixed(fixed)\n", "    fixed = True\n")
    ft = ft.replace("    from cc.force import force_fixed\n    fixed = force_fixed(fixed)\n", "    fixed = True\n")
    (fixed / name).write_text(ft, encoding="utf-8")
    print("fixed", name)

    et = text
    et = et.replace("from cc.force import force_fixed\n", "")
    et = et.replace("fixed = force_fixed(fixed)\n", "")
    et = et.replace(
        '    from cc.force import force_fixed\n\n    parser = build_parser()\n    ns = parser.parse_args(argv)\n    ns.fixed = force_fixed(bool(getattr(ns, "fixed", False)))\n',
        "    parser = build_parser()\n    ns = parser.parse_args(argv)\n",
    )
    et = et.replace("    from cc.force import force_fixed\n\n    Handler.fixed = force_fixed(fixed)\n", "    Handler.fixed = fixed\n")
    et = et.replace(
        '    from cc.force import force_fixed\n\n    host = os.environ.get("CC_API_HOST", "127.0.0.1")\n    port = int(os.environ.get("CC_API_PORT", "8080"))\n    fixed = force_fixed(os.environ.get("CC_FIXED", "").lower() in ("1", "true", "yes"))\n',
        '    host = os.environ.get("CC_API_HOST", "127.0.0.1")\n    port = int(os.environ.get("CC_API_PORT", "8080"))\n    fixed = os.environ.get("CC_FIXED", "").lower() in ("1", "true", "yes")\n',
    )
    et = et.replace("    from cc.force import force_fixed\n\n    fixed = force_fixed(fixed)\n", "")
    et = et.replace("    from cc.force import force_fixed\n    fixed = force_fixed(fixed)\n", "")
    src.write_text(et, encoding="utf-8")

print("done")
