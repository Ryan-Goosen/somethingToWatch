# Something To Watch

---

## Project Identity

| Field | Value |
| ----- | ----- |
| **Name** | Something To Watch |
| **Project ID** | STW-2025-003 |
| **Owner** | Ryan Goosen |
| **Date Created** | 2025-01-15 |
| **Last Updated** | 2026-05-02 |

---

## Vision & Purpose

**Elevator Pitch:**
Get notified of the latest sports matches directly from your terminal - never miss a game again.

**Long-Term Vision:**
A terminal-based sports notification system with live updates, alarms before matches, and support for multiple sports (F1, football, etc.).

**Success Metrics:**
- [x] F1 race data integration
- [ ] Football match data integration
- [ ] Terminal notifications/alarms
- [ ] Live score updates

---

## Tech Stack

| Category | Tools / Languages |
| -------- | ----------------- |
| **Core Language** | Python |
| **Framework** | None (CLI App) |
| **Libraries** | requests |
| **Tools** | VS Codium, UV |
| **Version Control** | [Codeberg](https://codeberg.org/Ryan-Goosen/somethingToWatch) |

---

## Current State

**Phase:** On Hold -> Looking for valid API
**Progress:** 30%

**Recent Wins:**
- [x] Integrated OpenF1 API for F1 race data
- [x] Basic data fetching structure

**Blockers:**
- [ ] Finding a free football API that doesn't require auth/account

---

## Roadmap

### Main Objectives

1. **Setup** *(Partial)*
   - [x] Get F1 race date data
   - [ ] Get football date data

2. **Core Features** *(On Hold)*
   - [ ] Detect if match is happening today/this week
   - [ ] Show match outcomes for past games
   - [ ] Create alarm for upcoming matches
   - [ ] Return recent match scores

3. **Polish** *(Backlog)*
   - [ ] Pretty TUI interface
   - [ ] Customizable settings
   - [ ] Multiple sport support

4. **Live Updates** *(Future)*
   - [ ] Live score updates during matches
   - [ ] Terminal notifications

### Immediate Next Steps
1. Research free football APIs without auth
2. Evaluate API options (API-Football, Football-Data.org, etc.)
3. Resume development once football API found

---

## Project Structure

```
/somethingToWatch
├── main.py                  # Entry point
├── helper_functions/        # Utility functions
├── sport_functions/         # Sport-specific logic
│   └── f1.py               # F1 integration
├── planning/               # Planning documents
└── pyproject.toml          # UV configuration
```

---

## Notes & Decisions

**Key Choices:**
- Using OpenF1 API for F1 data (no auth required)
- Terminal-first approach for developers
- Planning to support multiple sports

**Backlog / Ideas:**
- Add support for other sports (rugby, cricket, etc.)
- Web dashboard option
- Mobile notifications via pushover

**Debug Log:**

---

## Visuals

[Attach or link to mockups, screenshots, or diagrams]
