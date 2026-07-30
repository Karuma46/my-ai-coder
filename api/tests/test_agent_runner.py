import subprocess
from pathlib import Path

from src.agents.config import AgentSettings
from src.agents.runner import LocalAgentRunner, ProcessResult
from src.agents.schemas import AgentProvider


def run_git(directory: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=directory,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def create_test_repository(tmp_path: Path) -> tuple[Path, Path]:
    remote = tmp_path / "remote.git"
    seed = tmp_path / "seed"
    repository_root = tmp_path / "repositories"
    repository = repository_root / "shoppa"
    remote.mkdir()
    seed.mkdir()
    repository_root.mkdir()

    run_git(remote, "init", "--bare")
    run_git(seed, "init", "-b", "main")
    run_git(seed, "config", "user.name", "Test Agent")
    run_git(seed, "config", "user.email", "agent@example.com")
    (seed / "README.md").write_text("# Shoppa\n")
    run_git(seed, "add", "README.md")
    run_git(seed, "commit", "-m", "Initial commit")
    run_git(seed, "remote", "add", "origin", str(remote))
    run_git(seed, "push", "-u", "origin", "main")
    run_git(remote, "symbolic-ref", "HEAD", "refs/heads/main")
    run_git(seed, "checkout", "-b", "todo/add-cart")
    run_git(seed, "push", "-u", "origin", "todo/add-cart")
    subprocess.run(
        ["git", "clone", str(remote), str(repository)],
        check=True,
        capture_output=True,
        text=True,
    )
    return repository_root, repository


def create_runner(repository_root: Path) -> LocalAgentRunner:
    return LocalAgentRunner(
        AgentSettings(
            enabled=True,
            push_enabled=True,
        )
    )


def install_fake_agent(monkeypatch, runner: LocalAgentRunner) -> dict[str, object]:
    received: dict[str, object] = {}

    async def fake_run_agent(
        checked_out_repository: Path,
        provider: AgentProvider,
        prompt: str,
    ) -> ProcessResult:
        (checked_out_repository / "agent-output.txt").write_text("Implemented by the local agent\n")
        received.update(
            repository=checked_out_repository,
            provider=provider,
            prompt=prompt,
            branch=run_git(checked_out_repository, "branch", "--show-current"),
        )
        return ProcessResult(exit_code=0, output="Implemented the todo")

    monkeypatch.setattr(runner, "_run_agent", fake_run_agent)
    return received


async def run_todo(runner: LocalAgentRunner, repository: Path) -> ProcessResult:
    return await runner.run(
        folder_path=repository,
        branch_name="todo/add-cart",
        provider=AgentProvider.CODEX,
        title="Add cart",
        description="Implement a shopping cart.",
        push=True,
    )


def test_agent_commands_include_configured_models(tmp_path: Path, monkeypatch) -> None:
    settings = AgentSettings(
        enabled=True,
        model_name="qwen3.5",
        ollama_command="codex",
    )
    runner = LocalAgentRunner(settings)
    monkeypatch.setattr(
        runner,
        "_resolve_executable",
        lambda command, provider: f"/usr/bin/{command}",
    )

    codex_command = runner._agent_command(AgentProvider.CODEX, tmp_path)
    claude_command = runner._agent_command(AgentProvider.CLAUDE, tmp_path)
    ollama_command = runner._agent_command(AgentProvider.OLLAMA, tmp_path)

    assert ["--model", "qwen3.5"] == codex_command[-3:-1]
    assert claude_command[-2:] == ["--model", "qwen3.5"]
    assert ollama_command[:7] == [
        "/usr/bin/codex",
        "exec",
        "--oss",
        "--local-provider",
        "ollama",
        "--model",
        "qwen3.5",
    ]


async def test_runner_fetches_and_checks_out_todo_branch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repository_root, repository = create_test_repository(tmp_path)
    runner = create_runner(repository_root)
    received = install_fake_agent(monkeypatch, runner)

    result = await run_todo(runner, repository)

    assert result.output == "Implemented the todo"
    assert received["repository"] == repository
    assert received["provider"] is AgentProvider.CODEX
    assert received["branch"] == "todo/add-cart"
    assert "<todo_title>\nAdd cart\n</todo_title>" in str(received["prompt"])
    assert run_git(repository, "log", "-1", "--pretty=%s") == "todo: Add cart"
    assert run_git(repository, "rev-parse", "HEAD") == run_git(
        repository,
        "rev-parse",
        "origin/todo/add-cart",
    )


async def test_runner_stashes_changes_before_switching_branches(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repository_root, repository = create_test_repository(tmp_path)
    runner = create_runner(repository_root)
    received = install_fake_agent(monkeypatch, runner)
    (repository / "README.md").write_text("# Uncommitted work on main\n")
    (repository / "notes.txt").write_text("Untracked notes\n")

    await run_todo(runner, repository)

    assert received["branch"] == "todo/add-cart"
    assert run_git(repository, "status", "--porcelain") == ""
    stash_list = run_git(repository, "stash", "list")
    assert "project-release-api: auto-stash before switching to todo/add-cart" in stash_list
    stash_patch = run_git(repository, "stash", "show", "--include-untracked", "-p")
    assert "Uncommitted work on main" in stash_patch
    assert "Untracked notes" in stash_patch


async def test_runner_preserves_changes_when_already_on_required_branch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repository_root, repository = create_test_repository(tmp_path)
    run_git(repository, "checkout", "todo/add-cart")
    (repository / "README.md").write_text("# Work already in progress\n")
    runner = create_runner(repository_root)
    received = install_fake_agent(monkeypatch, runner)

    await run_todo(runner, repository)

    assert received["branch"] == "todo/add-cart"
    assert run_git(repository, "status", "--porcelain") == ""
    assert (repository / "README.md").read_text() == "# Work already in progress\n"
    assert run_git(repository, "show", "HEAD:README.md") == "# Work already in progress"
    assert run_git(repository, "stash", "list") == ""
