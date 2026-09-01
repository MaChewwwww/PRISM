from __future__ import annotations

import argparse
import re

WORK_BRANCH = re.compile(
    r"^(?:feature|fix|chore|docs|refactor|test|ci)/[a-z0-9][a-z0-9._-]*$"
)


def validate_branch_flow(head: str, base: str) -> str | None:
    if base == "main":
        if head == "staging" or WORK_BRANCH.fullmatch(head):
            return None
        return "Main accepts staging or an allowed typed work branch."
    if base == "staging":
        if WORK_BRANCH.fullmatch(head):
            return None
        return "Work targeting staging must use an allowed typed branch."
    return f"Unsupported pull request base: {base}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate the governed GitHub PR branch flow"
    )
    parser.add_argument("--head", required=True)
    parser.add_argument("--base", required=True)
    args = parser.parse_args()
    error = validate_branch_flow(args.head, args.base)
    if error:
        raise SystemExit(error)
    print(f"Allowed pull request: {args.head} -> {args.base}")


if __name__ == "__main__":
    main()
