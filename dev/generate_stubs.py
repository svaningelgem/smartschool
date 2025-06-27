#!/usr/bin/env python3
"""Generate .pyi stub files from Python modules"""

import argparse
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import get_type_hints, Any
from logprise import logger


def format_type_annotation(annotation: Any, imports_needed: set) -> str:
    """Format type annotation for stub file and track needed imports"""
    type_str = str(annotation)

    # Handle module-qualified types and track imports
    if hasattr(annotation, '__module__') and hasattr(annotation, '__name__'):
        module = annotation.__module__
        name = annotation.__name__

        # Handle types from same package (relative imports)
        if module and '.' in module:
            module_parts = module.split('.')
            if len(module_parts) >= 2:
                # e.g., smartschool.session.Smartschool -> from .session import Smartschool
                if module_parts[-2] in ['session', 'objects']:  # common submodules
                    imports_needed.add(f"from .{module_parts[-2]} import {name}")
                    return name
                # e.g., smartschool.objects.Result -> from . import objects
                elif module_parts[-1] == 'objects':
                    imports_needed.add("from . import objects")
                    return f"objects.{name}"

    # Handle generic types (like Iterable[Result])
    if hasattr(annotation, '__origin__') and hasattr(annotation, '__args__'):
        origin = annotation.__origin__
        args = annotation.__args__

        # Format the origin type
        origin_name = getattr(origin, '__name__', str(origin))
        if origin_name in ['Iterator', 'Iterable', 'List', 'Dict', 'Optional', 'Union']:
            imports_needed.add(f"from typing import {origin_name}")

        # Format the arguments
        if args:
            formatted_args = []
            for arg in args:
                formatted_args.append(format_type_annotation(arg, imports_needed))
            return f"{origin_name}[{', '.join(formatted_args)}]"

        return origin_name

    # Extract class names from complex type strings for imports
    # Look for patterns like "smartschool.objects.ResultGraphic"
    import re
    class_pattern = r'smartschool\.(\w+)\.(\w+)'
    matches = re.findall(class_pattern, type_str)
    for submodule, class_name in matches:
        if submodule == 'objects':
            imports_needed.add("from . import objects")
            type_str = type_str.replace(f'smartschool.objects.{class_name}', f'objects.{class_name}')
        else:
            imports_needed.add(f"from .{submodule} import {class_name}")
            type_str = type_str.replace(f'smartschool.{submodule}.{class_name}', class_name)

    # Type replacements
    replacements = {
        'typing.': '',
        '<class \'': '',
        '\'>': '',
        'builtins.': '',
        'DateTime': 'datetime',
        'String': 'str',
        # Clean up remaining smartschool references
        'smartschool.session.Smartschool': 'Smartschool',
        'smartschool.objects.': 'objects.',
    }

    for old, new in replacements.items():
        type_str = type_str.replace(old, new)

    return type_str


def load_module_from_file(file_path: Path):
    """Load module with proper package context"""
    file_path = file_path.absolute()

    # Set up package context
    package_root = file_path.parent  # e.g., /path/to/smartschool
    package_name = package_root.name  # e.g., "smartschool"
    module_name = file_path.stem  # e.g., "results"
    full_module_name = f"{package_name}.{module_name}"  # e.g., "smartschool.results"

    # Add parent of package root to sys.path (so we can import smartschool.*)
    parent_dir = package_root.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))

    logger.debug(f"Package root: {package_root}")
    logger.debug(f"Package name: {package_name}")
    logger.debug(f"Full module name: {full_module_name}")
    logger.debug(f"Added to sys.path: {parent_dir}")

    try:
        # First, ensure the package itself exists in sys.modules
        if package_name not in sys.modules:
            package_init = package_root / "__init__.py"
            if package_init.exists():
                logger.debug(f"Loading package {package_name}")
                package_spec = importlib.util.spec_from_file_location(package_name, package_init)
                if package_spec and package_spec.loader:
                    package_module = importlib.util.module_from_spec(package_spec)
                    sys.modules[package_name] = package_module
                    package_spec.loader.exec_module(package_module)
            else:
                # Create a dummy package module
                logger.debug(f"Creating dummy package {package_name}")
                package_module = type(sys)('dummy_package')
                package_module.__path__ = [str(package_root)]
                sys.modules[package_name] = package_module

        # Now load the actual module
        logger.debug(f"Loading module {full_module_name}")
        spec = importlib.util.spec_from_file_location(full_module_name, file_path)
        if not spec or not spec.loader:
            logger.error(f"Could not create spec for {full_module_name}")
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[full_module_name] = module
        spec.loader.exec_module(module)

        logger.info(f"Successfully loaded {full_module_name}")
        return module

    except Exception as e:
        logger.exception(f"Failed to load module {full_module_name}")
        return None


def get_class_info(cls, imports_needed: set) -> dict:
    """Extract all relevant info from a class"""
    info = {
        'name': cls.__name__,
        'bases': [],
        'attributes': {},
        'methods': {},
        'has_init': hasattr(cls, '__init__') and cls.__init__ is not object.__init__
    }

    # Get base classes and fix their names
    for base in cls.__bases__:
        if base is not object:
            base_name = base.__name__

            # Handle module-qualified base classes
            if hasattr(base, '__module__') and base.__module__:
                module = base.__module__
                if 'objects' in module:
                    imports_needed.add("from . import objects")
                    base_name = f"objects.{base.__name__}"
                elif 'session' in module and base.__name__ == 'SessionMixin':
                    imports_needed.add("from .session import SessionMixin")
                    base_name = "SessionMixin"
                elif base.__name__ in ['Iterable', 'Iterator', 'List', 'Dict']:
                    imports_needed.add(f"from typing import {base.__name__}")

            # Handle generic base classes like Iterable[Result]
            if hasattr(base, '__origin__') and hasattr(base, '__args__'):
                formatted_base = format_type_annotation(base, imports_needed)
                info['bases'].append(formatted_base)
            else:
                info['bases'].append(base_name)

    # Get all attributes with type hints
    try:
        type_hints = get_type_hints(cls)
        for name, annotation in type_hints.items():
            if not name.startswith('_'):
                info['attributes'][name] = format_type_annotation(annotation, imports_needed)
    except Exception as e:
        logger.debug(f"Could not get type hints for {cls.__name__}: {e}")

    # Also check for pydantic model_fields
    if hasattr(cls, 'model_fields'):
        for field_name, field_info in cls.model_fields.items():
            if field_name not in info['attributes']:
                if hasattr(field_info, 'annotation'):
                    info['attributes'][field_name] = format_type_annotation(field_info.annotation, imports_needed)
                else:
                    info['attributes'][field_name] = 'Any'

    # Get important methods (like __iter__)
    for method_name in ['__iter__', '__next__', '__len__', '__getitem__']:
        if hasattr(cls, method_name):
            method = getattr(cls, method_name)
            if callable(method) and method is not getattr(object, method_name, None):
                try:
                    sig = inspect.signature(method)
                    return_annotation = sig.return_annotation
                    if return_annotation != inspect.Signature.empty:
                        formatted_return = format_type_annotation(return_annotation, imports_needed)
                        info['methods'][method_name] = formatted_return
                    else:
                        info['methods'][method_name] = 'Any'
                except Exception as e:
                    logger.debug(f"Could not get signature for {method_name}: {e}")

    # Get __init__ signature if custom
    if info['has_init']:
        try:
            sig = inspect.signature(cls.__init__)
            info['init_params'] = []
            for name, param in sig.parameters.items():
                if name == 'self':
                    continue

                param_str = name
                if param.annotation != inspect.Parameter.empty:
                    param_str += f": {format_type_annotation(param.annotation, imports_needed)}"
                if param.default != inspect.Parameter.empty:
                    if isinstance(param.default, str):
                        param_str += f' = "{param.default}"'
                    elif param.default is None:
                        param_str += ' = None'
                    else:
                        param_str += f' = {param.default}'

                info['init_params'].append(param_str)
        except Exception as e:
            logger.debug(f"Could not get init signature for {cls.__name__}: {e}")
            info['init_params'] = ['**kwargs']

    return info


def generate_class_stub(class_info: dict) -> str:
    """Generate stub for a single class"""
    name = class_info['name']
    bases = class_info['bases']
    attributes = class_info['attributes']
    methods = class_info.get('methods', {})

    # Build class definition
    if bases:
        inheritance = f"({', '.join(bases)})"
    else:
        inheritance = ""

    stub = f"class {name}{inheritance}:\n"

    # Add attributes
    if attributes:
        for attr_name, attr_type in attributes.items():
            stub += f"    {attr_name}: {attr_type}\n"

    # Add important methods
    for method_name, return_type in methods.items():
        if method_name == '__iter__':
            stub += f"    def __iter__(self) -> {return_type}: ...\n"
        elif method_name == '__next__':
            stub += f"    def __next__(self) -> {return_type}: ...\n"
        elif method_name == '__len__':
            stub += f"    def __len__(self) -> {return_type}: ...\n"
        elif method_name == '__getitem__':
            stub += f"    def __getitem__(self, key) -> {return_type}: ...\n"

    # Add __init__ if present
    if class_info['has_init'] and 'init_params' in class_info:
        params = ['self'] + class_info['init_params']
        if len(params) <= 3:  # Simple case
            stub += f"    def __init__({', '.join(params)}) -> None: ...\n"
        else:  # Multi-line
            stub += "    def __init__(\n"
            stub += "        self,\n"
            for param in class_info['init_params']:
                stub += f"        {param},\n"
            stub += "    ) -> None: ...\n"
    elif not attributes and not methods:  # No attributes or methods, add basic init
        stub += "    def __init__(self, **kwargs) -> None: ...\n"

    return stub + "\n"


def generate_stub_file(python_file: Path) -> str:
    """Generate complete stub file"""
    module = load_module_from_file(python_file)
    if not module:
        return "# Failed to load module\n"

    # Find all classes in the module
    classes = []
    for name in dir(module):
        obj = getattr(module, name)
        if inspect.isclass(obj) and obj.__module__ == module.__name__:
            classes.append(obj)

    if not classes:
        return "# No classes found\n"

    logger.info(f"Found classes: {[cls.__name__ for cls in classes]}")

    # Track imports needed across all classes
    imports_needed = set()
    imports_needed.add("from typing import Any")

    # Process all classes to gather import requirements
    class_infos = []
    for cls in classes:
        try:
            class_info = get_class_info(cls, imports_needed)
            class_infos.append(class_info)
            logger.debug(f"Class {cls.__name__} attributes: {list(class_info['attributes'].keys())}")
        except Exception as e:
            logger.error(f"Failed to process {cls.__name__}: {e}")
            class_infos.append({'name': cls.__name__, 'bases': [], 'attributes': {}, 'has_init': False})

    # Generate stub content
    stub_content = "# Auto-generated stub file\n"

    # Add all needed imports
    for import_line in sorted(imports_needed):
        stub_content += f"{import_line}\n"
    stub_content += "\n"

    # Generate class stubs
    for class_info in class_infos:
        try:
            stub_content += generate_class_stub(class_info)
        except Exception as e:
            logger.error(f"Failed to generate stub for {class_info['name']}: {e}")
            stub_content += f"class {class_info['name']}:\n    def __init__(self, **kwargs) -> None: ...\n\n"

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