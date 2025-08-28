from typing import Literal, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

Ecosystem = Literal["npm", "PyPI"]

class SeverityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"

class Dep(BaseModel):
    """Represents a dependency in the dependency graph"""
    name: str
    version: str
    ecosystem: Ecosystem
    path: list[str] = Field(description="Provenance path showing how this dependency was reached")
    is_direct: bool = Field(default=False, description="Whether this is a direct dependency")
    is_dev: bool = Field(default=False, description="Whether this is a development dependency")

class Vuln(BaseModel):
    """Represents a vulnerability found in a package"""
    package: str
    version: str
    ecosystem: Ecosystem
    vulnerability_id: str = Field(description="OSV ID or CVE ID")
    severity: SeverityLevel | None = None
    cvss_score: float | None = Field(default=None, description="CVSS score (0.0-10.0)")
    cve_ids: list[str] = Field(default_factory=list)
    summary: str
    details: str | None = None
    advisory_url: str | None = None
    fixed_range: str | None = Field(description="Version range that fixes this vulnerability")
    published: datetime | None = None
    modified: datetime | None = None
    aliases: list[str] = Field(default_factory=list, description="Other identifiers for this vulnerability")
    
class IgnoreRule(BaseModel):
    """Configuration for ignoring specific vulnerabilities or packages"""
    rule_type: Literal["vulnerability", "package"]
    identifier: str  # CVE ID or package@version pattern
    reason: str
    expires: datetime | None = None

class ScanOptions(BaseModel):
    """Configuration options for a scan"""
    include_dev_dependencies: bool = Field(default=True)
    stale_months: int | None = Field(default=None, description="Consider packages stale if no release in X months")
    ignore_severities: list[SeverityLevel] = Field(default_factory=list)
    ignore_rules: list[IgnoreRule] = Field(default_factory=list)

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class ScanProgress(BaseModel):
    """Progress information for a running scan"""
    job_id: str
    status: JobStatus
    progress_percent: float = Field(ge=0, le=100)
    current_step: str
    total_dependencies: int | None = None
    scanned_dependencies: int = 0
    vulnerabilities_found: int = 0
    started_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None

class Report(BaseModel):
    """Complete vulnerability scan report"""
    job_id: str
    status: JobStatus
    total_dependencies: int
    vulnerable_count: int
    vulnerable_packages: list[Vuln]
    dependencies: list[Dep]
    suppressed_count: int = 0
    stale_packages: list[str] = Field(default_factory=list, description="Packages with no recent releases")
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata: generated_at, scan_duration, rate_limit_info, warnings, etc."
    )

class ScanRequest(BaseModel):
    """Request to start a vulnerability scan"""
    repo_path: str | None = None
    manifest_files: dict[str, str] | None = Field(
        default=None, 
        description="Manifest file contents keyed by filename"
    )
    options: ScanOptions = Field(default_factory=ScanOptions)

class OSVQuery(BaseModel):
    """Single query to OSV API"""
    package: dict[str, str]  # {"name": "package_name", "ecosystem": "PyPI"}
    version: str | None = None

class OSVBatchQuery(BaseModel):
    """Batch query to OSV API"""
    queries: list[OSVQuery]

class OSVVulnerability(BaseModel):
    """Raw vulnerability response from OSV API"""
    id: str
    summary: str | None = None
    details: str | None = None
    aliases: list[str] = Field(default_factory=list)
    published: str | None = None
    modified: str | None = None
    severity: list[dict[str, Any]] | None = None
    affected: list[dict[str, Any]] = Field(default_factory=list)
    references: list[dict[str, str]] = Field(default_factory=list)

class OSVBatchResponse(BaseModel):
    """Batch response from OSV API"""
    results: list[dict[str, Any]]  # Each result can be a dict with 'vulns' key or empty