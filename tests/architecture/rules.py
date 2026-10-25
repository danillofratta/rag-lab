"""Executable architecture rules derived from AGENTS.md.

Ported from AgentGate (github.com/danillofratta/agentgate-sdd) and extended for the RAG Lab
layout. The checks are AST based regression gates against accidental violations, not a sandbox.
Sources are keyed by POSIX path relative to ``src`` (``ROOT/...``) or to the repository root
(``ui/...`` and ``eval/...``).
"""

import ast
import importlib.util
import re
import sys
from pathlib import PurePosixPath

ROOT = "rag_lab"

DOMAIN = f"{ROOT}.domain"
APPLICATION = f"{ROOT}.application"
APPLICATION_PORTS = f"{ROOT}.application.ports"
APPLICATION_EXCEPTIONS = f"{ROOT}.application.exceptions"
FEATURES = f"{ROOT}.features"
INFRASTRUCTURE = f"{ROOT}.infrastructure"
INFRASTRUCTURE_SETTINGS = f"{ROOT}.infrastructure.settings"
TRANSPORT = f"{ROOT}.transport"
DEPENDENCIES = f"{ROOT}.dependencies"
COMPONENTS = f"{ROOT}.components"
MAIN = f"{ROOT}.main"
WORKER = f"{ROOT}.worker"

# Inward order: a package may import itself and the packages that come earlier.
DOMAIN_PACKAGES = ("shared", "workspaces", "rag")
DOMAIN_FOLDERS = {"entities", "value_objects", "policies", "repositories", "events", "exceptions"}
FEATURE_ROLES = {
    "endpoint",
    "models",
    "job",
    "command",
    "query",
    "handler",
    "result",
    "nodes",
    "workflow",
}
# Feature modules that adapt a framework to the slice; the other role files are framework-free.
FEATURE_ADAPTERS = {"endpoint", "models", "job"}
ADAPTER_IMPORTS = (".models", ".endpoint", ".job")

STDLIB = sys.stdlib_module_names
DOMAIN_IO_MODULES = {
    "os",
    "sys",
    "io",
    "pathlib",
    "socket",
    "subprocess",
    "sqlite3",
    "random",
    "secrets",
    "time",
    "importlib",
    "asyncio",
    "threading",
    "logging",
    "shutil",
    "tempfile",
    "http",
    "urllib",
    "psycopg",
}
CONCRETE_MODULES = {"sqlite3", "os", "socket", "subprocess", "importlib", "psycopg", "psycopg_pool"}
CONSTRUCTED_SUFFIXES = (
    "Repository",
    "Gateway",
    "Handler",
    "UnitOfWork",
    "Strategy",
    "Registry",
    "Parser",
    "Chunker",
    "Embedder",
    "Retriever",
    "Reranker",
    "Generator",
)
TECHNICAL_PORTS = {
    "Clock",
    "WorkspaceIdGenerator",
    "SessionTokenGenerator",
    "UnitOfWork",
    "UnitOfWorkFactory",
    "HealthProbe",
}
TECHNICAL_PORT_SUFFIXES = ("Gateway", "Generator")
RAG_PORT_SUFFIXES = (
    "Gateway",
    "Strategy",
    "StrategyRegistry",
    "Parser",
    "Chunker",
    "Embedder",
    "Retriever",
    "Reranker",
    "Generator",
)
ASYNC_CONTRACT_SUFFIXES = ("Repository", "Gateway", "Probe")
INJECTABLE_DATA = {"str", "int", "bool", "float", "bytes", "tuple", "frozenset", "None"}
INJECTABLE_STDLIB = {"datetime.timedelta", "datetime.datetime", "uuid.UUID"}
HIDDEN_RESOLVERS = {
    "get_components",
    "build_components",
    "get_repository",
    "build_repository",
    "get_gateway",
    "create_gateway",
    "get_instance",
}


def is_under(target, prefix):
    return target == prefix or target.startswith(prefix + ".")


def module_name(path):
    parts = list(PurePosixPath(path).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def resolved_imports(path, tree):
    """Resolve names consistently for normal, aliased, relative, and type-only imports."""
    module = module_name(path)
    package = module if path.endswith("__init__.py") else module.rpartition(".")[0]
    imports, aliases = [], {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
                binding = alias.asname or alias.name.split(".")[0]
                aliases[binding] = alias.name if alias.asname else binding
        elif isinstance(node, ast.ImportFrom):
            target = node.module or ""
            if node.level:
                target = importlib.util.resolve_name("." * node.level + target, package)
            imports.append(target)
            for alias in node.names:
                imports.append(target + "." + alias.name)
                aliases[alias.asname or alias.name] = target + "." + alias.name
    return imports, aliases


def qualified_name(node, aliases):
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        return qualified_name(node.value, aliases) + "." + node.attr
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        try:
            expression = ast.parse(node.value, mode="eval").body
        except SyntaxError:
            return ""
        return qualified_name(expression, aliases)
    return ""


def feature_parts(module):
    """Return (slice, role) for a feature module; role is None for the slice package."""
    parts = module.split(".")
    if module == FEATURES or not is_under(module, FEATURES):
        return None, None
    return parts[2], (parts[3] if len(parts) == 4 else None)


def domain_package(module):
    parts = module.split(".")
    return parts[2] if is_under(module, DOMAIN) and len(parts) > 2 else None


def bootstrap_allows(target):
    """Bootstrap files import components, DI, transport and feature adapter files only."""
    parts = target.split(".")
    if target in {ROOT, FEATURES} or any(
        is_under(target, item)
        for item in (COMPONENTS, DEPENDENCIES, TRANSPORT, INFRASTRUCTURE_SETTINGS)
    ):
        return True
    if not is_under(target, FEATURES):
        return False
    return len(parts) <= 3 or parts[3] in {"endpoint", "job"}


def evaluation_allows(target):
    """The evaluation entry uses the composition root and feature requests and handlers."""
    parts = target.split(".")
    if target in {ROOT, FEATURES} or is_under(target, DEPENDENCIES):
        return True
    if not is_under(target, FEATURES):
        return False
    return len(parts) <= 3 or parts[3] in {"command", "query", "handler", "result"}


def inspect_imports(path, module, imports, violations):
    slice_name, role = feature_parts(module)
    in_feature = slice_name is not None
    in_root = is_under(module, ROOT)
    in_domain = is_under(module, DOMAIN)
    in_infrastructure = is_under(module, INFRASTRUCTURE)
    in_transport = is_under(module, TRANSPORT)
    core = is_under(module, APPLICATION) or (in_feature and role not in FEATURE_ADAPTERS)
    own_slice = ".".join(module.split(".")[:3]) if in_feature else None
    top = module.split(".")[0]

    def reject(rule):
        violations.append(f"{path}: {rule}")

    for target in imports:
        root = target.split(".")[0]
        project = is_under(target, ROOT)

        if top == "ui" and root == ROOT:
            reject("ui imports the application package")
        if top == "eval" and project and not evaluation_allows(target):
            reject("evaluation entry bypasses the composition root")
        if not in_root:
            continue

        if root == "importlib":
            reject("dynamic import")
        if module == ROOT and project:
            reject("root re-export escape")

        # Framework confinement.
        if root == "langgraph" and not (in_feature and role == "workflow"):
            reject("langgraph confined to workflow.py")
        if root in {"pydantic", "pydantic_settings", "pydantic_core"} and not (
            in_infrastructure or (in_feature and role == "models")
        ):
            reject("pydantic confined to models.py and infrastructure")
        if root in {"fastapi", "starlette"} and not (
            (in_feature and role == "endpoint")
            or in_transport
            or module in {DEPENDENCIES, MAIN, WORKER}
        ):
            reject("web framework confined to endpoints, transport and bootstrap")

        if in_domain:
            if (project and not is_under(target, DOMAIN)) or (
                not project and root not in STDLIB and root != "__future__"
            ):
                reject("domain purity")
            if root in DOMAIN_IO_MODULES:
                reject("domain I/O")
            own, other = domain_package(module), domain_package(target)
            if (
                project
                and own in DOMAIN_PACKAGES
                and other in DOMAIN_PACKAGES
                and DOMAIN_PACKAGES.index(other) > DOMAIN_PACKAGES.index(own)
            ):
                reject("domain package order")

        if core:
            allowed = (DOMAIN, APPLICATION) + ((own_slice,) if in_feature else ())
            if project and not any(is_under(target, item) for item in allowed):
                reject("inward application imports")
            third_party = not project and root not in STDLIB and root != "__future__"
            if third_party and not (in_feature and role == "workflow" and root == "langgraph"):
                reject("framework-free application")
            if root in CONCRETE_MODULES:
                reject("concrete application dependency")
            if is_under(target, FEATURES) and not in_feature:
                reject("ports cannot depend on features")
            if in_feature and is_under(target, own_slice):
                adapters = ADAPTER_IMPORTS + ((".workflow",) if role != "workflow" else ())
                if target.endswith(adapters):
                    reject("handler/core imports HTTP adapter")
            if in_feature and is_under(target, FEATURES) and target.endswith((".handler",)):
                reject("direct feature handler dependency")
            if (
                in_feature
                and is_under(target, FEATURES)
                and target.split(".")[-1].endswith("Handler")
            ):
                reject("direct feature handler dependency")

        if in_feature and role in FEATURE_ADAPTERS and project:
            if role == "models":
                allowed = (DOMAIN, own_slice + ".models")
            else:
                allowed = (DOMAIN, own_slice, DEPENDENCIES)
            if not any(is_under(target, item) for item in allowed):
                reject("adapter imports outside its allowed dependencies")

        if in_feature and is_under(target, FEATURES) and target.split(".")[2] != slice_name:
            reject("sibling slice import")

        if in_infrastructure and any(
            is_under(target, item)
            for item in (FEATURES, TRANSPORT, MAIN, WORKER, DEPENDENCIES, COMPONENTS, "ui", "eval")
        ):
            reject("adapter depends outward")

        if in_feature or in_transport or module in {MAIN, WORKER, COMPONENTS}:
            # Typed settings are shared configuration for both entry points and the bundle.
            settings_allowed = module in {COMPONENTS, MAIN, WORKER} and is_under(
                target, INFRASTRUCTURE_SETTINGS
            )
            if (is_under(target, INFRASTRUCTURE) and not settings_allowed) or root == "sqlite3":
                reject("concrete dependency outside composition")
        if in_transport and project:
            if not (is_under(target, TRANSPORT) or is_under(target, APPLICATION_EXCEPTIONS)):
                reject("transport depends on more than shared HTTP concerns")
        if module in {MAIN, WORKER} and project and not bootstrap_allows(target):
            reject("bootstrap imports beyond components, DI, transport and routers")


def inspect_calls(path, module, tree, aliases, violations):
    slice_name, role = feature_parts(module)
    in_root = is_under(module, ROOT)
    core = is_under(module, APPLICATION) or (
        slice_name is not None and role not in FEATURE_ADAPTERS
    )
    if not in_root:
        return

    def reject(rule):
        violations.append(f"{path}: {rule}")

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        method = qualified_name(node.func, aliases).rsplit(".", 1)[-1]
        if method in {"eval", "exec", "__import__", "import_module"}:
            reject("dynamic execution")
        if is_under(module, DOMAIN) and method in {
            "open",
            "read_text",
            "write_text",
            "now",
            "utcnow",
            "today",
            "uuid4",
            "uuid1",
            "token_urlsafe",
            "token_hex",
            "getenv",
        }:
            reject("domain I/O or clock")
        if not is_under(module, INFRASTRUCTURE) and method in {
            "execute",
            "executemany",
            "executescript",
        }:
            reject("SQL outside adapter")
        if core and method in {"Depends", "resolve", "get_service", "get_dependency"}:
            reject("hidden dependency resolution")
    if core:
        for node in tree.body:
            if isinstance(node, ast.Assign | ast.AnnAssign) and isinstance(
                node.value, ast.Dict | ast.List | ast.Set
            ):
                reject("mutable application global")


def inspect_feature_files(path, module, violations):
    """A feature holds only the role files named in AGENTS.md."""
    slice_name, role = feature_parts(module)
    if slice_name is None or path.endswith("__init__.py"):
        return
    if len(module.split(".")) != 4 or role not in FEATURE_ROLES:
        violations.append(f"{path}: feature role files only")


def inspect_sources(sources):
    """Check inward imports, framework confinement, slice isolation and construction."""
    violations = []
    graph = {module_name(path): set() for path in sources}
    for path, source in sources.items():
        module = module_name(path)
        tree = ast.parse(source)
        imports, aliases = resolved_imports(path, tree)
        for target in imports:
            candidates = [name for name in graph if is_under(target, name)]
            if candidates:
                dependency = max(candidates, key=len)
                if dependency != module:
                    graph[module].add(dependency)
        inspect_imports(path, module, imports, violations)
        inspect_calls(path, module, tree, aliases, violations)
        inspect_feature_files(path, module, violations)

    visited, active = set(), set()

    def visit(module):
        if module in active:
            violations.append(f"{module}: dependency cycle")
            return
        if module in visited:
            return
        active.add(module)
        for dependency in graph[module]:
            visit(dependency)
        active.remove(module)
        visited.add(module)

    for module in graph:
        visit(module)
    violations.extend(inspect_cqrs(sources))
    violations.extend(inspect_injection(sources))
    violations.extend(inspect_async(sources))
    return violations


def inspect_cqrs(sources):
    """Check explicit request roles and common persistent effects in query handlers.

    Static guards cover declared imports and calls; behavior tests remain necessary
    for effects hidden behind arbitrary implementations of an injected port.
    """
    violations = []
    modules = {module_name(path): ast.parse(source) for path, source in sources.items()}
    for path in sources:
        module = module_name(path)
        parts = module.split(".")
        if len(parts) != 4 or parts[:2] != [ROOT, "features"]:
            continue
        feature = ".".join(parts[:3])
        role = parts[-1]
        tree = modules[module]
        imports, aliases = resolved_imports(path, tree)
        requests = [name for name in ("command", "query") if feature + "." + name in modules]
        if role in {"command", "query", "handler"} and len(requests) > 1:
            violations.append(f"{path}: CQRS feature mixes command and query requests")
        if role in {"command", "query"}:
            suffix = role.title()
            classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
            if len(classes) != 1 or not classes[0].name.endswith(suffix):
                violations.append(f"{path}: CQRS {role} module requires one {suffix} request")
            if any(
                is_under(target, feature + "." + other)
                for target in imports
                for other in {"command", "query"} - {role}
            ):
                violations.append(f"{path}: CQRS request depends on opposite request role")
            for node in classes:
                if any(
                    isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef)
                    and item.name in {"handle", "execute", "evaluate"}
                    for item in node.body
                ):
                    violations.append(f"{path}: CQRS requests carry data, not handlers")
        if role != "handler":
            continue
        for handler in (
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name.endswith("Handler")
        ):
            if len(requests) != 1:
                violations.append(f"{path}: CQRS handler requires exactly one request module")
                continue
            request_role = requests[0]
            handle = next(
                (
                    item
                    for item in handler.body
                    if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef)
                    and item.name == "handle"
                ),
                None,
            )
            expected_prefix = feature + "." + request_role + "."
            if handle is None:
                violations.append(f"{path}: CQRS handler requires an explicit handle method")
                continue
            annotations = [
                qualified_name(arg.annotation, aliases)
                for arg in handle.args.posonlyargs + handle.args.args + handle.args.kwonlyargs
                if arg.arg not in {"self", "cls"} and arg.annotation is not None
            ]
            own_requests = sum(
                name.startswith(expected_prefix) and name.endswith(request_role.title())
                for name in annotations
            )
            opposite = "Command" if request_role == "query" else "Query"
            if own_requests != 1 or any(name.endswith(opposite) for name in annotations):
                violations.append(
                    f"{path}: CQRS handler must accept its own {request_role} request"
                )
            if request_role != "query":
                continue
            for method in (
                item
                for item in handler.body
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef)
                and item.name != "__init__"
            ):
                for node in ast.walk(method):
                    if isinstance(node, ast.Call):
                        name = qualified_name(node.func, aliases)
                        action = name.rsplit(".", 1)[-1]
                        receiver = name.rpartition(".")[0].lower()
                        state_port = any(
                            part in receiver
                            for part in (
                                "repo",
                                "audit",
                                "work",
                                "uow",
                                "session",
                                "store",
                                "writer",
                                "gateway",
                                "queue",
                                "trac",
                            )
                        )
                        if action in {
                            "commit",
                            "consume",
                            "publish",
                            "publish_event",
                            "enqueue",
                        } or (
                            state_port and action in {"add", "append", "save", "update", "delete"}
                        ):
                            violations.append(
                                f"{path}: CQRS query handler performs a write/dispatch"
                            )
                    if isinstance(node, ast.Assign | ast.AnnAssign | ast.AugAssign):
                        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                        for target in targets:
                            name = qualified_name(target, aliases)
                            if isinstance(target, ast.Subscript):
                                name = qualified_name(target.value, aliases)
                            if name.startswith(("self.", "query.")):
                                violations.append(f"{path}: CQRS query handler mutates state")
    return violations


def inspect_async(sources):
    """Use-case entry points and I/O contracts are asynchronous."""
    violations = []
    for path, source in sources.items():
        module = module_name(path)
        _, role = feature_parts(module)
        in_contract_package = is_under(module, APPLICATION_PORTS) or (
            is_under(module, DOMAIN) and ".repositories" in module
        )
        for node in ast.parse(source).body:
            if not isinstance(node, ast.ClassDef):
                continue
            methods = [
                item
                for item in node.body
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef)
                and not item.name.startswith("_")
            ]
            if role == "handler" and node.name.endswith("Handler"):
                if any(isinstance(m, ast.FunctionDef) and m.name == "handle" for m in methods):
                    violations.append(f"{path}: I/O must be async, handle must be async def")
            if in_contract_package and node.name.endswith(ASYNC_CONTRACT_SUFFIXES):
                if any(isinstance(m, ast.FunctionDef) for m in methods):
                    violations.append(f"{path}: I/O must be async in {node.name}")
    return violations


def inspect_organization(sources):
    """Check feature-local endpoints, contract placement, and file naming."""
    violations = []
    cqrs_names = {"Command": "command", "Query": "query", "Handler": "handler", "Result": "result"}
    endpoint_methods = {
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "options",
        "head",
        "api_route",
        "websocket",
        "route",
    }
    for path, source in sources.items():
        tree = ast.parse(source)
        _, aliases = resolved_imports(path, tree)
        parts = PurePosixPath(path).parts
        if parts[0] != ROOT:
            continue
        stem = PurePosixPath(path).stem
        feature = len(parts) >= 4 and parts[1] == "features"
        schema_module = feature and stem == "models"
        endpoint_module = feature and stem == "endpoint"
        free_classes = feature and stem in {"nodes", "workflow"}
        if parts[1:2] == ("api",) or "controllers" in parts or "routes" in parts:
            violations.append(f"{path}: centralized endpoint directory is forbidden")
        if parts[1:3] == ("application", "features"):
            violations.append(f"{path}: features must live under {ROOT}/features")
        if stem in {"entities", "services", "ports"} or (stem == "models" and not schema_module):
            violations.append(f"{path}: grouped generic module")

        domain_file = parts[1:2] == ("domain",)
        if domain_file:
            if len(parts) == 3:
                if stem != "__init__":
                    violations.append(f"{path}: domain holds packages only")
            elif parts[2] not in DOMAIN_PACKAGES:
                violations.append(f"{path}: unknown domain package")
            elif len(parts) == 4:
                if stem != "__init__":
                    violations.append(f"{path}: domain package files belong in role folders")
            elif parts[3] not in DOMAIN_FOLDERS:
                violations.append(f"{path}: unknown domain package folder")
        domain_repository = domain_file and len(parts) >= 5 and parts[3] == "repositories"
        application_port = parts[1:3] == ("application", "ports")
        rag_port = parts[1:4] == ("application", "ports", "rag")
        adapter_kind = parts[1:3]

        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        known_schemas = {"BaseModel"}
        if not schema_module and not free_classes:
            if len(classes) > 1 or any(node not in tree.body for node in classes):
                violations.append(f"{path}: one class per file")
        for node in classes:
            if schema_module:
                if not any(ast.unparse(base) in known_schemas for base in node.bases):
                    violations.append(f"{path}: models.py may group only HTTP schemas")
                known_schemas.add(node.name)
            name = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", node.name)
            expected = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()
            if feature and not schema_module:
                expected = next(
                    (
                        filename
                        for suffix, filename in cqrs_names.items()
                        if node.name.endswith(suffix)
                    ),
                    expected,
                )
            if not schema_module and not free_classes and stem != expected:
                violations.append(f"{path}: class must use {expected}.py")
            bases = {
                qualified_name(
                    base.value if isinstance(base, ast.Subscript) else base, aliases
                ).rsplit(".", 1)[-1]
                for base in node.bases
            }
            contract = bool(bases & {"Protocol", "ABC"})
            if (
                contract
                and node.name.endswith(("Gateway", "EventPublisher"))
                and not application_port
            ):
                violations.append(
                    f"{path}: gateway/publisher contracts belong in application/ports"
                )
            if contract and node.name.endswith(("Strategy", "StrategyRegistry")) and not rag_port:
                violations.append(f"{path}: strategy contracts belong in application/ports/rag")
            if adapter_kind == ("infrastructure", "gateways") and not node.name.endswith("Gateway"):
                violations.append(f"{path}: gateway adapter requires Gateway suffix")
            if node.name.endswith("Gateway") and "infrastructure" in parts:
                if adapter_kind != ("infrastructure", "gateways"):
                    violations.append(f"{path}: gateway adapters belong in infrastructure/gateways")
            if node.name.endswith("Repository") and "infrastructure" in parts:
                if adapter_kind != ("infrastructure", "repositories"):
                    violations.append(
                        f"{path}: repository adapters belong in infrastructure/repositories"
                    )
            if "infrastructure" in parts and (
                re.match(r"I[A-Z]", node.name) or node.name.startswith("Base")
            ):
                violations.append(f"{path}: generic adapter name")
            if (
                node.name.endswith("Repository")
                and not domain_repository
                and (contract or "infrastructure" not in parts)
            ):
                violations.append(f"{path}: repository contracts belong in domain/repositories")
            if domain_repository or application_port:
                if not contract:
                    violations.append(f"{path}: port must declare Protocol or ABC")
                if re.match(r"I[A-Z]", node.name) or node.name.startswith("Base"):
                    violations.append(f"{path}: generic port name")
                if domain_repository:
                    if not node.name.endswith("Repository"):
                        violations.append(
                            f"{path}: domain persistence contracts require Repository"
                        )
                elif rag_port:
                    if not node.name.endswith(RAG_PORT_SUFFIXES):
                        violations.append(f"{path}: port name must express responsibility")
                elif node.name not in TECHNICAL_PORTS and not node.name.endswith(
                    TECHNICAL_PORT_SUFFIXES
                ):
                    violations.append(f"{path}: port name must express responsibility")
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "APIRouter" and not endpoint_module:
                    violations.append(f"{path}: routers belong in feature endpoint.py")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {"add_api_route", "add_route", "add_websocket_route"}:
                    if not endpoint_module:
                        violations.append(f"{path}: endpoints belong in feature endpoint.py")
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            for decorator in node.decorator_list:
                if (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Attribute)
                    and decorator.func.attr in endpoint_methods
                    and not endpoint_module
                ):
                    violations.append(f"{path}: endpoints belong in feature endpoint.py")
        if stem == "endpoint" and not endpoint_module:
            violations.append(f"{path}: endpoints belong in feature endpoint.py")
    return violations


def contract_classes(sources):
    """Fully qualified Protocol/ABC classes in domain repositories and application ports."""
    contracts = set()
    for path, source in sources.items():
        module = module_name(path)
        if not (
            is_under(module, APPLICATION_PORTS)
            or (is_under(module, DOMAIN) and ".repositories" in module)
        ):
            continue
        tree = ast.parse(source)
        _, aliases = resolved_imports(path, tree)
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and any(
                qualified_name(
                    base.value if isinstance(base, ast.Subscript) else base, aliases
                ).rsplit(".", 1)[-1]
                in {"Protocol", "ABC"}
                for base in node.bases
            ):
                contracts.add(module + "." + node.name)
    return contracts


def inspect_injection(sources):
    """Reject hidden collaborators; resolve constructor annotations against inward ports."""
    violations = []
    contracts = contract_classes(sources)
    for path, source in sources.items():
        module = module_name(path)
        slice_name, role = feature_parts(module)
        in_feature = slice_name is not None
        if not (is_under(module, APPLICATION) or in_feature or is_under(module, TRANSPORT)):
            continue
        core = is_under(module, APPLICATION) or (in_feature and role not in FEATURE_ADAPTERS)
        tree = ast.parse(source)
        _, aliases = resolved_imports(path, tree)
        if core:
            for node in tree.body:
                if not isinstance(node, ast.Assign | ast.AnnAssign):
                    continue
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                names = [qualified_name(target, aliases).lower().strip("_") for target in targets]
                value = node.value
                if any(
                    name in {"container", "services", "service_locator", "registry"}
                    for name in names
                ):
                    violations.append(f"{path}: hidden dependency in module-level container")
                if isinstance(value, ast.Call) and qualified_name(value.func, aliases).rsplit(
                    ".", 1
                )[-1] in {"dict", "list", "set", "defaultdict", "SimpleNamespace"}:
                    violations.append(f"{path}: hidden dependency in mutable module-level state")
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = qualified_name(node.func, aliases)
            leaf = name.rsplit(".", 1)[-1]
            receiver = name.rpartition(".")[0].lower()
            if leaf in HIDDEN_RESOLVERS or (
                leaf == "get"
                and any(term in receiver for term in ("container", "locator", "services"))
            ):
                violations.append(f"{path}: hidden dependency resolution")
            if (
                is_under(name, INFRASTRUCTURE)
                or name in contracts
                or (leaf[:1].isupper() and leaf.endswith(CONSTRUCTED_SUFFIXES))
            ):
                violations.append(f"{path}: collaborator constructed outside composition root")
        if role not in {"handler", "nodes", "workflow"}:
            continue
        own_slice = ".".join(module.split(".")[:3])
        owners = [
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            and (role != "handler" or node.name.endswith("Handler"))
        ]
        for owner in owners:
            constructor = next(
                (
                    node
                    for node in owner.body
                    if isinstance(node, ast.FunctionDef) and node.name == "__init__"
                ),
                None,
            )
            if constructor is None:
                continue  # A pure, dependency-free class needs no constructor ceremony.
            parameters = constructor.args.posonlyargs + constructor.args.args
            defaults = [None] * (
                len(parameters) - len(constructor.args.defaults)
            ) + constructor.args.defaults
            pairs = list(zip(parameters, defaults, strict=True)) + list(
                zip(constructor.args.kwonlyargs, constructor.args.kw_defaults, strict=True)
            )
            for parameter, default in pairs:
                if parameter.arg == "self":
                    continue
                annotation = parameter.annotation
                if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
                    annotation = ast.parse(annotation.value, mode="eval").body
                symbols = (
                    {
                        qualified_name(node, aliases)
                        for node in ast.walk(annotation)
                        if isinstance(node, ast.Name | ast.Attribute)
                    }
                    if annotation
                    else set()
                )
                inward_port = bool(symbols & contracts)
                data_value = bool(symbols) and all(
                    name in INJECTABLE_DATA
                    or name in INJECTABLE_STDLIB
                    or (is_under(name, DOMAIN) and ".value_objects." in name)
                    or (role == "workflow" and is_under(name, own_slice))
                    for name in symbols
                )
                if not inward_port and not data_value:
                    violations.append(
                        f"{path}: constructor collaborators must use inward port contracts"
                    )
                if (
                    inward_port
                    and default is not None
                    and not (isinstance(default, ast.Constant) and default.value is None)
                ):
                    violations.append(f"{path}: constructor collaborator has a hidden default")
            if constructor.args.vararg or constructor.args.kwarg:
                violations.append(f"{path}: constructor dependencies must be explicit")
    return violations
