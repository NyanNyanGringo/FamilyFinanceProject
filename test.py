import pandas as pd
import re


def parse_ftp_log(file_path):
    """
    Parse an FTP log file to generate upload statistics by user.

    Args:
    file_path (str): Path to the .txt log file.

    Returns:
    pd.DataFrame: DataFrame containing user statistics including total GB transferred,
                  total files uploaded, and upload paths.
    """
    # Define a list to store parsed log entries
    log_entries = []

    # Regular expression to parse each line of the log file
    log_pattern = re.compile(
        r"(?P<date>\d{4}-\d{2}-\d{2})\s(?P<time>\d{2}:\d{2}:\d{2}\.\d{3})\s+INFO\s+"
        r"\(pyftpdlib\)\s+(?P<ip>[^\s]+):(?P<port>\d+)-\[(?P<user>[^\]]+)\]\s+"
        r"STOR\s+(?P<file_path>[^\s]+)\s+completed=(?P<status>\d)\s+bytes=(?P<bytes>\d+)\s+seconds=(?P<seconds>[0-9.]+)"
    )

    # Open and read the file line by line
    with open(file_path, 'r') as file:
        for line in file:
            match = log_pattern.match(line)
            if match:
                # Convert matched groups to a dictionary
                entry = match.groupdict()
                entry["bytes"] = int(entry["bytes"])
                entry["seconds"] = float(entry["seconds"])
                log_entries.append(entry)

    # Convert log entries into a DataFrame
    df = pd.DataFrame(log_entries)

    # Calculate gigabytes transferred
    df["gigabytes"] = df["bytes"] / (1024 ** 3)

    # Group data by user and aggregate statistics
    user_stats = df.groupby("user").agg(
        total_gb_transferred=("gigabytes", "sum"),
        total_files_uploaded=("file_path", "count")
    ).reset_index()

    # Add detailed paths for each user
    user_paths = df.groupby("user")["file_path"].apply(list).reset_index()
    user_stats = user_stats.merge(user_paths, on="user")

    # Rename columns for clarity
    user_stats.columns = ["User", "Total GB Transferred", "Total Files Uploaded", "Upload Paths"]

    return user_stats

# Example usage:
stats_df = parse_ftp_log(r"C:\Users\user\Downloads\Explore-logs-2024-11-07 16_40_05.txt")
print(stats_df.head())  # Display the first few rows of the resulting DataFrame
print(stats_df)
print(stats_df.to_string())

# This function reads the log file, parses each line, aggregates data by user, and returns statistics.

