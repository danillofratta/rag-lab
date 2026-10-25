# Spec Delta

## Purpose

Give every contributor the same local service stack, a validated configuration and a predictable database schema, so the system behaves the same on every machine and in CI.

## ADDED Requirements

### Requirement: Local service stack
One documented command SHALL start the relational database and the vector database with health checks, persistent volumes, pinned image versions and ports bound to the loopback interface only.

#### Scenario: Services start healthy
- **WHEN** a contributor runs the documented start command with a complete environment file
- **THEN** the relational database and the vector database report healthy

#### Scenario: Data survives a restart
- **WHEN** the services are stopped and started again without removing volumes
- **THEN** previously stored data is still present

### Requirement: Optional observability services
The observability services SHALL start only when their profile is explicitly selected.

#### Scenario: Default start excludes observability
- **WHEN** a contributor starts the stack without selecting the observability profile
- **THEN** no observability service is running

#### Scenario: Observability on demand
- **WHEN** a contributor starts the stack with the observability profile
- **THEN** the observability services start and report healthy

### Requirement: No default secrets
Credentials SHALL come only from the environment. The example environment file SHALL contain placeholders only, and starting the stack or the application without a required credential SHALL fail with a message that names the missing variable.

#### Scenario: Missing credential
- **WHEN** the stack or the application starts without a required credential
- **THEN** startup fails and the message names the variable without printing any secret value

### Requirement: Startup configuration validation
The application SHALL validate its configuration at startup and refuse to start on missing, malformed or out-of-range values, naming the invalid setting without revealing its value.

#### Scenario: Invalid setting
- **WHEN** the application starts with a malformed database address or a non-positive workspace lifetime
- **THEN** it exits with an error naming the setting and no secret value appears in the output

### Requirement: Ordered schema migrations
Schema changes SHALL be applied by an explicit command, in order, exactly once each. An applied migration whose content changed SHALL be refused.

#### Scenario: Re-running migrations
- **WHEN** the migration command runs twice against the same database
- **THEN** the second run applies nothing and succeeds

#### Scenario: Tampered migration
- **WHEN** the content of an already applied migration changes and the migration command runs
- **THEN** the command fails and names the changed migration

### Requirement: Schema version check
The API SHALL refuse to report ready when the database schema is behind or ahead of the schema the code expects.

#### Scenario: Pending migrations
- **WHEN** the API runs against a database with pending migrations
- **THEN** readiness reports the database as not ready
