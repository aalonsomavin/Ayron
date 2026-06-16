class PdfGenerationError(Exception):
    pass


def html_to_pdf(html: str) -> bytes:
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise PdfGenerationError(
            "WeasyPrint is not installed. Install weasyprint and system libraries (pango, cairo)."
        ) from exc
    return HTML(string=html).write_pdf()
