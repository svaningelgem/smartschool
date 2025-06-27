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
        file_path = file_path.absolute()
        file_dir = file_path.parent

        # Add parent directories to sys.path to help with imports
        current_dir = file_dir
        while current_dir != current_dir.parent:
            if str(current_dir) not in sys.path:
                sys.path.insert(0, str(current_dir))
            current_dir = current_dir.parent

        # Try to determine package structure
        package_parts = []
        check_dir = file_dir
        while check_dir != check_dir.parent and (check_dir / "__init__.py").exists():
            package_parts.insert(0, check_dir.name)
            check_dir = check_dir.parent

        if package_parts:
            # Create package context
            package_name = ".".join(package_parts)
            module_name = f"{package_name}.{file_path.stem}"

            # Ensure parent packages exist in sys.modules
            for i in range(len(package_parts)):
                parent_package = ".".join(package_parts[:i+1])
                if parent_package not in sys.modules:
                    parent_spec = importlib.util.spec_from_file_location(
                        parent_package,
                        check_dir / "/".join(package_parts[:i+1]) / "__init__.py"
                    )
                    if parent_spec and parent_spec.loader:
                        parent_module = importlib.util.module_from_spec(parent_spec)
                        sys.modules[parent_package] = parent_module
                        parent_spec.loader.exec_module(parent_module)
        else:
            module_name = f"temp_module_{file_path.stem}"

        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if not spec or not spec.loader:
            logger.error(f"Could not create module spec for {file_path}")
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    except ImportError as e:
        logger.error(f"Import error loading {file_path}: {e}")
        # Try fallback approach - temporarily modify the file
        return load_module_with_fallback(file_path)
    except Exception as e:
        logger.exception(f"Unexpected error loading module {file_path}")
        return None


def load_module_with_fallback(file_path: Path):
    """Fallback: temporarily replace relative imports with absolute ones"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()

        # Simple pattern replacement for common relative imports
        modified_content = content
        modified_content = modified_content.replace('from . import', 'try:\n    from . import')
        modified_content = modified_content.replace('from .', 'try:\n    from .')

        # Add except clauses
        lines = modified_content.split('\n')
        new_lines = []
        for line in lines:
            new_lines.append(line)
            if line.strip().startswith('try:') and ('from .' in line):
                new_lines.append('except ImportError:')
                new_lines.append('    pass')

        modified_content = '\n'.join(new_lines)

        # Create temporary module
        spec = importlib.util.spec_from_loader("temp_fallback", loader=None)
        module = importlib.util.module_from_spec(spec)
        exec(modified_content, module.__dict__)
        return module

    except Exception as e:
        logger.debug(f"Fallback loading also failed: {e}")
        return None


def get_classes_from_file(file_path: Path) -> list[tuple[str, type]]:
    """Extract actual import statements from the file"""
    import_lines = []
    try:
        with open(file_path) as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        import_lines.append(f"from {node.module} import {alias.name}")
                else:  # relative import
                    level = "." * node.level
                    for alias in node.names:
                        import_lines.append(f"from {level} import {alias.name}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    import_lines.append(f"import {alias.name}")
    except Exception as e:
        logger.debug(f"Could not parse imports: {e}")

    return import_lines
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
    logger.debug(f"Checking bases for {cls.__name__}: {[base.__name__ for base in cls.__mro__]}")

    for base in cls.__mro__:
        if hasattr(base, '__module__') and base.__module__:
            module_parts = base.__module__.split('.')
            logger.debug(f"Base {base.__name__} module: {base.__module__}")

            # Check if this is a pydantic model
            if hasattr(base, 'model_fields') and base.model_fields:
                logger.debug(f"Found pydantic base: {base.__name__} with fields: {list(base.model_fields.keys())}")
                return base

            # Also check for objects module pattern
            if 'objects' in module_parts and hasattr(base, 'model_fields'):
                logger.debug(f"Found objects.* pydantic base: {base.__name__}")
                return base

    logger.debug(f"No pydantic base found for {cls.__name__}")
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
        logger.debug(f"No pydantic base for {class_name}, generating basic stub")
        return f"class {class_name}:\n    def __init__(self, **kwargs) -> None: ...\n\n"

    logger.debug(f"Generating full stub for {class_name} with pydantic base {pydantic_base.__name__}")

    # Generate full stub with pydantic fields
    base_classes = []
    additional_init_params = []

    for base in cls.__mro__[1:]:  # Skip the class itself
        if base.__name__ != 'object':
            if hasattr(base, '__module__') and base.__module__:
                if 'objects' in base.__module__:
                    base_classes.append(f"objects.{base.__name__}")
                elif base.__name__ == 'SessionMixin':
                    base_classes.append('SessionMixin')
                    additional_init_params.append('session: Session')
                elif not base.__module__.startswith('builtins'):
                    base_classes.append(base.__name__)

    inheritance = f"({', '.join(base_classes)})" if base_classes else ""

    stub_content = f"class {class_name}{inheritance}:\n"

    # Add session field if SessionMixin is inherited
    if any('SessionMixin' in base for base in base_classes):
        stub_content += "    session: Session\n"

    # Add fields from pydantic model
    if hasattr(pydantic_base, 'model_fields') and pydantic_base.model_fields:
        try:
            type_hints = get_type_hints(pydantic_base)
            logger.debug(f"Type hints for {pydantic_base.__name__}: {list(type_hints.keys())}")

            for field_name, field_type in type_hints.items():
                type_str = format_type_annotation(field_type)
                stub_content += f"    {field_name}: {type_str}\n"
        except Exception as e:
            logger.error(f"Failed to get type hints for {pydantic_base.__name__}: {e}")
            # Fallback to model_fields
            for field_name, field_info in pydantic_base.model_fields.items():
                annotation = getattr(field_info, 'annotation', 'Any')
                type_str = format_type_annotation(annotation)
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

    # Extract actual imports from the original file
    actual_imports = extract_imports_from_file(python_file)
    logger.debug(f"Found imports: {actual_imports}")

    stub_content = "# Auto-generated stub file\n"
    stub_content += "from typing import Any, Literal\n"

    # Add the actual imports found in the file
    for import_line in actual_imports:
        # Skip certain imports that might cause issues in stub files
        if not any(skip in import_line for skip in ['__future__', 'typing_extensions']):
            stub_content += f"{import_line}\n"

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