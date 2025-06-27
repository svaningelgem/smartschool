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


def format_type_annotation(annotation: Any, imports_needed: set) -> str:
    """Format type annotation for stub file and track needed imports"""
    type_str = str(annotation)

    # Handle special typing constructs first
    if 'Literal[' in type_str:
        imports_needed.add("from typing import Literal")
        # Don't modify Literal content - keep original quotes

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
                # e.g., smartschool.session.Smartschool -> from .session import Smartschool
                if module_parts[-2] in ['session', 'objects']:
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
        if origin_name in ['Iterator', 'Iterable', 'List', 'Dict', 'Optional', 'Union', 'Tuple']:
            imports_needed.add(f"from typing import {origin_name}")

        # Format the arguments
        if args:
            formatted_args = []
            for arg in args:
                formatted_args.append(format_type_annotation(arg, imports_needed))
            return f"{origin_name}[{', '.join(formatted_args)}]"

        return origin_name

    # Extract class names from complex type strings for imports
    import re

    # Handle objects.* references
    objects_pattern = r'objects\.(\w+)'
    objects_matches = re.findall(objects_pattern, type_str)
    if objects_matches:
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

    # Handle bare class names that should be objects.* (but not if already prefixed)
    if not re.search(r'objects\.\w+', type_str) and not type_str.startswith('Literal['):
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
                    # Skip private methods unless they're special methods
                    if not item.name.startswith('_') or item.name.startswith('__'):
                        methods.append(item.name)
            class_methods[node.name] = methods

    return class_methods


def load_module_from_file(file_path: Path):
    """Load module with proper package context"""
    file_path = file_path.absolute()

    # Set up package context
    package_root = file_path.parent
    package_name = package_root.name
    module_name = file_path.stem
    full_module_name = f"{package_name}.{module_name}"

    # Add parent of package root to sys.path
    parent_dir = package_root.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))

    logger.debug(f"Loading {full_module_name}")

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


def get_class_info(cls, imports_needed: set, ast_methods: list[str]) -> dict:
    """Extract all relevant info from a class using both inspection and AST"""
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
            # Handle generic base classes first
            if hasattr(base, '__origin__') and hasattr(base, '__args__'):
                formatted_base = format_type_annotation(base, imports_needed)
                info['bases'].append(formatted_base)
                continue

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
                elif base.__name__ in ['Iterable', 'Iterator', 'List', 'Dict', 'Tuple']:
                    imports_needed.add(f"from typing import {base.__name__}")

                    # Try to infer generic type for common patterns
                    if base.__name__ == 'Iterable':
                        # Look for __iter__ method to infer type
                        if hasattr(cls, '__iter__'):
                            try:
                                iter_sig = inspect.signature(cls.__iter__)
                                if iter_sig.return_annotation != inspect.Signature.empty:
                                    return_type = format_type_annotation(iter_sig.return_annotation, imports_needed)
                                    # Extract type from Iterator[Type]
                                    if return_type.startswith('Iterator[') and return_type.endswith(']'):
                                        inner_type = return_type[9:-1]  # Extract from Iterator[...]
                                        base_name = f"Iterable[{inner_type}]"
                            except Exception as e:
                                logger.debug(f"Could not infer Iterable type: {e}")

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

    # Get methods that are actually defined in this class (from AST)
    for method_name in ast_methods:
        if hasattr(cls, method_name):
            method = getattr(cls, method_name)
            if callable(method):
                try:
                    sig = inspect.signature(method)
                    return_annotation = sig.return_annotation

                    # Build parameter list
                    params = []
                    for param_name, param in sig.parameters.items():
                        if param_name == 'self':
                            continue
                        param_str = param_name
                        if param.annotation != inspect.Parameter.empty:
                            param_str += f": {format_type_annotation(param.annotation, imports_needed)}"
                        if param.default != inspect.Parameter.empty:
                            if isinstance(param.default, str):
                                param_str += f' = "{param.default}"'
                            elif param.default is None:
                                param_str += ' = None'
                            else:
                                param_str += f' = {param.default}'
                        params.append(param_str)

                    return_type = 'None'
                    if return_annotation != inspect.Signature.empty:
                        return_type = format_type_annotation(return_annotation, imports_needed)

                    info['methods'][method_name] = {
                        'params': params,
                        'return_type': return_type
                    }
                except Exception as e:
                    logger.debug(f"Could not get signature for {method_name}: {e}")
                    info['methods'][method_name] = {'params': [], 'return_type': 'Any'}

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

    # Add methods (excluding __init__ which is handled separately)
    for method_name, method_info in methods.items():
        if method_name == '__init__':
            continue

        params_str = ', '.join(['self'] + method_info['params'])
        return_type = method_info['return_type']

        if len(params_str) > 80:  # Multi-line for long signatures
            stub += f"    def {method_name}(\n"
            stub += "        self,\n"
            for param in method_info['params']:
                stub += f"        {param},\n"
            stub += f"    ) -> {return_type}: ...\n"
        else:
            stub += f"    def {method_name}({params_str}) -> {return_type}: ...\n"

    # Add __init__ if present
    if class_info['has_init'] and 'init_params' in class_info:
        params = ['self'] + class_info['init_params']
        if len(', '.join(params)) > 80:  # Multi-line
            stub += "    def __init__(\n"
            stub += "        self,\n"
            for param in class_info['init_params']:
                stub += f"        {param},\n"
            stub += "    ) -> None: ...\n"
        else:
            stub += f"    def __init__({', '.join(params)}) -> None: ...\n"
    elif not attributes and not methods:  # No attributes or methods, add basic init
        stub += "    def __init__(self, **kwargs) -> None: ...\n"

    return stub + "\n"


def generate_stub_file(python_file: Path) -> str:
    """Generate complete stub file"""
    # Parse AST to get method definitions
    class_methods_ast = parse_class_methods_from_ast(python_file)
    logger.debug(f"AST methods: {class_methods_ast}")

    # Load the module
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
            ast_methods = class_methods_ast.get(cls.__name__, [])
            class_info = get_class_info(cls, imports_needed, ast_methods)
            class_infos.append(class_info)
            logger.debug(f"Class {cls.__name__} - attributes: {list(class_info['attributes'].keys())}, methods: {list(class_info['methods'].keys())}")
        except Exception as e:
            logger.error(f"Failed to process {cls.__name__}: {e}")
            class_infos.append({'name': cls.__name__, 'bases': [], 'attributes': {}, 'methods': {}, 'has_init': False})

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