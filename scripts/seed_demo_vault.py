"""Seed a rich, realistic Judge Demo Vault in ./demo_vault for showcasing ARJUN."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "demo_vault"


def write(rel_path: str, content: str):
    p = ROOT / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def seed():
    ROOT.mkdir(parents=True, exist_ok=True)

    # 1. Academic & Research (Search showcase: recursion, python data cleaning, etc.)
    write(
        "01_Academic_&_Research/CS301_Lecture_Notes_Recursion_and_Dynamic_Programming.md",
        """# Lecture 14: Recursion, Recurrence Relations & Dynamic Programming

## 1. Fundamental Principles of Recursion
Recursion solves complex problems by decomposing them into smaller, self-similar subproblems:
- **Base Case**: The terminating condition that prevents infinite stack frames (e.g., `if n <= 1: return 1`).
- **Recursive Step**: Reducing the problem size toward the base case (`fib(n-1) + fib(n-2)`).
- **Tail Recursion**: Optimization where the recursive call is the final operation in the function frame.

## 2. Analyzing Recursion Trees & Master Theorem
For divide-and-conquer recurrences of the form `T(n) = aT(n/b) + f(n)`:
- Binary Search: `T(n) = T(n/2) + O(1)` -> `O(log n)`
- Merge Sort: `T(n) = 2T(n/2) + O(n)` -> `O(n log n)`
- Karatsuba Multiplication: `T(n) = 3T(n/2) + O(n)` -> `O(n^1.585)`

## 3. From Naive Recursion to Memoization
Naive recursion on overlapping subproblems leads to exponential `O(2^n)` blowup.
By caching intermediate results in a lookup table (memoization) or bottom-up tabulation, we reduce time complexity to polynomial `O(n)`.
""",
    )

    write(
        "01_Academic_&_Research/Data_Cleaning_Pipeline_Pandas.py",
        '''"""Automated Python Code for Data Cleaning, Imputation, and Schema Normalization."""
import re
import pandas as pd
import numpy as np


def clean_telemetry_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean raw CSV data: normalize column names, impute missing values, and strip outliers."""
    df = df.copy()
    # 1. Standardize column headers to snake_case
    df.columns = [re.sub(r"[^a-z0-9]+", "_", col.strip().lower()).strip("_") for col in df.columns]

    # 2. Drop duplicate rows and completely empty records
    df = df.drop_duplicates().dropna(how="all")

    # 3. Missing value imputation using median for numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        median_val = df[col].median()
        df[col] = df[col].fillna(median_val)
        # IQR outlier clipping
        q1, q3 = df[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        df[col] = df[col].clip(lower=q1 - 1.5 * iqr, upper=q3 + 1.5 * iqr)

    # 4. String trimming and standardization
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].astype(str).str.strip()

    return df
''',
    )

    write(
        "01_Academic_&_Research/Distributed_Consensus_Raft_Paper_Summary.txt",
        """Raft Consensus Algorithm — Study Summary
Leader election, log replication, and safety properties in distributed state machines.
Unlike Paxos, Raft decomposes consensus into independent subproblems:
1. Leader Election with randomized election timeouts (150ms - 300ms).
2. Log Replication via AppendEntries RPCs.
3. Safety guarantee: Leader Completeness Property ensures committed entries are present in all future leaders.
""",
    )

    # 2. Personal & Identity Vault (Privacy & PII Redaction showcase)
    write(
        "02_Personal_&_Identity_Vault/Income_Tax_Return_AY2026_PAN_Aadhaar.txt",
        """INDIAN INCOME TAX RETURN ACKNOWLEDGEMENT — ASSESSMENT YEAR 2026-27
====================================================================
Taxpayer Name   : Arjun Dev Sharma
PAN Number      : ABCDE1234F
Aadhaar Number  : 4589 2310 7845
Registered Email: arjun.sharma@indraprastha.dev
Mobile Number   : +91 98765 43210
Residential Addr: Flat 402, Sudarshana Enclave, Bengaluru 560034

BANK REFUND MANDATE
Bank Name       : HDFC Bank Ltd
Account Number  : 50100482910384
IFSC Code       : HDFC0001245
Gross Total Inc : INR 24,80,000
Tax Paid (TDS)  : INR 4,12,500
Status          : E-Verified via Aadhaar OTP
""",
    )

    write(
        "02_Personal_&_Identity_Vault/HDFC_Bank_Statement_2025_Annual.txt",
        """HDFC BANK LIMITED — ANNUAL ACCOUNT STATEMENT (LAST YEAR 2025)
==============================================================
Account Holder : Arjun Dev Sharma
Account Number : 50100482910384
IFSC Code      : HDFC0001245
Customer PAN   : ABCDE1234F
Contact Phone  : +91 98765 43210
Statement Period: 01-Jan-2025 to 31-Dec-2025

DATE        DESCRIPTION                                  DEBIT (INR)    CREDIT (INR)   BALANCE (INR)
----------------------------------------------------------------------------------------------------
05-Jan-2025 NEFT-SALARY CREDIT-TECH LABS                                1,85,000.00    6,42,100.00
14-Feb-2025 UPI/cloud-billing@axis/AWS Hosting            14,250.00                    6,27,850.00
28-Mar-2025 IMPS-TAX SAVING ELSS MUTUAL FUND             1,50,000.00                   4,77,850.00
19-Aug-2025 NEFT-HACKATHON GRANT AWARD                                  2,50,000.00    7,27,850.00
12-Dec-2025 POS-MANALI WINTER EXPEDITION GEAR             28,400.00                    6,99,450.00
""",
    )

    write(
        "02_Personal_&_Identity_Vault/Arjun_Sharma_Resume_2026_Final.md",
        """# ARJUN DEV SHARMA — Curriculum Vitae / Resume
Email: arjun.sharma@indraprastha.dev | Phone: +91 98765 43210 | Location: Bengaluru, India

## Summary
Systems & AI Privacy Engineer specializing in on-device semantic indexing, zero-egress PII redaction, and sub-50ms local vector search.

## Experience
- **Lead Systems Architect — Project ARJUN (2025–2026)**
  Built an on-device file intelligence engine with hybrid BM25 + semantic embeddings and reversible PII vault redaction.
- **Machine Learning Intern — Astral Compute Labs (2024–2025)**
  Optimized quantized transformer inference pipelines in Python and C++.

## Education
- **B.Tech in Computer Science & Engineering** (CGPA: 9.4/10)
  Coursework: Operating Systems, Compiler Design, Algorithms & Recursion, Cryptography.
""",
    )

    write(
        "02_Personal_&_Identity_Vault/Cloud_Infrastructure_Production_Secrets.env",
        """# PRODUCTION ENVIRONMENT SECRETS — DO NOT UPLOAD TO CLOUD
OPENAI_API_KEY=sk-proj-98a7b6c5d4e3f2a1b2c3d4e5f6a7b8c9d0e1f2a3
GOOGLE_GEMINI_API_KEY=AIzaSyD9x8W7v6U5t4S3r2Q1p0O9n8M7l6K5j4I
DATABASE_URL=postgresql://admin:Sup3rS3cr3tVaultP@ssw0rd!@10.0.4.12:5432/arjun_prod
ADMIN_ALERT_EMAIL=secops@indraprastha.dev
ONCALL_PHONE=+91 98111 22333
""",
    )

    # 3. Finance & Invoices (Search showcase: "invoices")
    write(
        "03_Finance_&_Invoices/INV_2026_089_AWS_Cloud_Hosting_Invoice.txt",
        """TAX INVOICE — AMAZON WEB SERVICES INDIA PVT LTD
================================================
Invoice Number : INV-2026-089
Invoice Date   : 01-Oct-2026
Billing Email  : billing@indraprastha.dev

Item Description                          Qty     Unit Price     Total (INR)
----------------------------------------------------------------------------
EC2 g5.xlarge GPU Instances (Hours)       120        85.00         10,200.00
S3 Glacier Encrypted Archive (TB)           4       450.00          1,800.00
CloudFront Data Transfer                   50        12.00            600.00
----------------------------------------------------------------------------
Subtotal                                                           12,600.00
IGST (18%)                                                          2,268.00
Grand Total Due                                                INR 14,868.00
""",
    )

    write(
        "03_Finance_&_Invoices/INV_2026_104_Hardware_Workstation_Invoice.txt",
        """COMMERCIAL INVOICE — PRECISION WORKSTATION SUPPLY
==================================================
Invoice Number : INV-2026-104
Invoice Date   : 10-Oct-2026
Customer       : Arjun Research Lab (+91 98765 43210)

1x Custom Local AI Workstation (64GB DDR5, NVMe 4TB RAID)      INR 1,68,000.00
1x Calibrated 4K Reference Display                             INR   42,000.00
GST (18%)                                                      INR   37,800.00
------------------------------------------------------------------------------
Total Paid via NEFT (Ref: HDFC0001245)                         INR 2,47,800.00
""",
    )

    # 4. Vague & Unnamed Files (Tidy Up -> Smart Rename showcase!)
    write(
        "04_Vague_&_Unnamed_Files/Untitled.txt",
        """# Quantum Cryptography Protocol Specification
Lattice-based post-quantum key exchange mechanism (CRYSTALS-Kyber) for local vault encryption.
Ensures zero-knowledge file indexing across untrusted storage media.
""",
    )

    write(
        "04_Vague_&_Unnamed_Files/Untitled (2).md",
        """# Indraprastha Smart Grid Telemetry Architecture
Real-time phasor measurement unit (PMU) ingestion pipeline and anomaly detection thresholds.
""",
    )

    write(
        "04_Vague_&_Unnamed_Files/IMG_2041.txt",
        """# Whiteboarding Session Neural Search Architecture
Diagram notes from our architecture review covering hybrid BM25 lexical scoring combined with dense vector cosine similarity.
""",
    )

    write(
        "04_Vague_&_Unnamed_Files/scan0001.txt",
        """Scanned Identity Verification Record
Holder: Arjun Dev Sharma
PAN: ABCDE1234F
Aadhaar: 4589 2310 7845
Verified on-device for KYC compliance.
""",
    )

    write(
        "04_Vague_&_Unnamed_Files/document_1.txt",
        """# Semester Exam Schedule And Syllabus 2026
Final examination dates for CS301 Algorithms, CS304 Operating Systems, and CS309 Cryptography.
""",
    )

    write(
        "04_Vague_&_Unnamed_Files/notes_03.md",
        """# Inspirathon 26 Judge Demo Pitch Script
1. Show instant semantic search on local files.
2. Demonstrate Tidy Up renaming vague files like Untitled and IMG_2041.
3. Prove zero raw PII egress in the Privacy Ledger with live redaction test.
""",
    )

    # 5. Duplicates & Media (Duplicates finder + "photos from december" search)
    write(
        "05_Duplicates_&_Media/December_2025_Manali_Winter_Photos_Catalog.md",
        """# Photos from December 2025 — Manali & Rohtang Winter Expedition
Catalog of RAW and JPEG photographs captured in December 2025:
- Rohtang Pass sunrise panorama (ISO 100, 24mm f/8)
- Solang Valley snow trek group photos from December 18
- Bonfire & stargazing long-exposure astrophotography shots
""",
    )

    dup_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">\n'
        + ('  <circle cx="400" cy="300" r="240" stroke="#d4af37" stroke-width="2" fill="none"/>\n' * 650)
        + "</svg>\n"
    )
    write("05_Duplicates_&_Media/Gandiva_Astrolabe_Diagram_Master.svg", dup_svg)
    write("05_Duplicates_&_Media/Gandiva_Astrolabe_Diagram_Backup_Copy.svg", dup_svg)

    dup_csv = "timestamp,sensor_id,voltage_mv,temperature_c,status\n" + (
        "2026-10-15T12:00:00Z,CHAKRA-01,3301.4,42.8,NOMINAL\n" * 1800
    )
    write("05_Duplicates_&_Media/Telemetry_Benchmark_Dataset_2026.csv", dup_csv)
    write("05_Duplicates_&_Media/Telemetry_Benchmark_Dataset_2026_Duplicate.csv", dup_csv)

    dup_report = (
        "ARJUN PRECISION ENGINE — FULL BENCHMARK REPORT 2026\n"
        + ("Throughput: 14,200 files/sec | P99 Search Latency: 8.4ms | Egress: 0 Bytes\n" * 600)
    )
    write("05_Duplicates_&_Media/Arjun_Engine_Benchmark_Report.txt", dup_report)
    write("05_Duplicates_&_Media/Copy_of_Arjun_Engine_Benchmark_Report.txt", dup_report)

    # 6. Temp & Leftovers (Junk / Leftovers cleanup showcase)
    write("06_Temp_&_Leftovers/build_artifact_cache_20261015.tmp", "TEMP_CACHE_BLOCK\n" * 3500)
    write("06_Temp_&_Leftovers/crash_memory_dump_0912.temp", "STACK_TRACE_DUMP\n" * 4200)
    write("06_Temp_&_Leftovers/index_schema_v1_backup.bak", "OLD_SQLITE_SNAPSHOT\n" * 3000)
    write("06_Temp_&_Leftovers/deprecated_settings_2024.old", "LEGACY_CONFIG_DATA\n" * 2500)

    # 7. Messy Downloads Folder (For Tidy Up -> "Organise a folder" showcase)
    write(
        "07_Messy_Folder_To_Organize/Q4_Vendor_GST_Invoice_2026.txt",
        "Invoice INV-9921 for server rack maintenance. Total INR 45,000 including 18% GST.",
    )
    write(
        "07_Messy_Folder_To_Organize/Algorithms_Homework_Graph_Traversal.md",
        "# CS301 Assignment: Dijkstra, Bellman-Ford, and A* Heuristic Search on Weighted Graphs.",
    )
    write(
        "07_Messy_Folder_To_Organize/Flight_Boarding_Pass_Bengaluru_To_Goa.txt",
        "IndiGo Flight 6E-412 Boarding Pass — Passenger: Arjun Sharma, Seat 14A, Gate 8.",
    )
    write(
        "07_Messy_Folder_To_Organize/Confidential_Salary_Slip_PAN_Aadhaar.txt",
        "Salary Slip Oct 2026 — Employee PAN: ABCDE1234F, Aadhaar: 4589 2310 7845, Net Pay: INR 1,85,000.",
    )
    write(
        "07_Messy_Folder_To_Organize/vector_quantization_kernel.py",
        "import numpy as np\ndef cosine_sim(a, b): return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))\n",
    )

    print(f"[+] Seeded Judge Demo Vault at: {ROOT}")


if __name__ == "__main__":
    seed()
