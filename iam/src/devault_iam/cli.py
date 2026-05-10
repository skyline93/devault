from __future__ import annotations

import os


def main() -> None:
    """Entry point: `devault-iam-serve` → uvicorn on port 8100."""
    import uvicorn

    host = os.environ.get("IAM_HOST", "0.0.0.0")
    port = int(os.environ.get("IAM_PORT", "8100"))
    uvicorn.run(
        "devault_iam.api.main:app",
        host=host,
        port=port,
        factory=False,
    )


if __name__ == "__main__":
    main()
