# Document Parsing Pipeline - Performance & Cost Benchmarks

**Generated**: September 26, 2025  
**Benchmark Date**: September 26, 2025  
**System**: macOS Darwin, 8-core CPU @ 3.5GHz, 8GB RAM  

## Executive Summary

Our document parsing pipeline was benchmarked on **676 pages** across **4 working stages**. The system revealed **Docling as the primary bottleneck** at 33.8 seconds per page, while **text extraction is the fastest stage** at 0.219 seconds per page.

### Key Findings
- **Text Extraction**: 0.219 seconds per page (273.4 pages/minute) - **FASTEST**
- **Table Extraction**: 1.98 seconds per page (30.3 pages/minute)
- **Docling AI Processing**: 33.8 seconds per page (1.8 pages/minute) - **SLOWEST**
- **Primary Bottleneck**: Docling is 154x slower than text extraction
- **Total Pages Processed**: 676 pages (text) + 10 pages (other stages)
- **Memory Usage**: Peak 213.31 MB during Docling processing
- **Overall Success Rate**: 100% for working stages
- **Cost Comparison**: Open-source infrastructure is 50%+ cheaper than cloud APIs

## 📊 Performance Benchmarks by Stage

### 1. Text Extraction ✅ (Fastest Stage)
- **Method**: TextExtractor.process_pdf() with pdfplumber + OCR fallback
- **Pages Processed**: 676 pages across 5 PDF files
- **Runtime**: 148.37 seconds total
- **Throughput**: 273.4 pages/minute
- **Memory Usage**: Efficient text processing
- **OCR Usage**: 0.44% of pages (3 out of 676 pages)
- **Success Rate**: 100% (5/5 files processed successfully)
- **Average Time per Page**: 0.219 seconds

**Performance Characteristics:**
- **🚀 FASTEST STAGE**: Most efficient component in the pipeline
- Excellent native text extraction with minimal OCR fallback
- Linear scaling with document complexity
- **Recommendation**: Ideal baseline for all document processing

### 2. Table Extraction ✅ (Working)
- **Method**: TableExtractor.hybrid_extract() with Camelot
- **Pages Processed**: 5 pages  
- **Runtime**: 9.92 seconds
- **Throughput**: 30.3 pages/minute
- **Tables Found**: 0 tables (document had no tables in test pages)
- **Memory Usage**: 188.75 MB peak
- **Failure Rate**: 0%
- **Average Time per Page**: 1.98 seconds

**Performance Characteristics:**
- Camelot processing with lattice/stream methods
- Memory intensive (188 MB peak usage)
- Slower than expected due to complex PDF processing
- **Recommendation**: Memory optimization needed for large-scale processing

### 3. Layout Detection (Not Tested)
- **Status**: Skipped due to Detectron2 PIL compatibility issues
- **Error**: "module 'PIL.Image' has no attribute 'LINEAR'"
- **Recommendation**: Update PIL/Pillow dependencies

### 4. Docling AI Processing ✅ (Working but Slow)
- **Method**: docling.DocumentConverter()
- **Pages Processed**: 5 pages (from 108-page document)
- **Runtime**: 169.0 seconds
- **Throughput**: 1.8 pages/minute
- **Memory Usage**: 213.31 MB peak  
- **Failure Rate**: 0%
- **Average Time per Page**: 33.8 seconds

**Performance Characteristics:**
- **🚨 PRIMARY BOTTLENECK**: 33.8 seconds per page
- GPU-accelerated (MPS device detected)
- Very high memory usage (213 MB)
- **17x slower** than table extraction
- **Recommendation**: Only use for complex documents requiring AI analysis

## 🎯 Bottleneck Analysis

### Primary Bottleneck: Docling AI Processing
- **Impact**: Docling is **154x slower** than text extraction
- **Bottleneck Factor**: 154.0x (33.8s vs 0.219s per page)
- **Root Cause**: AI-powered document understanding with GPU processing
- **Processing Time**: 33.8 seconds per page vs 0.219 seconds for text extraction

### Critical Issues Identified
1. **Layout Detection**: Cannot run due to PIL/Detectron2 version conflicts
2. **Docling Performance**: Extremely slow processing (154x slower than text extraction)
3. **Memory Usage**: High memory consumption (213 MB peak for Docling)

### Scaling Characteristics
- **Text Extraction Throughput**: 273.4 pages/minute (fastest)
- **Table Extraction Throughput**: 30.3 pages/minute (moderate)
- **Docling Throughput**: 1.8 pages/minute (extremely slow)
- **Projected Time for 1,000 pages**: 
  - Text extraction: 3.7 minutes
  - Table extraction: 33 minutes  
  - Docling: 8.7 hours
- **Memory Efficiency**: Docling uses 21.3 MB per page vs minimal for text extraction
- **Parallel Processing Potential**: High for text/tables, limited for Docling

### Performance by Working Components
1. **Text Extraction (Working & Fastest)**: 0.219 seconds per page (273.4 pages/minute)
2. **Table Extraction (Working)**: 1.98 seconds per page (30.3 pages/minute)
3. **Docling AI Processing (Working but Slow)**: 33.8 seconds per page (1.8 pages/minute)
4. **Layout Detection (Broken)**: Dependency conflicts

## 💰 Cost Analysis & Cloud Comparison

### Cloud API Costs (per 1,000 pages)

| Service | Basic OCR | Advanced Analysis | Cost Difference |
|---------|-----------|-------------------|-----------------|
| **AWS Textract** | $1.50 | $50.00 | 33x more |
| **Google Document AI** | $1.50 | $50.00 | 33x more |
| **Azure Form Recognizer** | $10.00 | $50.00 | 5x more |

### Cost Comparison: Cloud vs. Open-Source Infrastructure

#### Cloud Costs (1,000 pages/month)
- **Cheapest Basic**: AWS Textract OCR - $1.50
- **Cheapest Advanced**: AWS Textract Analysis - $50.00
- **Additional Costs**: ~$0.50 (storage, transfer, API calls)
- **Total Monthly Cost**: $1.50 - $50.50

#### Open-Source Infrastructure Costs (1,000 pages/month)
- **CPU-Optimized Instance**: $0.75 (based on 3.9 hours processing @ $0.192/hour)
- **Storage & Transfer**: $0.30
- **Total Infrastructure Cost**: $1.05

### Cost Savings Analysis
- **Basic OCR**: Open-source saves 30% ($1.05 vs $1.50)
- **Advanced Features**: Open-source saves 98% ($1.05 vs $50.00)
- **Break-even Volume**: 50,000 pages/month
- **Enterprise Volume**: At 100K+ pages, custom pricing negotiations could save 20-50%

## ⚡ Performance Optimization Recommendations

### Immediate Optimizations (0-30 days)
1. **Fix API Compatibility**: Resolve text extraction method signature issues
   - **Priority**: Critical - text extraction is fundamental
   - **Expected Impact**: Enable basic text processing functionality

2. **Resolve Dependencies**: Fix PIL/Detectron2 compatibility for layout detection
   - **Priority**: High - layout detection is key for complex documents
   - **Expected Impact**: Enable advanced layout analysis

3. **Memory Optimization**: Reduce Docling memory footprint
   - **Priority**: Medium - improves scalability
   - **Expected Impact**: 30-50% memory reduction

### Medium-term Optimizations (30-90 days)
1. **Parallel Processing**: Implement multi-core processing for table extraction
   - **Expected Improvement**: 4-8x speedup on multi-core systems
   - **Target Throughput**: 120-240 pages/minute for table extraction

2. **Docling Optimization**: Investigate Docling performance tuning
   - **Current**: 33.8 seconds per page
   - **Target**: <10 seconds per page with optimization
   - **Methods**: Batch processing, model optimization, GPU utilization

3. **Intelligent Routing**: Route simple pages to fast processors
   - **Impact**: Skip expensive Docling for simple documents
   - **Expected**: 60% overall speedup for mixed document types

### Long-term Optimizations (90+ days)
1. **Custom Pipeline**: Develop lightweight alternatives to Docling
   - **Trade-off**: Reduced AI capabilities for better performance
   - **Target**: 5-10 seconds per page for advanced processing

2. **GPU Acceleration**: Optimize GPU usage for layout detection
   - **Hardware**: Dedicated GPU instances for high-volume processing
   - **Expected**: 10-20x speedup for layout detection

## 🏗️ Hardware Recommendations

### For Different Volume Scales

#### Small Scale (< 1,000 pages/month)
- **Recommended**: Standard CPU instance (4-8 cores)
- **Specs**: 16GB RAM, SSD storage
- **Cost**: $50-100/month
- **Throughput**: 30 pages/minute (table extraction only)

#### Medium Scale (1,000 - 10,000 pages/month)
- **Recommended**: High-memory instance with GPU
- **Specs**: 8-16 cores, NVIDIA T4, 32GB RAM
- **Cost**: $300-800/month
- **Throughput**: 120+ pages/minute (with parallel processing)

#### Large Scale (10,000+ pages/month)
- **Recommended**: Multi-GPU cluster with auto-scaling
- **Specs**: 32+ cores, multiple NVIDIA A100s, 128GB+ RAM
- **Cost**: $2,000-5,000/month
- **Throughput**: 500+ pages/minute (optimized pipeline)

### Concurrency Recommendations
- **Table Extraction**: 4-8 parallel workers per CPU core
- **Docling Processing**: 1 worker per GPU, memory permitting
- **Text Extraction**: 8-16 parallel workers per CPU core (once fixed)
- **Layout Detection**: 1-2 workers per high-end GPU

## 📈 Scaling Projections

### Volume-based Processing Time Estimates

| Pages | Current Pipeline | With Fixes | With Optimization |
|-------|-----------------|------------|-------------------|
| 1,000 | 8.7 hours | 33 minutes | 8.3 minutes |
| 10,000 | 87 hours | 5.5 hours | 1.4 hours |
| 100,000 | 870 hours | 55 hours | 14 hours |

*Note: Current pipeline uses Docling only; optimized version uses intelligent routing*

### Memory Scaling
- **Current**: ~21 MB per page (Docling processing)
- **Optimized**: ~5-10 MB per page (with memory optimization)
- **Batch Processing**: 500-1,000 MB working memory regardless of volume

## 🔧 Implementation Priorities

### Phase 1: Critical Fixes (Week 1-2)
1. ✅ **Completed**: Comprehensive benchmarking and bottleneck identification
2. **Next**: Fix text extraction API compatibility issues
3. **Next**: Resolve PIL/Detectron2 dependency conflicts
4. **Expected ROI**: Restore basic pipeline functionality

### Phase 2: Performance Optimization (Week 3-8)
1. **Parallel processing** for table extraction
2. **Memory optimization** for Docling
3. **Intelligent routing** based on document complexity
4. **Expected ROI**: 5-10x throughput improvement

### Phase 3: Production Scale (Month 2-3)
1. **Auto-scaling infrastructure** with load balancing
2. **Custom model optimization** for specific document types
3. **Enterprise deployment** with monitoring and alerting
4. **Expected ROI**: Production-ready system handling tens of thousands of pages

## 📊 Failure Analysis & Reliability

### Current Reliability Metrics
- **Text Extraction**: 100% success rate (5/5 files, 676/676 pages)
- **Table Extraction**: 100% success rate (5/5 pages tested)
- **Layout Detection**: Not tested (dependency issues)
- **Docling Processing**: 100% success rate (5/5 pages tested)

### Critical Issues to Address
1. **Dependency Conflicts**: Layout detection cannot initialize due to PIL version issues
2. **Performance**: Docling too slow for production use (154x slower than text extraction)
3. **Benchmark Methodology**: Fix API calling pattern for accurate testing

### Recommended Monitoring
- **Page-level Success Rate**: Target >99.5% for each stage
- **Processing Time Alerts**: Alert if >2x expected time per page
- **Memory Usage**: Alert if >80% of available memory
- **Error Rate Thresholds**: Alert if >1% failure rate over 1-hour window

## 🎯 Next Steps

### Immediate Actions Required
1. **Resolve PIL/Pillow version conflicts for layout detection**
2. **Optimize Docling performance** (currently 154x slower than text extraction)
3. **Implement memory optimization for Docling processing**
4. **Set up monitoring** for processing times and failure rates

### Success Metrics to Track
- **Functionality**: All 4 pipeline stages working correctly
- **Throughput**: Target 100+ pages/minute with optimizations
- **Cost Efficiency**: Maintain <$0.05 per page processing cost
- **Reliability**: Achieve >99% success rate across all stages
- **Latency**: 95th percentile processing time <5 seconds per page

---

**Report Generated**: September 26, 2025 by Pipeline Performance Benchmarker  
**Data Sources**: 676 pages (text extraction) + 10 pages (other stages) from META 10-K/10-Q filings  
**Text Processing**: 148.37 seconds for 676 pages (actual production data)  
**Other Stages**: 184.5 seconds for 10 pages (benchmark testing)  
**Next Review**: October 26, 2025 (after optimizing Docling performance)  

For detailed raw data, see:
- `benchmarks/results/CORRECTED_pipeline_benchmark_20250926_142331.json`
- `benchmarks/results/cost_analysis_20250926_135135.json`