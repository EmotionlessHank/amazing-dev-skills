---
name: disk-cleanup
description: Developer storage disk cleanup. Triggers when the user says "/disk-cleanup", "disk is full", "hard drive is almost full", "clean up worktrees", or "out of space". Uses a layered investigation to locate the largest consumers (worktrees/Docker/caches/user files), performs safety checks per category before deletion, with zero data loss throughout. Pairs with mac-cleanup (system app audit).
version: 1.0.0
---

# /disk-cleanup — Developer Storage Disk Cleanup

Four-phase process: **layered investigation to locate top consumers → safety checks → categorized cleanup → verify reclaimed space**.

Core principles:
- Investigation and cleanup are two separate steps — **produce the report first, only proceed after user sign-off**
- Every category has a corresponding safety check before deletion — err on the side of deleting less rather than deleting incorrectly
- Division of responsibility with [mac-cleanup](../mac-cleanup): this skill handles **developer storage** (git worktrees, Docker, dev caches, user media, temp repos); mac-cleanup handles **system layer** (apps, Homebrew/npm/pip, Xcode DerivedData). Run both together for maximum coverage when disk space is critically low.

---

## Trigger Conditions

Activate on any of the following keywords:
- `/disk-cleanup`
- `disk is full`, `hard drive usage`, `out of space`, `clean up worktrees`
- `disk full`, `worktree cleanup`

---

## Phase 1: Layered Investigation (read-only, report first)

```bash
df -h /                                          # Total disk + available (APFS: check Avail, not Capacity %)
du -xsh ~/* 2>/dev/null | sort -rh | head -20    # Top consumers in home directory
du -xsh ~/Library/* | sort -rh | head -20        # Library is usually the largest
du -xsh ~/Library/"Application Support"/* ~/Library/Containers/* ~/Library/Caches/* | sort -rh
du -xsh {WORK_DIR}/* | sort -rh                  # Per-project directories
```

Common top consumers (from real-world experience, especially front-end projects):
- **`<project>/.claude/worktrees/`** — accumulated Claude Code worktrees; each front-end project carries 1.5–2 GB of `node_modules` + `.next`, often the single largest reclaimable source (real-world case: 32 worktrees in one project = 22 GB)
- **`~/Library/Containers/com.docker.docker`** — Docker build cache + unused images (real-world: up to 19 GB reclaimable)
- **`~/Library/Caches/`** — Spotify, JetBrains, go-build, ms-playwright, Homebrew — all safe to rebuild
- **`~/Movies`**, **`~/Downloads`**, project directories with "temp" in the name — require user decision

Sort the report by "reclaimable size × safety level", indicate which items can be auto-cleaned and which require user approval, **wait for user to confirm scope before entering Phase 2**.

---

## Phase 2: Safety Checks (hard gates before deletion)

### Git worktrees

1. `git worktree list` to identify **registered** worktrees; the actual directory count often exceeds the registered count (orphan directories exist)
2. ⚠️ **Trap: git output lies for orphan directories** — running `git -C <dir> status/log` on an unregistered directory falls back to the main repo and reports "main / committed today / 0 changes" — all data from the main repo. Orphan directory activity can only be assessed via **file mtime**
3. ⚠️ **Trap: `git merge-base --is-ancestor` always reports "not merged" after squash merges** — do not use this as a cleanup criterion. Use these three checks instead:
   - `git -C <wt> status --porcelain` is empty (no uncommitted changes)
   - `git rev-list --count origin/<branch>..<branch>` to check unpushed commits (reports "no remote branch" = never pushed, flag for attention)
   - `git worktree remove` only deletes the working copy — **branch refs are always preserved in the main repo** and can be recreated at any time
4. Activity assessment: for feature branches check `git log -1 --format=%cs`; for worktrees on main and orphan directories check actual file mtime (excluding node_modules)
5. Orphan directories (`git worktree remove` reports "is not a working tree"): inspect each with `ls -A` — **only delete with `rm -rf` if they contain only build artifacts and session state such as `.next`, `node_modules`, `.omc`, `.progress`, `tsconfig.tsbuildinfo`**; stop immediately and report if source files are found

### Docker

```bash
docker system df            # Check the RECLAIMABLE column
docker builder prune -af    # Build cache (usually the biggest consumer)
docker image prune -af      # Unused images
# Volumes — do NOT touch — contain database data
```

`Docker.raw` is a sparse file; space is gradually returned to the system after pruning. To reclaim space immediately, restart Docker Desktop.

### Application caches

Before deleting, run `pgrep -fl <app>` to confirm the application is not running (deleting JetBrains cache while running may corrupt indexes). Safe to clean: JetBrains, com.spotify.client, go-build, ms-playwright, Homebrew entries under `~/Library/Caches/`.

### User files (Movies / Downloads / temp project repos)

1. **Always `ls -lhR` to inspect actual contents before deleting** — never delete based on directory name alone. Real-world case: a "personal movie" folder turned out to be downloaded anime (deletable), but the same directory contained CapCut project files (user-created content that must be kept and flagged)
2. Downloaded movies/media can be deleted (re-downloadable); **user-created assets (CapCut projects, screen recordings, photos) must be kept** — ask if uncertain
3. **Temporary git repos**: first run `git branch -vv` + `git log --branches --not --remotes` to check for unpushed branches; if found, run `git push <remote> --all` to archive everything to remote — **only delete local copy after confirming the push succeeded**
4. Push reports `Repository not found` / 403 / 404 → multi-account scenario: `gh auth status` to list accounts → switch to the account that can see the repo → retry → **switch back to the original default account after success**

---

## Phase 3: Execution

- Run large `rm -rf` operations and docker prune in the background in parallel
- Batch delete worktrees: use a case statement to skip items on the keep list, fall back to `git worktree remove --force` if the standard command fails (only after confirming no uncommitted changes), then run `git worktree prune`

---

## Phase 4: Verify and Report

```bash
df -h /                # Compare Avail before and after cleanup
du -xsh <each target>  # Per-item verification
```

Report format: total space reclaimed + itemized breakdown (each item: how much was reclaimed, what safety checks were performed, what was kept and why).

---

## Success Criteria

- Available disk space has increased significantly and matches the sum of itemized reclaim figures
- Zero data loss: every deleted item passed its corresponding safety check (no uncommitted / unpushed changes / no user-created content)
- All user-decision items (media files, temp repos) were reported with their contents before execution

## Preventing Recurrence

Worktree accumulation will happen again. Recommended practice: run `git worktree remove` right after merging a feature branch, or re-run the investigation phase of this skill every few weeks.

## Real-world Results

First run (2026-06): available disk space went from 35 GB to 97 GB — approximately 62 GB reclaimed (worktrees 20 GB + Docker 19 GB + caches 9 GB + media/temp repos 24 GB), zero data loss (15 unpushed branches archived to a remote private repo before local deletion).
