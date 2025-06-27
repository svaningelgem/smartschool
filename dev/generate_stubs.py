#!/usr/bin/env python3
"""Generate .pyi stub files from Python modules with pydantic base classes"""

import argparse
import ast
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import get_type_hints, Any
from logprise import logger


def load_module_from_file(file_path: Path):
    """Load a Python module from file path"""
    try:
        # Add the file's directory to sys.path to handle relative imports
        file_dir = file_path.parent.absolute()
        if str(file_dir) not in sys.path:
            sys.path.insert(0, str(file_dir))

        spec = importlib.util.spec_from_file_location("temp_module", file_path)
        if not spec or not spec.loader:
            logger.error(f"Could not create module spec for {file_path}")
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules["temp_module"] = module
        spec.loader.exec_module(module)
        return module
    except ImportError as e:
        logger.error(f"Import error loading {file_path}: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error loading module {file_path}")
        return None


def get_classes_from_file(file_path: Path) -> list[tuple[str, type]]:
    """Extract all class definitions from a Python file"""
    try:
        with open(file_path) as f:
            tree = ast.parse(f.read())
    except Exception as e:
        logger.error(f"Failed to parse {file_path}: {e}")
        return []

    class_names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_names.append(node.name)

    logger.debug(f"Found class names: {class_names}")

    # Load the actual module to get class objects
    module = load_module_from_file(file_path)
    if not module:
        return []

    classes = []
    for class_name in class_names:
        if hasattr(module, class_name):
            cls = getattr(module, class_name)
            classes.append((class_name, cls))
            logger.debug(f"Loaded class: {class_name}")
        else:
            logger.warning(f"Class {class_name} not found in module")

    return classes


def get_pydantic_base_class(cls):
    """Find the objects.<ClassName> base class if it exists"""
    for base in cls.__mro__:
        if hasattr(base, '__module__') and base.__module__:
            module_parts = base.__module__.split('.')
            if 'objects' in module_parts:
                # Check if this is a pydantic model
                if hasattr(base, 'model_fields'):
                    return base
    return None


def format_type_annotation(annotation: Any) -> str:
    """Format type annotation for stub file"""
    type_str = str(annotation)
    # Clean up common type annotations
    replacements = {
        'typing.': '',
        '<class \'': '',
        '\'>': '',
        'builtins.': '',
    }

    for old, new in replacements.items():
        type_str = type_str.replace(old, new)

    return type_str


def generate_init_signature(pydantic_class, additional_params: list[str] = None) -> str:
    """Generate __init__ method signature from pydantic model"""
    if not hasattr(pydantic_class, 'model_fields'):
        return "self, **kwargs"

    params = ["self"]
    if additional_params:
        params.extend(additional_params)

    type_hints = get_type_hints(pydantic_class)

    for field_name, field_info in pydantic_class.model_fields.items():
        field_type = type_hints.get(field_name, Any)
        type_str = format_type_annotation(field_type)

        # Handle default values
        if field_info.default is not None:
            if isinstance(field_info.default, bool):
                params.append(f"{field_name}: {type_str} = {field_info.default}")
            elif isinstance(field_info.default, str):
                params.append(f'{field_name}: {type_str} = "{field_info.default}"')
            elif isinstance(field_info.default, (int, float)):
                params.append(f"{field_name}: {type_str} = {field_info.default}")
            else:
                params.append(f"{field_name}: {type_str} = ...")
        else:
            params.append(f"{field_name}: {type_str}")

    return ",\n        ".join(params)


def generate_class_stub(class_name: str, cls: type) -> str:
    """Generate stub content for a single class"""
    pydantic_base = get_pydantic_base_class(cls)

    if not pydantic_base:
        # No pydantic base class found, generate basic stub
        return f"class {class_name}:\n    def __init__(self, **kwargs) -> None: ...\n\n"

    # Generate full stub with pydantic fields
    base_classes = []
    additional_init_params = []

    for base in cls.__mro__[1:]:  # Skip the class itself
        if base.__name__ != 'object':
            if hasattr(base, '__module__') and 'objects' in base.__module__:
                base_classes.append(f"objects.{base.__name__}")
            elif base.__name__ == 'SessionMixin':
                base_classes.append('SessionMixin')
                additional_init_params.append('session: Session')
            else:
                base_classes.append(base.__name__)

    inheritance = f"({', '.join(base_classes)})" if base_classes else ""

    stub_content = f"class {class_name}{inheritance}:\n"

    # Add session field if SessionMixin is inherited
    if 'SessionMixin' in base_classes:
        stub_content += "    session: Session\n"

    # Add fields from pydantic model
    if hasattr(pydantic_base, 'model_fields'):
        type_hints = get_type_hints(pydantic_base)
        for field_name, field_type in type_hints.items():
            type_str = format_type_annotation(field_type)
            stub_content += f"    {field_name}: {type_str}\n"

    # Generate __init__ method
    init_signature = generate_init_signature(pydantic_base, additional_init_params)
    stub_content += f"\n    def __init__(\n        {init_signature}\n    ) -> None: ...\n\n"

    return stub_content


def generate_stub_file(python_file: Path) -> str:
    """Generate complete stub file content"""
    classes = get_classes_from_file(python_file)

    if not classes:
        logger.warning("No classes found")
        return "# No classes found\n"

    stub_content = "# Auto-generated stub file\n"
    stub_content += "from typing import Any, Literal\n"

    # Try to detect actual imports needed
    try:
        with open(python_file) as f:
            content = f.read()
            if 'SessionMixin' in content:
                stub_content += "from . import SessionMixin\n"
            if 'objects.' in content:
                stub_content += "from . import objects\n"
    except Exception as e:
        logger.debug(f"Could not analyze imports: {e}")
        stub_content += "# Add necessary imports here\n"

    stub_content += "\n"

    for class_name, cls in classes:
        try:
            stub_content += generate_class_stub(class_name, cls)
        except Exception as e:
            logger.error(f"Failed to generate stub for {class_name}: {e}")
            stub_content += f"class {class_name}:\n    def __init__(self, **kwargs) -> None: ...\n\n"

    return stub_content


def main():
    parser = argparse.ArgumentParser(description="Generate .pyi stub files from Python modules")
    parser.add_argument("python_file", type=Path, help="Python file to analyze")
    parser.add_argument("-o", "--output", type=Path, help="Output .pyi file (default: same name with .pyi extension)")

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
        logger.exception(f"Error generating stub")
        return 1


if __name__ == "__main__":
    sys.exit(main())