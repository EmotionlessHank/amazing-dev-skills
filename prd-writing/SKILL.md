---
name: prd-writing
description: Write production-grade Product Requirements Documents (PRD) following Oddfi's proven PM writing methodology. Use this skill when the user asks to write, draft, review, or improve a PRD, feature spec, or product requirements document. Covers Web3/fintech and general product domains.
---

# PRD Writing Skill — Oddfi PM Documentation Methodology

This skill is distilled from two high-quality PRDs in the Oddfi project (Sign in-Deposit and Markets Page). It applies to Web3 products, fintech, and any scenario requiring high-precision product documentation.

---

## I. Document Structure (Standard Structure)

Choose between the "heavyweight" or "medium-weight" template based on feature complexity:

### Heavyweight PRD (cross-module / on-chain interactions / multi-stakeholder)

```
1. Version Log            — version number + date + notes (table)
2. Background             — one-sentence context + objectives (numbered list) + executive summary (key steps table)
3. Requirements           — split by functional module (3.1 / 3.2 ...), each module contains:
   3.x.1 Interaction Flow  — prototype screenshots / competitor screenshots
   3.x.2 Technical Constraints — comparison tables (e.g., Wallet type matrix)
   3.x.3 Requirement Details   — expanded per phase (see "Phase-based Drill-down" pattern)
   3.x.4 Edge Cases        — collected separately for all edge cases
   3.x.5 Supplemental Rules — categorized by dimension (general principles / security / UX)
   3.x.6 Business Constraints — gas fees, rates, limits, etc.
4. Flowchart              — complete end-to-end flowchart
   4.1 Restrictions        — IP / region / compliance
   4.2 Edge Scenarios      — network errors, timeouts, retry strategies
5. Analytics Tracking     — event definitions per business module, structured as tables
6. Development Schedule   — detailed schedule table + Gantt chart + Todo
```

### Medium-weight PRD (single page / single feature module)

```
1. Objective              — one sentence describing what to build
2. Requirements           — prototype screenshot + zone-by-zone breakdown
   2.x Sub-module          — element table + rules + calculation formulas
3. Notes                  — edge cases / items to be confirmed
```

---

## II. Six Core Writing Patterns

### Pattern 1: "Display Content + Rules" Two-Column Separation (Most Important)

**Always separate "what the user sees" from "how the system works".**

```markdown
### 1. First Entry to Page

**Display Content**:
- Login/register modal
- Login entry buttons: email, Google, Telegram, wallet
- Promo code input field
- Main CTA button
- Terms of service / privacy policy links

**Rules**:
- Show this modal by default when user enters without being logged in
- Sign in / Sign up share a single entry page — do not split into two separate pages
- After the user completes auth via any method, proceed directly to the onboarding deposit page / connected state page
```

**Why it works**: Developers read "Display Content" to know what UI to build, and "Rules" to know what logic to write — zero ambiguity.

---

### Pattern 2: Phase-Based Drill-Down

Organize content by time slices of the user journey; each phase is self-contained.

```markdown
| Phase | Description |
|-------|-------------|
| 1. Pre-trade | Asset selection, amount input, balance validation |
| 2. Trade confirmation | Token approval → transaction approval (two steps) |
| 3. Post-trade | Success: asset update + block explorer link; Failure: reason + retry |
```

Expand each phase further using the "Display Content + Rules" two-column format.

**Use cases**: Any user flow with defined steps (registration, payment, order placement, deposit).

---

### Pattern 3: Table-Driven Comparison

**Force all structured information into tables — never prose.**

**Field description table** (UI element breakdown):
```markdown
| Field | Description | Example |
|-------|-------------|---------|
| Match name | Home VS Away | Braga VS Ferencvarosi |
| Odds | Current odds, blue text | 1.53 |
| Amount input | User enters bet amount, **each bet slip is independent** | Amount |
```

**Comparison matrix** (technology selection / competitor analysis):
```markdown
| Wallet | Type | When to use | Wallet Type | Support Chain |
|--------|------|-------------|-------------|---------------|
| EOA Wallet | Standard Web3 wallet | User pays gas for Swap | EOA | EVM, SOL, Tron |
| Web3 Wallet | Metamask, OKX... | Browser wallet for account creation | GNOSIS_SAFE | Note: ... |
```

**State matrix** (permissions / fees):
```markdown
| Scenario | Gas fee required | Who pays |
|----------|------------------|----------|
| Deposit | ✅ | User |
| Create Proxy Wallet | ❌ | Not supported in v1 |
```

---

### Pattern 4: Edge Cases as First-Class Citizens

**Do not weave exception handling into the happy path — collect it separately.**

```markdown
### 3.1.4 Edge Cases

| Scenario | Description |
|----------|-------------|
| Auth cancelled | User closes the authorization modal, cancels approval, or rejects signature → return to login page, show toast `Authorization cancelled` |
| Auth failed | Third-party API failure, system error, network error → return to login page, show toast `Login failed, please try again` |
| Account conflict | Third-party credential already bound to another account → block auto-registration; prompt user to switch method or contact support |
| Token expired | Logged in but token has expired → clear local auth state, redirect to login page |
| Binding failed | Login succeeded but promo code / wallet binding post-processing failed → do not affect primary account login, but notify user that feature is inactive |
```

**Why it works**: Developers can complete the happy path first, then handle all edge cases systematically — nothing gets missed.

---

### Pattern 5: Domain Education Inline

**When a feature involves a specialized domain (sports betting, finance, on-chain interactions), explain concepts directly in the PRD using plain language and concrete examples.**

```markdown
#### 1x2 (Match Result)

The simplest bet type — pick who wins. Three options: home win, draw, away win.
For example: Brazil vs France. You bet on Brazil. Odds 2.10. Stake 100 → payout 210.

#### Asian Handicap

Give the underdog a head start to balance the skill gap. For example, Brazil gives France a 0.5-ball handicap — Brazil must win by at least 1 goal for your bet to win. Eliminates the draw outcome; result is win or lose only.

**Scenario: Brazil vs Saudi Arabia**
Brazil is far stronger, so 1x2 odds are uninteresting (Brazil win odds might be just 1.10).
The handicap's purpose is to **make Brazil's task harder**, leveling the playing field and producing more attractive odds.

**What does Brazil -1.5 mean:**
Brazil must win by **at least 2 goals** for your bet to win.
- Brazil wins 3:0 → you win ✅
- Brazil wins 1:0 → you lose ❌ (won, but not by enough)
```

**Use cases**: When developers are not domain experts, the PRD needs to double as a "mini training manual".

---

### Pattern 6: Analytics Tracking as First-Class Citizens

Dedicated section with a structured table defining every tracking event.

```markdown
## 5. Analytics Tracking

### 1. Deposit

| Business | Event | Behavior Type | Action | Site | page_id | block_id | location_id | Business Params | Track Impression | Trigger Timing |
|----------|-------|---------------|--------|------|---------|----------|-------------|-----------------|------------------|----------------|
| Deposit | Modal impression | Event impression | Impression | WebsitWallet | Deposit | Deposit | 1 | | 1 | |
| | Click event | | Click | | | | | Param: WalletAddress | | |
```

**Field conventions**:
- `Behavior Type`: Event impression / Result event
- `Action`: Impression / Click / Success / Failure
- `Business Params`: Enum values use `0/1/2/3` + meaning mapping (e.g., `0:Google; 1:TG; 2:Walletkit`)

---

## III. Visual Marking System (Typography Conventions)

| Marker | Meaning | When to Use |
|--------|---------|-------------|
| ~~strikethrough~~ | Not building / deprecated | Keep context when cutting features; mark as not in scope |
| **red text** | To be confirmed / important warning | Points that require further discussion between product/engineering |
| ✅ / ❌ | Supported / Not supported | Feature matrix, comparison tables |
| → arrow | Flow transition | Step connectors (`frontend sends nonce → user signs → backend verifies → login succeeds`) |
| `code block` | Button copy / field placeholder / toast copy | Precisely define UI copy (`Enter promo code`) |
| > blockquote | Notes / remarks | Supplemental info that doesn't interrupt the main flow |
| **bold** | Key decisions / emphasis | Highlight rules that must be followed |

---

## IV. Language Style Rules

1. **Bilingual anchoring**: Technical terms, button copy, and field names stay in English (Sign in, Deposit, Token, Gas fee); descriptions are written in the team's primary language
2. **Extreme conciseness**: Do not write "We believe users might need" — write "Display XXX" or "Rule: XXX" directly
3. **No filler**: Delete phrases like "User experience is paramount" or "We are committed to building"
4. **One rule per bullet**: Each bullet point says exactly one thing
5. **Start with a verb**: Display, Call, Evaluate, Return, Notify, Clear, Prohibit
6. **Make TBDs explicit**: No ambiguity — use a red label or `TBD` tag to clearly mark unresolved items

---

## V. Flowchart Standards

**Complex flows must include a complete flowchart at the end of the document** (not scattered across individual sections).

Flowchart elements:
- Use color blocks to distinguish different phases (e.g., Sign in/up in one color block, deposit in another)
- Diamonds = decision nodes ("Does the user already have a wallet?", "Is it a platform token?")
- Rectangles = action steps
- Branches are clear; Y/N labels are explicit

---

## VI. Supplemental Rules Closing Pattern

At the end of each major feature module, use a categorized table to collect cross-scenario general constraints:

```markdown
### 3.1.5 Supplemental Rules

| Category | Rule |
|----------|------|
| General principle | Sign in / Sign up should share as much frontend flow as possible; avoid complex branching |
| Security requirement | Third-party login must validate the authorization token |
| Security requirement | Wallet login must verify the signature; connecting the wallet alone is not sufficient for login |
| UX requirement | All authentication failures must display a clear error message |
| UX requirement | After successful login, page navigation must be deterministic; do not leave the user on a stateless intermediate page |
```

---

## VII. How to Use

### When the user says "write a PRD":

1. **Confirm feature complexity** → choose heavyweight or medium-weight template
2. **List user journey phases** → split into sections by phase
3. **Apply "Display Content + Rules" two-column format to each phase** → zero ambiguity
4. **All structured information in tables** → field tables, comparison tables, state matrices
5. **Collect edge cases separately** → do not interleave with the happy path
6. **Embed explanations of domain concepts** → developers can understand the business semantics
7. **Dedicated analytics tracking section** → event granularity down to the button level
8. **Draw a flowchart for complex flows** → close out at the end of the document
9. **Visual marking system** → consistent use of strikethrough, bold, checkmarks
10. **Schedule table (optional)** → Gantt chart + responsibility assignments

### When the user says "review this PRD":

Review checklist:
- [ ] Does every feature point have the "Display Content + Rules" two-column format?
- [ ] Are edge cases in a dedicated section? Are cancel / failure / conflict / timeout / degradation scenarios covered?
- [ ] Is structured information in tables rather than prose?
- [ ] Are TBD items explicitly marked with a red label or tag?
- [ ] Are button copy, toast copy defined precisely in code blocks?
- [ ] Is there a flowchart at the end?
- [ ] Are analytics events defined?
- [ ] Are domain-specific concepts explained in plain language?
