"""
Document models for intelligent document processing
"""

from datetime import datetime
from typing import Any, ClassVar

from base.backend.config.loader import storage_config
from base.backend.dataops.models.base_model import StorageModel
from base.backend.dataops.models.storage_config import StorageConfig
from base.backend.utils.standard_imports import setup_imports
from pydantic import Field

# Use standard import setup

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()


class Document(StorageModel):
    """Main document model with multi-storage configurations"""

    # Document identification (id inherited from StorageModel)
    file_path: str
    file_type: str
    file_size: int
    # created_at and modified_at inherited from SecuredModelMixin
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
            "graph": StorageConfig.from_dict(storage_config.get_storage_config("dgraph")),
            "vector": StorageConfig.from_dict(storage_config.get_storage_config("pgvector")),
            "relational": StorageConfig.from_dict(storage_config.get_storage_config("postgres")),
            "inmem": StorageConfig.from_dict(storage_config.get_storage_config("redis")),
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
        data: dict[str, Any] = super().to_storage_dict()

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

        return data


class DocumentSection(StorageModel):
    """Document section with hierarchical structure"""

    # id inherited from StorageModel
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

    # Timestamps inherited from SecuredModelMixin

    class Meta:
        storage_configs: ClassVar[dict[str, StorageConfig]] = {
            "graph": StorageConfig.from_dict(storage_config.get_storage_config("dgraph")),
            "vector": StorageConfig.from_dict(storage_config.get_storage_config("pgvector")),
            "inmem": StorageConfig.from_dict(storage_config.get_storage_config("redis")),
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

    # id inherited from StorageModel
    document_id: str
    section_id: str | None = None

    # Table metadata
    name: str | None = None
    caption: str | None = None
    headers: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)

    # Schema information
    table_schema: dict[str, str] = Field(default_factory=dict)  # Column name -> data type
    primary_key: str | None = None
    foreign_keys: dict[str, str] = Field(default_factory=dict)  # Column -> referenced table

    # Storage
    relational_table: str | None = None  # PostgreSQL table name
    indexed_columns: list[str] = Field(default_factory=list)

    # Timestamps inherited from SecuredModelMixin

    class Meta:
        storage_configs: ClassVar[dict[str, StorageConfig]] = {
            "relational": StorageConfig.from_dict(storage_config.get_storage_config("postgres")),
            "graph": StorageConfig.from_dict(storage_config.get_storage_config("dgraph")),
            "inmem": StorageConfig.from_dict(storage_config.get_storage_config("redis")),
        }
        path = "document_tables"
        indexes: ClassVar[list[dict[str, Any]]] = [
            {"field": "document_id", "type": "hash"},
            {"field": "section_id", "type": "hash"},
            {"field": "relational_table", "type": "hash"},
        ]

    def to_storage_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage"""
        data: dict[str, Any] = super().to_storage_dict()

        # Ensure proper serialization of complex fields
        if self.headers:
            data["headers"] = list(self.headers)
        if self.rows:
            data["rows"] = [dict(row) for row in self.rows]
        if self.table_schema:
            data["table_schema"] = dict(self.table_schema)
        if self.foreign_keys:
            data["foreign_keys"] = dict(self.foreign_keys)
        if self.indexed_columns:
            data["indexed_columns"] = list(self.indexed_columns)

        return data


class DocumentImage(StorageModel):
    """Image extracted from document"""

    # id inherited from StorageModel
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
    detected_objects: list[dict[str, Any]] = Field(default_factory=list)
    chart_data: dict[str, Any] | None = None

    visual_embedding: list[float] | None = None
    text_embedding: list[float] | None = None

    # LLM analysis cache
    analysis_prompt: str | None = None
    analysis_result: str | None = None
    analysis_timestamp: datetime | None = None

    # Timestamps inherited from SecuredModelMixin

    class Meta:
        storage_configs: ClassVar[dict[str, StorageConfig]] = {
            "vector": StorageConfig.from_dict(storage_config.get_storage_config("pgvector")),
            "graph": StorageConfig.from_dict(storage_config.get_storage_config("dgraph")),
            "inmem": StorageConfig.from_dict(storage_config.get_storage_config("redis")),
        }
        path = "document_images"
        indexes: ClassVar[list[dict[str, Any]]] = [
            {"field": "document_id", "type": "hash"},
            {"field": "section_id", "type": "hash"},
            {"field": "mime_type", "type": "hash"},
        ]

    def to_storage_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage"""
        data: dict[str, Any] = super().to_storage_dict()

        # Ensure proper serialization
        if self.dimensions:
            data["dimensions"] = dict(self.dimensions)
        if self.detected_objects:
            data["detected_objects"] = [dict(obj) for obj in self.detected_objects]
        if self.chart_data:
            data["chart_data"] = dict(self.chart_data) if isinstance(self.chart_data, dict) else self.chart_data
        if self.visual_embedding:
            data["visual_embedding"] = list(self.visual_embedding)
        if self.text_embedding:
            data["text_embedding"] = list(self.text_embedding)

        return data
