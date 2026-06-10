class ProviderError(Exception):
    error_code = "PROVIDER_ERROR"


class TransientProviderError(ProviderError):
    error_code = "PROVIDER_TRANSIENT"
