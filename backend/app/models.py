from typing import Optional, Literal, List, Dict, Any
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
    path: List[str] = Field(description="Provenance path showing how this dependency was reached")
    is_direct: bool = Field(default=False, description="Whether this is a direct dependency")
    is_dev: bool = Field(default=False, description="Whether this is a development dependency")

class Vuln(BaseModel):
    """Represents a vulnerability found in a package"""
    package: str
    version: str
    ecosystem: Ecosystem
    vulnerability_id: str = Field(description="OSV ID or CVE ID")
    severity: Optional[SeverityLevel] = None
    cve_ids: List[str] = Field(default_factory=list)
    summary: str
    details: Optional[str] = None
    advisory_url: Optional[str] = None
    fixed_range: Optional[str] = Field(description="Version range that fixes this vulnerability")
    published: Optional[datetime] = None
    modified: Optional[datetime] = None
    aliases: List[str] = Field(default_factory=list, description="Other identifiers for this vulnerability")
    
class IgnoreRule(BaseModel):
    """Configuration for ignoring specific vulnerabilities or packages"""
    rule_type: Literal["vulnerability", "package"]
    identifier: str  # CVE ID or package@version pattern
    reason: str
    expires: Optional[datetime] = None

class ScanOptions(BaseModel):
    """Configuration options for a scan"""
    include_dev_dependencies: bool = Field(default=True)
    stale_months: Optional[int] = Field(default=None, description="Consider packages stale if no release in X months")
    ignore_severities: List[SeverityLevel] = Field(default_factory=list)
    ignore_rules: List[IgnoreRule] = Field(default_factory=list)

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
    total_dependencies: Optional[int] = None
    scanned_dependencies: int = 0
    vulnerabilities_found: int = 0
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class Report(BaseModel):
    """Complete vulnerability scan report"""
    job_id: str
    status: JobStatus
    total_dependencies: int
    vulnerable_count: int
    vulnerable_packages: List[Vuln]
    dependencies: List[Dep]
    suppressed_count: int = 0
    stale_packages: List[str] = Field(default_factory=list, description="Packages with no recent releases")
    meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata: generated_at, scan_duration, rate_limit_info, warnings, etc."
    )

class ScanRequest(BaseModel):
    """Request to start a vulnerability scan"""
    repo_path: Optional[str] = None
    manifest_files: Optional[Dict[str, str]] = Field(
        default=None, 
        description="Manifest file contents keyed by filename"
    )
    options: ScanOptions = Field(default_factory=ScanOptions)

class OSVQuery(BaseModel):
    """Single query to OSV API"""
    package: Dict[str, str]  # {"name": "package_name", "ecosystem": "PyPI"}
    version: Optional[str] = None

class OSVBatchQuery(BaseModel):
    """Batch query to OSV API"""
    queries: List[OSVQuery]

class OSVVulnerability(BaseModel):
    """Raw vulnerability response from OSV API"""
    id: str
    summary: Optional[str] = None
    details: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    published: Optional[str] = None
    modified: Optional[str] = None
    severity: Optional[List[Dict[str, Any]]] = None
    affected: List[Dict[str, Any]] = Field(default_factory=list)
    references: List[Dict[str, str]] = Field(default_factory=list)

class OSVBatchResponse(BaseModel):
    """Batch response from OSV API"""
    results: List[Dict[str, Any]]  # Each result can be a dict with 'vulns' key or empty