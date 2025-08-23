export interface Dependency {
  name: string;
  version: string;
  ecosystem: 'npm' | 'PyPI';
  path: string[];
  is_direct: boolean;
  is_dev: boolean;
}

export interface Vulnerability {
  package: string;
  version: string;
  ecosystem: 'npm' | 'PyPI';
  vulnerability_id: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN' | null;
  cve_ids: string[];
  summary: string;
  details?: string;
  advisory_url?: string;
  fixed_range?: string;
  published?: string;
  modified?: string;
  aliases: string[];
}

export interface ScanReport {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  total_dependencies: number;
  vulnerable_count: number;
  vulnerable_packages: Vulnerability[];
  dependencies: Dependency[];
  suppressed_count: number;
  stale_packages: string[];
  meta: {
    generated_at: string;
    ecosystems: string[];
    scan_options: any;
  };
}

export interface ScanProgress {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress_percent: number;
  current_step: string;
  total_dependencies?: number;
  scanned_dependencies: number;
  vulnerabilities_found: number;
  started_at: string;
  completed_at?: string;
  error_message?: string;
}

export interface ScanRequest {
  repo_path?: string;
  manifest_files?: Record<string, string>;
  options: {
    include_dev_dependencies: boolean;
    stale_months?: number;
    ignore_severities: string[];
    ignore_rules: any[];
  };
}