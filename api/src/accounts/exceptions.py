class AccountDomainError(Exception):
    code = "ACCOUNT_ERROR"


class AuthenticationError(AccountDomainError):
    code = "UNAUTHORIZED"


class AccountForbiddenError(AccountDomainError):
    code = "FORBIDDEN"


class AccountNotFoundError(AccountDomainError):
    code = "NOT_FOUND"


class AccountConflictError(AccountDomainError):
    code = "CONFLICT"
