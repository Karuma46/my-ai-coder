class GithubIntegrationError(Exception):
    pass


class GithubConfigurationError(GithubIntegrationError):
    pass


class GithubRepositoryNotAllowedError(GithubIntegrationError):
    pass


class GithubOperationDisabledError(GithubIntegrationError):
    pass


class GithubUpstreamError(GithubIntegrationError):
    pass
