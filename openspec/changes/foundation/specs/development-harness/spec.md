# Spec Delta

## Purpose

Keep RAG Lab changes reviewable and safe to delegate to coding agents through a reproducible toolchain, enforced quality gates and executable architecture rules.

## ADDED Requirements

### Requirement: Reproducible development environment
The project SHALL pin direct and transitive dependencies, declare its supported Python version and document the commands that install and verify it. Unit tests SHALL run without network access, running services, credentials or model downloads.

#### Scenario: Clean environment verification
- **WHEN** a contributor installs the locked dependencies in a clean environment and runs the documented unit test, lint, format and type-check commands
- **THEN** every command passes without any external service or outbound network access

### Requirement: Enforced quality gates
Every pull request and every push to the main branch SHALL run unit tests, architecture tests, linting, format checking, strict type checking and strict OpenSpec validation in CI. A failure in any gate SHALL fail the workflow.

#### Scenario: Gate failure fails the workflow
- **WHEN** a pull request introduces a failing test, a lint violation, a formatting error, a type error, an invalid spec or a forbidden dependency
- **THEN** CI reports the corresponding check as failed

#### Scenario: Integration tests run against real services
- **WHEN** CI runs the integration job
- **THEN** tests marked as integration run against the local service stack and a failure fails the workflow

### Requirement: Isolated unit tests
Unit tests SHALL be unable to open outbound network connections or start subprocesses. Tests marked as integration or evaluation SHALL be excluded from the default test run.

#### Scenario: Outbound network blocked
- **WHEN** a unit test attempts to open an outbound socket or start a subprocess
- **THEN** the attempt fails and the test reports it

#### Scenario: Default run excludes slow suites
- **WHEN** a contributor runs the default test command
- **THEN** tests marked integration or eval are not executed

### Requirement: Inward dependency rules
Architecture tests SHALL enforce the import matrix in AGENTS.md: a framework-free, I/O-free domain; the domain package order shared, then workspaces, then rag; framework-free feature cores; no imports between sibling feature slices; and infrastructure that never imports features, transport or the composition root.

#### Scenario: Forbidden import detected
- **WHEN** a fixture adds a forbidden import using a plain, relative, aliased, type-only or re-exported form
- **THEN** the architecture gate fails and names the offending file and dependency

#### Scenario: Domain package order enforced
- **WHEN** a fixture makes the workspaces domain package import the rag domain package
- **THEN** the architecture gate fails

### Requirement: Framework confinement
Architecture tests SHALL confine frameworks to their adapters: the agent orchestration framework only in feature workflow modules, the web framework only in endpoints, transport, the composition root and bootstrap, and validation models only in feature HTTP schemas and infrastructure.

#### Scenario: Agent framework outside a workflow module
- **WHEN** a fixture imports the agent orchestration framework in a handler or node module
- **THEN** the architecture gate fails, while the same import in a feature workflow module passes

#### Scenario: Validation models in a handler
- **WHEN** a fixture uses a validation model or HTTP object inside a handler, command, query or result
- **THEN** the architecture gate fails

### Requirement: Single composition root
Concrete adapters and concrete RAG strategies SHALL be constructed and registered only in the composition root. Handlers, nodes and workflows SHALL receive their collaborators through constructors.

#### Scenario: Concrete adapter created in a handler
- **WHEN** a fixture constructs a concrete repository, gateway or strategy inside a handler, node, workflow or endpoint
- **THEN** the architecture gate fails, while the same construction in the composition root passes

### Requirement: Feature slice organization and CQRS roles
Each feature SHALL live in its own folder with role files for its adapters, request, handler and result. A feature SHALL be either a command or a query, never both. Centralized endpoint folders SHALL be rejected.

#### Scenario: Mixed request roles
- **WHEN** a fixture defines both a command and a query in one feature
- **THEN** the architecture gate fails

#### Scenario: Centralized routes
- **WHEN** a fixture adds an endpoint outside a feature folder
- **THEN** the architecture gate fails

### Requirement: Isolated user interface
The user interface SHALL communicate with the system only through the HTTP API and SHALL NOT import the application package.

#### Scenario: UI imports the package
- **WHEN** a fixture makes a UI module import the application package
- **THEN** the architecture gate fails

### Requirement: Accurate contributor instructions
Contributor instructions SHALL define code ownership, test policy, architecture rules and verification commands, and every verification command they name SHALL run successfully on the repository.

#### Scenario: Documented commands are real
- **WHEN** each verification command named in the contributor instructions is run
- **THEN** every command succeeds
