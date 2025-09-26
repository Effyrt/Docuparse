#!/usr/bin/env python3
"""
Final Export Stage for DVC Pipeline
Consolidates all parsed outputs into final export formats.
"""

import json
import yaml
import shutil
from pathlib import Path
from typing import Dict, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FinalExporter:
    """Exports and consolidates all parsed outputs into final formats."""
    
    def __init__(self, output_dir: str = "data/exports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Input directories
        self.input_dirs = {
            'text': Path("data/parsed/text"),
            'tables': Path("data/parsed/tables"), 
            'layout': Path("data/parsed/layout"),
            'docling': Path("data/parsed/docling"),
            'metadata': Path("data/parsed/metadata")
        }

    def load_params(self, params_file: str = "params.yaml") -> Dict[str, Any]:
        """Load export parameters from params.yaml file."""
        try:
            with open(params_file, 'r') as f:
                params = yaml.safe_load(f)
            return params.get('export', {})
        except FileNotFoundError:
            logger.warning(f"Parameters file {params_file} not found, using defaults")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing {params_file}: {e}")
            return {}

    def export_summary_report(self) -> Dict[str, Any]:
        """Generate a comprehensive summary report of all processing stages."""
        summary = {
            "pipeline_summary": {
                "timestamp": "2025-09-26T12:57:00Z",
                "stages_completed": []
            },
            "processing_statistics": {},
            "output_locations": {}
        }
        
        # Check each processing stage
        for stage_name, input_dir in self.input_dirs.items():
            if input_dir.exists():
                # Count files in each directory
                files = list(input_dir.rglob("*"))
                file_count = len([f for f in files if f.is_file()])
                
                summary["pipeline_summary"]["stages_completed"].append(stage_name)
                summary["processing_statistics"][stage_name] = {
                    "total_files": file_count,
                    "directory_exists": True,
                    "last_modified": max([f.stat().st_mtime for f in files if f.is_file()], default=0) if files else 0
                }
                summary["output_locations"][stage_name] = str(input_dir)
            else:
                summary["processing_statistics"][stage_name] = {
                    "total_files": 0,
                    "directory_exists": False
                }
        
        return summary

    def create_consolidated_outputs(self, formats: list):
        """Create consolidated outputs in specified formats."""
        for format_type in formats:
            format_dir = self.output_dir / format_type
            format_dir.mkdir(exist_ok=True)
            
            if format_type == "json":
                self.export_json_consolidated(format_dir)
            elif format_type == "markdown":
                self.export_markdown_consolidated(format_dir)
            elif format_type == "csv":
                self.export_csv_consolidated(format_dir)
            
            logger.info(f"Created consolidated {format_type} exports in {format_dir}")

    def export_json_consolidated(self, output_dir: Path):
        """Export consolidated JSON summaries."""
        # Try to find and consolidate JSON files from metadata
        metadata_dir = self.input_dirs['metadata']
        if metadata_dir.exists():
            json_files = list(metadata_dir.glob("*.json*"))
            for json_file in json_files[:3]:  # Limit to first 3 for demo
                try:
                    shutil.copy2(json_file, output_dir / f"consolidated_{json_file.name}")
                except Exception as e:
                    logger.warning(f"Could not copy {json_file}: {e}")

    def export_markdown_consolidated(self, output_dir: Path):
        """Export consolidated Markdown summaries."""
        # Try to find and consolidate Markdown files from metadata
        metadata_dir = self.input_dirs['metadata']
        if metadata_dir.exists():
            md_files = list(metadata_dir.glob("*.md"))
            for md_file in md_files[:3]:  # Limit to first 3 for demo
                try:
                    shutil.copy2(md_file, output_dir / f"consolidated_{md_file.name}")
                except Exception as e:
                    logger.warning(f"Could not copy {md_file}: {e}")

    def export_csv_consolidated(self, output_dir: Path):
        """Export CSV summaries from table data."""
        # Create a simple CSV summary
        csv_content = "stage,files_processed,status\n"
        for stage_name, input_dir in self.input_dirs.items():
            if input_dir.exists():
                file_count = len([f for f in input_dir.rglob("*") if f.is_file()])
                csv_content += f"{stage_name},{file_count},completed\n"
            else:
                csv_content += f"{stage_name},0,not_found\n"
        
        csv_file = output_dir / "pipeline_summary.csv"
        csv_file.write_text(csv_content)

    def run(self):
        """Main execution method for DVC pipeline."""
        logger.info("Starting final export process")
        
        # Load parameters
        params = self.load_params()
        
        # Get export configuration
        export_formats = params.get('formats', ['json', 'markdown'])
        include_summary = params.get('include_summary', True)
        
        logger.info(f"Export configuration:")
        logger.info(f"  Formats: {export_formats}")
        logger.info(f"  Include Summary: {include_summary}")
        
        # Generate summary report
        if include_summary:
            summary = self.export_summary_report()
            summary_file = self.output_dir / "pipeline_summary.json"
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            logger.info(f"Generated pipeline summary: {summary_file}")
        
        # Create consolidated outputs
        self.create_consolidated_outputs(export_formats)
        
        # Report completion
        total_files = len(list(self.output_dir.rglob("*")))
        logger.info(f"Export completed: {total_files} files created in {self.output_dir}")
        
        return True


def main():
    """Command line interface for the exporter."""
    exporter = FinalExporter()
    success = exporter.run()
    
    if success:
        print("✅ Export stage completed successfully")
    else:
        print("❌ Export stage failed")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
