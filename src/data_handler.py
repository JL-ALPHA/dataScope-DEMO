# src/data_handler.py

# ----------------------------------------------------------------------
# Libraries
# ----------------------------------------------------------------------
import logging
import pandas as pd
from pathlib import Path
import csv
import os
from tqdm import tqdm
from tabulate import tabulate
from typing import List, Union, Dict, Tuple, Optional
import re
import chardet
import psutil

logger = logging.getLogger(__name__)

# Global variable to store the current file path
saved_filepath = None


# ----------------------------------------------------------------------
# File Validation and Auto-Detection Functions
# ----------------------------------------------------------------------

def detect_file_encoding(file_path: str, sample_size: int = 32768) -> Dict[str, any]:
    """
    Detect the encoding of a text file using chardet library.
    
    Parameters
    ----------
    file_path : str
        Path to the file to analyze
    sample_size : int, optional
        Number of bytes to read for detection (default: 32KB)
    
    Returns
    -------
    Dict[str, any]
        Dictionary containing detected encoding, confidence, and fallback options
    """
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(sample_size)
        
        detection = chardet.detect(raw_data)
        confidence = detection.get('confidence', 0)
        detected_encoding = detection.get('encoding', 'utf-8')
        
        # Define fallback encodings in order of preference
        fallback_encodings = ['utf-8', 'latin-1', 'cp1252', 'utf-16']
        
        return {
            'detected_encoding': detected_encoding,
            'confidence': confidence,
            'fallback_encodings': fallback_encodings,
            'is_high_confidence': confidence > 0.85,
            'detection_details': detection
        }
    except Exception as e:
        logger.warning("Failed to detect encoding for %s: %s", file_path, e)
        return {
            'detected_encoding': 'utf-8',
            'confidence': 0,
            'fallback_encodings': ['utf-8', 'latin-1', 'cp1252'],
            'is_high_confidence': False,
            'detection_details': None,
            'error': str(e)
        }


def detect_delimiter(file_path: str, encoding: str = 'utf-8', sample_lines: int = 10) -> Dict[str, any]:
    """
    Detect the delimiter of a CSV/text file using csv.Sniffer and heuristics.
    
    Parameters
    ----------
    file_path : str
        Path to the file to analyze
    encoding : str, optional
        Encoding to use when reading the file
    sample_lines : int, optional
        Number of lines to read for detection
    
    Returns
    -------
    Dict[str, any]
        Dictionary containing detected delimiter and confidence information
    """
    common_delimiters = [',', '\t', ';', '|', ':']
    
    try:
        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            # Read sample lines
            sample_lines_data = []
            for i, line in enumerate(f):
                if i >= sample_lines:
                    break
                sample_lines_data.append(line.strip())
            
            sample_text = '\n'.join(sample_lines_data)
        
        # Try csv.Sniffer first
        try:
            dialect = csv.Sniffer().sniff(sample_text, delimiters=''.join(common_delimiters))
            detected_delimiter = dialect.delimiter
            sniffer_success = True
        except csv.Error:
            detected_delimiter = None
            sniffer_success = False
        
        # Fallback to manual detection
        delimiter_scores = {}
        for delimiter in common_delimiters:
            scores = []
            for line in sample_lines_data:
                if line.strip():
                    count = line.count(delimiter)
                    scores.append(count)
            
            if scores:
                # Good delimiter should have consistent counts across lines
                avg_count = sum(scores) / len(scores)
                variance = sum((x - avg_count) ** 2 for x in scores) / len(scores)
                consistency = 1 / (1 + variance) if variance > 0 else 1
                delimiter_scores[delimiter] = {
                    'avg_count': avg_count,
                    'consistency': consistency,
                    'total_score': avg_count * consistency
                }
        
        # Find best delimiter from manual detection
        best_manual_delimiter = None
        if delimiter_scores:
            best_manual_delimiter = max(delimiter_scores.keys(), 
                                      key=lambda x: delimiter_scores[x]['total_score'])
        
        # Choose final delimiter
        if sniffer_success and detected_delimiter in common_delimiters:
            final_delimiter = detected_delimiter
            confidence = 0.9
            method = 'csv.Sniffer'
        elif best_manual_delimiter and delimiter_scores[best_manual_delimiter]['total_score'] > 1:
            final_delimiter = best_manual_delimiter
            confidence = min(0.8, delimiter_scores[best_manual_delimiter]['consistency'])
            method = 'heuristic'
        else:
            # Default based on file extension
            ext = Path(file_path).suffix.lower()
            if ext == '.tsv':
                final_delimiter = '\t'
            elif ext == '.csv':
                final_delimiter = ','
            else:
                final_delimiter = ','
            confidence = 0.3
            method = 'extension_default'
        
        return {
            'detected_delimiter': final_delimiter,
            'confidence': confidence,
            'method': method,
            'sniffer_result': detected_delimiter if sniffer_success else None,
            'delimiter_scores': delimiter_scores,
            'is_high_confidence': confidence > 0.7
        }
        
    except Exception as e:
        logger.warning("Failed to detect delimiter for %s: %s", file_path, e)
        return {
            'detected_delimiter': ',',
            'confidence': 0,
            'method': 'error_fallback',
            'error': str(e),
            'is_high_confidence': False
        }


def estimate_memory_usage(file_path: str) -> Dict[str, any]:
    """
    Estimate memory requirements for loading a file.
    
    Parameters
    ----------
    file_path : str
        Path to the file to analyze
    
    Returns
    -------
    Dict[str, any]
        Dictionary containing memory estimates and system information
    """
    try:
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        # Get system memory info
        memory = psutil.virtual_memory()
        available_memory_mb = memory.available / (1024 * 1024)
        total_memory_mb = memory.total / (1024 * 1024)
        
        # Estimate memory usage (rough heuristics)
        # Text files typically expand 2-4x in memory
        # Excel files can expand 3-6x
        # CSV files typically expand 2-3x
        ext = Path(file_path).suffix.lower()
        
        if ext in ['.csv', '.txt', '.tsv']:
            multiplier = 2.5
        elif ext in ['.xlsx', '.xls']:
            multiplier = 4.0
        else:
            multiplier = 3.0
        
        estimated_memory_mb = file_size_mb * multiplier
        
        # Safety recommendations
        memory_ratio = estimated_memory_mb / available_memory_mb
        
        if memory_ratio > 0.8:
            recommendation = "HIGH_RISK"
            warning_message = "File may consume too much memory. Consider chunking or using a machine with more RAM."
        elif memory_ratio > 0.5:
            recommendation = "MEDIUM_RISK"
            warning_message = "File will use significant memory. Monitor system performance."
        elif memory_ratio > 0.2:
            recommendation = "LOW_RISK"
            warning_message = "File should load safely but may slow down other applications."
        else:
            recommendation = "SAFE"
            warning_message = "File should load without memory concerns."
        
        return {
            'file_size_mb': round(file_size_mb, 2),
            'estimated_memory_mb': round(estimated_memory_mb, 2),
            'available_memory_mb': round(available_memory_mb, 2),
            'total_memory_mb': round(total_memory_mb, 2),
            'memory_ratio': round(memory_ratio, 3),
            'recommendation': recommendation,
            'warning_message': warning_message,
            'multiplier_used': multiplier
        }
        
    except Exception as e:
        logger.warning("Failed to estimate memory usage for %s: %s", file_path, e)
        return {
            'file_size_mb': 0,
            'estimated_memory_mb': 0,
            'available_memory_mb': 0,
            'total_memory_mb': 0,
            'memory_ratio': 0,
            'recommendation': "UNKNOWN",
            'warning_message': f"Could not estimate memory usage: {e}",
            'error': str(e)
        }


def validate_file_size(file_path: str, max_size_mb: int = 500) -> Dict[str, any]:
    """
    Validate file size and provide warnings for large files.
    
    Parameters
    ----------
    file_path : str
        Path to the file to check
    max_size_mb : int, optional
        Maximum recommended file size in MB
    
    Returns
    -------
    Dict[str, any]
        Dictionary containing size validation results
    """
    try:
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        if file_size_mb > max_size_mb:
            level = "WARNING"
            message = f"Large file detected ({file_size_mb:.1f} MB). Loading may take time."
        elif file_size_mb > max_size_mb * 2:
            level = "ERROR"
            message = f"Very large file ({file_size_mb:.1f} MB). Consider splitting or chunking."
        else:
            level = "OK"
            message = f"File size acceptable ({file_size_mb:.1f} MB)."
        
        return {
            'file_size_bytes': file_size_bytes,
            'file_size_mb': round(file_size_mb, 2),
            'max_size_mb': max_size_mb,
            'is_oversized': file_size_mb > max_size_mb,
            'level': level,
            'message': message
        }
        
    except Exception as e:
        logger.warning("Failed to validate file size for %s: %s", file_path, e)
        return {
            'file_size_bytes': 0,
            'file_size_mb': 0,
            'max_size_mb': max_size_mb,
            'is_oversized': False,
            'level': "ERROR",
            'message': f"Could not check file size: {e}",
            'error': str(e)
        }


def comprehensive_file_check(file_path: str) -> Dict[str, any]:
    """
    Perform comprehensive file validation including encoding, delimiter, and memory checks.
    
    Parameters
    ----------
    file_path : str
        Path to the file to analyze
    
    Returns
    -------
    Dict[str, any]
        Comprehensive validation results
    """
    results = {
        'file_path': file_path,
        'timestamp': pd.Timestamp.now().isoformat(),
        'checks_performed': []
    }
    
    # File size check
    try:
        size_check = validate_file_size(file_path)
        results['size_validation'] = size_check
        results['checks_performed'].append('size_validation')
    except Exception as e:
        results['size_validation'] = {'error': str(e)}
    
    # Memory estimation
    try:
        memory_check = estimate_memory_usage(file_path)
        results['memory_estimation'] = memory_check
        results['checks_performed'].append('memory_estimation')
    except Exception as e:
        results['memory_estimation'] = {'error': str(e)}
    
    # For text files, check encoding and delimiter
    ext = Path(file_path).suffix.lower()
    if ext in ['.csv', '.txt', '.tsv']:
        try:
            encoding_check = detect_file_encoding(file_path)
            results['encoding_detection'] = encoding_check
            results['checks_performed'].append('encoding_detection')
            
            # Use detected encoding for delimiter detection
            best_encoding = encoding_check.get('detected_encoding', 'utf-8')
            delimiter_check = detect_delimiter(file_path, encoding=best_encoding)
            results['delimiter_detection'] = delimiter_check
            results['checks_performed'].append('delimiter_detection')
            
        except Exception as e:
            results['encoding_detection'] = {'error': str(e)}
            results['delimiter_detection'] = {'error': str(e)}
    
    # Overall recommendation
    recommendations = []
    warnings = []
    
    # Size warnings
    if results.get('size_validation', {}).get('level') == 'WARNING':
        warnings.append("Large file detected - loading may be slow")
    elif results.get('size_validation', {}).get('level') == 'ERROR':
        warnings.append("Very large file - consider chunking")
    
    # Memory warnings
    memory_rec = results.get('memory_estimation', {}).get('recommendation', 'UNKNOWN')
    if memory_rec == 'HIGH_RISK':
        warnings.append("High memory usage expected - monitor system resources")
    elif memory_rec == 'MEDIUM_RISK':
        warnings.append("Significant memory usage expected")
    
    # Encoding confidence
    encoding_conf = results.get('encoding_detection', {}).get('confidence', 0)
    if encoding_conf < 0.7:
        warnings.append("Low confidence in encoding detection - verify manually if needed")
    
    # Delimiter confidence
    delimiter_conf = results.get('delimiter_detection', {}).get('confidence', 0)
    if delimiter_conf < 0.7:
        warnings.append("Low confidence in delimiter detection - verify manually if needed")
    
    results['overall_assessment'] = {
        'warnings': warnings,
        'recommendations': recommendations,
        'safe_to_proceed': len([w for w in warnings if 'very large' in w.lower()]) == 0
    }
    
    return results


# ----------------------------------------------------------------------
def save_filepath(path):
    """Save the file path to a module level variable for reuse.

    This helper allows other functions to easily retrieve the most
    recent file path.  A log entry and print statement are emitted so
    the user can trace when the path is set.
    """
    global saved_filepath
    saved_filepath = str(path)
    logger.info("File path saved: %s", saved_filepath)
    print(f"[Data Handler] Saved file path -> {saved_filepath}")


# ----------------------------------------------------------------------
def create_dataset_environment(dataset_name: str) -> dict:
    """Create a structured directory environment for the dataset."""
    documents_dir = Path.home() / "Documents"
    base_path = documents_dir / "ProtexxaDatascope" / dataset_name

    subdirs = {
        "stages": base_path / "stages",
        "process": base_path / "process",
        "garbage": base_path / "garbage",
        "chunks": base_path / "chunks",
        "converted": base_path / "converted",
    }

    for path in subdirs.values():
        path.mkdir(parents=True, exist_ok=True)

    return {"project": base_path, **subdirs}


def convert_to_csv(df: pd.DataFrame, original_path: str) -> Path:
    """Convert a DataFrame to CSV next to the original file.

    Parameters
    ----------
    df : pd.DataFrame
        Data to write out.
    original_path : str
        Location of the source file. The CSV will share this directory.

    Returns
    -------
    Path
        Path to the newly written CSV file.
    """
    csv_path = Path(original_path).with_suffix(".csv")
    df.to_csv(csv_path, index=False)
    logger.info("Converted %s to CSV -> %s", original_path, csv_path)
    print(f"[Data Handler] Converted {original_path} -> {csv_path}")
    return csv_path


def convert_txt_to_csv(txt_path: str) -> Path:
    """Convert a whitespace delimited TXT file to CSV.

    Parameters
    ----------
    txt_path : str
        Path to the TXT file to convert.

    Returns
    -------
    Path
        Location of the written CSV file.
    """
    df = pd.read_csv(txt_path, sep=r"\s+", engine="python")
    logger.info("Read TXT file %s with shape %s", txt_path, df.shape)
    print(f"[Data Handler] Loaded TXT file -> {txt_path}")
    return convert_to_csv(df, txt_path)


def convert_file(
    input_path: str,
    output_dir: str,
    target_format: str = "csv",
    progress_fn=None,
) -> Union[Path, List[Path]]:
    """Convert an input file to CSV or Excel. Supports robust TXT parsing by
    splitting on multiple delimiters, skipping blank lines, and merging extras into the last column."""
    # Prepare paths
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Helper to write DataFrame to file
    def _write(df: pd.DataFrame, suffix: str) -> Path:
        name = f"{input_path.stem}{suffix}.{target_format}"
        out_path = output_dir / name
        if target_format == "csv":
            df.to_csv(out_path, index=False)
        else:
            df.to_excel(out_path, index=False)
        return out_path

    # Progress: start
    if progress_fn:
        progress_fn(0, "Reading input")

    suffix = input_path.suffix.lower()
    outputs: List[Path] = []

    if suffix == ".txt":
        # Read lines and split by any of comma, tab, semicolon, or pipe
        delim_pattern = r"[,\t;|]+"
        records = []
        with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
            # Skip blank lines to find header
            for raw in f:
                header_line = raw.strip()
                if header_line:
                    break
            else:
                raise ValueError("Input TXT file is empty or has no header.")

            # Parse header
            headers = [h.strip() for h in re.split(delim_pattern, header_line) if h.strip()]
            n_cols = len(headers)

            # Process remaining lines
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                parts = [p.strip() for p in re.split(delim_pattern, line)]
                # Pad short rows
                if len(parts) < n_cols:
                    parts += [None] * (n_cols - len(parts))
                # Merge extras into last field
                if len(parts) > n_cols:
                    parts = parts[:n_cols-1] + [" ".join(parts[n_cols-1:])]
                records.append(parts)

        # Build DataFrame
        df = pd.DataFrame(records, columns=headers)
        outputs.append(_write(df, ""))

    else:
        # Fallback to pandas for known formats
        try:
            if suffix == ".csv":
                df = pd.read_csv(input_path)
            elif suffix in {".xls", ".xlsx"}:
                df = pd.read_excel(input_path)
            elif suffix == ".json":
                df = pd.read_json(input_path)
            elif suffix in {".parquet", ".pq"}:
                df = pd.read_parquet(input_path)
            elif suffix == ".tsv":
                df = pd.read_csv(input_path, sep="\t")
            else:
                raise ValueError(f"Unsupported format: {suffix}")
        except Exception as e:
            raise RuntimeError(f"Failed to parse input file: {e}")
        outputs.append(_write(df, ""))

    # Progress: write complete
    if progress_fn:
        progress_fn(100, "Conversion complete")

    # Log and return
    for out in outputs:
        print(f"[Data Handler] Converted {input_path} -> {out}")

    return outputs[0] if len(outputs) == 1 else outputs







def load_data(
    file_path: str,
    progress_fn=None,
    encoding: str = "auto",
    delimiter: str | None = None,
    perform_validation: bool = True,
):
    """Load a dataset with automatic encoding/delimiter detection and validation.

    Parameters
    ----------
    file_path : str
        Location of the dataset to load.
    progress_fn : callable, optional
        Callback accepting ``(percent, message)`` for UI updates.
    encoding : str, optional
        Text encoding to use. Use "auto" for automatic detection.
    delimiter : str | None, optional
        Specific delimiter to use when reading CSV or TXT. When ``None`` the
        function attempts auto-detection for text formats.
    perform_validation : bool, optional
        Whether to perform comprehensive file validation before loading.

    Returns
    -------
    tuple[pd.DataFrame | None, dict]
        The loaded data and validation results, or (None, validation_results) on failure.

    Notes
    -----
    ``pandas`` does not provide native progress callbacks.  For text based
    formats we therefore read the file in chunks and approximate progress
    based on the number of rows processed.  This approach keeps the UI
    responsive while large files are being loaded.
    """
    validation_results = {}
    
    try:
        if progress_fn:
            progress_fn(0, "Starting validation and load")

        # Perform comprehensive file validation
        if perform_validation:
            if progress_fn:
                progress_fn(5, "Validating file...")
            validation_results = comprehensive_file_check(file_path)
            
            # Check if it's safe to proceed
            if not validation_results.get('overall_assessment', {}).get('safe_to_proceed', True):
                logger.warning("File validation suggests unsafe to proceed: %s", file_path)
                return None, validation_results

        suffix = Path(file_path).suffix.lower()

        # Auto-detect encoding for text files
        if encoding == "auto" and suffix in {".csv", ".tsv", ".txt"}:
            if progress_fn:
                progress_fn(10, "Detecting encoding...")
            
            if 'encoding_detection' in validation_results:
                encoding_info = validation_results['encoding_detection']
            else:
                encoding_info = detect_file_encoding(file_path)
                validation_results['encoding_detection'] = encoding_info
            
            detected_encoding = encoding_info.get('detected_encoding', 'utf-8')
            confidence = encoding_info.get('confidence', 0)
            
            # Use detected encoding if confidence is reasonable
            if confidence > 0.7:
                final_encoding = detected_encoding
                logger.info("Using auto-detected encoding: %s (confidence: %.2f)", final_encoding, confidence)
            else:
                # Try fallback encodings
                final_encoding = 'utf-8'  # Safe default
                logger.warning("Low confidence encoding detection (%.2f), using UTF-8", confidence)
        else:
            final_encoding = encoding if encoding != "auto" else "utf-8"

        if suffix in {".csv", ".tsv", ".txt"}:
            # ------------------------------------------------------------------
            # For line-based text files we stream the data in chunks so that
            # the progress bar can be updated incrementally.  We first count the
            # lines to determine the total number of rows.  Progress is then
            # calculated from the proportion of processed rows.
            # ------------------------------------------------------------------
            if progress_fn:
                progress_fn(15, "Counting rows...")
            
            total_rows = sum(1 for _ in open(file_path, "r", encoding=final_encoding, errors='ignore'))
            logger.info("Total rows detected: %s", total_rows)
            print(f"[Data Handler] Total rows detected: {total_rows}")

            # Auto-detect delimiter
            if delimiter is None:
                if progress_fn:
                    progress_fn(20, "Detecting delimiter...")
                
                if 'delimiter_detection' in validation_results:
                    delimiter_info = validation_results['delimiter_detection']
                else:
                    delimiter_info = detect_delimiter(file_path, final_encoding)
                    validation_results['delimiter_detection'] = delimiter_info
                
                detected_delimiter = delimiter_info.get('detected_delimiter', ',')
                delimiter_confidence = delimiter_info.get('confidence', 0)
                
                logger.info("Auto-detected delimiter: '%s' (confidence: %.2f)", 
                           detected_delimiter, delimiter_confidence)
                sep = detected_delimiter
            else:
                sep = delimiter

            if progress_fn:
                progress_fn(25, "Loading data...")

            reader = pd.read_csv(
                file_path,
                sep=sep,
                chunksize=10000,
                encoding=final_encoding,
                engine="python" if suffix == ".txt" else "c",
                on_bad_lines='skip'  # Skip problematic lines
            )

            chunks = []
            rows_read = 0
            for chunk in reader:
                chunks.append(chunk)
                rows_read += len(chunk)
                if progress_fn and total_rows > 0:
                    progress = min(25 + (rows_read / total_rows * 65), 90)  # 25-90% for chunked reading
                    progress_fn(progress, f"Loading data ({rows_read:,}/{total_rows:,} rows)")
                    logger.debug("Loaded %s/%s rows", rows_read, total_rows)

            # Indicate we're combining the chunks
            if progress_fn:
                progress_fn(95, "Combining data chunks")
            
            df = pd.concat(chunks, ignore_index=True)

        elif suffix in {".xls", ".xlsx"}:
            if progress_fn:
                progress_fn(30, "Reading Excel file...")
            df = pd.read_excel(file_path)
        elif suffix == ".json":
            if progress_fn:
                progress_fn(30, "Reading JSON file...")
            df = pd.read_json(file_path)
        elif suffix in {".parquet", ".pq"}:
            if progress_fn:
                progress_fn(30, "Reading Parquet file...")
            df = pd.read_parquet(file_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

        if suffix != ".csv":
            if progress_fn:
                progress_fn(98, "Converting to CSV format")
            csv_path = convert_to_csv(df, file_path)
            save_filepath(csv_path)
        else:
            save_filepath(file_path)

        if progress_fn:
            progress_fn(100, "Load complete")

        # Add final data info to validation results
        validation_results['final_data_info'] = {
            'rows': len(df),
            'columns': len(df.columns),
            'encoding_used': final_encoding,
            'delimiter_used': sep if 'sep' in locals() else None,
            'memory_usage_mb': round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2)
        }

        logger.info("Successfully loaded data: %s rows, %s columns", len(df), len(df.columns))
        return df, validation_results
        
    except Exception as e:
        logger.error("Failed to load data: %s", e)
        print(f"[Data Handler] Error loading {file_path}: {e}")
        validation_results['load_error'] = str(e)
        return None, validation_results


def get_data_stats(df, file_path):
    """
    Returns a dict of human-readable info about the dataset.
    """
    try:
        row_count = len(df)
        file_size = os.path.getsize(file_path) / (1024 * 1024)

        return {
            "row_count": row_count,
            "file_size": file_size,
            "log1": f"[Data Handler] Loaded {row_count} rows.",
            "log2": f"[Data Handler] File size: {file_size:.2f} MB",
        }

    except Exception as e:
        logger.error(f"Error getting data stats: {e}")
        return {
            "row_count": 0,
            "file_size": 0,
            "log1": "[Data Handler] Failed to get row count.",
            "log2": "[Data Handler] Failed to calculate file size.",
        }


def split_into_chunks(
    dataset_name, input_file, chunk_size_mb=256, logger_fn=None, progress_fn=None
):
    """Split a CSV into smaller chunks with optional progress updates.

    Progress callbacks are throttled to roughly one percent increments to
    avoid overwhelming the UI while still providing frequent feedback.

    Parameters
    ----------
    dataset_name : str
        Name of the dataset. Used to create output folders.
    input_file : str
        Path to the CSV file to split.
    chunk_size_mb : int, optional
        Desired chunk size in megabytes. Defaults to ``256``.
    logger_fn : callable, optional
        Function used for log messages. ``print`` is used when omitted.
    progress_fn : callable, optional
        Callback invoked with ``(percent, message)`` as the file is processed.
    """

    try:
        paths = create_dataset_environment(dataset_name)
        output_dir = paths["chunks"]

        chunk_size_bytes = chunk_size_mb * 1024 * 1024
        base_filename = os.path.splitext(os.path.basename(input_file))[0]

        def log(msg):
            if logger_fn:
                logger_fn(msg)
            else:
                print(msg)

        log(f"Reading from: {input_file}")
        log(f"Writing chunks to: {output_dir}")
        log(f"Chunk size: {chunk_size_mb} MB")
        if progress_fn:
            progress_fn(0, "Starting chunking")

        total_bytes = os.path.getsize(input_file)

        with open(input_file, "r", encoding="utf-8") as infile:
            reader = csv.reader(infile)
            try:
                header = next(reader)
            except StopIteration:
                log("Error: File is empty or missing a header.")
                return {
                    "total_rows": 0,
                    "total_chunks": 0,
                    "output_dir": str(output_dir),
                }

            chunk_index = 0
            current_chunk = []
            current_chunk_size = 0
            row_count = 0
            bytes_read = 0
            # Track last reported progress to throttle updates to ~1% steps
            last_percent = 0

            for row in tqdm(reader, desc="Splitting CSV", unit="rows"):
                row_size = len(",".join(row).encode("utf-8"))

                if current_chunk_size + row_size > chunk_size_bytes:
                    output_file = os.path.join(
                        output_dir, f"{base_filename}_chunk_{chunk_index}.csv"
                    )
                    with open(
                        output_file, "w", encoding="utf-8", newline=""
                    ) as outfile:
                        writer = csv.writer(outfile)
                        writer.writerow(header)
                        writer.writerows(current_chunk)
                    log(f"Chunk {chunk_index} written: {len(current_chunk)} rows")

                    chunk_index += 1
                    current_chunk = []
                    current_chunk_size = 0

                current_chunk.append(row)
                current_chunk_size += row_size
                row_count += 1
                bytes_read += row_size
                if progress_fn and total_bytes > 0:
                    progress = bytes_read / total_bytes * 100
                    if progress - last_percent >= 1:
                        progress_fn(min(progress, 99), "Chunking")
                        logger.debug("Chunking progress: %.2f%%", progress)
                        print(f"[Data Handler] Progress: {progress:.2f}%")
                        last_percent = progress

            # Final chunk
            if current_chunk:
                output_file = os.path.join(
                    output_dir, f"{base_filename}_chunk_{chunk_index}.csv"
                )
                with open(output_file, "w", encoding="utf-8", newline="") as outfile:
                    writer = csv.writer(outfile)
                    writer.writerow(header)
                    writer.writerows(current_chunk)
                log(f"Final chunk {chunk_index} written: {len(current_chunk)} rows")
                bytes_read += sum(
                    len(",".join(r).encode("utf-8")) for r in current_chunk
                )

        log(f"All chunks written. Total rows: {row_count}")
        log(f"Output directory contents: {os.listdir(output_dir)}")

        if progress_fn:
            progress_fn(100, "Chunking complete")

        return {
            "total_rows": row_count,
            "total_chunks": chunk_index + 1,
            "output_dir": str(output_dir),
        }

    except FileNotFoundError as e:
        logging.error(f"File not found: {e}")
        if logger_fn:
            logger_fn(f"Error: {e}")
    except PermissionError as e:
        logging.error(f"Permission error: {e}")
        if logger_fn:
            logger_fn(f"Error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        if logger_fn:
            logger_fn(f"Unexpected error: {e}")

    return {"total_rows": 0, "total_chunks": 0, "output_dir": ""}


# SOURCE APP FUNCTIONALITY BUILDOUT (SEAN)
PLACEHOLDERS = {
    "N/A",
    "NA",
    "None",
    "none",
    "unknown",
    "Unknown",
    "-",
    "TBD",
    "tbd",
    "0000",
    "",
    "null",
    "NULL",
    "n/a",
}


def run_analysis(
    df: pd.DataFrame,
    analysis_type: str,
    column: str = None,
    num_rows: int = 10,
    sort_desc: bool = False,
) -> str:
    """
    Dispatch to one of:
      - Data Preview
      - Missing Values
      - Duplicate Detection
      - Placeholder Detection
      - Special Character Analysis
    Returns a formatted string.
    """
    # subset + sort
    working = df[[column]] if column and column in df.columns else df.copy()
    if sort_desc:
        working = working.iloc[::-1]

    if analysis_type == "Data Preview":
        preview = working.head(num_rows)
        dtypes = [(c, str(t)) for c, t in working.dtypes.items()]
        return (
            "[Data Types]\n"
            + tabulate(dtypes, headers=["Column", "Dtype"], tablefmt="fancy_grid")
            + "\n\n[Preview]\n"
            + tabulate(preview, headers="keys", tablefmt="fancy_grid")
        )

    if analysis_type == "Missing Values":
        miss = working.isnull().sum()
        total = len(working)
        rows = [
            (c, int(cnt), f"{cnt/total*100:.2f}%") for c, cnt in miss.items() if cnt > 0
        ]
        if not rows:
            return "No missing values detected."
        return (
            "=== Missing Values ===\n"
            + tabulate(rows, headers=["Column", "Count", "%"], tablefmt="fancy_grid")
            + f"\n\nTotal rows: {total}"
        )

    if analysis_type == "Duplicate Detection":
        dups = working[working.duplicated(keep=False)]
        if dups.empty:
            return f"No duplicates. Checked {len(working)} rows."
        unique = working[working.duplicated()]
        report = [
            ["Total Rows", len(working)],
            ["Duplicate entries", len(dups)],
            ["Unique duplicate rows", len(unique)],
        ]
        body = tabulate(dups.head(num_rows), headers="keys", tablefmt="fancy_grid")
        return (
            "🔍 Duplicate Report\n"
            + tabulate(report, headers=["Metric", "Value"], tablefmt="fancy_grid")
            + "\n\n"
            + body
        )

    if analysis_type == "Placeholder Detection":
        rec = []
        total = len(working)
        for c in working.columns:
            col_ser = working[c].astype(str).str.strip()
            cnt = col_ser.isin(PLACEHOLDERS).sum()
            if cnt > 0:
                rec.append([c, cnt, f"{cnt/total*100:.2f}%"])
        if not rec:
            return "No placeholders found."
        return tabulate(rec, headers=["Column", "Count", "%"], tablefmt="fancy_grid")

    if analysis_type == "Special Character Analysis":
        pat = r"[^\w\s]"
        rec = []
        for c in working.columns:
            ser = working[c].astype(str)
            mask = ser.str.contains(pat, regex=True)
            cnt = int(mask.sum())
            if cnt:
                chars = set("".join(ser[mask]))
                rec.append([c, cnt, "".join(sorted(chars))])
        if not rec:
            return "No special characters found."
        return tabulate(
            rec, headers=["Column", "Count", "Chars"], tablefmt="fancy_grid"
        )

    return f"[Notice] {analysis_type} not recognized."


def search_dataframe(
    df: pd.DataFrame,
    term: str,
    column: str | None = None,
    case: bool = False,
    whole: bool = False,
) -> list[int]:
    """Return indices of rows containing ``term``.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to search.
    term : str
        Search term.
    column : str | None, optional
        Specific column to search within. ``None`` searches all columns.
    case : bool, optional
        Perform case-sensitive matching.
    whole : bool, optional
        Match whole words only when ``True``.

    Returns
    -------
    list[int]
        List of row indices with matches.
    """

    if column and column in df.columns:
        data = df[[column]]
    else:
        data = df

    pattern = rf"\b{term}\b" if whole else term
    mask = data.apply(
        lambda s: s.astype(str).str.contains(pattern, case=case, regex=True)
    ).any(axis=1)
    matches = mask[mask].index.tolist()

    logger.info(
        "Search performed: term=%s column=%s matches=%s",
        term,
        column or "ALL",
        len(matches),
    )
    print(
        f"[Data Handler] Search term='{term}' column='{column or 'ALL'}' -> {len(matches)} matches"
    )
    return matches


def export_dataframe(df: pd.DataFrame, path: str, fmt: str = "csv") -> Path:
    """Export a DataFrame to CSV or Excel."""
    out_path = Path(path)
    if fmt == "csv":
        df.to_csv(out_path, index=False)
    elif fmt == "xlsx":
        df.to_excel(out_path, index=False)
    else:
        raise ValueError("fmt must be 'csv' or 'xlsx'")
    logger.info("Exported DataFrame to %s", out_path)
    print(f"[Data Handler] Exported DataFrame -> {out_path}")
    return out_path


def export_text(text: str, path: str) -> Path:
    """Write text to ``path`` using UTF-8 encoding."""
    out_path = Path(path)
    out_path.write_text(text, encoding="utf-8")
    logger.info("Exported text to %s", out_path)
    print(f"[Data Handler] Exported text -> {out_path}")
    return out_path
