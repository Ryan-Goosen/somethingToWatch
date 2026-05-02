# Something To Watch

> Get notified of the latest sports matches directly from your terminal.

---

## About

### What it does
A terminal application that tells you when there's a sports match happening. Currently supports F1 races; football integration is planned.

### Why I built it
I kept forgetting when my football team plays games, so I decided to make this terminal application to notify me whenever there's a match.

### Who it's for
Sports fans who want quick terminal-based notifications about upcoming matches without checking multiple apps or websites.

**Note:** This project is currently on hold — only the F1 section is functional.

---

## Built With

| Category | Tool |
| -------- | ---- |
| **Language** | Python |
| **Framework** | None (CLI App) |
| **Libraries** | requests |

---

## Getting Started

### Prerequisites

- Python 3.13+
- uv

### Installation

1. Clone the repo:
```bash
git clone https://codeberg.org/Ryan-Goosen/somethingToWatch.git
```

2. Navigate into the project:
```bash
cd somethingToWatch
```

3. Setup environment:
```bash
uv venv
uv pip install -e .
```

4. Run the project:
```bash
python3 main.py
```

---

## Usage

Currently supports F1 race date checking:

```bash
python3 main.py
```

Football support coming in a future update.

---

## License

Distributed under the GPL-3.0 License. See `LICENSE` for more information.

---

## Acknowledgments

- [OpenF1 API](https://openf1.org/) for F1 race data
