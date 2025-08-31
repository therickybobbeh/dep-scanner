import { SeverityLevel, JobStatus, EcosystemType } from './common';

export interface Dependency {
  name: string;
  version: string;
  ecosystem: EcosystemType;
  path: string[];
  is_direct: boolean;
  is_dev: boolean;
  parent?: string; // Parent package for transitive deps
  depth?: number; // Depth in dependency tree
  required_by?: string[]; // List of packages requiring this
}

export interface Vulnerability {
  package: string;
  version: string;
  ecosystem: EcosystemType;
  vulnerability_id: string;
  severity: SeverityLevel | null;
  cvss_score?: number; // CVSS score (matches backend field name)
  cve_ids: string[];
  summary: string;
  details?: string;
  advisory_url?: string;
  fixed_range?: string;
  published?: string;
  modified?: string;
  aliases: string[];
  immediate_parent?: string; // Direct dependency that introduced this transitive vulnerability
  affected_dependencies?: DependencyPath[]; // Which dependencies are affected
}

export interface DependencyPath {
  package: string;
  version: string;
  path: string[]; // Full dependency path from root
  is_direct: boolean;
  parent: string;
}

export interface ScanReport {
  job_id: string;
  status: JobStatus;
  total_dependencies: number;
  vulnerable_count: number;
  vulnerable_packages: Vulnerability[];
  dependencies: Dependency[];
  suppressed_count: number;
  stale_packages?: string[];
  meta: {
    generated_at: string;
    ecosystems: string[];
    scan_options: ScanOptions;
  };
}

export interface ScanProgress {
  job_id: string;
  status: JobStatus;
  progress_percent: number;
  current_step: string;
  total_dependencies?: number;
  scanned_dependencies: number;
  vulnerabilities_found: number;
  started_at: string;
  completed_at?: string;
  error_message?: string;
}

export interface ScanOptions {
  include_dev_dependencies: boolean;
  stale_months?: number;
  ignore_severities: SeverityLevel[];
  ignore_rules?: any[];
}

export interface ScanRequest {
  repo_path?: string;
  manifest_files?: Record<string, string>;
  options: ScanOptions;
}
