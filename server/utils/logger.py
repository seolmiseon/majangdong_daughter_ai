import csv
import os
from datetime import datetime


def save_rank_log(store_name: str, keyword: str, rank: int):
    """결과를 data/rank_history.csv에 누적 저장합니다."""
    log_dir = "data"
    log_file = os.path.join(log_dir, "rank_history.csv")

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    file_exists = os.path.isfile(log_file)

    with open(log_file, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "store_name", "keyword", "rank"])

        writer.writerow(
            [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), store_name, keyword, rank]
        )
