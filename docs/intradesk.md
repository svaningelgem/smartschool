# Intradesk

The intradesk is a shared file storage area in Smartschool. Browse folders and download files.

## Browsing

```python
from smartschool import Smartschool, PathCredentials, Intradesk, IntradeskFile, IntradeskFolder

session = Smartschool(PathCredentials())

intradesk = Intradesk(session=session)

for item in intradesk:
    if isinstance(item, IntradeskFolder):
        print(f"[folder] {item.name}")
        # Navigate into subfolders
        for subitem in item:
            print(f"  - {subitem.name}")
    elif isinstance(item, IntradeskFile):
        print(f"[file]   {item.name}")
```

## Recursive Listing

```python
def print_tree(folder, indent=0):
    for item in folder:
        prefix = "  " * indent
        if isinstance(item, IntradeskFolder):
            print(f"{prefix}[folder] {item.name}")
            print_tree(item, indent + 1)
        elif isinstance(item, IntradeskFile):
            print(f"{prefix}[file]   {item.name}")

print_tree(Intradesk(session=session))
```

## Downloading Files

```python
from pathlib import Path

for item in Intradesk(session=session):
    if isinstance(item, IntradeskFile):
        # Download to directory
        path = item.download_to_dir(Path("downloads"))
        print(f"Saved: {path}")

        # Download to specific path
        item.download(Path("my_file.pdf"), overwrite=True)

        # Download as bytes
        content: bytes = item.download()
```
