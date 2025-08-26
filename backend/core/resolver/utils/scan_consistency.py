"""
Scan Result Consistency Analysis

Utilities for comparing and analyzing consistency between different
scan approaches (package.json vs package-lock.json vs other formats).
"""
from typing import List, Dict, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
import logging

from ...models import Dep, Report

logger = logging.getLogger(__name__)


@dataclass
class DependencyComparison:
    """Comparison result for a single dependency"""
    name: str
    manifest_version: Optional[str] = None
    lockfile_version: Optional[str] = None
    resolved_version: Optional[str] = None
    version_match: bool = False
    presence_match: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScanConsistencyReport:
    """Comprehensive consistency analysis between scan approaches"""
    total_manifest_deps: int = 0
    total_lockfile_deps: int = 0
    matching_dependencies: int = 0
    version_mismatches: int = 0
    missing_in_manifest: int = 0
    missing_in_lockfile: int = 0
    
    dependency_comparisons: List[DependencyComparison] = field(default_factory=list)
    version_resolution_stats: Dict[str, int] = field(default_factory=dict)
    
    # Vulnerability impact analysis
    vulnerability_differences: Dict[str, Any] = field(default_factory=dict)
    
    # Summary metrics
    consistency_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)


class ScanConsistencyAnalyzer:
    """
    Analyzer for comparing scan results between different dependency resolution methods
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def compare_dependency_lists(
        self, 
        manifest_deps: List[Dep], 
        lockfile_deps: List[Dep],
        include_dev: bool = True
    ) -> ScanConsistencyReport:
        """
        Compare two dependency lists and generate a consistency report
        
        Args:
            manifest_deps: Dependencies from manifest file (e.g., package.json)
            lockfile_deps: Dependencies from lockfile (e.g., package-lock.json)
            include_dev: Whether to include dev dependencies in comparison
            
        Returns:
            Detailed consistency report
        """
        report = ScanConsistencyReport()
        
        # Filter dependencies if needed
        if not include_dev:
            manifest_deps = [d for d in manifest_deps if not d.is_dev]
            lockfile_deps = [d for d in lockfile_deps if not d.is_dev]
        
        # Create lookup dictionaries
        manifest_lookup = {dep.name: dep for dep in manifest_deps}
        lockfile_lookup = {dep.name: dep for dep in lockfile_deps}
        
        report.total_manifest_deps = len(manifest_deps)
        report.total_lockfile_deps = len(lockfile_deps)
        
        # Get all unique package names
        all_packages = set(manifest_lookup.keys()) | set(lockfile_lookup.keys())
        
        # Compare each package
        for package_name in all_packages:
            manifest_dep = manifest_lookup.get(package_name)
            lockfile_dep = lockfile_lookup.get(package_name)
            
            comparison = DependencyComparison(
                name=package_name,
                manifest_version=manifest_dep.version if manifest_dep else None,
                lockfile_version=lockfile_dep.version if lockfile_dep else None
            )
            
            # Determine presence match
            comparison.presence_match = bool(manifest_dep and lockfile_dep)
            
            if manifest_dep and lockfile_dep:
                # Both present - check version match
                comparison.version_match = (manifest_dep.version == lockfile_dep.version)
                if comparison.version_match:
                    report.matching_dependencies += 1
                else:
                    report.version_mismatches += 1
                
                # Add metadata
                comparison.metadata = {
                    "manifest_is_dev": manifest_dep.is_dev,
                    "lockfile_is_dev": lockfile_dep.is_dev,
                    "manifest_is_direct": manifest_dep.is_direct,
                    "lockfile_is_direct": lockfile_dep.is_direct,
                }
            
            elif manifest_dep and not lockfile_dep:
                report.missing_in_lockfile += 1
                comparison.metadata = {"only_in": "manifest"}
            
            elif not manifest_dep and lockfile_dep:
                report.missing_in_manifest += 1
                comparison.metadata = {"only_in": "lockfile"}
            
            report.dependency_comparisons.append(comparison)
        
        # Calculate consistency score
        total_deps = max(report.total_manifest_deps, report.total_lockfile_deps)
        if total_deps > 0:
            report.consistency_score = report.matching_dependencies / total_deps
        
        # Generate recommendations
        report.recommendations = self._generate_recommendations(report)
        
        return report
    
    def compare_scan_reports(
        self, 
        manifest_report: Report, 
        lockfile_report: Report
    ) -> Dict[str, Any]:
        """
        Compare two complete scan reports for consistency analysis
        
        Args:
            manifest_report: Scan report from manifest file
            lockfile_report: Scan report from lockfile
            
        Returns:
            Comprehensive comparison analysis
        """
        dependency_comparison = self.compare_dependency_lists(
            manifest_report.dependencies,
            lockfile_report.dependencies
        )
        
        vulnerability_comparison = self._compare_vulnerabilities(
            manifest_report.vulnerable_packages,
            lockfile_report.vulnerable_packages
        )
        
        return {
            "dependency_analysis": dependency_comparison,
            "vulnerability_analysis": vulnerability_comparison,
            "summary": {
                "manifest_total_deps": len(manifest_report.dependencies),
                "lockfile_total_deps": len(lockfile_report.dependencies),
                "manifest_vulnerabilities": len(manifest_report.vulnerable_packages),
                "lockfile_vulnerabilities": len(lockfile_report.vulnerable_packages),
                "consistency_score": dependency_comparison.consistency_score,
                "vulnerability_difference": abs(
                    len(manifest_report.vulnerable_packages) - 
                    len(lockfile_report.vulnerable_packages)
                )
            }
        }
    
    def _compare_vulnerabilities(
        self, 
        manifest_vulns: List[Any], 
        lockfile_vulns: List[Any]
    ) -> Dict[str, Any]:
        """Compare vulnerability findings between two scan approaches"""
        
        # Create lookups by vulnerability ID and package
        manifest_vuln_lookup = {}
        for vuln in manifest_vulns:
            key = f"{vuln.package}:{vuln.vulnerability_id}"
            manifest_vuln_lookup[key] = vuln
        
        lockfile_vuln_lookup = {}
        for vuln in lockfile_vulns:
            key = f"{vuln.package}:{vuln.vulnerability_id}"
            lockfile_vuln_lookup[key] = vuln
        
        # Analyze differences
        all_vuln_keys = set(manifest_vuln_lookup.keys()) | set(lockfile_vuln_lookup.keys())
        
        common_vulnerabilities = []
        only_in_manifest = []
        only_in_lockfile = []
        
        for vuln_key in all_vuln_keys:
            manifest_vuln = manifest_vuln_lookup.get(vuln_key)
            lockfile_vuln = lockfile_vuln_lookup.get(vuln_key)
            
            if manifest_vuln and lockfile_vuln:
                common_vulnerabilities.append({
                    "key": vuln_key,
                    "manifest_severity": manifest_vuln.severity,
                    "lockfile_severity": lockfile_vuln.severity,
                    "severity_match": manifest_vuln.severity == lockfile_vuln.severity
                })
            elif manifest_vuln:
                only_in_manifest.append({
                    "key": vuln_key,
                    "vulnerability": manifest_vuln
                })
            elif lockfile_vuln:
                only_in_lockfile.append({
                    "key": vuln_key,
                    "vulnerability": lockfile_vuln
                })
        
        return {
            "total_manifest_vulnerabilities": len(manifest_vulns),
            "total_lockfile_vulnerabilities": len(lockfile_vulns),
            "common_vulnerabilities": len(common_vulnerabilities),
            "only_in_manifest": len(only_in_manifest),
            "only_in_lockfile": len(only_in_lockfile),
            "common_details": common_vulnerabilities,
            "manifest_only_details": only_in_manifest,
            "lockfile_only_details": only_in_lockfile
        }
    
    def _generate_recommendations(self, report: ScanConsistencyReport) -> List[str]:
        """Generate recommendations based on consistency analysis"""
        recommendations = []
        
        if report.consistency_score < 0.5:
            recommendations.append(
                "Low consistency detected. Consider using lockfiles for more reliable results."
            )
        
        if report.missing_in_lockfile > 0:
            recommendations.append(
                f"{report.missing_in_lockfile} dependencies found in manifest but not in lockfile. "
                f"This may indicate the lockfile is out of date."
            )
        
        if report.missing_in_manifest > 0:
            recommendations.append(
                f"{report.missing_in_manifest} dependencies found in lockfile but not in manifest. "
                f"These are likely transitive dependencies."
            )
        
        if report.version_mismatches > 0:
            recommendations.append(
                f"{report.version_mismatches} version mismatches detected. "
                f"Consider regenerating lockfile or using version resolution."
            )
        
        if report.consistency_score > 0.9:
            recommendations.append(
                "High consistency detected. Results should be reliable across both approaches."
            )
        
        return recommendations
    
    def generate_consistency_summary(self, report: ScanConsistencyReport) -> str:
        """Generate a human-readable consistency summary"""
        lines = [
            f"Scan Consistency Analysis",
            f"=" * 30,
            f"Manifest dependencies: {report.total_manifest_deps}",
            f"Lockfile dependencies: {report.total_lockfile_deps}",
            f"Matching dependencies: {report.matching_dependencies}",
            f"Version mismatches: {report.version_mismatches}",
            f"Missing in manifest: {report.missing_in_manifest}",
            f"Missing in lockfile: {report.missing_in_lockfile}",
            f"Consistency score: {report.consistency_score:.2%}",
            f"",
            f"Recommendations:",
        ]
        
        for i, rec in enumerate(report.recommendations, 1):
            lines.append(f"{i}. {rec}")
        
        return "\n".join(lines)
    
    def get_version_mismatch_details(
        self, 
        report: ScanConsistencyReport, 
        limit: int = 10
    ) -> List[Dict[str, str]]:
        """Get detailed information about version mismatches"""
        mismatches = [
            comp for comp in report.dependency_comparisons 
            if comp.presence_match and not comp.version_match
        ]
        
        return [
            {
                "package": comp.name,
                "manifest_version": comp.manifest_version,
                "lockfile_version": comp.lockfile_version,
                "metadata": str(comp.metadata)
            }
            for comp in mismatches[:limit]
        ]