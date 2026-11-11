# Planner element types are not read from Smartschool's JavaScript

**Decision: the library does not discover the planner's element types.** `PlannedElements.element_types` takes plain
strings, and [the planner guide](../planner.md#element-types) lists the accepted ones. Not now, maybe never.

## Context

`PlannedElements` filters on types such as `planned-lessons`. Smartschool validates them: a request naming an unknown
type is refused with a bare `400`, and no call lists the valid ones. The web interface has them hardcoded in its
JavaScript bundle, which is the only place they can be read from.

## How it would be done

1. Fetch `/planner` (about 360 KB of HTML) and find the script whose URL contains `Planner/planner-app/common.rev-`.
   The name carries a content hash, so the URL cannot be kept.
2. Download that bundle from the static host: about 1.2 MB, 280 KB compressed, no login needed.
3. Read the constants out of it. They are plain assignments, which survive minification:

   ```python
   candidates = set(re.findall(r'PLE_[A-Z_]+_TYPE="([a-z-]+)"', bundle))
   ```

4. Keep the ones the planner accepts, by asking for each over a one-day window: `200` is accepted, `400` is not.

   ```python
   accepted = {t for t in candidates if session.get(f"{url}?{urlencode({**day, 'types': t})}").status_code == 200}
   ```

Step 4 is needed because the bundle names more than the endpoint takes: of its 19 constants, 16 are accepted, and those
are the ones in the planner guide. One of the refused ones even sits in the bundle's own list for the week view, so the
web interface filters on something else as well.

## Why not

- **Cost.** Two extra requests and about 1.5 MB to get the candidates, then one request per candidate: over twenty
  requests to learn sixteen strings, in every session that wants them.
- **Fragile.** It leans on the name of a bundle and on the names of constants inside minified code. Either can change
  without notice, and the result would be an empty list, not an error.
- **Not needed.** `element_types=()` returns every element the planner has, whatever its type, so nothing has to be
  known up front. A wrong name fails loudly: the `400` is raised as a `SmartSchoolDownloadError`.

## When to look again

- Smartschool adds a call that lists the types.
- The list in the planner guide keeps going stale. The steps above then fit a script under `dev/` that prints the
  accepted types, run by hand when the guide needs a refresh. That still stays out of the library.
