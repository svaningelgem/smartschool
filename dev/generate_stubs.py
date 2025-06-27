#!/usr/bin/env python3
"""Generate .pyi stub files from Python modules"""

import argparse
import ast
import importlib.util
import inspect
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


def format_type_annotation(annotation: Any, imports_needed: set) -> str:
    """Format type annotation for stub file and track needed imports"""
    if annotation is None or annotation == inspect.Parameter.empty or annotation == inspect.Signature.empty:
        return 'Any'

    type_str = str(annotation)

    # Handle special typing constructs first
    if hasattr(annotation, '__module__') and annotation.__module__ == 'typing':
        if hasattr(annotation, '_name'):
            type_name = annotation._name
            if type_name in ['Literal', 'Union', 'Optional', 'List', 'Dict', 'Tuple']:
                imports_needed.add(f"from typing import {type_name}")
        elif 'Literal[' in type_str:
            imports_needed.add("from typing import Literal")

    if 'datetime.datetime' in type_str:
        imports_needed.add("import datetime")

    # Handle module-qualified types and track imports
    if hasattr(annotation, '__module__') and hasattr(annotation, '__name__'):
        module = annotation.__module__
        name = annotation.__name__

        # Handle types from same package (relative imports)
        if module and '.' in module:
            module_parts = module.split('.')
            if len(module_parts) >= 2:
                if module_parts[-2] in ['session', 'objects']:
                    imports_needed.add(f"from .{module_parts[-2]} import {name}")
                    return name
                elif module_parts[-1] == 'objects':
                    imports_needed.add("from . import objects")
                    return f"objects.{name}"

    # Handle generic types (like Iterable[Result])
    if hasattr(annotation, '__origin__') and hasattr(annotation, '__args__'):
        origin = annotation.__origin__
        args = annotation.__args__

        origin_name = getattr(origin, '__name__', str(origin))
        if origin_name in ['Iterator', 'Iterable', 'List', 'Dict', 'Optional', 'Union', 'Tuple']:
            imports_needed.add(f"from typing import {origin_name}")

        if args:
            formatted_args = []
            for arg in args:
                formatted_args.append(format_type_annotation(arg, imports_needed))
            return f"{origin_name}[{', '.join(formatted_args)}]"

        return origin_name

    # Extract class names for imports
    import re

    # Handle objects.* references
    if 'objects.' in type_str:
        imports_needed.add("from . import objects")

    # Handle smartschool.* references
    class_pattern = r'smartschool\.(\w+)\.(\w+)'
    matches = re.findall(class_pattern, type_str)
    for submodule, class_name in matches:
        if submodule == 'objects':
            imports_needed.add("from . import objects")
            type_str = type_str.replace(f'smartschool.objects.{class_name}', f'objects.{class_name}')
        else:
            imports_needed.add(f"from .{submodule} import {class_name}")
            type_str = type_str.replace(f'smartschool.{submodule}.{class_name}', class_name)

    # Handle bare class names that should be objects.*
    if not re.search(r'objects\.\w+', type_str) and not type_str.startswith('Literal'):
        bare_class_pattern = r'\b(Result|Course|Teacher|Component|Period|Feedback|FeedbackFull|ResultDetails|ResultGraphic)\b'
        def replace_with_objects(match):
            class_name = match.group(1)
            imports_needed.add("from . import objects")
            return f"objects.{class_name}"

        type_str = re.sub(bare_class_pattern, replace_with_objects, type_str)

    # Type replacements
    replacements = {
        'typing.': '',
        '<class \'': '',
        '\'>': '',
        'builtins.': '',
        'DateTime': 'datetime.datetime',
        'String': 'str',
        'smartschool.session.Smartschool': 'Smartschool',
    }

    for old, new in replacements.items():
        type_str = type_str.replace(old, new)

    return type_str


def parse_class_methods_from_ast(file_path: Path) -> dict[str, list[str]]:
    """Parse class methods from AST to get actual method definitions"""
    try:
        with open(file_path) as f:
            tree = ast.parse(f.read())
    except Exception as e:
        logger.error(f"Failed to parse AST: {e}")
        return {}

    class_methods = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    if not item.name.startswith('_') or item.name.startswith('__'):
                        methods.append(item.name)
            class_methods[node.name] = methods

    return class_methods


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


def extract_class_data(cls, ast_methods: list[str]) -> ClassInfo:
    """Extract all class data into unified structure"""
    class_info = ClassInfo(name=cls.__name__)

    # Extract base classes
    for base in cls.__bases__:
        if base is not object:
            class_info.bases.append(base)

    # Extract attributes from type hints
    try:
        type_hints = get_type_hints(cls)
        for name, annotation in type_hints.items():
            if not name.startswith('_'):
                field_info = FieldInfo(name=name, type_annotation=annotation)
                class_info.attributes.append(field_info)
                logger.debug(f"Type hint {name}: {annotation}")
    except Exception as e:
        logger.debug(f"Could not get type hints: {e}")

    # Extract pydantic model fields
    if hasattr(cls, 'model_fields'):
        existing_attrs = {attr.name for attr in class_info.attributes}
        for field_name, field_info in cls.model_fields.items():
            if field_name not in existing_attrs:
                if hasattr(field_info, 'annotation'):
                    field_data = FieldInfo(name=field_name, type_annotation=field_info.annotation)
                    class_info.attributes.append(field_data)
                    logger.debug(f"Pydantic field {field_name}: {field_info.annotation}")

    # Extract __init__ method
    if hasattr(cls, '__init__') and cls.__init__ is not object.__init__:
        try:
            sig = inspect.signature(cls.__init__)
            init_params = []
            for name, param in sig.parameters.items():
                if name == 'self':
                    continue

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

    # Extract other methods
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
        if hasattr(base, '__origin__') and hasattr(base, '__args__'):
            formatted_base = format_type_annotation(base, imports_needed)
            formatted_bases.append(formatted_base)
        else:
            base_name = base.__name__
            if hasattr(base, '__module__') and base.__module__:
                module = base.__module__
                if 'objects' in module:
                    imports_needed.add("from . import objects")
                    base_name = f"objects.{base.__name__}"
                elif 'session' in module and base.__name__ == 'SessionMixin':
                    imports_needed.add("from .session import SessionMixin")
                elif base.__name__ in ['Iterable', 'Iterator', 'List', 'Dict', 'Tuple']:
                    imports_needed.add(f"from typing import {base.__name__}")
                    # Try to infer Iterable type from __iter__ return type
                    if base.__name__ == 'Iterable':
                        for method in class_info.methods:
                            if method.name == '__iter__' and method.return_annotation:
                                return_type = format_type_annotation(method.return_annotation, imports_needed)
                                if return_type.startswith('Iterator[') and return_type.endswith(']'):
                                    inner_type = return_type[9:-1]
                                    base_name = f"Iterable[{inner_type}]"
                                    break
            formatted_bases.append(base_name)

    # Build class definition
    inheritance = f"({', '.join(formatted_bases)})" if formatted_bases else ""
    stub = f"class {class_info.name}{inheritance}:\n"

    # Add attributes
    for attr in class_info.attributes:
        type_str = format_type_annotation(attr.type_annotation, imports_needed)
        stub += f"    {attr.name}: {type_str}\n"

    # Add methods
    for method in class_info.methods:
        params = ['self']
        for param in method.params:
            param_str = param.name
            if param.type_annotation:
                param_str += f": {format_type_annotation(param.type_annotation, imports_needed)}"
            if param.has_default:
                if isinstance(param.default_value, str):
                    param_str += f' = "{param.default_value}"'
                elif param.default_value is None:
                    param_str += ' = None'
                else:
                    param_str += f' = {param.default_value}'
            params.append(param_str)

        return_type = format_type_annotation(method.return_annotation, imports_needed)

        if len(', '.join(params)) > 80:
            stub += f"    def {method.name}(\n"
            for param in params:
                stub += f"        {param},\n"
            stub += f"    ) -> {return_type}: ...\n"
        else:
            stub += f"    def {method.name}({', '.join(params)}) -> {return_type}: ...\n"

    # Add __init__ method
    if class_info.init_method:
        params = ['self']
        for param in class_info.init_method.params:
            param_str = param.name
            if param.type_annotation:
                param_str += f": {format_type_annotation(param.type_annotation, imports_needed)}"
            if param.has_default:
                if isinstance(param.default_value, str):
                    param_str += f' = "{param.default_value}"'
                elif param.default_value is None:
                    param_str += ' = None'
                else:
                    param_str += f' = {param.default_value}'
            params.append(param_str)

        if len(', '.join(params)) > 80:
            stub += "    def __init__(\n"
            for param in params:
                stub += f"        {param},\n"
            stub += "    ) -> None: ...\n"
        else:
            stub += f"    def __init__({', '.join(params)}) -> None: ...\n"
    elif not class_info.attributes and not class_info.methods:
        stub += "    def __init__(self, **kwargs) -> None: ...\n"

    return stub + "\n"


def generate_stub_file(python_file: Path) -> str:
    """Generate complete stub file"""
    class_methods_ast = parse_class_methods_from_ast(python_file)
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
        ast_methods = class_methods_ast.get(cls.__name__, [])
        class_info = extract_class_data(cls, ast_methods)
        class_infos.append(class_info)

    # Generate stub content
    stub_content = "# Auto-generated stub file\n"

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
        logger.info(f"Generated {output_file}")
        return 0
    except Exception as e:
        logger.exception("Error generating stub")
        return 1


if __name__ == "__main__":
    sys.exit(main())