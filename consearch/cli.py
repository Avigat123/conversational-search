"""Interactive terminal interface."""

import argparse

from .session import ConversationSession, new_session

HELP = "Commands: /sources  list cited sources   /reset  start a new conversation   /quit  exit"


def _show(result, verbose: bool) -> None:
    print(f"\n{result.text}")
    if result.sources:
        print("\nSources:")
        for s in result.sources:
            print(f"  [{s.id}] {s.title} - {s.url}")
    if verbose:
        print(f"\n(steps: {result.steps}) " + ("; ".join(result.trace) or "no tool calls"))


def _build(ingest: list[str]) -> ConversationSession:
    session = new_session()
    for path in ingest:
        src = session.ingest_file(path)
        print(f"Indexed {path} as source [{src.id}]")
    return session


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="consearch", description="Conversational search with citations.")
    ap.add_argument("-q", "--question", help="Ask a single question and exit.")
    ap.add_argument("--ingest", nargs="*", default=[], metavar="FILE", help="Local .txt/.md files to search.")
    ap.add_argument("-v", "--verbose", action="store_true", help="Show tool calls and step counts.")
    args = ap.parse_args(argv)

    session = _build(args.ingest)

    if args.question:
        _show(session.ask(args.question), args.verbose)
        return 0

    print("Conversational search. " + HELP)
    while True:
        try:
            line = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            continue
        if line in ("/quit", "/exit"):
            return 0
        if line == "/reset":
            session = _build(args.ingest)
            print("Started a new conversation.")
            continue
        if line == "/sources":
            for s in session.workspace.registry.all():
                print(f"  [{s.id}] {s.title} - {s.url}")
            continue
        _show(session.ask(line), args.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
