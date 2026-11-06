class InvoiceIQBaseError(Exception):
    """Base exception for all InvoiceIQ domain and operational errors."""
    pass

class ExtractionError(InvoiceIQBaseError):
    """Raised when document intelligence or AI extraction fails."""
    pass

class DocumentValidationError(ExtractionError):
    """Raised when an uploaded document violates ingestion constraints."""
    pass

class ProviderTimeoutError(ExtractionError):
    """Raised when an AI provider call exceeds configured timeout."""
    pass

class ProviderQuotaExhaustedError(ExtractionError):
    """Raised when an AI provider returns HTTP 429 quota exhausted."""
    pass

class MalformedResponseError(ExtractionError):
    """Raised when AI output fails JSON parsing or canonical schema validation."""
    pass

class ValidationError(InvoiceIQBaseError):
    """Raised during deterministic financial validation checks."""
    pass

class OverbillingError(ValidationError):
    """Raised when price or total exceeds contracted bounds."""
    pass

class CapExceededError(ValidationError):
    """Raised when billed quantity exceeds available PO allocation."""
    pass

class DuplicateInvoiceError(ValidationError):
    """Raised when duplicate invoice number is detected."""
    pass

class DatabaseError(InvoiceIQBaseError):
    """Raised on persistence failures or integrity constraint violations."""
    pass

class ConcurrencyConflictError(DatabaseError):
    """Raised when an optimistic lock or transaction rollback occurs."""
    pass

class EntityNotFoundError(DatabaseError):
    """Raised when a requested entity does not exist in storage."""
    pass

