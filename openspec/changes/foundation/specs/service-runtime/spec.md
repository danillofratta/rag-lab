# Spec Delta

## Purpose

Define the behavior every RAG Lab API request shares regardless of feature: health reporting, request identification, size limits, sanitized errors and safe logging.

## ADDED Requirements

### Requirement: Liveness reporting
The API SHALL expose a liveness endpoint that answers success whenever the process can serve requests, without checking dependencies and without authentication.

#### Scenario: Process alive
- **WHEN** a client calls the liveness endpoint while the database is unreachable
- **THEN** the response is 200

### Requirement: Readiness reporting
The API SHALL expose an unauthenticated readiness endpoint that answers 200 only when every required dependency is reachable and the schema is current, and 503 otherwise, listing each dependency name and status without error details.

#### Scenario: All dependencies ready
- **WHEN** the database is reachable and fully migrated
- **THEN** readiness returns 200 and lists the database as ready

#### Scenario: Dependency unavailable
- **WHEN** the database is unreachable
- **THEN** readiness returns 503, lists the database as not ready and includes no exception text, host or credential

### Requirement: Request identification
Every response SHALL carry a request identifier header, and every log record produced while handling the request SHALL include the same identifier.

#### Scenario: Identifier on every response
- **WHEN** a client calls any endpoint, including one that fails
- **THEN** the response carries a request identifier that also appears in the related log records

### Requirement: Request body limit
The API SHALL reject request bodies larger than the configured limit with 413 and error code `BODY_TOO_LARGE`, including bodies sent in chunks without a declared length.

#### Scenario: Oversized body
- **WHEN** a client sends a body one byte over the limit, declared or streamed
- **THEN** the response is 413 with error code `BODY_TOO_LARGE` and the handler is not invoked

### Requirement: Sanitized error envelope
Every error response SHALL use the envelope `{"error": "<CODE>"}` with a stable code and SHALL NOT include stack traces, SQL, internal messages, tokens or raw rejected input.

#### Scenario: Invalid input
- **WHEN** a request fails validation, including unknown fields
- **THEN** the response is 422 with error code `INVALID_INPUT` and does not echo the rejected input

#### Scenario: Unexpected failure
- **WHEN** a handler raises an unexpected exception
- **THEN** the response is 500 with error code `INTERNAL_ERROR` and the exception text appears in neither the response nor the access log

### Requirement: Structured safe logging
The API SHALL write structured log records and SHALL NOT log authorization headers, session tokens, request bodies or secret settings.

#### Scenario: Secrets never logged
- **WHEN** requests with authorization headers and bodies are handled, successfully or not
- **THEN** no captured log record contains the header value, the token or the body

### Requirement: Optional API documentation
Interactive API documentation SHALL be served only when enabled by configuration.

#### Scenario: Documentation disabled
- **WHEN** the documentation setting is disabled
- **THEN** the documentation routes return 404
