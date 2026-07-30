class ProjectDomainError(Exception):
    code = "PROJECT_ERROR"


class ProjectNotFoundError(ProjectDomainError):
    code = "NOT_FOUND"


class ProjectConflictError(ProjectDomainError):
    code = "INVALID_STATE_TRANSITION"


class ProjectGithubReferenceError(ProjectDomainError):
    code = "GITHUB_REFERENCE_ERROR"
