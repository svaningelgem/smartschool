# Courses & Documents

## Browsing Courses

There are three ways to list courses, each returning different data:

### TopNavCourses

Courses from the navigation bar. Each course gives access to its document tree.

```python
from smartschool import Smartschool, PathCredentials, TopNavCourses

session = Smartschool(PathCredentials())

for course in TopNavCourses(session):
    print(f"{course.name} (teacher: {course.teacher})")
```

### CourseList

All courses via the course-list API. Always works, even when no results are available yet.

```python
from smartschool import CourseList

for course in CourseList(session):
    print(f"{course.name} (platform: {course.platformId})")
```

### Courses

Courses from the results/evaluations API. Requires results to be published (will raise an error at the start of the school year).

```python
from smartschool import Courses

for course in Courses(session):
    print(course)  # "Wiskunde (Teacher: Jansen)"
```

## Browsing Documents

`TopNavCourses` provides access to course documents via the `items` property:

```python
from smartschool import TopNavCourses, FileItem, FolderItem, InternetShortcut

for course in TopNavCourses(session):
    for item in course.items:
        if isinstance(item, FileItem):
            print(f"  [file]   {item.filename} ({item.size_kb} KB)")
        elif isinstance(item, FolderItem):
            print(f"  [folder] {item.name}")
            # Navigate into subfolders
            for subitem in item.items:
                print(f"    - {subitem.name}")
        elif isinstance(item, InternetShortcut):
            print(f"  [link]   {item.name} -> {item.link}")
```

## Downloading Files

```python
from pathlib import Path

# Download to a specific directory
for course in TopNavCourses(session):
    for item in course.items:
        if isinstance(item, FileItem):
            path = item.download_to_dir(Path("downloads") / course.name)
            print(f"Saved: {path}")

# Download to a specific file path
item.download(Path("my_file.pdf"), overwrite=True)

# Download as bytes (in-memory)
content: bytes = item.download()
```

`InternetShortcut` items generate `.url` shortcut files when downloaded.
