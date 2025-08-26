"""
Package.json vs Package-lock.json Consistency Validation Service

This service validates that scanning a package.json and its corresponding
package-lock.json produces consistent results, and provides detailed
analysis when inconsistencies are found.
"""
import asyncio
import logging
from typing import Dict, List, Any, Tuple, Optional

from .cli_service import CLIService

logger = logging.getLogger(__name__)


class ConsistencyValidationResult:
    """Result of consistency validation between package.json and package-lock.json"""
    
    def __init__(self):
        self.is_consistent = False
        self.package_json_result: Optional[Dict[str, Any]] = None
        self.package_lock_result: Optional[Dict[str, Any]] = None
        self.analysis: Optional[Dict[str, Any]] = None
        self.recommendations: List[str] = []
        self.warnings: List[str] = []
        self.errors: List[str] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            'is_consistent': self.is_consistent,
            'analysis': self.analysis,
            'recommendations': self.recommendations,
            'warnings': self.warnings,
            'errors': self.errors,
            'scan_results': {
                'package_json': self.package_json_result,
                'package_lock': self.package_lock_result
            }
        }


class ConsistencyService:
    """Service for validating consistency between package.json and package-lock.json scans"""
    
    @staticmethod
    def extract_vulnerability_summary(scan_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key vulnerability metrics from scan result"""
        vulnerabilities = scan_result.get('vulnerabilities', [])
        scan_info = scan_result.get('scan_info', {})
        
        # Group vulnerabilities by package
        vuln_by_package = {}
        severity_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'UNKNOWN': 0}
        
        for vuln in vulnerabilities:
            package = vuln.get('package', 'unknown')
            severity = vuln.get('severity', 'UNKNOWN').upper()
            
            if package not in vuln_by_package:
                vuln_by_package[package] = []
            vuln_by_package[package].append(vuln)
            
            if severity in severity_counts:
                severity_counts[severity] += 1
        
        return {
            'total_vulnerabilities': len(vulnerabilities),
            'total_dependencies': scan_info.get('total_dependencies', 0),
            'vulnerable_packages': len(vuln_by_package),
            'vulnerabilities_by_package': vuln_by_package,
            'severity_counts': severity_counts,
            'package_names': set(vuln_by_package.keys())
        }
    
    @staticmethod
    def analyze_consistency(package_json_summary: Dict[str, Any], 
                           package_lock_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze consistency between two scan summaries"""
        
        # Basic consistency checks
        vuln_count_match = (package_json_summary['total_vulnerabilities'] == 
                           package_lock_summary['total_vulnerabilities'])
        
        vulnerable_packages_match = (package_json_summary['vulnerable_packages'] == 
                                   package_lock_summary['vulnerable_packages'])
        
        # Package-level analysis
        json_packages = package_json_summary['package_names']
        lock_packages = package_lock_summary['package_names']
        
        missing_in_lock = json_packages - lock_packages
        missing_in_json = lock_packages - json_packages
        common_packages = json_packages & lock_packages
        
        # Vulnerability count differences by package
        vuln_count_differences = {}
        for package in common_packages:
            json_count = len(package_json_summary['vulnerabilities_by_package'].get(package, []))
            lock_count = len(package_lock_summary['vulnerabilities_by_package'].get(package, []))
            
            if json_count != lock_count:
                vuln_count_differences[package] = {
                    'package_json': json_count,
                    'package_lock': lock_count,
                    'difference': abs(json_count - lock_count)
                }
        
        # Severity distribution comparison
        severity_differences = {}
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            json_count = package_json_summary['severity_counts'][severity]
            lock_count = package_lock_summary['severity_counts'][severity]
            if json_count != lock_count:
                severity_differences[severity] = {
                    'package_json': json_count,
                    'package_lock': lock_count,
                    'difference': abs(json_count - lock_count)
                }
        
        # Overall consistency assessment
        is_consistent = (
            vuln_count_match and
            vulnerable_packages_match and
            len(missing_in_lock) == 0 and
            len(missing_in_json) == 0 and
            len(vuln_count_differences) == 0
        )
        
        # Dependency count difference (expected to be different)
        dep_count_difference = abs(
            package_json_summary['total_dependencies'] - 
            package_lock_summary['total_dependencies']
        )
        
        return {
            'overall': {
                'is_consistent': is_consistent,
                'vulnerability_count_match': vuln_count_match,
                'vulnerable_packages_match': vulnerable_packages_match,
                'dependency_count_difference': dep_count_difference
            },
            'packages': {
                'missing_in_package_lock': list(missing_in_lock),
                'missing_in_package_json': list(missing_in_json),
                'common_packages': list(common_packages),
                'vulnerability_count_differences': vuln_count_differences
            },
            'severity': {
                'differences': severity_differences
            },
            'metrics': {
                'package_json': {
                    'vulnerabilities': package_json_summary['total_vulnerabilities'],
                    'dependencies': package_json_summary['total_dependencies'],
                    'vulnerable_packages': package_json_summary['vulnerable_packages']
                },
                'package_lock': {
                    'vulnerabilities': package_lock_summary['total_vulnerabilities'],
                    'dependencies': package_lock_summary['total_dependencies'],
                    'vulnerable_packages': package_lock_summary['vulnerable_packages']
                }
            }
        }
    
    @staticmethod
    def generate_recommendations(analysis: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Generate recommendations and warnings based on analysis"""
        
        recommendations = []
        warnings = []
        
        if analysis['overall']['is_consistent']:
            recommendations.append("✅ Scan results are consistent between package.json and package-lock.json")
            recommendations.append("Both files can be used reliably for vulnerability scanning")
        else:
            warnings.append("⚠️ Inconsistencies detected between package.json and package-lock.json scans")
            
            # Specific inconsistency recommendations
            if not analysis['overall']['vulnerability_count_match']:
                pkg_json_vulns = analysis['metrics']['package_json']['vulnerabilities']
                pkg_lock_vulns = analysis['metrics']['package_lock']['vulnerabilities']
                
                warnings.append(f"Different vulnerability counts: {pkg_json_vulns} vs {pkg_lock_vulns}")
                
                if pkg_lock_vulns > pkg_json_vulns:
                    recommendations.append("📋 Consider using package-lock.json scan results - it found more vulnerabilities")
                    recommendations.append("This may indicate version range resolution differences")
                else:
                    recommendations.append("📋 Package.json scan found more vulnerabilities")
                    recommendations.append("This may indicate different dependency parsing logic")
            
            # Missing packages
            if analysis['packages']['missing_in_package_lock']:
                warnings.append(f"Packages only found in package.json: {analysis['packages']['missing_in_package_lock']}")
                recommendations.append("Ensure package-lock.json is up to date with package.json")
            
            if analysis['packages']['missing_in_package_json']:
                warnings.append(f"Packages only found in package-lock.json: {analysis['packages']['missing_in_package_json']}")
                recommendations.append("This may indicate transitive dependencies being scanned")
            
            # Per-package differences
            if analysis['packages']['vulnerability_count_differences']:
                warnings.append("Per-package vulnerability count differences found:")
                for package, diff in analysis['packages']['vulnerability_count_differences'].items():
                    warnings.append(f"  • {package}: {diff['package_json']} vs {diff['package_lock']} vulnerabilities")
                recommendations.append("Consider regenerating package-lock.json to ensure consistency")
            
            # Severity differences
            if analysis['severity']['differences']:
                warnings.append("Severity distribution differences found")
                recommendations.append("Review individual vulnerability details to understand severity discrepancies")
        
        # Dependency count guidance
        dep_diff = analysis['overall']['dependency_count_difference']
        if dep_diff > 0:
            if analysis['metrics']['package_lock']['dependencies'] > analysis['metrics']['package_json']['dependencies']:
                recommendations.append(f"✓ Package-lock.json includes {dep_diff} additional transitive dependencies (expected)")
            else:
                warnings.append(f"⚠️ Package.json has {dep_diff} more dependencies than package-lock.json (unusual)")
                recommendations.append("Consider updating package-lock.json")
        
        return recommendations, warnings
    
    @staticmethod
    async def validate_consistency(manifest_files: Dict[str, str], 
                                  include_dev: bool = False,
                                  ignore_severities: Optional[List[str]] = None) -> ConsistencyValidationResult:
        """
        Validate consistency between package.json and package-lock.json
        
        Args:
            manifest_files: Dictionary with file contents (must contain both package.json and package-lock.json)
            include_dev: Include development dependencies
            ignore_severities: List of severities to ignore
            
        Returns:
            ConsistencyValidationResult with detailed analysis
        """
        result = ConsistencyValidationResult()
        
        if ignore_severities is None:
            ignore_severities = []
        
        # Check that both files are provided
        has_package_json = 'package.json' in manifest_files
        has_package_lock = 'package-lock.json' in manifest_files
        
        if not (has_package_json and has_package_lock):
            result.errors.append("Both package.json and package-lock.json are required for consistency validation")
            return result
        
        try:
            # Scan package.json only
            logger.info("Scanning package.json for consistency validation")
            package_json_files = {'package.json': manifest_files['package.json']}
            result.package_json_result = await CLIService.run_cli_scan_async(
                manifest_files=package_json_files,
                include_dev=include_dev,
                ignore_severities=ignore_severities
            )
            
            # Scan package-lock.json only
            logger.info("Scanning package-lock.json for consistency validation")
            package_lock_files = {'package-lock.json': manifest_files['package-lock.json']}
            result.package_lock_result = await CLIService.run_cli_scan_async(
                manifest_files=package_lock_files,
                include_dev=include_dev,
                ignore_severities=ignore_severities
            )
            
            # Extract summaries
            package_json_summary = ConsistencyService.extract_vulnerability_summary(result.package_json_result)
            package_lock_summary = ConsistencyService.extract_vulnerability_summary(result.package_lock_result)
            
            # Analyze consistency
            result.analysis = ConsistencyService.analyze_consistency(
                package_json_summary, 
                package_lock_summary
            )
            
            # Generate recommendations
            result.recommendations, result.warnings = ConsistencyService.generate_recommendations(result.analysis)
            
            # Set overall consistency flag
            result.is_consistent = result.analysis['overall']['is_consistent']
            
            logger.info(f"Consistency validation completed: {'consistent' if result.is_consistent else 'inconsistent'}")
            
        except Exception as e:
            error_msg = f"Error during consistency validation: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)
        
        return result