#!/usr/bin/env python3
"""Generate .pyi stub files from Python modules"""

import argparse
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import get_type_hints, Any
from logprise import logger


def format_type_annotation(annotation: Any) -> str:
    """Format type annotation for stub file"""
    type_str = str(annotation)
    replacements = {
        'typing.': '',
        '<class \'': '',
        '\'>': '',
        'builtins.': '',
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


def get_class_info(cls) -> dict:
    """Extract all relevant info from a class"""
    info = {
        'name': cls.__name__,
        'bases': [],
        'attributes': {},
        'has_init': hasattr(cls, '__init__') and cls.__init__ is not object.__init__
    }

    # Get base classes
    for base in cls.__bases__:
        if base is not object:
            info['bases'].append(base.__name__)

    # Get all attributes with type hints
    try:
        type_hints = get_type_hints(cls)
        for name, annotation in type_hints.items():
            if not name.startswith('_'):
                info['attributes'][name] = format_type_annotation(annotation)
    except Exception as e:
        logger.debug(f"Could not get type hints for {cls.__name__}: {e}")

    # Also check for pydantic model_fields
    if hasattr(cls, 'model_fields'):
        for field_name, field_info in cls.model_fields.items():
            if field_name not in info['attributes']:
                if hasattr(field_info, 'annotation'):
                    info['attributes'][field_name] = format_type_annotation(field_info.annotation)
                else:
                    info['attributes'][field_name] = 'Any'

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
                    param_str += f": {format_type_annotation(param.annotation)}"
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
    elif not attributes:  # No attributes, add basic init
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

    # Generate stub content
    stub_content = "# Auto-generated stub file\n"
    stub_content += "from typing import Any\n\n"

    for cls in classes:
        try:
            class_info = get_class_info(cls)
            logger.debug(f"Class {cls.__name__} attributes: {list(class_info['attributes'].keys())}")
            stub_content += generate_class_stub(class_info)
        except Exception as e:
            logger.error(f"Failed to process {cls.__name__}: {e}")
            stub_content += f"class {cls.__name__}:\n    def __init__(self, **kwargs) -> None: ...\n\n"

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