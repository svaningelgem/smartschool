# Student Notes & Absences

The school's pupil-follow-up system (leerlingvolgsysteem, LVS) keeps notes ("dossierlijnen") and absences per pupil.
This is **sensitive pupil information**: don't log it, share it or store it carelessly.

## Notes

```python
from smartschool import Smartschool, PathCredentials, StudentNotes

session = Smartschool(PathCredentials())

for note in StudentNotes(session):
    print(f"{note.date:%Y-%m-%d} [{note.cat_name}] {note.title} ({note.author})")
    if note.private:
        print("  (private: meant for staff)")
```

This only lists the headers. By default the notes of the logged-in user are returned, so a pupil's account sees their own
notes. The query accepts keyword-only arguments:

| Argument | Default | Meaning |
|----------|---------|---------|
| `pupil_id` | the logged-in user | The full user id string, in the form `<platform>_<id>_<role>` (e.g. `49_10880_2`), sent as is |
| `group_id` | `0` | The class group id |
| `since` | everything | Only ask for the period starting at this `date` |

```python
from datetime import date

notes = StudentNotes(session, since=date(2025, 9, 1))
```

`StudentNote.pupil_id` is only the numeric middle part of the user id.
The `title` and `author` are left out of `repr()` so they don't end up in logs or tracebacks.

## Absences

```python
from smartschool import StudentAbsences

for absence in StudentAbsences(session):
    print(f"{absence.date} {absence.part_of_day}: {absence.description}")
```

`part_of_day` is `VM` (morning) or `NM` (afternoon).

## Details of one note

The content of a note takes one extra request per note.

```python
from smartschool import StudentNoteDetails

note = next(iter(StudentNotes(session)))
detail = StudentNoteDetails(session, item_id=note.item_id).get()

print(detail.text)      # an announcement's free text, as plain text
print(detail.text_html) # the same text as the HTML Smartschool sends
print(detail.measure)   # the chosen disciplinary measure, if any
print(detail.date)      # only for categories that have a date parameter
print(detail.fields)    # other plain parameters by title, e.g. the teacher
print(detail.attachments)
```

An announcement ("mededeling") has no date parameter: use `note.date`.
Reading the details does not mark a note as viewed.

## Caveats

- This is an undocumented interface. Categories, parameters and their ids differ per school and can change without notice, so the details are
  interpreted by type and title, and unknown fields are ignored. All `StudentNoteDetail` properties are optional.
- What a pupil gets to see is decided by the server; `private` is only marked, not filtered.
- Read-only: nothing here can change a note.
