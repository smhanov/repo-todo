#!/usr/bin/env python3
"""board.py — mechanical board management for repo-todo (.plans/todo.md).

Hand-editing the board is how duplicate rows happen. This script does the
three mechanical operations safely and identically on every machine:

  validate            check structure, duplicate IDs, plan links, conventions
  next-id             print the next free task ID (numeric max + 1)
  move ID SECTION     move a row between sections; idempotent, never duplicates

Examples:
  python3 board.py validate
  python3 board.py next-id
  python3 board.py move T007 in-progress --notes "owner=hermes; updated=2026-10-27T17:00Z"
  python3 board.py move T007 done --priority P1 --notes "completed=2026-10-27"

Sections: todo | in-progress | blocked | done (several aliases accepted).

Exit codes: 0 = OK, 1 = validation found problems, 2 = usage/IO error.
Stdlib only; runs on any Python 3.6+ (Linux, macOS, anywhere).
"""

import argparse
import os
import re
import sys
import tempfile

# ---------------------------------------------------------------------------
# Constants

BOARD_REL_PATH = os.path.join(".plans", "todo.md")

# Canonical section key -> heading text used in the template.
SECTION_TITLES = [
    ("todo", "Todo"),
    ("in-progress", "In Progress"),
    ("blocked", "Blocked"),
    ("done", "Done"),
]

# CLI section names -> canonical key.
SECTION_ALIASES = {
    "todo": "todo", "t": "todo", "to-do": "todo",
    "in-progress": "in-progress", "inprogress": "in-progress",
    "in_progress": "in-progress", "in progress": "in-progress",
    "progress": "in-progress", "ip": "in-progress", "wip": "in-progress",
    "doing": "in-progress", "active": "in-progress",
    "blocked": "blocked", "block": "blocked", "waiting": "blocked",
    "done": "done", "complete": "done", "completed": "done", "closed": "done",
}
# Heading text (lowercased) -> canonical key.
HEADING_TO_KEY = {title.lower(): key for key, title in SECTION_TITLES}

EXPECTED_HEADER_CELLS = ["Priority", "ID", "Description / plan", "Notes"]
VALID_PRIORITIES = ("P0", "P1", "P2")

CELL_SPLIT_RE = re.compile(r"(?<!\\)\|")
ID_CELL_RE = re.compile(r"^\s*T(\d+)\s*$")
HEADING2_RE = re.compile(r"^##\s+(.+?)\s*$")
HEADING1_RE = re.compile(r"^#\s+Tasks\s*$")
SEP_ROW_RE = re.compile(r"^\s*\|[\s:\-|]+\|?\s*$")
ROW_LINE_RE = re.compile(r"^\s*\|.*\|\s*$")
PLAN_FILENAME_RE = re.compile(r"^T(\d+)")

E, W = "ERROR:", "WARN:"


def err(msg):
    print("%s %s" % (E, msg))


def warn(msg):
    print("%s %s" % (W, msg))


# ---------------------------------------------------------------------------
# Small helpers

def split_cells(line):
    """Split a table row into cells. '|' inside a cell must be escaped as \\|."""
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [c.strip() for c in CELL_SPLIT_RE.split(body)]


def normalize_id(raw):
    """Accept T007, t7, 7, 007 -> (canonical, number). None if not an ID."""
    s = re.sub(r"[^0-9A-Za-z]", "", str(raw)).upper()
    if s.startswith("T"):
        s = s[1:]
    if not s.isdigit():
        return None
    num = int(s)
    return "T%03d" % num if num < 1000 else "T%d" % num, num


def row_sort_key(cells):
    """Sort key: priority (P0 first), then numeric ID."""
    p = cells[0].strip().upper()
    pnum = int(p[1:]) if re.match(r"^P\d+$", p) else 9
    m = ID_CELL_RE.match(cells[1])
    inum = int(m.group(1)) if m else 10 ** 9
    return (pnum, inum)


def build_row_line(cells, newline="\n"):
    return "| " + " | ".join(c.strip() for c in cells) + " |" + newline


def board_path(root):
    return os.path.join(root, BOARD_REL_PATH)


def read_board(root):
    path = board_path(root)
    if not os.path.isfile(path):
        return None, path
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    if text and not text.endswith("\n"):
        text += "\n"
    return text.split("\n")[:-1], path


def write_board(path, lines):
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".todo-", suffix=".md", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)  # atomic on POSIX and Windows
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def section_key_from_heading(title):
    return HEADING_TO_KEY.get(title.strip().lower())


# ---------------------------------------------------------------------------
# Parsing

class Section(object):
    def __init__(self, key, heading_idx):
        self.key = key
        self.heading_idx = heading_idx
        self.table_start = -1    # first table line index (header); -1 = no table
        self.sep_idx = -1
        self.rows = []            # list of dict(idx, cells)
        self.problems = []        # malformed table lines: (idx, why)


def parse_board(lines):
    """Structural parse: locate sections and their table rows.

    Returns (sections_by_key, section_order, stray_rows, problems) where
    stray_rows are T-ID table rows under unknown headings, and problems are
    (idx, message) structural problems found during parsing.
    """
    sections = {}
    order = []
    current = None
    stray_rows = []
    problems = []

    for i, line in enumerate(lines):
        m2 = HEADING2_RE.match(line)
        if m2:
            key = section_key_from_heading(m2.group(1))
            if key:
                if key in sections:
                    problems.append((i, "duplicate section heading '## %s'" % m2.group(1).strip()))
                    current = None
                    continue
                current = Section(key, i)
                sections[key] = current
                order.append(key)
            else:
                current = None
            continue

        if not ROW_LINE_RE.match(line):
            continue

        if current is None:
            cells = split_cells(line)
            if len(cells) >= 2 and ID_CELL_RE.match(cells[1]):
                stray_rows.append((i, cells))
            continue

        if current.table_start < 0:
            cells = split_cells(line)
            if SEP_ROW_RE.match(line) and not any(c for c in cells):
                problems.append((i, "table separator without a header row"))
                continue
            if [c.lower() for c in cells][:1] == ["priority"]:
                current.table_start = i
                continue
            problems.append((i, "expected header row '%s', found: %s"
                             % (" | ".join(EXPECTED_HEADER_CELLS), line.strip())))
            current.table_start = i  # avoid repeating this error for every line
            continue

        if current.sep_idx < 0:
            if SEP_ROW_RE.match(line):
                current.sep_idx = i
                continue
            # A second header-ish line or misformatted separator.
            cells = split_cells(line)
            if [c.lower() for c in cells][:1] == ["priority"]:
                problems.append((i, "duplicate header row"))
                continue
            current.problems.append((i, "missing separator row after header"))
            # fall through: try to parse as data row

        cells = split_cells(line)
        if len(cells) == 4 and ID_CELL_RE.match(cells[1]):
            current.rows.append({"idx": i, "cells": cells})
        elif SEP_ROW_RE.match(line) and not any(cells):
            problems.append((i, "duplicate separator row"))
        else:
            current.problems.append((i, "malformed table row (need 4 cells: Priority | ID | Description / plan | Notes)"))

    return sections, order, stray_rows, problems


def all_rows(sections):
    for key, _ in SECTION_TITLES:
        sec = sections.get(key)
        if sec:
            for row in sec.rows:
                yield key, row


# ---------------------------------------------------------------------------
# validate

def cmd_validate(root, _args):
    """Structural and semantic checks; exit 1 if any ERROR was printed."""
    lines, path = read_board(root)
    if lines is None:
        err("board not found: %s (run from the checkout root, or pass --root)" % path)
        return 2

    errors = []

    def e(msg):
        err(msg)
        errors.append(msg)

    sections, order, stray_rows, problems = parse_board(lines)

    if not any(HEADING1_RE.match(l) for l in lines):
        warn("no '# Tasks' H1 heading found")

    for key, title in SECTION_TITLES:
        if key not in sections:
            e("missing section '## %s' (keep empty tables)" % title)
    for idx, msg in problems:
        e("line %d: %s" % (idx + 1, msg))
    for idx, _cells in stray_rows:
        e("line %d: task row outside the four board sections" % (idx + 1))

    seen = {}
    plans_dir = os.path.join(root, ".plans")

    for key, row in all_rows(sections):
        cells = row["cells"]
        where = "line %d" % (row["idx"] + 1)
        canon = normalize_id(cells[1])
        pid = canon[0] if canon else cells[1].strip().upper()
        num = canon[1] if canon else None

        if cells[0].strip().upper() not in VALID_PRIORITIES:
            e("%s: invalid priority '%s' (must be one of %s)"
              % (where, cells[0].strip() or "—", "/".join(VALID_PRIORITIES)))
        if num is None:
            e("%s: bad ID cell '%s'" % (where, cells[1].strip()))
        else:
            if len(re.sub(r"\D", "", cells[1])) < 3:
                e("%s: ID %s is not zero-padded to at least 3 digits" % (where, pid))
            if pid in seen:
                e("%s: duplicate row for %s (first seen on line %d in '%s')"
                  % (where, pid, seen[pid][1] + 1, seen[pid][0]))
            else:
                seen[pid] = (key, row["idx"])

        # Plan file must exist, exactly one per ID.
        if num is not None:
            nums = plan_file_nums(plans_dir)
            matches = [fname for n, fname in nums if n == num]
            if not matches:
                e("%s: no plan file .plans/%s-*.md for row %s" % (where, pid, pid))
            elif len(matches) > 1:
                e("%s: %d plan files for %s: %s" % (where, len(matches), pid, ", ".join(sorted(matches))))
            m = re.search(r"\((T[^)]+\.md)\)", cells[2])
            if m and os.path.isdir(plans_dir) and not os.path.exists(os.path.join(plans_dir, m.group(1))):
                warn("%s: description links to .plans/%s which does not exist" % (where, m.group(1)))

        notes = cells[3].strip()
        if key == "in-progress" and "owner=" not in notes:
            warn("%s: In Progress row %s has no owner= in Notes" % (where, pid))
        if key == "blocked" and notes in ("", "—"):
            warn("%s: Blocked row %s has no blocker/unblock action in Notes" % (where, pid))
        if key == "done" and "completed=" not in notes:
            warn("%s: Done row %s has no completed= date in Notes" % (where, pid))

    # Orphan plan files: plan exists, board row does not.
    for num, fname in plan_file_nums(plans_dir):
        canon = ("T%03d" % num) if num < 1000 else ("T%d" % num)
        if canon not in seen:
            e("plan file .plans/%s has no board row" % fname)

    # Sort convention in open sections (priority, then ID).
    for key in ("todo", "in-progress", "blocked"):
        sec = sections.get(key)
        if not sec:
            continue
        keys = [row_sort_key(r["cells"]) for r in sec.rows]
        if keys != sorted(keys):
            warn("section '%s' is not sorted by priority, then ID" % dict(SECTION_TITLES)[key])

    for sec in sections.values():
        for idx, msg in sec.problems:
            e("line %d: %s" % (idx + 1, msg))

    n = sum(len(s.rows) for s in sections.values())
    if errors:
        print("FAILED: %d error(s), board has %d row(s) — %s" % (len(errors), n, path))
        return 1
    print("OK: %d row(s), no problems found — %s" % (n, path))
    return 0


# ---------------------------------------------------------------------------
# next-id

def plan_file_nums(plans_dir):
    """[(num, filename)] for every .plans/T<num>*.md plan file."""
    out = []
    if os.path.isdir(plans_dir):
        for fname in sorted(os.listdir(plans_dir)):
            if not fname.endswith(".md"):
                continue
            m = PLAN_FILENAME_RE.match(fname)
            if m:
                out.append((int(m.group(1)), fname))
    return out


def collect_ids(plans_dir):
    """Numeric IDs used by plan filenames. Returns (max_num, source_desc)."""
    best, desc = 0, None
    for num, fname in plan_file_nums(plans_dir):
        if num > best:
            best, desc = num, fname
    return best, desc


def board_max_id(sections):
    best = 0
    for _key, row in all_rows(sections):
        canon = normalize_id(row["cells"][1])
        if canon and canon[1] > best:
            best = canon[1]
    return best


def cmd_next_id(root, _args):
    lines, path = read_board(root)
    sections = {}
    if lines is not None:
        sections, _order, _stray, _problems = parse_board(lines)
    else:
        print("%s board %s not found (treating as empty; use Setup to create it)" % (W, path), file=sys.stderr)

    plan_max, plan_desc = collect_ids(os.path.join(root, ".plans"))
    board_max = board_max_id(sections)
    nxt = max(plan_max, board_max) + 1

    print("%s" % ("T%03d" % nxt if nxt < 1000 else "T%d" % nxt))
    if plan_desc:
        print("%s highest plan file: %s" % (W, plan_desc), file=sys.stderr)
    if board_max:
        print("%s highest board row: T%03d" % (W, board_max), file=sys.stderr)
    print("%s claim it by creating the plan file first, then re-run next-id" % (W,), file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# move

def resolve_section(raw):
    key = SECTION_ALIASES.get(str(raw).strip().lower().replace("_", "-").replace(" ", "-"))
    if key is None:
        # allow "in progress" with arbitrary spacing
        key = SECTION_ALIASES.get(re.sub(r"[\s_\-]+", " ", str(raw).strip().lower()))
    return key


def cmd_move(root, args):
    canon = normalize_id(args.id)
    if not canon:
        err("not a task ID: '%s' (expected like T007)" % args.id)
        return 2
    pid, num = canon

    target = resolve_section(args.section)
    if target is None:
        err("unknown section '%s' (use todo | in-progress | blocked | done)" % args.section)
        return 2

    if args.priority is not None and args.priority.strip().upper() not in VALID_PRIORITIES:
        err("invalid priority '%s' (must be one of %s)" % (args.priority, "/".join(VALID_PRIORITIES)))
        return 2

    lines, path = read_board(root)
    if lines is None:
        err("board not found: %s (run from the checkout root, or pass --root)" % path)
        return 2

    sections, _order, _stray, _problems = parse_board(lines)

    matches = [(key, row) for key, row in all_rows(sections)
               if normalize_id(row["cells"][1]) == (pid, num)]
    if not matches:
        err("%s is not on the board (never invent rows — capture it first)" % pid)
        return 2

    # Keeper: a row already in the target section, else the first match.
    keeper_idx = 0
    for i, (key, _row) in enumerate(matches):
        if key == target:
            keeper_idx = i
            break
    keeper = matches[keeper_idx]
    cells = list(keeper[1]["cells"])

    changed = False
    if args.priority is not None and cells[0].strip().upper() != args.priority.strip().upper():
        cells[0] = args.priority.strip().upper()
        changed = True
    if args.notes is not None:
        notes = args.notes.strip() or "—"
        if cells[3].strip() != notes:
            cells[3] = notes
            changed = True

    dups = [m for i, m in enumerate(matches) if i != keeper_idx]
    already_there = keeper[0] == target
    if already_there and not changed and not dups:
        print("OK: %s already in '%s', nothing to do" % (pid, dict(SECTION_TITLES)[target]))
        return 0

    # Remove every matching row (keeper included; re-inserted below).
    remove = set(row["idx"] for _k, row in matches)
    kept = [l for i, l in enumerate(lines) if i not in remove]

    # Re-parse the reduced file to find the insertion point.
    sections2, _o, _s, _p = parse_board(kept)
    sec = sections2.get(target)
    new_line = build_row_line(cells, newline="\n")

    if sec is None:
        err("section '## %s' missing from board — run validate and fix structure first"
            % dict(SECTION_TITLES)[target])
        return 2

    ins = None
    if sec.table_start < 0:
        ins = sec.heading_idx + 1  # will splice header + separator + row
        splice = ["| %s |" % " | ".join(EXPECTED_HEADER_CELLS) + "\n",
                  "| --- | --- | --- | --- |\n", new_line]
    else:
        rows = sec.rows
        if target == "done":
            ins = (rows[0]["idx"] if rows else sec.sep_idx + 1)  # newest first
            splice = [new_line]
        else:
            key = row_sort_key(cells)
            ins = sec.sep_idx + 1
            for r in rows:
                if row_sort_key(r["cells"]) > key:
                    ins = r["idx"]
                    break
                ins = r["idx"] + 1
            splice = [new_line]

    kept[ins:ins] = splice
    write_board(path, kept)

    where = dict(SECTION_TITLES)[target]
    if dups:
        print("WARN: collapsed %d duplicate row(s) for %s" % (len(dups), pid))
    if already_there:
        print("OK: updated %s in '%s'%s" % (pid, where, " (notes/priority)" if changed else ""))
    else:
        print("OK: moved %s to '%s'" % (pid, where))
    return 0


# ---------------------------------------------------------------------------

def main(argv):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", default=None, metavar="DIR",
                        help="checkout root containing .plans/ (default: cwd)")

    ap = argparse.ArgumentParser(prog="board.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 parents=[common])
    sub = ap.add_subparsers(dest="cmd")

    p_v = sub.add_parser("validate", parents=[common], help="check the board for problems")
    p_n = sub.add_parser("next-id", parents=[common], help="print the next free task ID")
    p_m = sub.add_parser("move", parents=[common], help="move/update a row, never duplicating it")
    p_m.add_argument("id", help="task ID, e.g. T007 (T7 / 7 accepted)")
    p_m.add_argument("section", help="todo | in-progress | blocked | done")
    p_m.add_argument("--notes", default=None, metavar="TEXT", help="replace the Notes cell")
    p_m.add_argument("--priority", default=None, metavar="P#", help="set priority (P0/P1/P2)")

    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help()
        return 2

    root = args.root or os.getcwd()
    if not os.path.isdir(root):
        err("root directory not found: %s" % root)
        return 2

    return {"validate": cmd_validate, "next-id": cmd_next_id, "move": cmd_move}[args.cmd](root, args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
