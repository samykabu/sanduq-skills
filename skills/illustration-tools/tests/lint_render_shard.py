"""CI helper: run `lint-render.py --all` as COUNT parallel slices of the shipped assets.

usage: python lint_render_shard.py INDEX COUNT [lint-render options]

Slice 0 runs lint-render's own `--all` path with the asset list cut to its slice, so the checks that only
`--all` runs (mobile layouts, template exports) run once, there. The other slices pass their files as paths.
Together the slices render exactly the files `--all` renders and run every `--all` check. Run it from the
skill directory, as CI runs lint-render.py itself.
"""

import sys

from _helpers import load

index, count = int(sys.argv[1]), int(sys.argv[2])
lint = load("lint-render.py")
mine = lint.shipped_assets()[index::count]
if index == 0:
    lint.shipped_assets = lambda: mine
    sys.argv = ["lint-render.py", "--all", *sys.argv[3:]]
else:
    sys.argv = ["lint-render.py", *map(str, mine), *sys.argv[3:]]
sys.exit(lint.main())
