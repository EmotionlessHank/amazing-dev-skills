---
name: mac-cleanup
description: macOS system cleanup audit. Triggers when the user says "/mac-cleanup", "clean up my mac", "system cleanup", "disk cleanup", or "clean up apps". Automatically scans Applications, Homebrew, npm, pip, system caches, and outputs a structured cleanup recommendation report. Waits for user confirmation before executing any deletions.
version: 1.0.0
---

# /mac-cleanup — macOS System Cleanup Audit

Automatically scans installed applications, package managers, and system caches, outputs structured cleanup recommendations, and executes cleanup only after user confirmation.

---

## Trigger Conditions

Activate on any of the following keywords:
- `/mac-cleanup`
- `clean up my mac`, `system cleanup`, `disk cleanup`, `clean up apps`
- `mac cleanup`, `disk cleanup`

---

## Execution Steps

### Step 1: Scan Installed Applications (/Applications)

Find applications not opened in over a month and applications consuming significant disk space:

```bash
# Get app name, last used date, and physical size for all apps
find /Applications -maxdepth 2 -name "*.app" -exec mdls -name kMDItemLastUsedDate -name kMDItemDisplayName -name kMDItemPhysicalSize {} \; 2>/dev/null | paste - - - | sort

# List all apps sorted by disk usage
find /Applications -maxdepth 2 -name "*.app" -exec du -sm {} + 2>/dev/null | sort -rn
```

Analysis dimensions:
- **Not opened in over a month** (based on kMDItemLastUsedDate)
- **No recorded usage time** (kMDItemLastUsedDate is null)
- **Large footprint but low usage frequency**

### Step 2: Scan Homebrew

```bash
# Installed formulae and casks
brew list --formula
brew list --cask

# Check for orphaned dependencies
brew autoremove --dry-run

# Old versions and cache
brew cleanup --dry-run

# Cache size
du -sh $(brew --cache)

# Largest formula installations
du -sh /opt/homebrew/Cellar/* 2>/dev/null | sort -rh | head -15
```

### Step 3: Scan npm

```bash
# Global packages
npm list -g --depth=0

# Global packages disk usage
du -sh $(npm root -g)

# npm cache size
du -sh ~/.npm
```

### Step 4: Scan pip

```bash
# Installed packages
python3 -m pip list

# pip cache size
du -sh ~/Library/Caches/pip
```

### Step 5: Scan System Caches and Miscellaneous

```bash
# Top 15 directories in ~/Library/Caches by size
du -sh ~/Library/Caches/* 2>/dev/null | sort -rh | head -15

# ~/.cache size
du -sh ~/.cache

# Xcode DerivedData and Archives
du -sh ~/Library/Developer/Xcode/DerivedData ~/Library/Developer/Xcode/Archives 2>/dev/null

# Docker (if installed)
which docker &>/dev/null && docker system df 2>/dev/null || echo "Docker not installed"

# pnpm store
pnpm store status 2>/dev/null; du -sh ~/Library/Caches/pnpm 2>/dev/null

# yarn global packages
which yarn &>/dev/null && yarn global list 2>/dev/null
```

### Step 6: Output Cleanup Report

Compile the above data into a structured report using the following format:

---

#### Report Template

```
# macOS System Cleanup Report ({date})

## 1. Applications (/Applications)

### Not opened in over a month
| App | Last Used | Disk Usage | Recommendation |
|-----|-----------|------------|----------------|

### No recorded usage time
| App | Disk Usage | Recommendation |
|-----|------------|----------------|

### Other notable items
| App | Last Used | Disk Usage | Notes |
|-----|-----------|------------|-------|

## 2. Homebrew
| Item | Reclaimable Space | Cleanup Command |
|------|-------------------|-----------------|

### Large packages worth noting
| Package | Size | Recommendation |
|---------|------|----------------|

## 3. npm
| Item | Size | Notes |
|------|------|-------|

## 4. pip
| Package | Notes |
|---------|-------|

## 5. System Caches (~/Library/Caches)
| Cache Directory | Size | Recommendation |
|-----------------|------|----------------|

## 6. Miscellaneous (Xcode / Docker / pnpm / etc.)
| Item | Size | Cleanup Command |
|------|------|-----------------|

## Summary
| Category | Estimated Reclaimable | Risk Level |
|----------|-----------------------|------------|

### One-click safe cleanup commands (low-risk items)
(List all zero-risk cleanup commands here)
```

---

### Step 7: Wait for User Confirmation

After outputting the report, **do not automatically execute any cleanup operations**. Wait for the user to specify which items to clean, then execute them one by one.

When performing deletions:
- Apps under `/Applications`: try `rm -rf` first; if permission is denied (Mac App Store apps), prompt the user to manually long-press in Launchpad to delete
- Homebrew packages: use `brew uninstall <package>` or `brew cleanup`
- npm global packages: use `npm uninstall -g <package>`
- Cache directories: use `rm -rf <path>`
- pip packages: use `pip3 uninstall <package>`

---

## Notes

- Run all scan steps **in parallel** where possible to improve efficiency
- Mark the **risk level** of each cleanup item in the report (safe / low-risk / requires confirmation)
- **Never auto-execute deletions** — always wait for explicit user instruction
- For applications or packages whose purpose cannot be determined, mark as "requires confirmation" rather than recommending deletion
