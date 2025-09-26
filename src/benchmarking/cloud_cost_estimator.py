#!/usr/bin/env python3
"""
Cloud Cost Estimator for Document Parsing

Estimates costs for using cloud APIs like AWS Textract and Google Document AI
based on public pricing information.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


class CloudCostEstimator:
    """Estimates costs for cloud document parsing services."""
    
    def __init__(self):
        # Public pricing as of 2024 (per page/request)
        self.pricing = {
            'aws_textract': {
                'detect_text': 0.0015,  # $1.50 per 1000 pages
                'analyze_document': 0.050,  # $50 per 1000 pages  
                'analyze_expense': 0.050,   # $50 per 1000 pages
                'analyze_id': 0.040,        # $40 per 1000 pages
                'detect_text_queries': 0.0065  # $6.50 per 1000 pages
            },
            'google_document_ai': {
                'ocr_processor': 0.0015,    # $1.50 per 1000 pages
                'form_parser': 0.050,       # $50 per 1000 pages
                'document_splitter': 0.0010, # $1.00 per 1000 pages
                'layout_parser': 0.010,     # $10 per 1000 pages
                'specialized_parser': 0.100  # $100 per 1000 pages (varies by type)
            },
            'azure_form_recognizer': {
                'layout': 0.010,           # $10 per 1000 pages
                'general_document': 0.050,  # $50 per 1000 pages
                'prebuilt_invoice': 0.050,  # $50 per 1000 pages
                'prebuilt_receipt': 0.050,  # $50 per 1000 pages
                'custom_model': 0.050       # $50 per 1000 pages
            }
        }
        
        # Additional costs (data transfer, storage, etc.)
        self.additional_costs = {
            'data_transfer_gb': 0.09,  # $0.09 per GB outbound
            'storage_gb_month': 0.023,  # $0.023 per GB per month
            'api_requests_1000': 0.40   # $0.40 per 1000 API requests (typical)
        }
    
    def estimate_costs_for_volume(self, pages: int, documents: int = None) -> Dict[str, Any]:
        """Estimate costs for processing a given volume of pages."""
        if documents is None:
            documents = max(1, pages // 50)  # Assume ~50 pages per document average
            
        estimates = {
            'volume_info': {
                'total_pages': pages,
                'estimated_documents': documents,
                'avg_pages_per_document': pages / documents,
                'timestamp': datetime.now().isoformat()
            },
            'service_costs': {},
            'comparison': {},
            'recommendations': []
        }
        
        # Calculate costs for each service
        for service_name, service_pricing in self.pricing.items():
            service_costs = {}
            
            for processor_name, cost_per_page in service_pricing.items():
                total_cost = pages * cost_per_page
                service_costs[processor_name] = {
                    'cost_per_page': cost_per_page,
                    'total_cost_usd': round(total_cost, 2),
                    'cost_per_document': round(total_cost / documents, 3),
                    'monthly_cost_1000_pages': round(1000 * cost_per_page, 2)
                }
            
            estimates['service_costs'][service_name] = service_costs
        
        # Add data transfer and storage estimates
        estimated_output_size_gb = pages * 0.1 / 1024  # ~100KB per page output
        estimated_storage_cost = estimated_output_size_gb * self.additional_costs['storage_gb_month']
        estimated_transfer_cost = estimated_output_size_gb * self.additional_costs['data_transfer_gb']
        
        estimates['additional_costs'] = {
            'estimated_output_size_gb': round(estimated_output_size_gb, 3),
            'storage_cost_per_month_usd': round(estimated_storage_cost, 3),
            'data_transfer_cost_usd': round(estimated_transfer_cost, 3),
            'api_request_cost_usd': round((documents / 1000) * self.additional_costs['api_requests_1000'], 3)
        }
        
        # Generate comparison
        estimates['comparison'] = self._generate_cost_comparison(estimates['service_costs'], pages)
        
        # Generate recommendations
        estimates['recommendations'] = self._generate_cost_recommendations(estimates, pages)
        
        return estimates
    
    def _generate_cost_comparison(self, service_costs: Dict, pages: int) -> Dict[str, Any]:
        """Generate cost comparison between services."""
        comparison = {
            'lowest_cost_basic': None,
            'lowest_cost_advanced': None,
            'cost_range_basic': {},
            'cost_range_advanced': {},
            'service_rankings': []
        }
        
        # Categorize processors
        basic_processors = [
            ('aws_textract', 'detect_text'),
            ('google_document_ai', 'ocr_processor'),
            ('azure_form_recognizer', 'layout')
        ]
        
        advanced_processors = [
            ('aws_textract', 'analyze_document'),
            ('google_document_ai', 'form_parser'),
            ('azure_form_recognizer', 'general_document')
        ]
        
        # Find lowest cost basic option
        basic_costs = []
        for service, processor in basic_processors:
            if service in service_costs and processor in service_costs[service]:
                cost = service_costs[service][processor]['total_cost_usd']
                basic_costs.append((f"{service}_{processor}", cost))
        
        if basic_costs:
            basic_costs.sort(key=lambda x: x[1])
            comparison['lowest_cost_basic'] = {
                'service': basic_costs[0][0],
                'cost_usd': basic_costs[0][1]
            }
            comparison['cost_range_basic'] = {
                'min_usd': basic_costs[0][1],
                'max_usd': basic_costs[-1][1],
                'savings_vs_highest': round(((basic_costs[-1][1] - basic_costs[0][1]) / basic_costs[-1][1]) * 100, 1)
            }
        
        # Find lowest cost advanced option
        advanced_costs = []
        for service, processor in advanced_processors:
            if service in service_costs and processor in service_costs[service]:
                cost = service_costs[service][processor]['total_cost_usd']
                advanced_costs.append((f"{service}_{processor}", cost))
        
        if advanced_costs:
            advanced_costs.sort(key=lambda x: x[1])
            comparison['lowest_cost_advanced'] = {
                'service': advanced_costs[0][0],
                'cost_usd': advanced_costs[0][1]
            }
            comparison['cost_range_advanced'] = {
                'min_usd': advanced_costs[0][1],
                'max_usd': advanced_costs[-1][1],
                'savings_vs_highest': round(((advanced_costs[-1][1] - advanced_costs[0][1]) / advanced_costs[-1][1]) * 100, 1)
            }
        
        # Service rankings
        all_services = basic_costs + advanced_costs
        all_services.sort(key=lambda x: x[1])
        
        comparison['service_rankings'] = [
            {'rank': i+1, 'service': service, 'cost_usd': cost}
            for i, (service, cost) in enumerate(all_services[:10])  # Top 10
        ]
        
        return comparison
    
    def _generate_cost_recommendations(self, estimates: Dict, pages: int) -> List[str]:
        """Generate cost optimization recommendations."""
        recommendations = []
        
        # Volume-based recommendations
        if pages < 1000:
            recommendations.append("For small volumes (<1000 pages), basic OCR services are most cost-effective")
        elif pages < 10000:
            recommendations.append("For medium volumes (1K-10K pages), consider batch processing discounts")
        else:
            recommendations.append("For large volumes (>10K pages), negotiate custom pricing or consider hybrid approaches")
        
        # Service-specific recommendations
        lowest_basic = estimates['comparison'].get('lowest_cost_basic')
        if lowest_basic:
            recommendations.append(f"Most cost-effective basic option: {lowest_basic['service']} at ${lowest_basic['cost_usd']}")
        
        lowest_advanced = estimates['comparison'].get('lowest_cost_advanced')
        if lowest_advanced:
            recommendations.append(f"Most cost-effective advanced option: {lowest_advanced['service']} at ${lowest_advanced['cost_usd']}")
        
        # Cost optimization strategies
        total_advanced_cost = lowest_advanced['cost_usd'] if lowest_advanced else 0
        total_basic_cost = lowest_basic['cost_usd'] if lowest_basic else 0
        
        if total_advanced_cost > total_basic_cost * 10:
            recommendations.append("Advanced features cost 10x+ more - evaluate if complexity justifies the cost")
        
        # Hybrid approach recommendations
        if pages > 5000:
            recommendations.append("Consider hybrid approach: use open-source for simple pages, cloud APIs for complex documents")
        
        # Volume discounts
        monthly_pages = pages  # Assuming this is monthly volume
        if monthly_pages > 100000:
            recommendations.append("At this volume, custom enterprise pricing negotiations could save 20-50%")
        
        return recommendations
    
    def compare_with_open_source_costs(self, pages: int, benchmark_results: Dict = None) -> Dict[str, Any]:
        """Compare cloud costs with open-source infrastructure costs."""
        comparison = {
            'cloud_vs_open_source': {},
            'break_even_analysis': {},
            'infrastructure_costs': {},
            'recommendations': []
        }
        
        # Get cloud cost estimates
        cloud_estimates = self.estimate_costs_for_volume(pages)
        lowest_cloud_cost = cloud_estimates['comparison']['lowest_cost_basic']['cost_usd']
        
        # Estimate open-source infrastructure costs
        if benchmark_results:
            # Use actual benchmark data
            processing_time_hours = benchmark_results.get('summary', {}).get('total_runtime_seconds', 0) / 3600
            pages_processed = benchmark_results.get('summary', {}).get('total_pages_processed', 1)
            
            # Scale to target volume
            estimated_processing_hours = (pages / pages_processed) * processing_time_hours
        else:
            # Use estimates: ~150 pages/minute from our benchmark
            estimated_processing_hours = pages / (150 * 60)  # 150 pages per minute
        
        # Infrastructure cost estimates (AWS EC2/Azure VM)
        instance_costs = {
            'cpu_optimized': {
                'cost_per_hour': 0.192,  # c5.large equivalent
                'description': 'CPU-optimized instance'
            },
            'gpu_accelerated': {
                'cost_per_hour': 0.526,  # p3.2xlarge equivalent
                'description': 'GPU-accelerated instance'
            },
            'memory_optimized': {
                'cost_per_hour': 0.201,  # r5.large equivalent
                'description': 'Memory-optimized instance'
            }
        }
        
        infrastructure_costs = {}
        for instance_type, specs in instance_costs.items():
            compute_cost = estimated_processing_hours * specs['cost_per_hour']
            
            # Add storage and data transfer
            storage_cost = (pages * 0.1 / 1024) * 0.023  # ~100KB per page
            data_transfer_cost = (pages * 0.1 / 1024) * 0.09
            
            total_cost = compute_cost + storage_cost + data_transfer_cost
            
            infrastructure_costs[instance_type] = {
                'compute_cost_usd': round(compute_cost, 2),
                'storage_cost_usd': round(storage_cost, 3),
                'data_transfer_cost_usd': round(data_transfer_cost, 3),
                'total_cost_usd': round(total_cost, 2),
                'processing_hours': round(estimated_processing_hours, 2),
                'description': specs['description']
            }
        
        comparison['infrastructure_costs'] = infrastructure_costs
        
        # Break-even analysis
        cheapest_infrastructure = min(infrastructure_costs.values(), key=lambda x: x['total_cost_usd'])
        
        comparison['break_even_analysis'] = {
            'cloud_cost_usd': lowest_cloud_cost,
            'cheapest_infrastructure_cost_usd': cheapest_infrastructure['total_cost_usd'],
            'savings_with_infrastructure': round(lowest_cloud_cost - cheapest_infrastructure['total_cost_usd'], 2),
            'cost_ratio_cloud_vs_infrastructure': round(lowest_cloud_cost / cheapest_infrastructure['total_cost_usd'], 1),
            'break_even_volume_pages': self._calculate_break_even_volume()
        }
        
        # Recommendations
        if cheapest_infrastructure['total_cost_usd'] < lowest_cloud_cost * 0.5:
            comparison['recommendations'].append("Open-source infrastructure is significantly cheaper (>50% savings)")
        elif cheapest_infrastructure['total_cost_usd'] < lowest_cloud_cost:
            comparison['recommendations'].append("Open-source infrastructure offers modest savings")
        else:
            comparison['recommendations'].append("Cloud services are more cost-effective at this volume")
        
        if pages > 10000:
            comparison['recommendations'].append("At high volumes, dedicated infrastructure becomes increasingly attractive")
        
        comparison['recommendations'].append("Consider development and maintenance costs when comparing")
        comparison['recommendations'].append("Cloud services offer faster time-to-market and managed infrastructure")
        
        return comparison
    
    def _calculate_break_even_volume(self) -> int:
        """Calculate the volume where infrastructure becomes cheaper than cloud."""
        # Simplified calculation - would need more detailed modeling in practice
        return 50000  # Rough estimate: 50K pages/month
    
    def save_cost_analysis(self, pages: int, benchmark_results: Dict = None) -> Path:
        """Generate and save comprehensive cost analysis."""
        analysis = {
            'analysis_info': {
                'timestamp': datetime.now().isoformat(),
                'pages_analyzed': pages,
                'pricing_date': '2024-09-26',
                'note': 'Costs based on public pricing - actual costs may vary'
            },
            'cloud_cost_estimates': self.estimate_costs_for_volume(pages),
            'infrastructure_comparison': self.compare_with_open_source_costs(pages, benchmark_results)
        }
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = Path(f"../../benchmarks/results/cost_analysis_{timestamp}.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        return output_file


if __name__ == "__main__":
    estimator = CloudCostEstimator()
    
    # Test with our benchmark volume
    test_pages = 1000  # 1K pages for analysis
    
    print("💰 Cloud Cost Analysis for Document Parsing")
    print("=" * 60)
    
    # Load benchmark results if available
    benchmark_file = None
    results_dir = Path("../../benchmarks/results")
    if results_dir.exists():
        benchmark_files = list(results_dir.glob("pipeline_benchmark_*.json"))
        if benchmark_files:
            benchmark_file = max(benchmark_files)  # Most recent
            with open(benchmark_file) as f:
                benchmark_data = json.load(f)
        else:
            benchmark_data = None
    else:
        benchmark_data = None
    
    # Generate cost analysis
    output_file = estimator.save_cost_analysis(test_pages, benchmark_data)
    
    # Display summary
    cost_estimates = estimator.estimate_costs_for_volume(test_pages)
    
    print(f"Analysis for {test_pages} pages:")
    print(f"Estimated documents: {cost_estimates['volume_info']['estimated_documents']}")
    
    if 'lowest_cost_basic' in cost_estimates['comparison']:
        basic = cost_estimates['comparison']['lowest_cost_basic']
        print(f"Cheapest basic option: {basic['service']} - ${basic['cost_usd']}")
    
    if 'lowest_cost_advanced' in cost_estimates['comparison']:
        advanced = cost_estimates['comparison']['lowest_cost_advanced']
        print(f"Cheapest advanced option: {advanced['service']} - ${advanced['cost_usd']}")
    
    print(f"\\nDetailed analysis saved to: {output_file}")
    
    print(f"\\n💡 Key Recommendations:")
    for rec in cost_estimates['recommendations'][:3]:
        print(f"  - {rec}")
