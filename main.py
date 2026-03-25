from receipt_ai.app import create_app


def main() -> None:
    """Local helper entrypoint for scripts/tools."""
    _ = create_app()
    print("Reflex app factory loaded. Run: uv run reflex run")


if __name__ == "__main__":
    main()
