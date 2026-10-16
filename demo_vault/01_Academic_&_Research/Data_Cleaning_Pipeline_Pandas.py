"""Automated Python Code for Data Cleaning, Imputation, and Schema Normalization."""
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
