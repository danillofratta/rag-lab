# Spec Delta

## Purpose

Give every anonymous visitor an isolated, expiring workspace and a session token that scopes all of their later requests, so the public lab never mixes one visitor's data with another's.

## ADDED Requirements

### Requirement: Workspace creation
An unauthenticated client SHALL be able to create a workspace. The response SHALL be 201 and contain the workspace identifier, a session token and the expiry time, computed as the creation time plus the configured workspace lifetime (24 hours by default).

#### Scenario: Create a workspace
- **WHEN** a client creates a workspace
- **THEN** the response is 201 with an identifier, a session token and an expiry exactly one configured lifetime after creation

#### Scenario: Unknown fields rejected
- **WHEN** a client sends unknown fields when creating a workspace
- **THEN** the response is 422 with error code `INVALID_INPUT`

### Requirement: Session token confidentiality
Session tokens SHALL be generated with at least 256 bits of randomness, returned only once in the creation response, and stored only as a one-way hash.

#### Scenario: Token never stored or repeated
- **WHEN** a workspace is created and then inspected through the API and the database
- **THEN** the token appears only in the creation response, and neither the database, logs nor later responses contain it

### Requirement: Session authentication
Workspace-scoped endpoints SHALL require a bearer session token. Missing, malformed and unknown tokens SHALL receive identical 401 responses with error code `UNAUTHENTICATED`.

#### Scenario: Invalid credentials are indistinguishable
- **WHEN** a client calls a workspace-scoped endpoint with no token, a malformed token or an unknown token
- **THEN** each response is 401 with error code `UNAUTHENTICATED` and identical bodies

### Requirement: Workspace expiry
A workspace SHALL expire at its expiry time. Requests with the token of an expired workspace SHALL receive 401 with error code `SESSION_EXPIRED`. Expiry SHALL NOT be extended by activity.

#### Scenario: Expiry boundary
- **WHEN** a request arrives at exactly the expiry time, under a controlled clock
- **THEN** the response is 401 with error code `SESSION_EXPIRED`

#### Scenario: Activity does not extend expiry
- **WHEN** a client makes several authenticated requests before expiry
- **THEN** the expiry time stays unchanged

### Requirement: Current workspace inspection
An authenticated client SHALL be able to read its own workspace identifier, creation time and expiry time. Inspection SHALL NOT change any stored state.

#### Scenario: Read-only inspection
- **WHEN** a client reads its current workspace several times
- **THEN** each response returns the same identifier and times and no stored record changes

### Requirement: Trusted workspace scope
The workspace of a request SHALL come only from the authenticated session, never from the request path, query or body. Use-case handlers SHALL require that trusted workspace even when invoked without HTTP.

#### Scenario: No client-supplied workspace parameter
- **WHEN** the API schema of every workspace-scoped endpoint is inspected
- **THEN** no path, query or body parameter carries a workspace identifier

#### Scenario: Direct handler call without a session
- **WHEN** a workspace-scoped handler is invoked directly without a trusted workspace principal
- **THEN** the call is rejected before any persistence access
