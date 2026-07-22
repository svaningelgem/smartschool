## 0.9.1 (2026-07-14)
- fix: handle empty inbox, image graphics, empty body and lazy login (#165) (#166)


# 0.9.0
* **Breaking**: importing from `smartschool.<submodule>` no longer works; import from `smartschool` directly. The public API is now flat. (#151)
* Added a `My Documents` (mydoc) client: browse, download, upload and manage your personal files. (#154)
* Added sending of messages. (#117)
* Stub generation (`.pyi`) is now self-maintaining. (#153)
* _bugfix_: Don't base64-decode message attachment downloads. (#159)
* _bugfix_: Tolerate new colors, result types, and icon graphics. (#131)
* _bugfix_: The session no longer re-fires every non-auth request. (#120)

# 0.8.2
* _bugfix_: Resolve forward-reference annotations in the stub generator. (#113)

# 0.8.1
* _bugfix_: Support letter-grade (text) results in `ResultGraphic`. (#110)
* _bugfix_: Make `PlannedElement` fields optional for planned to-dos. (#103)

# 0.8.0
* Added `Intradesk` module for browsing and downloading intradesk files
* Added `CourseList` class for `/course-list` API (works even when no results are available)
* Added `platform_id` property on `Smartschool` session
* Added dev tracing support for debugging API interactions
* Relaxed Python version requirement to `^3.10`

# 0.7.3
* _bugfix_: Fix MFA credential validation when using a `datetime.date` object (#88)

# 0.7.2
* At the start of the year, there are no results available, so `Courses` will throw an error. Clarify this in the error message.

# 0.7.1
* Updating README

# 0.7.0
* Adding `Report` integration
* type hints for `Result` and `Course` in IDE

# 0.6.0
* Major rework of the session system: you'll need to provide it now for each instantiation instead of initialiating it once. (global vs local) The advantage here is that you can have multiple concurrent sessions at once.
* Added ability to fetch documents from the courses. (see `smartschool_browse_docs` & `smartschool_dwnload_all_documents` scripts)
* Added `PlannedElements` (Smartschool's new 'agenda' implementation)
* Auto-search for the credentials file in most applicable places (cwd + up, home folder, cache folder)

# 0.5.0
* Added 'birthday' multi-factor-authentication (#7)

# 0.4.0
* Download errors show a nicer exception. (#4)

# 0.2.1
* Float dependencies.

# 0.2.0
* Updated dependencies.

# 0.1.9
* _bugfix_: The result comparison has been fixed.

# 0.1.8
* _bugfix_: FutureTasks had a bug in it which prevented it from loading moved tasks.

# 0.1.7
* Cleaning up login sequence: ensure the cookies are refreshed the first time you're using it.

# 0.1.6
* More fixes for 'XMLHttpRequest's.
* Open a new connection first thing, so we can be sure the cookies are fresh enough for usage.

# 0.1.5
* Bump minimal Python version to 3.11
* Setting the scripts executable.
* Fixing remote calls that needed the 'XMLHttpRequest' to be set.
* Adding `smartschool_report_on_future_tasks` to report on future tasks.

# 0.1.4
* Better caching mechanism
* Added MarkMessageUnread
* Added AdjustMessageLabel
* Added MessageMoveToArchive
* Added MessageMoveToTrash
* Added ResultDetails
* Renamed `SmartSchool` to `Smartschool`.
* Increased test coverage
* Code cleanup
* Added `smartschool_report_on_results` script to send emails about new results.

# 0.1.3
* Added fetching of 1 specific message and its attachments.

# 0.1.2
* Added StudentSupportLinks
* Added Messages

# 0.1.1
* Added AgendaMomentInfos
* Improved XML parsing
* Add a __lot__ of tests
* General cleanup of the code base

# 0.1.0
First commit