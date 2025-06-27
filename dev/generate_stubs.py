#!/usr/bin/env python3
"""Generate .pyi stub files from Python modules"""

import argparse
import ast
import importlib.util
import inspect
import subprocess
import sys
from pathlib import Path
from typing import get_type_hints, Any
from logprise import logger
from dataclasses import dataclass, field


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
    bases: list[Any] = field(default_factory=list)
    attributes: list[FieldInfo] = field(default_factory=list)
    methods: list[MethodInfo] = field(default_factory=list)
    init_method: MethodInfo = None


def format_type_annotation(annotation: Any, imports_needed: set, current_class_name: str = None) -> str:
    """Format type annotation for stub file and track needed imports"""
    if annotation is None or annotation == inspect.Parameter.empty or annotation == inspect.Signature.empty:
        return 'Any'

    # Handle basic Python types first
    if annotation == str:
        return 'str'
    elif annotation == int:
        return 'int'
    elif annotation == bool:
        return 'bool'
    elif annotation == float:
        return 'float'
    elif annotation == list:
        return 'list'
    elif annotation == dict:
        return 'dict'
    elif annotation == tuple:
        return 'tuple'

    # For actual type objects with module info
    if hasattr(annotation, '__module__') and hasattr(annotation, '__name__'):
        module = annotation.__module__
        name = annotation.__name__

        # Handle typing module dynamically
        if module == 'typing':
            imports_needed.add(f"from typing import {name}")
            # For special forms like Literal, preserve their representation
            if hasattr(annotation, '__repr__'):
                repr_str = repr(annotation)
                if repr_str.startswith('typing.'):
                    return repr_str.replace('typing.', '')
                return repr_str
            return name

        # Handle collections.abc
        elif module == 'collections.abc':
            imports_needed.add(f"from typing import {name}")
            return name

        # Handle our package modules
        elif module and '.' in module:
            module_parts = module.split('.')
            if len(module_parts) >= 2:
                # Handle session module
                if module_parts[-2] == 'session' or module_parts[-1] == 'session':
                    imports_needed.add(f"from .session import {name}")
                    return name
                # Handle objects module
                elif module_parts[-2] == 'objects' or module_parts[-1] == 'objects':
                    # Check for name conflict with current class
                    if name == current_class_name:
                        imports_needed.add("from . import objects")
                        return f"objects.{name}"
                    else:
                        imports_needed.add("from . import objects")
                        return f"objects.{name}"

        # Handle datetime
        elif module == 'datetime' and name == 'datetime':
            imports_needed.add("import datetime")
            return 'datetime.datetime'

        # Handle built-in types
        elif module == 'builtins':
            return name

    # Handle generic types recursively
    if hasattr(annotation, '__origin__') and hasattr(annotation, '__args__'):
        origin = annotation.__origin__
        args = annotation.__args__

        # Format origin
        origin_formatted = format_type_annotation(origin, imports_needed, current_class_name)

        # Format arguments
        if args:
            formatted_args = []
            for arg in args:
                formatted_args.append(format_type_annotation(arg, imports_needed, current_class_name))
            return f"{origin_formatted}[{', '.join(formatted_args)}]"

        return origin_formatted

    # Handle string representations
    type_str = str(annotation)

    # Clean up <class '...'> representations
    if type_str.startswith("<class '") and type_str.endswith("'>"):
        clean_name = type_str[8:-2]  # Remove <class ' and '>
        if clean_name in ['str', 'int', 'bool', 'float', 'list', 'dict', 'tuple']:
            return clean_name
        return clean_name

    # Handle Union types
    if 'Union[' in type_str:
        imports_needed.add("from typing import Union")
    elif type_str.startswith('typing.'):
        type_name = type_str.replace('typing.', '')
        if '[' in type_name:
            type_name = type_name.split('[')[0]
        imports_needed.add(f"from typing import {type_name}")

    # Clean up the string representation
    type_str = type_str.replace('typing.', '')

    # Handle smartschool package references
    import re
    package_pattern = r'smartschool\.(\w+)\.(\w+)'
    matches = re.findall(package_pattern, type_str)
    for submodule, class_name in matches:
        if submodule == 'objects':
            imports_needed.add("from . import objects")
            type_str = type_str.replace(f'smartschool.objects.{class_name}', f'objects.{class_name}')
        elif submodule == 'session':
            imports_needed.add(f"from .session import {class_name}")
            type_str = type_str.replace(f'smartschool.session.{class_name}', class_name)
        else:
            imports_needed.add(f"from .{submodule} import {class_name}")
            type_str = type_str.replace(f'smartschool.{submodule}.{class_name}', class_name)

    # Handle legacy type names
    if type_str == 'DateTime':
        imports_needed.add("import datetime")
        return 'datetime.datetime'
    elif type_str == 'String':
        return 'str'

    # Handle bare class names that should be from objects
    if type_str in ['Course', 'Teacher', 'Component', 'Period', 'Feedback', 'FeedbackFull', 'ResultDetails', 'ResultGraphic']:
        imports_needed.add("from . import objects")
        return f"objects.{type_str}"
    elif type_str == 'Result' and current_class_name != 'Result':
        imports_needed.add("from . import objects")
        return f"objects.{type_str}"

    return type_str


def parse_class_ast_info(file_path: Path) -> dict:
    """Parse AST to get class structure info as written in source"""
    try:
        with open(file_path) as f:
            tree = ast.parse(f.read())
    except Exception as e:
        logger.error(f"Failed to parse AST: {e}")
        return {}

    class_info = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            info = {
                'methods': [],
                'bases': [],
                'annotations': {}
            }

            # Get base classes as written in source
            for base in node.bases:
                if isinstance(base, ast.Name):
                    info['bases'].append(base.id)
                elif isinstance(base, ast.Subscript):
                    # Handle generic bases like Iterable[Result]
                    if isinstance(base.value, ast.Name):
                        base_name = base.value.id
                        if isinstance(base.slice, ast.Name):
                            slice_name = base.slice.id
                            info['bases'].append(f"{base_name}[{slice_name}]")
                        else:
                            info['bases'].append(base_name)
                elif isinstance(base, ast.Attribute):
                    # Handle qualified names like objects.Result
                    parts = []
                    current = base
                    while isinstance(current, ast.Attribute):
                        parts.insert(0, current.attr)
                        current = current.value
                    if isinstance(current, ast.Name):
                        parts.insert(0, current.id)
                    info['bases'].append('.'.join(parts))

            # Get method names
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    if not item.name.startswith('_') or item.name.startswith('__'):
                        info['methods'].append(item.name)
                elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    # Get type annotations as written
                    annotation_str = ast.unparse(item.annotation)
                    info['annotations'][item.target.id] = annotation_str

            class_info[node.name] = info

    return class_info


def load_module_from_file(file_path: Path):
    """Load module with proper package context"""
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
                package_module = type(sys)('dummy_package')
                package_module.__path__ = [str(package_root)]
                sys.modules[package_name] = package_module

        spec = importlib.util.spec_from_file_location(full_module_name, file_path)
        if not spec or not spec.loader:
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[full_module_name] = module
        spec.loader.exec_module(module)

        return module

    except Exception as e:
        logger.exception(f"Failed to load module {full_module_name}")
        return None


def extract_class_data(cls, ast_info: dict) -> ClassInfo:
    """Extract all class data into unified structure"""
    class_info = ClassInfo(name=cls.__name__)

    # Use AST for base classes to get exactly what's written
    ast_bases = ast_info.get('bases', [])
    if ast_bases:
        # Convert AST base strings back to actual types for consistent formatting
        for base_str in ast_bases:
            # Try to resolve the base class from the actual class
            for actual_base in cls.__bases__:
                if actual_base is not object:
                    class_info.bases.append(actual_base)
    else:
        # Fallback to introspection
        for base in cls.__bases__:
            if base is not object:
                class_info.bases.append(base)

    # Get ALL type annotations from the class - this is the single source of truth
    all_annotations = {}

    # Get from type hints (this includes pydantic fields)
    try:
        type_hints = get_type_hints(cls)
        all_annotations.update(type_hints)
        logger.debug(f"Got type hints for {cls.__name__}: {list(type_hints.keys())}")
    except Exception as e:
        logger.debug(f"Could not get type hints: {e}")

    # Also check pydantic model_fields to get any that might be missing
    if hasattr(cls, 'model_fields'):
        for field_name, field_info in cls.model_fields.items():
            if field_name not in all_annotations and hasattr(field_info, 'annotation'):
                all_annotations[field_name] = field_info.annotation
                logger.debug(f"Added pydantic field {field_name}: {field_info.annotation}")

    # Convert all annotations to attributes
    for name, annotation in all_annotations.items():
        if not name.startswith('_'):
            field_info = FieldInfo(name=name, type_annotation=annotation)
            class_info.attributes.append(field_info)

    # Extract __init__ method signature
    if hasattr(cls, '__init__') and cls.__init__ is not object.__init__:
        try:
            sig = inspect.signature(cls.__init__)
            init_params = []
            for name, param in sig.parameters.items():
                if name == 'self':
                    continue

                # Use the annotation from the signature
                field_info = FieldInfo(
                    name=name,
                    type_annotation=param.annotation,
                    default_value=param.default if param.default != inspect.Parameter.empty else None,
                    has_default=param.default != inspect.Parameter.empty
                )
                init_params.append(field_info)
                logger.debug(f"Init param {name}: {param.annotation}")

            class_info.init_method = MethodInfo(name='__init__', params=init_params)
        except Exception as e:
            logger.debug(f"Could not get init signature: {e}")

    # Extract other methods from AST
    ast_methods = ast_info.get('methods', [])
    for method_name in ast_methods:
        if method_name == '__init__':
            continue

        if hasattr(cls, method_name):
            method = getattr(cls, method_name)
            if callable(method):
                try:
                    sig = inspect.signature(method)
                    method_params = []
                    for name, param in sig.parameters.items():
                        if name == 'self':
                            continue
                        field_info = FieldInfo(
                            name=name,
                            type_annotation=param.annotation,
                            default_value=param.default if param.default != inspect.Parameter.empty else None,
                            has_default=param.default != inspect.Parameter.empty
                        )
                        method_params.append(field_info)

                    method_info = MethodInfo(
                        name=method_name,
                        params=method_params,
                        return_annotation=sig.return_annotation
                    )
                    class_info.methods.append(method_info)
                except Exception as e:
                    logger.debug(f"Could not get method signature for {method_name}: {e}")

    return class_info


def generate_stub_from_class_info(class_info: ClassInfo, imports_needed: set) -> str:
    """Generate stub code from unified class info"""

    # Format base classes
    formatted_bases = []
    for base in class_info.bases:
        base_formatted = format_type_annotation(base, imports_needed, class_info.name)
        formatted_bases.append(base_formatted)

    # Build class definition
    inheritance = f"({', '.join(formatted_bases)})" if formatted_bases else ""
    stub = f"class {class_info.name}{inheritance}:\n"

    # Add attributes
    for attr in class_info.attributes:
        type_str = format_type_annotation(attr.type_annotation, imports_needed, class_info.name)
        stub += f"    {attr.name}: {type_str}\n"

    # Add methods
    for method in class_info.methods:
        params = ['self']
        for param in method.params:
            param_str = param.name
            if param.type_annotation:
                param_str += f": {format_type_annotation(param.type_annotation, imports_needed, class_info.name)}"
            if param.has_default:
                if isinstance(param.default_value, str):
                    param_str += f' = "{param.default_value}"'
                elif param.default_value is None:
                    param_str += ' = None'
                else:
                    param_str += f' = {param.default_value}'
            params.append(param_str)

        return_type = format_type_annotation(method.return_annotation, imports_needed, class_info.name)
        stub += f"    def {method.name}({', '.join(params)}) -> {return_type}: ...\n"

    # Add __init__ method
    if class_info.init_method:
        params = ['self']
        for param in class_info.init_method.params:
            param_str = param.name
            if param.type_annotation:
                param_str += f": {format_type_annotation(param.type_annotation, imports_needed, class_info.name)}"
            if param.has_default:
                if isinstance(param.default_value, str):
                    param_str += f' = "{param.default_value}"'
                elif param.default_value is None:
                    param_str += ' = None'
                else:
                    param_str += f' = {param.default_value}'
            params.append(param_str)

        stub += f"    def __init__({', '.join(params)}) -> None: ...\n"
    elif not class_info.attributes and not class_info.methods:
        stub += "    def __init__(self, **kwargs) -> None: ...\n"

    return stub + "\n"


def generate_stub_file(python_file: Path) -> str:
    """Generate complete stub file"""
    from datetime import datetime

    ast_info = parse_class_ast_info(python_file)
    module = load_module_from_file(python_file)
    if not module:
        return "# Failed to load module\n"

    # Find all classes
    classes = []
    for name in dir(module):
        obj = getattr(module, name)
        if inspect.isclass(obj) and obj.__module__ == module.__name__:
            classes.append(obj)

    if not classes:
        return "# No classes found\n"

    imports_needed = set()
    imports_needed.add("from typing import Any")

    # Extract data for all classes
    class_infos = []
    for cls in classes:
        class_ast_info = ast_info.get(cls.__name__, {})
        class_info = extract_class_data(cls, class_ast_info)
        class_infos.append(class_info)

    # Generate stub content
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stub_content = f"# Auto-generated stub file\n# Generated on {now}\n"

    # Generate stubs and collect imports
    class_stubs = []
    for class_info in class_infos:
        stub = generate_stub_from_class_info(class_info, imports_needed)
        class_stubs.append(stub)

    # Add imports
    for import_line in sorted(imports_needed):
        stub_content += f"{import_line}\n"
    stub_content += "\n"

    # Add class stubs
    for stub in class_stubs:
        stub_content += stub

    return stub_content


def main():
    parser = argparse.ArgumentParser(description="Generate .pyi stub files")
    parser.add_argument("python_file", type=Path, help="Python file to analyze")
    parser.add_argument("-o", "--output", type=Path, help="Output .pyi file")

    args = parser.parse_args()

    if not args.python_file.exists():
        logger.error(f"File {args.python_file} does not exist")
        return 1

    output_file = args.output or args.python_file.with_suffix('.pyi')

    try:
        stub_content = generate_stub_file(args.python_file)
        output_file.write_text(stub_content)

        # Run ruff format on the generated file
        try:
            subprocess.run(['ruff', 'format', str(output_file)], check=True, capture_output=True)
            logger.info(f"Generated and formatted {output_file}")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Generated {output_file} but ruff formatting failed: {e}")
        except FileNotFoundError:
            logger.warning(f"Generated {output_file} but ruff not found - install ruff for formatting")

        return 0
    except Exception as e:
        logger.exception("Error generating stub")
        return 1


if __name__ == "__main__":
    sys.exit(main())