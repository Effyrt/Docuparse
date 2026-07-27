#!/usr/bin/env python3
"""
SEC Filing Downloader for DVC Pipeline
Downloads 10-K or 10-Q filings based on company and fiscal year parameters.
"""

import os
import re
import sys
import yaml
import requests
import time
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SECDownloader:
    """Downloads SEC filings based on company and fiscal year parameters."""
    
    def __init__(self, output_dir: str = "data/raw"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # SEC API base URL
        self.sec_base_url = "https://www.sec.gov/Archives/edgar/data"
        
        # Company to CIK mapping (Central Index Key)
        self.company_cik_map = {
            "META": "0001326801",
            "AAPL": "0000320193", 
            "GOOGL": "0001652044",
            "MSFT": "0000789019",
            "AMZN": "0001018724"
        }
        
        # Pre-defined URLs for known filings (fallback)
        self.known_filings = {
            ("META", 2024, "10-K"): "https://drive.google.com/uc?export=download&id=1g2BpxM1T4lvxNrH3MCSJM0DNKLMi-J6B",
            ("META", 2024, "10-Q"): "https://drive.google.com/uc?export=download&id=1mGuAxXvKaXbi9_4XHxOmbRd8AlKM_rxA"
        }

    def load_params(self, params_file: str = "params.yaml") -> Dict[str, Any]:
        """Load parameters from params.yaml file."""
        try:
            with open(params_file, 'r') as f:
                params = yaml.safe_load(f)
            return params.get('download', {})
        except FileNotFoundError:
            logger.warning(f"Parameters file {params_file} not found, using defaults")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing {params_file}: {e}")
            return {}

    @staticmethod
    def _extract_gdrive_confirm_token(response: "requests.Response") -> Optional[str]:
        """Return Google Drive's download-confirmation token, if the response is an interstitial page.

        Large Google Drive files can't be virus-scanned, so the first request returns an
        HTML page instead of the file. We must resend the request with the confirm token to
        get the real bytes. Without this the downloader silently saves the HTML page as a PDF.
        """
        # Older style: token is set as a cookie named ``download_warning*``.
        for key, value in response.cookies.items():
            if key.startswith("download_warning"):
                return value

        # Newer style: token is embedded in the HTML form of the interstitial page.
        content_type = response.headers.get("Content-Type", "")
        if "text/html" in content_type:
            match = re.search(r'name="confirm"\s+value="([^"]+)"', response.text)
            if match:
                return match.group(1)
            match = re.search(r'confirm=([0-9A-Za-z_\-]+)', response.text)
            if match:
                return match.group(1)
        return None

    def download_file(self, url: str, output_path: Path, filename: str) -> bool:
        """Download a file from URL and verify it is a real PDF before keeping it."""
        file_path = output_path / filename
        try:
            logger.info(f"Downloading {filename} from {url}")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            session = requests.Session()
            response = session.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()

            # Handle Google Drive's large-file confirmation interstitial.
            if "drive.google.com" in url or "drive.usercontent.google.com" in url:
                token = self._extract_gdrive_confirm_token(response)
                if token:
                    logger.info("Google Drive confirmation required, retrying with token")
                    response = session.get(
                        url, headers=headers, params={'confirm': token},
                        stream=True, timeout=30
                    )
                    response.raise_for_status()

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            # Guard against silently saving an HTML error/interstitial page as a ".pdf".
            if not self._is_pdf(file_path):
                logger.error(
                    f"Downloaded {filename} is not a valid PDF (likely an HTML error page). "
                    "Discarding the file."
                )
                file_path.unlink(missing_ok=True)
                return False

            file_size = file_path.stat().st_size
            logger.info(f"Successfully downloaded {filename} ({file_size:,} bytes)")
            return True

        except requests.RequestException as e:
            logger.error(f"Failed to download {filename}: {e}")
            file_path.unlink(missing_ok=True)
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading {filename}: {e}")
            file_path.unlink(missing_ok=True)
            return False

    @staticmethod
    def _is_pdf(file_path: Path) -> bool:
        """Return True if the file starts with the PDF magic bytes (``%PDF``)."""
        try:
            with open(file_path, 'rb') as f:
                return f.read(5).startswith(b'%PDF')
        except OSError:
            return False

    def get_filing_url(self, company: str, fiscal_year: int, filing_type: str) -> Optional[str]:
        """Get the download URL for a specific filing."""
        # Check known filings first (fallback for reliable downloads)
        key = (company.upper(), fiscal_year, filing_type.upper())
        if key in self.known_filings:
            logger.info(f"Using known URL for {company} {fiscal_year} {filing_type}")
            return self.known_filings[key]
        
        # For other companies/years, you would implement SEC EDGAR API integration here
        logger.warning(f"No known URL for {company} {fiscal_year} {filing_type}")
        logger.info("To add more companies, update the known_filings dictionary or implement SEC API integration")
        return None

    def download_filings(self, companies: list, fiscal_years: list, filing_types: list) -> Dict[str, bool]:
        """Download specified filings for given companies and years."""
        results = {}

        for company in companies:
            for year in fiscal_years:
                for filing_type in filing_types:
                    # Organize downloads by filing type (e.g. data/raw/10-K/) so the
                    # downstream extractors, which read from data/raw/<FILING_TYPE>/,
                    # find their inputs. This also keeps dvc.yaml's `outs` consistent
                    # with what is actually produced.
                    filing_dir = self.output_dir / filing_type.upper()
                    filing_dir.mkdir(parents=True, exist_ok=True)

                    # Generate filename
                    filename = f"{year}_{company.lower()}_{filing_type.lower()}.pdf"

                    # Check if file already exists
                    file_path = filing_dir / filename
                    if file_path.exists():
                        logger.info(f"File already exists: {file_path}")
                        results[f"{company}_{year}_{filing_type}"] = True
                        continue

                    # Get download URL
                    url = self.get_filing_url(company, year, filing_type)
                    if not url:
                        logger.error(f"No URL found for {company} {year} {filing_type}")
                        results[f"{company}_{year}_{filing_type}"] = False
                        continue

                    # Download the file
                    success = self.download_file(url, filing_dir, filename)
                    results[f"{company}_{year}_{filing_type}"] = success
                    
                    # Small delay to be respectful to servers
                    time.sleep(1)
        
        return results

    def run(self):
        """Main execution method for DVC pipeline."""
        logger.info("Starting SEC filing download process")
        
        # Load parameters
        params = self.load_params()
        
        # Get configuration from parameters or use defaults
        companies = params.get('companies', ['META'])
        fiscal_years = params.get('fiscal_years', [2024])
        filing_types = params.get('filing_types', ['10-K', '10-Q'])
        
        logger.info(f"Download configuration:")
        logger.info(f"  Companies: {companies}")
        logger.info(f"  Fiscal Years: {fiscal_years}")
        logger.info(f"  Filing Types: {filing_types}")
        
        # Download filings
        results = self.download_filings(companies, fiscal_years, filing_types)
        
        # Report results
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        logger.info(f"Download completed: {successful}/{total} files successful")
        
        if successful == 0:
            logger.error("No files were downloaded successfully")
            sys.exit(1)
        elif successful < total:
            logger.warning(f"{total - successful} files failed to download")
        else:
            logger.info("All files downloaded successfully")
        
        return results


def main():
    """Command line interface for the downloader."""
    downloader = SECDownloader()
    results = downloader.run()
    
    # Print summary
    print("\n" + "="*50)
    print("DOWNLOAD SUMMARY")
    print("="*50)
    for filing, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{filing}: {status}")
    print("="*50)


if __name__ == "__main__":
    main()
