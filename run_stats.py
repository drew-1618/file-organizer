import logging


class FileStats:
    def __init__(self):
        self.files_moved = 0
        self.files_deleted = 0
        self.files_skipped = 0
        self.files_renamed = 0
        self.total_processed = 0
        self.directories_created = 0

    def increment_count(self, metric_name):
        metric_name = metric_name.lower()
        if hasattr(self, metric_name):
            setattr(self, metric_name, getattr(self, metric_name) + 1)
            self.total_processed += 1 if metric_name != "directories_created" else 0
        else:
            raise ValueError(f"Metric '{metric_name}' does not exist in FileStats.")

    def generate_report(self):
        report = "\n----- File Organization Report -----"
        report += f"\n\tTotal files processed: {self.total_processed}"
        report += f"\n\tFiles moved: {self.files_moved}"
        report += f"\n\tFiles deleted: {self.files_deleted}"
        report += f"\n\tFiles skipped: {self.files_skipped}"
        report += f"\n\tDirectories created: {self.directories_created}"
        report += "\n------------------------------------"
        logging.info(report)
        return report
