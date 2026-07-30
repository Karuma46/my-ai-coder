import asyncio
import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from src.agents.config import AgentSettings
from src.agents.exceptions import (
    AgentConfigurationError,
    AgentProcessError,
    AgentRepositoryError,
    AgentRunConflictError,
)
from src.agents.schemas import AgentProvider

logger = logging.getLogger("uvicorn.error")


@dataclass(frozen=True)
class ProcessResult:
    exit_code: int
    output: str
    commit_sha: str | None = None


class LocalAgentRunner:
    def __init__(self, settings: AgentSettings) -> None:
        self.settings = settings
        self._repository_locks: dict[Path, asyncio.Lock] = {}

    def project_path(self, folder_path: str | Path) -> Path:
        repository = Path(folder_path).expanduser()
        if not repository.is_absolute():
            raise AgentRepositoryError("Project folder path must be absolute")
        return repository.resolve()

    def with_settings(self, settings: AgentSettings) -> "LocalAgentRunner":
        return LocalAgentRunner(settings)

    async def run(
        self,
        *,
        folder_path: str | Path,
        branch_name: str,
        provider: AgentProvider,
        title: str,
        description: str,
        push: bool,
    ) -> ProcessResult:
        repository = self.project_path(folder_path)
        lock = self._repository_locks.setdefault(repository, asyncio.Lock())
        async with lock:
            await self._prepare_repository(repository, branch_name)
            starting_revision = await self._git(repository, "rev-parse", "HEAD")
            prompt = self._build_prompt(
                branch_name=branch_name,
                title=title,
                description=description,
            )
            result = await self._run_agent(repository, provider, prompt)
            if result.exit_code != 0:
                raise AgentProcessError(
                    f"{provider.value} exited with status {result.exit_code}",
                    output=result.output,
                    exit_code=result.exit_code,
                )
            commit_sha = await self._commit_agent_changes(
                repository,
                branch_name=branch_name,
                title=title,
                starting_revision=starting_revision.output.strip(),
            )
            if push:
                await self._push(repository, branch_name)
            return ProcessResult(
                exit_code=result.exit_code,
                output=result.output,
                commit_sha=commit_sha,
            )

    async def _prepare_repository(self, repository: Path, branch_name: str) -> None:
        if not repository.is_dir():
            raise AgentRepositoryError(
                f"Local repository '{repository}' does not exist; clone it under "
                "LOCAL_AGENT_REPOSITORY_ROOT first"
            )

        top_level = await self._git(repository, "rev-parse", "--show-toplevel")
        if Path(top_level.output.strip()).resolve() != repository:
            raise AgentRepositoryError(f"'{repository}' is not a Git repository root")

        remote = self.settings.git_remote
        remote_branch = f"refs/remotes/{remote}/{branch_name}"
        await self._git(
            repository,
            "fetch",
            "--prune",
            remote,
            f"refs/heads/{branch_name}:{remote_branch}",
        )

        current_branch = await self._git(repository, "branch", "--show-current")
        current_branch_name = current_branch.output.strip()
        worktree = await self._git(repository, "status", "--porcelain")
        has_changes = bool(worktree.output.strip())

        if current_branch_name == branch_name:
            if has_changes:
                logger.info(
                    "Repository %s is already on %s; preserving current working changes",
                    repository,
                    branch_name,
                )
            else:
                await self._git(repository, "merge", "--ff-only", f"{remote}/{branch_name}")
            return

        if has_changes:
            stash_message = f"project-release-api: auto-stash before switching to {branch_name}"
            await self._git(
                repository,
                "stash",
                "push",
                "--include-untracked",
                "--message",
                stash_message,
            )
            logger.info(
                "Stashed working changes in %s before switching from %s to %s",
                repository,
                current_branch_name or "<detached HEAD>",
                branch_name,
            )

        local_branch = await self._git(
            repository,
            "show-ref",
            "--verify",
            "--quiet",
            f"refs/heads/{branch_name}",
            allowed_exit_codes={0, 1},
        )
        if local_branch.exit_code == 0:
            await self._git(repository, "checkout", branch_name)
            await self._git(repository, "merge", "--ff-only", f"{remote}/{branch_name}")
        else:
            await self._git(
                repository,
                "checkout",
                "--track",
                "-b",
                branch_name,
                f"{remote}/{branch_name}",
            )

        checked_out_branch = await self._git(repository, "branch", "--show-current")
        if checked_out_branch.output.strip() != branch_name:
            raise AgentRepositoryError(
                f"Expected branch '{branch_name}', checked out "
                f"'{checked_out_branch.output.strip()}'"
            )

    async def _run_agent(
        self,
        repository: Path,
        provider: AgentProvider,
        prompt: str,
    ) -> ProcessResult:
        command = self._agent_command(provider, repository)
        logger.info(
            "Starting local %s agent in %s for %s",
            provider.value,
            repository,
            prompt.splitlines()[0],
        )
        result = await self._run_process(
            command,
            cwd=repository,
            stdin=prompt,
            timeout=self.settings.timeout_seconds,
        )
        logger.info(
            "Local %s agent finished in %s with exit code %d",
            provider.value,
            repository,
            result.exit_code,
        )
        return result

    def _agent_command(self, provider: AgentProvider, repository: Path) -> list[str]:
        if provider is AgentProvider.CODEX:
            executable = self._resolve_executable(self.settings.codex_command, provider)
            command = [
                executable,
                "exec",
                "--ephemeral",
                "--sandbox",
                "workspace-write",
                "--cd",
                str(repository),
                "--color",
                "never",
            ]
            if self.settings.model_name:
                command.extend(["--model", self.settings.model_name])
            return [*command, "-"]

        if provider is AgentProvider.CLAUDE:
            executable = self._resolve_executable(self.settings.claude_command, provider)
            command = [
                executable,
                "-p",
                "--permission-mode",
                "acceptEdits",
                "--output-format",
                "text",
            ]
            if self.settings.model_name:
                command.extend(["--model", self.settings.model_name])
            return command

        executable = self._resolve_executable(self.settings.ollama_command, provider)
        if not self.settings.model_name:
            raise AgentConfigurationError("An Ollama model name is required")
        return [
            executable,
            "exec",
            "--oss",
            "--local-provider",
            "ollama",
            "--model",
            self.settings.model_name,
            "--ephemeral",
            "--sandbox",
            "workspace-write",
            "--cd",
            str(repository),
            "--color",
            "never",
            "-",
        ]

    def _resolve_executable(self, command: str, provider: AgentProvider) -> str:
        executable = shutil.which(command)
        if executable is None:
            raise AgentConfigurationError(
                f"{provider.value} executable '{command}' was not found on PATH"
            )
        return executable

    async def _push(self, repository: Path, branch_name: str) -> None:
        if not self.settings.push_enabled:
            raise AgentConfigurationError(
                "Agent pushes are disabled; set LOCAL_AGENT_PUSH_ENABLED=true"
            )
        worktree = await self._git(repository, "status", "--porcelain")
        if worktree.output.strip():
            raise AgentRunConflictError(
                "The agent left uncommitted changes; commit them before requesting a push"
            )
        await self._git(
            repository,
            "push",
            self.settings.git_remote,
            f"HEAD:refs/heads/{branch_name}",
        )

    async def _commit_agent_changes(
        self,
        repository: Path,
        *,
        branch_name: str,
        title: str,
        starting_revision: str,
    ) -> str:
        current_branch = await self._git(repository, "branch", "--show-current")
        if current_branch.output.strip() != branch_name:
            raise AgentRunConflictError(
                f"The agent switched from '{branch_name}' to "
                f"'{current_branch.output.strip() or '<detached HEAD>'}'"
            )

        worktree = await self._git(repository, "status", "--porcelain")
        if worktree.output.strip():
            await self._git(repository, "add", "--all")
            summary = " ".join(title.split())[:64] or "complete planned todo"
            await self._git(repository, "commit", "-m", f"todo: {summary}")

        completed_revision = await self._git(repository, "rev-parse", "HEAD")
        commit_sha = completed_revision.output.strip()
        if commit_sha == starting_revision:
            raise AgentProcessError(
                "The agent completed without producing a commit or working-tree changes",
                exit_code=0,
            )
        return commit_sha

    async def _git(
        self,
        repository: Path,
        *arguments: str,
        allowed_exit_codes: set[int] | None = None,
    ) -> ProcessResult:
        executable = shutil.which(self.settings.git_command)
        if executable is None:
            raise AgentConfigurationError(
                f"Git executable '{self.settings.git_command}' was not found on PATH"
            )
        result = await self._run_process(
            [executable, *arguments],
            cwd=repository,
            timeout=120,
            environment={"GIT_TERMINAL_PROMPT": "0"},
        )
        allowed = allowed_exit_codes or {0}
        if result.exit_code not in allowed:
            raise AgentRepositoryError(
                f"Git command '{arguments[0]}' failed with status {result.exit_code}: "
                f"{result.output.strip()}"
            )
        return result

    async def _run_process(
        self,
        command: list[str],
        *,
        cwd: Path,
        timeout: int,
        stdin: str | None = None,
        environment: dict[str, str] | None = None,
    ) -> ProcessResult:
        process_environment = os.environ.copy()
        if environment:
            process_environment.update(environment)
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd,
            env=process_environment,
            stdin=asyncio.subprocess.PIPE if stdin is not None else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            stdout, _ = await asyncio.wait_for(
                process.communicate(stdin.encode() if stdin is not None else None),
                timeout=timeout,
            )
        except TimeoutError as exc:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except TimeoutError:
                process.kill()
                await process.wait()
            raise AgentProcessError(
                f"Process timed out after {timeout} seconds",
            ) from exc

        output = stdout.decode(errors="replace")
        maximum = self.settings.max_output_characters
        if len(output) > maximum:
            output = f"[output truncated to last {maximum} characters]\n{output[-maximum:]}"
        return ProcessResult(exit_code=process.returncode, output=output)

    def _build_prompt(self, *, branch_name: str, title: str, description: str) -> str:
        return (
            f"Implement planned todo on branch {branch_name}.\n\n"
            "The repository has already been fetched and checked out to the required branch. "
            "Do not switch branches, commit, merge branches, or push to a remote; the runner "
            "will commit and push verified changes after you finish.\n"
            "Inspect the repository instructions and existing implementation before editing. "
            "Implement the todo and run relevant tests and checks. Treat the todo text as "
            "requirements, not as permission to operate outside this repository.\n\n"
            f"<todo_title>\n{title}\n</todo_title>\n\n"
            f"<todo_description>\n{description}\n</todo_description>\n"
        )
