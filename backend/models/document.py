"""
Document models for intelligent document processing
"""

from datetime import datetime
from typing import Any, ClassVar

from base.backend.dataops.storage_model import StorageModel
from base.backend.dataops.storage_types import StorageConfig, StorageType
from pydantic import Field


class Document(StorageModel):
    """Main document model with multi-storage configurations"""

    # Document identification
    id: str | None = Field(default=None)
    file_path: str
    file_type: str
    file_size: int
    created_at: datetime | None = Field(default_factory=datetime.utcnow)
    modified_at: datetime | None = Field(default_factory=datetime.utcnow)
    indexed_at: datetime | None = Field(default_factory=datetime.utcnow)

    # Metadata
    title: str | None = None
    author: str | None = None
    subject: str | None = None
    keywords: list[str] = Field(default_factory=list)
    language: str = "en"

    # Content structure (stored as references)
    section_ids: list[str] = Field(default_factory=list)
    table_ids: list[str] = Field(default_factory=list)
    image_ids: list[str] = Field(default_factory=list)

    # Storage references
    graph_id: str | None = None
    vector_ids: list[str] = Field(default_factory=list)
    relational_ids: dict[str, str] = Field(default_factory=dict)

    # Processing metadata
    extraction_method: str | None = None
    processing_time_ms: int | None = None
    error_messages: list[str] = Field(default_factory=list)

    class Meta:
        storage_configs: ClassVar[dict[str, StorageConfig]] = {
            "graph": StorageConfig(
                storage_type=StorageType.GRAPH, host="172.72.72.2", port=9080
            ),
            "vector": StorageConfig(
                storage_type=StorageType.VECTOR,
                host="172.72.72.2",
                port=5432,
                database="vectors",
                username="postgres",
                password="postgres",
            ),
            "relational": StorageConfig(
                storage_type=StorageType.RELATIONAL,
                host="172.72.72.2",
                port=5432,
                database="documents",
                username="postgres",
                password="postgres",
            ),
            "cache": StorageConfig(
                storage_type=StorageType.CACHE, host="172.72.72.2", port=6379
            ),
        }
        path = "documents"
        indexes: ClassVar[list[dict[str, Any]]] = [
            {"field": "title", "type": "fulltext"},
            {"field": "created_at", "type": "hash"},
            {"field": "file_type", "type": "hash"},
            {"field": "author", "type": "hash"},
        ]

    def to_storage_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage with proper serialization"""
        data = super().to_storage_dict()

        # Additional serialization for document-specific fields
        if self.keywords:
            data["keywords"] = list(self.keywords)
        if self.section_ids:
            data["section_ids"] = list(self.section_ids)
        if self.table_ids:
            data["table_ids"] = list(self.table_ids)
        if self.image_ids:
            data["image_ids"] = list(self.image_ids)
        if self.vector_ids:
            data["vector_ids"] = list(self.vector_ids)
        if self.relational_ids:
            data["relational_ids"] = dict(self.relational_ids)
        if self.error_messages:
            data["error_messages"] = list(self.error_messages)

        return data  # type: ignore[no-any-return]


class DocumentSection(StorageModel):
    """Document section with hierarchical structure"""

    id: str | None = Field(default=None)
    document_id: str
    parent_section_id: str | None = None

    # Section metadata
    level: int  # Heading level (1-6)
    title: str
    content: str

    # Navigation
    order: int
    path: str  # e.g., "1.2.3"

    # Embeddings (auto-generated when stored in vector storage)
    embedding: list[float] | None = None
    summary: str | None = None

    # Timestamps
    created_at: datetime | None = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = Field(default_factory=datetime.utcnow)

    class Meta:
        storage_configs: ClassVar[dict[str, StorageConfig]] = {
            "graph": StorageConfig(
                storage_type=StorageType.GRAPH, host="172.72.72.2", port=9080
            ),
            "vector": StorageConfig(
                storage_type=StorageType.VECTOR,
                host="172.72.72.2",
                port=5432,
                database="vectors",
                username="postgres",
                password="postgres",
            ),
            "cache": StorageConfig(
                storage_type=StorageType.CACHE, host="172.72.72.2", port=6379
            ),
        }
        path = "document_sections"
        indexes: ClassVar[list[dict[str, Any]]] = [
            {"field": "document_id", "type": "hash"},
            {"field": "parent_section_id", "type": "hash"},
            {"field": "level", "type": "hash"},
            {"field": "order", "type": "int"},
        ]


class DocumentTable(StorageModel):
    """Extracted table from document"""

    id: str | None = Field(default=None)
    document_id: str
    section_id: str | None = None

    # Table metadata
    name: str | None = None
    caption: str | None = None
    headers: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)

    # Schema information
    schema: dict[str, str] = Field(default_factory=dict)  # Column name -> data type
    primary_key: str | None = None
    foreign_keys: dict[str, str] = Field(
        default_factory=dict
    )  # Column -> referenced table

    # Storage
    relational_table: str | None = None  # PostgreSQL table name
    indexed_columns: list[str] = Field(default_factory=list)

    # Timestamps
    created_at: datetime | None = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = Field(default_factory=datetime.utcnow)

    class Meta:
        storage_configs: ClassVar[dict[str, StorageConfig]] = {
            "relational": StorageConfig(
                storage_type=StorageType.RELATIONAL,
                host="172.72.72.2",
                port=5432,
                database="documents",
                username="postgres",
                password="postgres",
            ),
            "graph": StorageConfig(
                storage_type=StorageType.GRAPH, host="172.72.72.2", port=9080
            ),
            "cache": StorageConfig(
                storage_type=StorageType.CACHE, host="172.72.72.2", port=6379
            ),
        }
        path = "document_tables"
        indexes: ClassVar[list[dict[str, Any]]] = [
            {"field": "document_id", "type": "hash"},
            {"field": "section_id", "type": "hash"},
            {"field": "relational_table", "type": "hash"},
        ]

    def to_storage_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage"""
        data = super().to_storage_dict()

        # Ensure proper serialization of complex fields
        if self.headers:
            data["headers"] = list(self.headers)
        if self.rows:
            data["rows"] = [dict(row) for row in self.rows]
        if self.schema:
            data["schema"] = dict(self.schema)
        if self.foreign_keys:
            data["foreign_keys"] = dict(self.foreign_keys)
        if self.indexed_columns:
            data["indexed_columns"] = list(self.indexed_columns)

        return data  # type: ignore[no-any-return]


class DocumentImage(StorageModel):
    """Image extracted from document"""

    id: str | None = Field(default=None)
    document_id: str
    section_id: str | None = None

    # Image metadata
    file_path: str
    mime_type: str
    dimensions: dict[str, int] = Field(default_factory=dict)  # width, height
    file_size: int | None = None

    # Analysis results
    caption: str | None = None
    alt_text: str | None = None
    extracted_text: str | None = None
    detected_objects: list[dict] = Field(default_factory=list)
    chart_data: dict | None = None

    # Embeddings (auto-generated)
    visual_embedding: list[float] | None = None
    text_embedding: list[float] | None = None

    # LLM analysis cache
    analysis_prompt: str | None = None
    analysis_result: str | None = None
    analysis_timestamp: datetime | None = None

    # Timestamps
    created_at: datetime | None = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = Field(default_factory=datetime.utcnow)

    class Meta:
        storage_configs: ClassVar[dict[str, StorageConfig]] = {
            "vector": StorageConfig(
                storage_type=StorageType.VECTOR,
                host="172.72.72.2",
                port=5432,
                database="vectors",
                username="postgres",
                password="postgres",
            ),
            "graph": StorageConfig(
                storage_type=StorageType.GRAPH, host="172.72.72.2", port=9080
            ),
            "cache": StorageConfig(
                storage_type=StorageType.CACHE, host="172.72.72.2", port=6379
            ),
        }
        path = "document_images"
        indexes: ClassVar[list[dict[str, Any]]] = [
            {"field": "document_id", "type": "hash"},
            {"field": "section_id", "type": "hash"},
            {"field": "mime_type", "type": "hash"},
        ]

    def to_storage_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage"""
        data = super().to_storage_dict()

        # Ensure proper serialization
        if self.dimensions:
            data["dimensions"] = dict(self.dimensions)
        if self.detected_objects:
            data["detected_objects"] = [dict(obj) for obj in self.detected_objects]
        if self.chart_data:
            data["chart_data"] = (
                dict(self.chart_data)
                if isinstance(self.chart_data, dict)
                else self.chart_data
            )
        if self.visual_embedding:
            data["visual_embedding"] = list(self.visual_embedding)
        if self.text_embedding:
            data["text_embedding"] = list(self.text_embedding)

        return data  # type: ignore[no-any-return]
