# My Documents

"My Documents" (`/mydoc`) is your personal file storage in Smartschool. Browse
folders, download files, upload new files, create folders and delete items.

## Browsing

```python
from smartschool import Smartschool, PathCredentials, MyDocs, MyDocsFile, MyDocsFolder

session = Smartschool(PathCredentials())

mydocs = MyDocs(session=session)

for item in mydocs:
    if isinstance(item, MyDocsFolder):
        print(f"[folder] {item.name} ({item.color})")
        # Navigate into subfolders
        for subitem in item:
            print(f"  - {subitem.name}")
    elif isinstance(item, MyDocsFile):
        print(f"[file]   {item.name} ({item.size} bytes)")
```

## Recursive Listing

```python
def print_tree(folder, indent=0):
    for item in folder:
        prefix = "  " * indent
        if isinstance(item, MyDocsFolder):
            print(f"{prefix}[folder] {item.name}")
            print_tree(item, indent + 1)
        elif isinstance(item, MyDocsFile):
            print(f"{prefix}[file]   {item.name}")

print_tree(MyDocs(session=session))
```

## Downloading Files

```python
from pathlib import Path

for item in MyDocs(session=session):
    if isinstance(item, MyDocsFile):
        # Download to directory (keeps the original name)
        path = item.download_to_dir(Path("downloads"))

        # Download to a specific path
        item.download(Path("my_file.pdf"), overwrite=True)

        # Download as bytes
        content: bytes = item.download()
```

## Uploading, Creating Folders and Deleting

```python
mydocs = MyDocs(session=session)

# Create a folder in the root (or inside any MyDocsFolder)
homework = mydocs.create_folder("Homework")

# Upload a local file into it
uploaded = homework.upload("essay.docx")
print(uploaded.name, uploaded.size)

# Delete a file or a whole folder
uploaded.delete()
homework.delete()
```
