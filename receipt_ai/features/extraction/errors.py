class ExtractionError(Exception):
    """Base extraction error."""


class UnsupportedFileTypeError(ExtractionError):
    """Raised when no extractor supports the given file type."""


class ParsingError(ExtractionError):
    """Raised when parser fails to decode structured content."""


class ExternalAIError(ExtractionError):
    """Raised when Kimi/AI extraction fails."""


class ValidationError(ExtractionError):
    """Raised when extracted content is considered low quality."""
