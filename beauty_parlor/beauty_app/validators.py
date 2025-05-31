# validators.py

from django.core.exceptions import ValidationError
import re


def email_validator(value):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, value):
        raise ValidationError("Enter a valid email address.")
    return value


def phone_validator(value):
    pattern = r'^\+?[0-9]{10,15}$'
    if not re.match(pattern, value):
        raise ValidationError("Enter a valid phone number (10-15 digits).")
    return value


def price_validator(value):
    if value <= 0:
        raise ValidationError("Price must be greater than zero.")
    return value


def discount_validator(value):
    if value < 0 or value > 100:
        raise ValidationError("Discount must be between 0 and 100.")
    return value


def date_time_validator(value):
    from django.utils import timezone
    if value < timezone.now():
        raise ValidationError("Date and time cannot be in the past.")
    return value


import os
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils.deconstruct import deconstructible


@deconstructible
class FileSizeValidator:
    """Validator to check file size doesn't exceed maximum allowed size"""

    def __init__(self, max_size=None):
        # Use settings value or default to 20MB
        self.max_size = max_size or getattr(settings, 'MAX_UPLOAD_SIZE', 20 * 1024 * 1024)

    def __call__(self, value):
        if value.size > self.max_size:
            size_mb = self.max_size / (1024 * 1024)
            current_size_mb = value.size / (1024 * 1024)
            raise ValidationError(
                f'File size ({current_size_mb:.2f}MB) exceeds maximum allowed size ({size_mb:.0f}MB).'
            )

    def __eq__(self, other):
        return isinstance(other, FileSizeValidator) and self.max_size == other.max_size


@deconstructible
class FileExtensionValidator:
    """Validator to check file extension is allowed"""

    def __init__(self, allowed_extensions=None):
        self.allowed_extensions = allowed_extensions or []

    def __call__(self, value):
        if not self.allowed_extensions:
            return

        ext = os.path.splitext(value.name)[1].lower()
        if ext not in self.allowed_extensions:
            raise ValidationError(
                f'File extension "{ext}" is not allowed. '
                f'Allowed extensions: {", ".join(self.allowed_extensions)}'
            )

    def __eq__(self, other):
        return (isinstance(other, FileExtensionValidator) and
                self.allowed_extensions == other.allowed_extensions)


@deconstructible
class ImageFileValidator:
    """Combined validator for image files with size and extension checks"""

    def __init__(self, max_size=None, allowed_extensions=None):
        self.max_size = max_size or getattr(settings, 'MAX_UPLOAD_SIZE', 20 * 1024 * 1024)
        self.allowed_extensions = allowed_extensions or getattr(
            settings, 'ALLOWED_IMAGE_EXTENSIONS',
            ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        )

    def __call__(self, value):
        # Check file size
        if value.size > self.max_size:
            size_mb = self.max_size / (1024 * 1024)
            current_size_mb = value.size / (1024 * 1024)
            raise ValidationError(
                f'Image size ({current_size_mb:.2f}MB) exceeds maximum allowed size ({size_mb:.0f}MB).'
            )

        # Check file extension
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in self.allowed_extensions:
            raise ValidationError(
                f'File extension "{ext}" is not allowed for images. '
                f'Allowed extensions: {", ".join(self.allowed_extensions)}'
            )

    def __eq__(self, other):
        return (isinstance(other, ImageFileValidator) and
                self.max_size == other.max_size and
                self.allowed_extensions == other.allowed_extensions)


@deconstructible
class DocumentFileValidator:
    """Combined validator for document files with size and extension checks"""

    def __init__(self, max_size=None, allowed_extensions=None):
        self.max_size = max_size or getattr(settings, 'MAX_UPLOAD_SIZE', 20 * 1024 * 1024)
        self.allowed_extensions = allowed_extensions or getattr(
            settings, 'ALLOWED_DOCUMENT_EXTENSIONS',
            ['.pdf', '.doc', '.docx', '.txt']
        )

    def __call__(self, value):
        # Check file size
        if value.size > self.max_size:
            size_mb = self.max_size / (1024 * 1024)
            current_size_mb = value.size / (1024 * 1024)
            raise ValidationError(
                f'Document size ({current_size_mb:.2f}MB) exceeds maximum allowed size ({size_mb:.0f}MB).'
            )

        # Check file extension
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in self.allowed_extensions:
            raise ValidationError(
                f'File extension "{ext}" is not allowed for documents. '
                f'Allowed extensions: {", ".join(self.allowed_extensions)}'
            )

    def __eq__(self, other):
        return (isinstance(other, DocumentFileValidator) and
                self.max_size == other.max_size and
                self.allowed_extensions == other.allowed_extensions)


# Convenience functions for common use cases
def validate_image_size_20mb(value):
    """Validate image file is under 20MB"""
    validator = ImageFileValidator(max_size=20 * 1024 * 1024)
    return validator(value)


def validate_file_size_20mb(value):
    """Validate any file is under 20MB"""
    validator = FileSizeValidator(max_size=20 * 1024 * 1024)
    return validator(value)


def validate_profile_picture(value):
    """Validate profile picture (5MB limit)"""
    validator = ImageFileValidator(
        max_size=5 * 1024 * 1024,  # 5MB for profile pictures
        allowed_extensions=['.jpg', '.jpeg', '.png']
    )
    return validator(value)


def validate_service_image(value):
    """Validate service image (10MB limit)"""
    validator = ImageFileValidator(
        max_size=10 * 1024 * 1024,  # 10MB for service images
        allowed_extensions=['.jpg', '.jpeg', '.png', '.webp']
    )
    return validator(value)