# src/data_handler.py

#----------------------------------------------------------------------
#Libraries
#----------------------------------------------------------------------
import logging
import pandas as pd
from pathlib import Path   
import csv
import os
from tqdm import tqdm
from tabulate import tabulate
#----------------------------------------------------------------------
def save_filepath(path):
    '''Save the file path to a global variable for later use.'''
    global saved_filepath
    saved_filepath = str(path)
#----------------------------------------------------------------------
def create_dataset_environment(dataset_name: str) -> dict:
    '''Create a structured directory environment for the dataset.'''
    documents_dir = Path.home() / "Documents"
    base_path = documents_dir / "ProtexxaDatascope" / dataset_name

    subdirs = {
        "stages": base_path / "stages",
        "process": base_path / "process",
        "garbage": base_path / "garbage",
        "chunks": base_path / "chunks",
        "converted": base_path / "converted"
    }

    for path in subdirs.values():
        path.mkdir(parents=True, exist_ok=True)

    return {
        "project": base_path,
        **subdirs
    }



logger = logging.getLogger(__name__)

def load_data(file_path):
    """
    Loads a dataset and returns the DataFrame or None if it fails.
    """
    try:
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        elif file_path.endswith((".xls", ".xlsx")):
            df = pd.read_excel(file_path)
        else:
            raise ValueError("Unsupported file format")

        return df
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return None


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
            "log2": f"[Data Handler] File size: {file_size:.2f} MB"
        }

    except Exception as e:
        logger.error(f"Error getting data stats: {e}")
        return {
            "row_count": 0,
            "file_size": 0,
            "log1": "[Data Handler] Failed to get row count.",
            "log2": "[Data Handler] Failed to calculate file size."
        }




def split_into_chunks(dataset_name, input_file, chunk_size_mb=256, logger_fn=None):
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

        with open(input_file, 'r', encoding='utf-8') as infile:
            reader = csv.reader(infile)
            try:
                header = next(reader)
            except StopIteration:
                log("Error: File is empty or missing a header.")
                return {
                    "total_rows": 0,
                    "total_chunks": 0,
                    "output_dir": str(output_dir)
                }

            chunk_index = 0
            current_chunk = []
            current_chunk_size = 0
            row_count = 0

            for row in tqdm(reader, desc="Splitting CSV", unit="rows"):
                row_size = len(",".join(row).encode("utf-8"))

                if current_chunk_size + row_size > chunk_size_bytes:
                    output_file = os.path.join(output_dir, f"{base_filename}_chunk_{chunk_index}.csv")
                    with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
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

            # Final chunk
            if current_chunk:
                output_file = os.path.join(output_dir, f"{base_filename}_chunk_{chunk_index}.csv")
                with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
                    writer = csv.writer(outfile)
                    writer.writerow(header)
                    writer.writerows(current_chunk)
                log(f"Final chunk {chunk_index} written: {len(current_chunk)} rows")

        log(f"All chunks written. Total rows: {row_count}")
        log(f"Output directory contents: {os.listdir(output_dir)}")

        return {
            "total_rows": row_count,
            "total_chunks": chunk_index + 1,
            "output_dir": str(output_dir)
        }

    except FileNotFoundError as e:
        logging.error(f"File not found: {e}")
        if logger_fn: logger_fn(f"Error: {e}")
    except PermissionError as e:
        logging.error(f"Permission error: {e}")
        if logger_fn: logger_fn(f"Error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        if logger_fn: logger_fn(f"Unexpected error: {e}")

    return {
        "total_rows": 0,
        "total_chunks": 0,
        "output_dir": ""
    }




#SOURCE APP FUNCTIONALITY BUILDOUT (SEAN)
PLACEHOLDERS = {"N/A","NA","None","none","unknown","Unknown","-","TBD","tbd","0000","","null","NULL","n/a"}

def run_analysis(df: pd.DataFrame,
                 analysis_type: str,
                 column: str = None,
                 num_rows: int = 10,
                 sort_desc: bool = False
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
        dtypes = [(c,str(t)) for c,t in working.dtypes.items()]
        return (
            "[Data Types]\n" +
            tabulate(dtypes, headers=["Column","Dtype"], tablefmt="fancy_grid") +
            "\n\n[Preview]\n" +
            tabulate(preview, headers="keys", tablefmt="fancy_grid")
        )
    
    if analysis_type == "Missing Values":
        miss = working.isnull().sum()
        total = len(working)
        rows = [
            (c, int(cnt), f"{cnt/total*100:.2f}%")
            for c,cnt in miss.items() if cnt>0
        ]
        if not rows:
            return "No missing values detected."
        return (
            "=== Missing Values ===\n" +
            tabulate(rows, headers=["Column","Count","%"], tablefmt="fancy_grid") +
            f"\n\nTotal rows: {total}"
        )
    
    if analysis_type == "Duplicate Detection":
        dups = working[working.duplicated(keep=False)]
        if dups.empty:
            return f"No duplicates. Checked {len(working)} rows."
        unique = working[working.duplicated()]
        report = [
            ["Total Rows", len(working)],
            ["Duplicate entries", len(dups)],
            ["Unique duplicate rows", len(unique)]
        ]
        body = tabulate(dups.head(num_rows), headers="keys", tablefmt="fancy_grid")
        return "🔍 Duplicate Report\n" + tabulate(report, headers=["Metric","Value"], tablefmt="fancy_grid") + "\n\n" + body
    
    if analysis_type == "Placeholder Detection":
        rec = []
        total= len(working)
        for c in working.columns:
            col_ser = working[c].astype(str).str.strip()
            cnt = col_ser.isin(PLACEHOLDERS).sum()
            if cnt>0:
                rec.append([c, cnt, f"{cnt/total*100:.2f}%"])
        if not rec:
            return "No placeholders found."
        return tabulate(rec, headers=["Column","Count","%"], tablefmt="fancy_grid")
    
    if analysis_type == "Special Character Analysis":
        pat = r"[^\w\s]"
        rec=[]
        for c in working.columns:
            ser = working[c].astype(str)
            mask = ser.str.contains(pat, regex=True)
            cnt = int(mask.sum())
            if cnt:
                chars = set("".join(ser[mask]))
                rec.append([c, cnt, "".join(sorted(chars))])
        if not rec:
            return "No special characters found."
        return tabulate(rec, headers=["Column","Count","Chars"], tablefmt="fancy_grid")
    
    return f"[Notice] {analysis_type} not recognized."
