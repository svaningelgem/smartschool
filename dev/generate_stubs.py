#!/usr/bin/env python3
"""Generate .pyi stub files from Python modules."""

from __future__ import annotations

import argparse
import ast
import importlib.util
import inspect
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, get_type_hints

from logprise import logger

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
    real_class: type = None
    bases: list[Any] = field(default_factory=list)
    attributes: list[FieldInfo] = field(default_factory=list)
    method_names: list[str] = field(default_factory=list)
    methods: list[MethodInfo] = field(default_factory=list)
    annotations: dict = field(default_factory=dict)
    init_method: MethodInfo = None


def _format_import(annotation: type, current_module: types.ModuleType) -> str:
    """Generate relative import when modules share common package."""
    module = annotation.__module__
    name = annotation.__name__

    if module == "builtins":
        return ""

    current_parts = current_module.__name__.split(".")
    target_parts = module.split(".")

    common_len = next((i for i, (a, b) in enumerate(zip(current_parts, target_parts)) if a != b), min(len(current_parts), len(target_parts)))

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
    # # For actual type objects with module info
    # if hasattr(annotation, '__module__') and hasattr(annotation, '__name__'):
    #     module = annotation.__module__
    #     name = annotation.__name__
    #
    #     # Handle typing module dynamically
    #     if module == 'typing':
    #         imports_needed.add(f"from typing import {name}")
    #         # For special forms like Literal, preserve their representation
    #         if hasattr(annotation, '__repr__'):
    #             repr_str = repr(annotation)
    #             if repr_str.startswith('typing.'):
    #                 return repr_str.replace('typing.', '')
    #             return repr_str
    #         return name
    #
    #     # Handle collections.abc
    #     elif module == 'collections.abc':
    #         imports_needed.add(f"from typing import {name}")
    #         return name
    #
    #     # Handle our package modules
    #     elif module and '.' in module:
    #         module_parts = module.split('.')
    #         if len(module_parts) >= 2:
    #             # Handle session module
    #             if module_parts[-2] == 'session' or module_parts[-1] == 'session':
    #                 imports_needed.add(f"from .session import {name}")
    #                 return name
    #             # Handle objects module
    #             elif module_parts[-2] == 'objects' or module_parts[-1] == 'objects':
    #                 # Check for name conflict with current class
    #                 if name == current_class_name:
    #                     imports_needed.add("from . import objects")
    #                     return f"objects.{name}"
    #                 else:
    #                     imports_needed.add("from . import objects")
    #                     return f"objects.{name}"
    #
    #     # Handle datetime
    #     elif module == 'datetime' and name == 'datetime':
    #         imports_needed.add("import datetime")
    #         return 'datetime.datetime'
    #
    #     # Handle built-in types
    #     elif module == 'builtins':
    #         return name
    #
    # # Handle generic types recursively
    # if hasattr(annotation, '__origin__') and hasattr(annotation, '__args__'):
    #     origin = annotation.__origin__
    #     args = annotation.__args__
    #
    #     # Format origin
    #     origin_formatted = format_type_annotation(origin, imports_needed, current_class_name)
    #
    #     # Format arguments
    #     if args:
    #         formatted_args = []
    #         for arg in args:
    #             formatted_args.append(format_type_annotation(arg, imports_needed, current_class_name))
    #         return f"{origin_formatted}[{', '.join(formatted_args)}]"
    #
    #     return origin_formatted
    #
    # # Handle string representations
    # type_str = str(annotation)
    #
    # # Clean up <class '...'> representations
    # if type_str.startswith("<class '") and type_str.endswith("'>"):
    #     clean_name = type_str[8:-2]  # Remove <class ' and '>
    #     if clean_name in ['str', 'int', 'bool', 'float', 'list', 'dict', 'tuple']:
    #         return clean_name
    #     return clean_name
    #
    # # Handle Union types
    # if 'Union[' in type_str:
    #     imports_needed.add("from typing import Union")
    # elif type_str.startswith('typing.'):
    #     type_name = type_str.replace('typing.', '')
    #     if '[' in type_name:
    #         type_name = type_name.split('[')[0]
    #     imports_needed.add(f"from typing import {type_name}")
    #
    # # Clean up the string representation
    # type_str = type_str.replace('typing.', '')
    #
    # # Handle smartschool package references
    # package_pattern = r'smartschool\.(\w+)\.(\w+)'
    # matches = re.findall(package_pattern, type_str)
    # for submodule, class_name in matches:
    #     if submodule == 'objects':
    #         imports_needed.add("from . import objects")
    #         type_str = type_str.replace(f'smartschool.objects.{class_name}', f'objects.{class_name}')
    #     elif submodule == 'session':
    #         imports_needed.add(f"from .session import {class_name}")
    #         type_str = type_str.replace(f'smartschool.session.{class_name}', class_name)
    #     else:
    #         imports_needed.add(f"from .{submodule} import {class_name}")
    #         type_str = type_str.replace(f'smartschool.{submodule}.{class_name}', class_name)
    #
    # # Handle legacy type names
    # if type_str == 'DateTime':
    #     imports_needed.add("import datetime")
    #     return 'datetime.datetime'
    # elif type_str == 'String':
    #     return 'str'
    #
    # # Handle bare class names that should be from objects
    # if type_str in ['Course', 'Teacher', 'Component', 'Period', 'Feedback', 'FeedbackFull', 'ResultDetails', 'ResultGraphic']:
    #     imports_needed.add("from . import objects")
    #     return f"objects.{type_str}"
    # elif type_str == 'Result' and current_class_name != 'Result':
    #     imports_needed.add("from . import objects")
    #     return f"objects.{type_str}"
    #
    # return type_str


def _get_import_from_ast(node: ast.Import | ast.ImportFrom) -> str:
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
            methods = []
            bases = []
            annotations = {}

            # Get base classes as written in source
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Subscript):
                    # Handle generic bases like Iterable[Result]
                    if isinstance(base.value, ast.Name):
                        base_name = base.value.id
                        if isinstance(base.slice, ast.Name):
                            slice_name = base.slice.id
                            bases.append(f"{base_name}[{slice_name}]")
                        else:
                            bases.append(base_name)
                elif isinstance(base, ast.Attribute):
                    # Handle qualified names like objects.Result
                    parts = []
                    current = base
                    while isinstance(current, ast.Attribute):
                        parts.insert(0, current.attr)
                        current = current.value
                    if isinstance(current, ast.Name):
                        parts.insert(0, current.id)
                    bases.append(".".join(parts))

            # Get method names
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    if not item.name.startswith("_") or re.match("^__.+__$", item.name):  # Don't add hidden functions
                        methods.append(item.name)
                elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    # Get type annotations as written
                    annotation_str = ast.unparse(item.annotation)
                    annotations[item.target.id] = annotation_str

            class_info[node.name] = ClassInfo(name=node.name, method_names=methods, bases=bases, annotations=annotations)

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
    "DateTime": "datetime",
}


def _extract_method_info(real_class: type, method_name: str) -> MethodInfo:
    sig = inspect.signature(getattr(real_class, method_name))
    method_params = []
    for name, param in sig.parameters.items():
        annotation = param.annotation
        if annotation in _pydantic_replacements:
            annotation = _pydantic_replacements[annotation]

        field_info = FieldInfo(
            name=name,
            type_annotation=annotation,
            default_value=param.default if param.default != inspect.Parameter.empty else None,
            has_default=param.default != inspect.Parameter.empty,
        )
        method_params.append(field_info)

    return MethodInfo(name=method_name, params=method_params, return_annotation=sig.return_annotation)


def extract_class_data(class_info: ClassInfo) -> ClassInfo:
    """Extract all class data into unified structure."""
    # Get ALL type annotations from the class - this is the single source of truth
    all_annotations = {}
    real_class = class_info.real_class

    # Get from type hints (this includes pydantic fields)
    try:
        type_hints = get_type_hints(real_class)
        all_annotations.update(type_hints)
        logger.debug(f"Got type hints for {real_class.__name__}: {list(type_hints.keys())}")
    except Exception as e:
        logger.debug(f"Could not get type hints: {e}")

    # # Update types from pydantic:
    # if hasattr(real_class, '__dataclass_fields__'):
    #     for attr, field in real_class.__dataclass_fields__.items():
    #         if attr not in all_annotations and hasattr(field, 'type'):
    #             all_annotations[attr] = field.type
    #             logger.debug(f"Added pydantic field {attr}: {field.type}")

    # Also check pydantic model_fields to get any that might be missing
    if hasattr(real_class, "model_fields"):
        for field_name, field_info in real_class.model_fields.items():
            if field_name not in all_annotations and hasattr(field_info, "annotation"):
                all_annotations[field_name] = field_info.annotation
                logger.debug(f"Added pydantic field {field_name}: {field_info.annotation}")

    # Convert all annotations to attributes
    for name, annotation in all_annotations.items():
        if not name.startswith("_"):
            field_info = FieldInfo(name=name, type_annotation=annotation)
            class_info.attributes.append(field_info)

    # Extract __init__ method signature
    if hasattr(real_class, "__init__") and real_class.__init__ is not object.__init__:
        class_info.init_method = _extract_method_info(real_class, "__init__")

    # Extract other methods from AST
    for method_name in class_info.method_names:
        if method_name == "__init__":
            continue

        if hasattr(real_class, method_name):
            method = getattr(real_class, method_name)
            if callable(method):
                class_info.methods.append(_extract_method_info(real_class, method_name))

    return class_info


def generate_stub_from_class_info(class_info: ClassInfo, imports_needed: set, current_module: types.ModuleType) -> str:
    """Generate stub code from unified class info."""
    formatted_bases = ", ".join(class_info.bases)

    # Build class definition
    inheritance = f"({formatted_bases})" if formatted_bases else ""
    stub = f"class {class_info.name}{inheritance}:\n"

    # Add attributes
    for attr in class_info.attributes:
        type_str = format_type_annotation(attr.type_annotation, imports_needed, current_module)
        stub += f"    {attr.name}: {type_str}\n"

    # Add methods
    for method in class_info.methods:
        stub += _generate_method_stub(current_module, imports_needed, method)

    # Add __init__ method
    stub += _generate_method_stub(current_module, imports_needed, class_info.init_method)
    return stub + "\n"


def _generate_method_stub(current_module: types.ModuleType, imports_needed: set[str], method: MethodInfo | None) -> str:
    if not method:
        return ""

    params = []
    for param in method.params:
        param_str = param.name
        if param.type_annotation and param.type_annotation is not inspect.Signature.empty:
            param_str += f": {param.type_annotation}"
        if param.has_default:
            if isinstance(param.default_value, str):
                param_str += f' = "{param.default_value}"'
            elif param.default_value is None:
                param_str += " = None"
            else:
                param_str += f" = {param.default_value}"
        params.append(param_str)

    if method.return_annotation and method.return_annotation is not inspect.Signature.empty:
        return_type = f" -> {method.return_annotation}"
    else:
        return_type = ""

    return f"    def {method.name}({', '.join(params)}){return_type}: ...\n"


def generate_stub_file(python_file: Path) -> str:
    """Generate complete stub file."""
    classes, imports = parse_class_ast_info(python_file)
    module = load_module_from_file(python_file)
    if not module:
        return "# Failed to load module\n"

    if not classes:
        return "# No classes found\n"

    # Find all classes
    for name in dir(module):
        obj = getattr(module, name)
        if inspect.isclass(obj) and obj.__module__ == module.__name__:
            classes[obj.__name__].real_class = obj

    imports_needed = set()

    # Extract data for all classes
    for cls in classes.values():
        extract_class_data(cls)

    # Generate stub content
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stub_content = f"# Auto-generated stub file\n# Generated on {now}\n"

    # Generate stubs and collect imports
    class_stubs = []
    for class_info in classes.values():
        stub = generate_stub_from_class_info(class_info, imports_needed, module)
        class_stubs.append(stub)

    stub_content += "\n".join(imports) + "\n"
    stub_content += "\n".join(imports_needed) + "\n"
    stub_content += "\n".join(class_stubs) + "\n"

    return stub_content


def main():
    parser = argparse.ArgumentParser(description="Generate .pyi stub files")
    parser.add_argument("python_file", type=Path, help="Python file to analyze")
    parser.add_argument("-o", "--output", type=Path, help="Output .pyi file")

    args = parser.parse_args()

    if not args.python_file.exists():
        logger.error(f"File {args.python_file} does not exist")
        return 1

    output_file = args.output or args.python_file.with_suffix(".pyi")

    stub_content = generate_stub_file(args.python_file)
    output_file.write_text(stub_content)
    reformat_file(output_file)


def reformat_file(output_file):
    try:
        subprocess.run(["ruff", "format", str(output_file)], check=True, capture_output=True)
        subprocess.run(["ruff", "check", "--select", "I,F,E", "--fix", str(output_file)], check=True, capture_output=True)
        logger.info(f"Generated and formatted {output_file}")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Generated {output_file} but ruff formatting failed: {e}")
    except FileNotFoundError:
        logger.warning(f"Generated {output_file} but ruff not found - install ruff for formatting")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Error generating stub")
        exit(1)
