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