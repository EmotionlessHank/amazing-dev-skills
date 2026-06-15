---
name: sync-tokens
description: Sync Figma Design Tokens. Triggers when the user says "/sync-tokens", "sync tokens", "update tokens", or "sync design variables". Accepts a path to a Figma-exported JSON file, copies it to tokens/figma/, runs pnpm sync-tokens to generate CSS variables and TS constants, and displays the diff.
version: 0.1.0
---

# Sync Figma Design Tokens

Sync design tokens from a Figma-exported JSON file into project code.

---

## Trigger Conditions

Activate on any of the following keywords:
- `/sync-tokens`
- `sync tokens`, `update tokens`, `update design variables`
- `sync tokens`, `update tokens`

---

## Parameters

The user must provide a path to a Figma-exported JSON file when invoking the skill. Supported formats:

```
/sync-tokens /path/to/Dark.tokens.json /path/to/Light.tokens.json
/sync-tokens /path/to/Dark.tokens.json          # Update Dark only
/sync-tokens /path/to/Light.tokens.json         # Update Light only
```

The filename must contain `Dark` or `Light` (case-insensitive) to determine the target slot.

---

## Behavior When No Arguments Are Provided

If the user invokes the skill **without providing any JSON file path**, respond with:

> Please provide the path to your Figma-exported JSON file, for example:
> ```
> /sync-tokens ~/Downloads/Dark.tokens.json ~/Downloads/Light.tokens.json
> ```
>
> **How to export the JSON file:**
> 1. In Figma, open the right-hand panel → Local variables
> 2. Export → select JSON format
> 3. Export the Dark and Light collections separately

Then **stop execution** — do not proceed to subsequent steps.

---

## Execution Steps

### Step 1: Validate files

- Confirm the provided file paths exist
- Determine type (Dark / Light) from the filename
- If the filename does not indicate the type, ask the user

### Step 2: Copy JSON to the project

```bash
# Copy to the appropriate location based on type
cp <dark-json-path>  tokens/figma/Dark.tokens.json
cp <light-json-path> tokens/figma/Light.tokens.json
```

### Step 3: Run the sync script

```bash
pnpm sync-tokens
```

This command automatically generates:
- `app/design-tokens.css` — CSS custom properties (`:root` for Dark + `[data-theme="light"]` for Light)
- `lib/design-tokens.ts` — TypeScript constant exports

### Step 4: Show the diff

```bash
git diff --stat
git diff app/design-tokens.css lib/design-tokens.ts
```

Show the user:
- How many tokens changed
- Which variables were added, removed, or modified
- If there are `@deprecated` legacy tokens in `tailwind.config.ts` that need cleanup, flag them

### Step 5: Confirm commit

Ask the user whether to commit the changes. If confirmed, create a commit following the project's Git conventions.

---

## Artifact Relationship Diagram

```
tokens/figma/Dark.tokens.json   ─┐
                                  ├─→ pnpm sync-tokens ─┬─→ app/design-tokens.css (CSS variables)
tokens/figma/Light.tokens.json  ─┘                      ├─→ lib/design-tokens.ts  (TS constants)
                                                         └─→ tailwind.config.ts references via var()
```

---

## Notes

- `app/design-tokens.css` and `lib/design-tokens.ts` are auto-generated files — **do not edit them manually**
- `tailwind.config.ts` already references CSS variables via `var()` and typically does not need manual changes
- If Figma introduces an entirely new token category that is not in the existing `CATEGORY_PREFIX_MAP`, update the mapping in `scripts/sync-tokens.ts` as well
