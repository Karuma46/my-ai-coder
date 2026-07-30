class AgentDomainError(Exception):
    code = "AGENT_ERROR"


class AgentConfigurationError(AgentDomainError):
    code = "AGENT_NOT_CONFIGURED"


class AgentRunNotFoundError(AgentDomainError):
    code = "AGENT_RUN_NOT_FOUND"


class AgentRunConflictError(AgentDomainError):
    code = "AGENT_RUN_CONFLICT"


class AgentRepositoryError(AgentDomainError):
    code = "AGENT_REPOSITORY_ERROR"


class AgentProcessError(AgentDomainError):
    code = "AGENT_PROCESS_ERROR"

    def __init__(
        self,
        message: str,
        *,
        output: str = "",
        exit_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.output = output
        self.exit_code = exit_code
