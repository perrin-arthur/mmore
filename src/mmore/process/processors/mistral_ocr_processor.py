import base64
import io
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from PIL import Image

from ...type import DocumentMetadata, FileDescriptor, MultimodalSample
from .base import Processor, ProcessorConfig

logger = logging.getLogger(__name__)

# Env var that selects the PDF backend. When set to "mistral", MistralOCRProcessor
# accepts .pdf files and the default PDFProcessor steps aside.
PDF_BACKEND_ENV = "MMORE_PDF_BACKEND"
MISTRAL_BACKEND = "mistral"

IMG_REGEX = r"!\[[^\]]*\]\([^)]+\)"


@dataclass
class MistralOCRMetadata(DocumentMetadata):
    paragraph_starts: List[Tuple[int, int, int]] = field(default_factory=list)
    backend: str = "mistral-ocr"
    model: str = "mistral-ocr-latest"

    def to_dict(self) -> Dict[str, Any]:
        metadata = super().to_dict()
        if self.paragraph_starts:
            metadata["paragraph_starts"] = self.paragraph_starts
        metadata["backend"] = self.backend
        metadata["model"] = self.model
        return metadata


class MistralOCRProcessor(Processor):
    """PDF processor backed by Mistral's hosted OCR endpoint.

    Activated by setting MMORE_PDF_BACKEND=mistral. Requires MISTRAL_API_KEY.
    """

    def __init__(self, config=None):
        super().__init__(config=config or ProcessorConfig())
        self._client = None
        self._model = (
            self.config.custom_config.get("mistral_ocr_model", "mistral-ocr-latest")
            if config is not None
            else "mistral-ocr-latest"
        )

    @classmethod
    def accepts(cls, file: FileDescriptor) -> bool:
        if os.environ.get(PDF_BACKEND_ENV, "").lower() != MISTRAL_BACKEND:
            return False
        return file.file_extension.lower() == ".pdf"

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from mistralai import Mistral
        except ImportError as e:
            raise ImportError(
                "mistralai SDK is required for MistralOCRProcessor. "
                "Install with `pip install mistralai`."
            ) from e
        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            raise RuntimeError(
                "MISTRAL_API_KEY env var is not set. Required for MistralOCRProcessor."
            )
        self._client = Mistral(api_key=api_key)
        return self._client

    def process(self, file_path: str) -> MultimodalSample:
        client = self._get_client()

        with open(file_path, "rb") as fh:
            pdf_bytes = fh.read()
        encoded = base64.b64encode(pdf_bytes).decode("utf-8")

        extract_images = self.config.custom_config.get("extract_images", True)

        response = client.ocr.process(
            model=self._model,
            document={
                "type": "document_url",
                "document_url": f"data:application/pdf;base64,{encoded}",
            },
            include_image_base64=extract_images,
        )

        pages = getattr(response, "pages", None) or []
        page_texts: List[Tuple[int, str]] = []
        images: List[Image.Image] = []

        for page_idx, page in enumerate(pages):
            md = getattr(page, "markdown", "") or ""
            if extract_images:
                for img in getattr(page, "images", []) or []:
                    b64 = getattr(img, "image_base64", None)
                    if not b64:
                        continue
                    try:
                        raw = base64.b64decode(b64.split(",", 1)[-1])
                        images.append(Image.open(io.BytesIO(raw)).convert("RGB"))
                    except Exception as e:
                        logger.warning(
                            f"Could not decode image on page {page_idx} of {file_path}: {e}"
                        )
            md = re.sub(IMG_REGEX, "<attachment>", md)
            page_texts.append((page_idx, md))

        paragraph_starts, full_text = self._build_pagination(page_texts)

        metadata = MistralOCRMetadata(
            file_path=file_path,
            paragraph_starts=paragraph_starts,
            model=self._model,
        )
        return self.create_sample([full_text], images, metadata)

    @staticmethod
    def _build_pagination(
        page_texts: List[Tuple[int, str]],
    ) -> Tuple[List[Tuple[int, int, int]], str]:
        paragraph_starts: List[Tuple[int, int, int]] = []
        current_position = 0
        parts: List[str] = []
        for page_id, page_content in page_texts:
            para_idx = 0
            offset_in_page = 0
            for segment in page_content.split("\n\n"):
                if segment.strip():
                    paragraph_starts.append(
                        (current_position + offset_in_page, page_id, para_idx)
                    )
                    para_idx += 1
                offset_in_page += len(segment) + 2
            parts.append(page_content)
            current_position += len(page_content)
        paragraph_starts.append((current_position, -1, -1))
        return paragraph_starts, "".join(parts)
