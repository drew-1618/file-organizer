import logging


class FileStats:
    def __init__(self):
        self.files_moved = 0
        self.files_deleted = 0
        self.files_skipped = 0
        self.files_renamed = 0
        self.total_processed = 0
        self.directories_created = 0
        self.total_size_bytes = 0
        self.file_type_counts = {}

    def increment_count(self, metric_name):
        metric_name = metric_name.lower()
        if hasattr(self, metric_name):
            setattr(self, metric_name, getattr(self, metric_name) + 1)
            self.total_processed += 1 if metric_name != "directories_created" else 0
        else:
            logging.warning(f"Attempted to increment unknown metric: '{metric_name}'. Ignoring.")

    def add_file_data(self, size_bytes, extension):
        """Updates statistics related to file size and type."""
        self.total_size_bytes += size_bytes
        ext = extension.lower().lstrip('.')
        self.file_type_counts[ext] = self.file_type_counts.get(ext, 0) + 1

    def _convert_bytes(self, size_bytes):
        """Converts bytes to a human-readable format."""
        if size_bytes == 0:
            return "0 Bytes"
        size_names = ('Bytes', 'KB', 'MB', 'GB', 'TB')
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1

        return f"{size_bytes:.2f} {size_names[i]}"

    def generate_report(self):

        # sort file types for cleaner report
        sorted_types = sorted(self.file_type_counts.items(),
                              key=lambda x: x[1], reverse=True)

        report = "\n------- FILE ORGANIZATION REPORT -------"

        report += f"\n\n--- SUMMARY ---"
        report += f"\n\tTotal files processed: {self.total_processed}"
        report += f"\n\tTotal data processed: {self._convert_bytes(self.total_size_bytes)}"
        report += f"\n\tDirectories created: {self.directories_created}"

        report += f"\n\n--- ACTION BREAKDOWN ---"
        report += f"\n\tFiles moved: {self.files_moved}"
        report += f"\n\tFiles deleted: {self.files_deleted}"
        report += f"\n\tFiles skipped: {self.files_skipped}"
        report += f"\n\tFiles renamed: {self.files_renamed}"

        report += f"\n\n--- FILE TYPE BREAKDOWN ({len(self.file_type_counts)} unique counts) ---"
        if sorted_types:
            top_types = sorted_types[:5]
            other_count = sum(count for _, count in sorted_types[5:])

            for ext, count in top_types:
                report += f"\n\t.{ext}: {count} files"
            if other_count > 0:
                report += f"\n\t.Other types: {other_count} files"
        else:
            report += "\n\tNo file types tracked."
        
        report += "\n\n----------------------------------------\n"
        logging.info(report)
        return report
