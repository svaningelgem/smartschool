#!/usr/bin/env python3
"""Generate .pyi stub files from Python modules."""

from __future__ import annotations

import argparse
import ast
import collections.abc
import enum
import importlib.util
import inspect
import re
import subprocess
import sys
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, get_type_hints

import pydantic.fields
from logprise import logger
from pydantic.dataclasses import is_pydantic_dataclass
from pydantic_core import PydanticUndefined

if TYPE_CHECKING:
    import types


@dataclass
class FieldInfo:
    name: str
    type_annotation: Any
    default_value: Any = None
    has_default: bool = False


@dataclass
class MethodInfo:
    name: str
    params: list[FieldInfo] = field(default_factory=list)
    return_annotation: Any = None


@dataclass
class ClassInfo:
    name: str
    real_class: type | None = None
    bases: list[Any] = field(default_factory=list)
    attributes: list[FieldInfo] = field(default_factory=list)
    method_names: dict[str, list[ast.FunctionDef]] = field(default_factory=lambda: defaultdict(list))
    methods: list[MethodInfo | str] = field(default_factory=list)
    annotations: dict = field(default_factory=dict)
    init_method: MethodInfo | None = None
    is_enum: bool = False


def _format_import(annotation: type, current_module: types.ModuleType) -> str:
    """Generate relative import when modules share common package."""
    module = annotation.__module__
    name = annotation.__name__

    if module == "builtins":
        return ""

    if module == "typing" and getattr(collections.abc, name, None) is not None:
        module = "collections.abc"

    current_parts = current_module.__name__.split(".")
    target_parts = module.split(".")

    if current_parts == target_parts:
        return ""  # Local stuff

    common_len = next((i for i, (a, b) in enumerate(zip(current_parts, target_parts, strict=False)) if a != b), min(len(current_parts), len(target_parts)))

    if not common_len or len(target_parts) < len(current_parts):
        return f"from {module} import {name}"

    dots = "." * (len(current_parts) - common_len)
    suffix = ".".join(target_parts[common_len:])

    return f"from {dots}{suffix} import {name}"


def format_type_annotation(annotation: Any, imports_needed: set, current_module: types.ModuleType) -> str:
    """Format type annotation for stub file and track needed imports."""
    if annotation is None or annotation == inspect.Parameter.empty or annotation == inspect.Signature.empty:
        return ""

    if annotation is type(None):
        return "None"

    if inspect.isclass(annotation):
        imports_needed.add(_format_import(annotation, current_module))
        return annotation.__name__

    if isinstance(annotation, str):
        return f'"{annotation}"'

    if hasattr(annotation, "__origin__"):
        base = annotation.__origin__
        imports_needed.add(_format_import(base, current_module))
        result = base.__name__
        pre, mid, post = "[,]"
    else:
        result = ""
        pre, mid, post = " | "

    if hasattr(annotation, "__args__") and annotation.__args__:
        args = annotation.__args__
        assert isinstance(args, Sequence)
        result += pre
        for arg in args:
            result += format_type_annotation(arg, imports_needed, current_module) + mid
        return result[: -len(mid)] + post

    raise ValueError(f"Unexpected type annotation: {annotation}")


def _get_import_from_ast(node: ast.AST) -> str:
    if not isinstance(node, (ast.Import, ast.ImportFrom)):
        return ""

    result = ""
    if isinstance(node, ast.ImportFrom):
        result = f"from {'.' * node.level}{node.module if node.module else ''} import "
    elif isinstance(node, ast.Import):
        result = "import "

    for name in node.names:
        result += name.name
        if name.asname:
            result += f" as {name.asname}"
        result += ", "

    return result[:-2]


def _render_base(base: ast.expr) -> str | None:
    """Render a single base-class expression as written in source."""
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Subscript) and isinstance(base.value, ast.Name):
        # Generic base like Iterable[Result]
        if isinstance(base.slice, ast.Name):
            return f"{base.value.id}[{base.slice.id}]"
        return base.value.id
    if isinstance(base, ast.Attribute):
        # Qualified name like objects.Result
        parts = []
        current: ast.expr = base
        while isinstance(current, ast.Attribute):
            parts.insert(0, current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.insert(0, current.id)
        return ".".join(parts)
    return None


def _parse_class_def(node: ast.ClassDef) -> ClassInfo:
    """Build a ClassInfo from a ClassDef node, as written in source."""
    bases = [rendered for base in node.bases if (rendered := _render_base(base)) is not None]

    methods = defaultdict(list)
    annotations = {}
    for item in node.body:
        # Skip hidden helpers, but keep dunders.
        if isinstance(item, ast.FunctionDef) and (not item.name.startswith("_") or re.match("^__.+__$", item.name)):
            methods[item.name].append(item)
        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            annotations[item.target.id] = ast.unparse(item.annotation)

    return ClassInfo(name=node.name, method_names=methods, bases=bases, annotations=annotations)


def parse_class_ast_info(file_path: Path) -> tuple[dict[str, ClassInfo], list[str]]:
    """Parse AST to get class structure info as written in source."""
    try:
        tree = ast.parse(file_path.read_bytes())
    except Exception as e:
        logger.error(f"Failed to parse AST: {e}")
        return {}, []

    class_info: dict[str, ClassInfo] = {}
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(_get_import_from_ast(node))
        elif isinstance(node, ast.ClassDef):
            class_info[node.name] = _parse_class_def(node)

    return class_info, imports


def load_module_from_file(file_path: Path):
    """Load module with proper package context."""
    file_path = file_path.absolute()
    package_root = file_path.parent
    package_name = package_root.name
    module_name = file_path.stem
    full_module_name = f"{package_name}.{module_name}"

    parent_dir = package_root.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))

    try:
        if package_name not in sys.modules:
            package_init = package_root / "__init__.py"
            if package_init.exists():
                package_spec = importlib.util.spec_from_file_location(package_name, package_init)
                if package_spec and package_spec.loader:
                    package_module = importlib.util.module_from_spec(package_spec)
                    sys.modules[package_name] = package_module
                    package_spec.loader.exec_module(package_module)
            else:
                package_module = type(sys)("dummy_package")
                package_module.__path__ = [str(package_root)]
                sys.modules[package_name] = package_module

        spec = importlib.util.spec_from_file_location(full_module_name, file_path)
        if not spec or not spec.loader:
            logger.warning(f"Failed to load module {full_module_name} from {file_path}")
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[full_module_name] = module
        spec.loader.exec_module(module)
    except Exception:
        logger.exception(f"Failed to load module {full_module_name}")
        return None
    else:
        return module


_pydantic_replacements = {
    "String": "str",
    "Url": "str",
    "DateTime": "datetime",
}
_MISSING = object()


def _extract_method_info(real_class: type, method_name: str) -> MethodInfo:
    sig = inspect.signature(getattr(real_class, method_name))

    # Resolve string annotations (forward references) via class-level type hints
    try:
        class_hints = get_type_hints(real_class, include_extras=False)
    except Exception:
        class_hints = {}

    method_params = []
    for name, param in sig.parameters.items():
        annotation = param.annotation
        # If annotation is a string (forward reference), resolve it from class hints
        if isinstance(annotation, str) and name in class_hints:
            annotation = class_hints[name]
        if annotation in _pydantic_replacements:
            annotation = _pydantic_replacements[annotation]

        default = param.default
        if default == inspect.Parameter.empty:
            default = _MISSING
        elif isinstance(default, pydantic.fields.FieldInfo):
            if default.default is PydanticUndefined:
                default = _MISSING
            else:
                assert not default.default_factory
                default = default.default

        field_info = FieldInfo(
            name=name,
            type_annotation=annotation,
            default_value=default,
            has_default=default is not _MISSING,
        )
        method_params.append(field_info)

    return MethodInfo(name=method_name, params=method_params, return_annotation=sig.return_annotation)


def _collect_annotations(real_class: type) -> dict[str, Any]:
    """Gather every public annotation for a class (type hints + pydantic fields)."""
    all_annotations: dict[str, Any] = {}

    # Type hints are the single source of truth (and include pydantic fields).
    try:
        all_annotations.update(get_type_hints(real_class))
    except Exception as e:
        logger.exception(f"Could not get type hints: {e}")

    # Also check pydantic model_fields to get any that might be missing.
    for field_name, field_info in getattr(real_class, "model_fields", {}).items():
        if field_name not in all_annotations and hasattr(field_info, "annotation"):
            all_annotations[field_name] = field_info.annotation

    return {name: annotation for name, annotation in all_annotations.items() if not name.startswith("_")}


def _collect_methods(class_info: ClassInfo) -> None:
    """Append __init__ and the public methods of a class to its ClassInfo."""
    real_class = class_info.real_class

    if real_class.__init__ is not object.__init__:
        class_info.methods.append(_extract_method_info(real_class, "__init__"))

    for method_name, ast_methods in class_info.method_names.items():
        if method_name in ("__init__", "__post_init__"):
            continue
        if not callable(getattr(real_class, method_name, None)):
            continue
        if len(ast_methods) == 1:
            class_info.methods.append(_extract_method_info(real_class, method_name))
            continue
        # Overloaded method: pass each signature through verbatim from the AST.
        for overloaded_method in ast_methods:
            overloaded_method.body.clear()
            class_info.methods.append(ast.unparse(overloaded_method) + " ...")


def extract_class_data(class_info: ClassInfo) -> ClassInfo:
    """Extract all class data into unified structure."""
    real_class = class_info.real_class

    # Enums carry members, not a synthesized __init__; emit the members instead.
    if isinstance(real_class, type) and issubclass(real_class, enum.Enum):
        class_info.is_enum = True
        return class_info

    class_info.attributes.extend(FieldInfo(name=name, type_annotation=annotation) for name, annotation in _collect_annotations(real_class).items())
    _collect_methods(class_info)
    return class_info


def generate_stub_from_class_info(class_info: ClassInfo, imports_needed: set, current_module: types.ModuleType) -> str:
    """Generate stub code from unified class info."""
    formatted_bases = ", ".join(class_info.bases)
    inheritance = f"({formatted_bases})" if formatted_bases else ""

    body = ""
    if class_info.is_enum:
        for member in class_info.real_class:
            body += f"    {member.name} = {member.value!r}\n"
    else:
        for attr in class_info.attributes:
            type_str = format_type_annotation(attr.type_annotation, imports_needed, current_module)
            body += f"    {attr.name}: {type_str}\n"
        for method in class_info.methods:
            body += _generate_method_stub(method, imports_needed, current_module)

    if not body:  # a marker/empty class still needs a body to be valid
        body = "    ...\n"

    return f"class {class_info.name}{inheritance}:\n{body}\n"


def _format_default(value: Any) -> str:
    """
    Render a parameter default for a stub.

    Falls back to ``...`` for anything that isn't a clean literal — most
    importantly the ``dataclasses`` default_factory sentinel, whose repr
    (``<factory>``) is not valid Python.
    """
    if value is None:
        return "None"
    if isinstance(value, enum.Enum):
        return f"{type(value).__name__}.{value.name}"
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, (bool, int, float)):
        return f"{value}"
    return "..."


def _generate_method_stub(method: MethodInfo | str | None, imports_needed: set[str], current_module: types.ModuleType) -> str:
    if not method:
        return ""

    if isinstance(method, str):
        lines = method.splitlines()
        return "\n".join(f"{' ' * 4}{line}" for line in lines) + "\n"

    params = []
    for param in method.params:
        param_str = param.name
        if param.type_annotation and param.type_annotation is not inspect.Signature.empty:
            if isinstance(param.type_annotation, str):
                param_str += f": {param.type_annotation}"
            else:
                param_str += f": {format_type_annotation(param.type_annotation, imports_needed, current_module)}"
        if param.has_default:
            param_str += f" = {_format_default(param.default_value)}"
        params.append(param_str)

    if method.return_annotation and method.return_annotation is not inspect.Signature.empty:
        if isinstance(method.return_annotation, str):
            return_type = f" -> {method.return_annotation}"
        else:
            return_type = f" -> {format_type_annotation(method.return_annotation, imports_needed, current_module)}"
    else:
        return_type = ""

    return f"    def {method.name}({', '.join(params)},){return_type}: ...\n"


def _is_type_checking_block(node: ast.AST) -> bool:
    return isinstance(node, ast.If) and (
        (isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING")
        or (
            isinstance(node.test, ast.Attribute)
            and node.test.attr == "TYPE_CHECKING"
            and isinstance(node.test.value, ast.Name)
            and node.test.value.id == "typing"
        )
    )


def _bind_typechecking_import(module: types.ModuleType, stmt: ast.stmt) -> None:
    """Bind the names of one ``if TYPE_CHECKING:`` import into ``module`` at runtime."""
    if isinstance(stmt, ast.ImportFrom):
        # Resolve relative imports (level > 0) against the module's package.
        source = importlib.import_module("." * stmt.level + (stmt.module or ""), module.__package__)
        targets = [(alias.asname or alias.name, source, alias.name) for alias in stmt.names]
    elif isinstance(stmt, ast.Import):
        targets = [(alias.asname or alias.name, None, alias.name) for alias in stmt.names]
    else:
        return

    for name, source, attr in targets:
        if hasattr(module, name):
            continue
        setattr(module, name, getattr(source, attr) if source is not None else importlib.import_module(attr))


def _inject_typechecking_imports(module: types.ModuleType) -> list[str]:
    """
    Make a module's ``if TYPE_CHECKING:`` imports importable at runtime.

    get_type_hints resolves a class's annotations in the namespace of the
    module each base is defined in, so forward references parked behind
    TYPE_CHECKING (in this module *or any base's* module) must be injected
    there first. Returns the import statements as source, for the stub header.
    """
    source_file = getattr(module, "__file__", None)
    if not source_file:
        return []

    collected: list[str] = []
    for node in ast.walk(ast.parse(Path(source_file).read_bytes())):
        if not _is_type_checking_block(node):
            continue
        for stmt in ast.walk(node):
            collected.append(_get_import_from_ast(stmt))  # Ensure the imports are available in the stub
            _bind_typechecking_import(module, stmt)
    return collected


def generate_stub_file(python_file: Path) -> str:
    """Generate complete stub file."""
    classes, imports = parse_class_ast_info(python_file)
    module = load_module_from_file(python_file)
    if not module:
        raise ModuleNotFoundError(f"Failed to load module {python_file}")

    if not classes:
        raise ValueError("No classes found")

    imports.extend(_inject_typechecking_imports(module))

    # Find all classes
    for name in dir(module):
        obj = getattr(module, name)
        if inspect.isclass(obj) and obj.__module__ == module.__name__:
            classes[obj.__name__].real_class = obj

    # A base class's annotations are resolved in *its* module, so inject the
    # TYPE_CHECKING imports of every base module within this package too.
    package = module.__name__.split(".")[0] + "."
    base_modules = {
        sys.modules[base.__module__]
        for cls in classes.values()
        if cls.real_class
        for base in cls.real_class.__mro__[1:]
        if base.__module__.startswith(package) and base.__module__ in sys.modules
    }
    for base_module in base_modules - {module}:
        _inject_typechecking_imports(base_module)

    imports_needed = set(imports)

    # Extract data for all classes
    for cls in classes.values():
        extract_class_data(cls)

    # Generate stub content
    stub_content = "# Auto-generated stub file\n"

    # Generate stubs and collect imports
    class_stubs = []
    for class_info in classes.values():
        stub = generate_stub_from_class_info(class_info, imports_needed, module)
        class_stubs.append(stub)

    stub_content += "\n".join(imports) + "\n"
    stub_content += "\n".join(imports_needed) + "\n"
    stub_content += "\n".join(class_stubs) + "\n"

    return stub_content


def reformat_file(output_file):
    # Use the project's full ruff config (not a fixed --select) so a stub is
    # clean under CI lint and re-runs a no-op. skip-magic-trailing-comma
    # collapses short imports/signatures onto one line (e.g. a single-name
    # `from x import (\n    Name,\n)` becomes `from x import Name`); the result
    # is a fixed point of the default formatter, so no drift.
    try:
        subprocess.run(
            ["ruff", "check", "--fix", "--unsafe-fixes", str(output_file)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        subprocess.run(
            ["ruff", "format", "--config", "format.skip-magic-trailing-comma=true", str(output_file)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        logger.info(f"Generated and formatted {output_file}")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Generated {output_file} but ruff formatting failed: {e}")
        for line in e.output.splitlines():
            logger.warning(line)
    except FileNotFoundError:
        logger.warning(f"Generated {output_file} but ruff not found - install ruff for formatting")


def _warrants_stub(module: types.ModuleType) -> bool:
    """
    Whether a module needs a hand-pinned ``.pyi``.

    A module warrants a stub when it defines a class that mixes a pydantic
    dataclass with ``SessionMixin``: type checkers cannot infer the
    ``__init__`` that combination synthesises, so we pin it in a stub.
    """
    for obj in vars(module).values():
        if not (inspect.isclass(obj) and obj.__module__ == module.__name__):
            continue
        ancestors = obj.__mro__[1:]
        if any(base.__name__ == "SessionMixin" for base in ancestors) and any(is_pydantic_dataclass(base) for base in ancestors):
            return True
    return False


def discover_stub_sources(package_dir: Path) -> list[Path]:
    """Return the source ``.py`` files in ``package_dir`` that warrant a stub."""
    sources = []
    for python_file in sorted(package_dir.glob("*.py")):
        if python_file.stem == "__init__":
            continue
        module = load_module_from_file(python_file)
        if module and _warrants_stub(module):
            sources.append(python_file)
    return sources


def sync_stubs(package_dir: Path) -> None:
    """
    Make the set of ``.pyi`` files a deterministic function of the sources.

    (Re)generate a stub for every module that warrants one and prune any
    orphaned stub whose source no longer exists or no longer qualifies.
    ``py.typed`` is left untouched (it is a PEP 561 marker, not a stub).
    """
    package_dir = package_dir.resolve()
    sources = discover_stub_sources(package_dir)
    wanted = {source.with_suffix(".pyi") for source in sources}

    for orphan in sorted(set(package_dir.glob("*.pyi")) - wanted):
        orphan.unlink()
        logger.info(f"Pruned orphaned stub {orphan}")

    for source in sources:
        output_file = source.with_suffix(".pyi")
        output_file.write_text(generate_stub_file(source))
        reformat_file(output_file)


def main():
    parser = argparse.ArgumentParser(description="Generate .pyi stub files for a package")
    parser.add_argument("package_dir", type=Path, help="Package directory whose stubs to (re)sync")

    args = parser.parse_args()
    sync_stubs(args.package_dir)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Error generating stub")
        exit(1)
