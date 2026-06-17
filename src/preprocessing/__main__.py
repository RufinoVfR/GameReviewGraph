"""Entry point for ``python -m src.preprocessing`` (target of ``make preprocessing``)."""

from src.preprocessing import PreprocessingFilter

if __name__ == "__main__":
    PreprocessingFilter().execute()
