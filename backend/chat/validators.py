from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


def validate_document_file(upload):
    extension = Path(upload.name).suffix.lower()
    if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValidationError(
            _("Unsupported document type. Use PDF, DOCX, TXT, or Markdown.")
        )
    if upload.size > settings.MAX_DOCUMENT_UPLOAD_BYTES:
        raise ValidationError(
            _("Document exceeds the maximum upload size of %(max_mb)s MB."),
            params={"max_mb": settings.MAX_DOCUMENT_UPLOAD_BYTES // (1024 * 1024)},
        )
