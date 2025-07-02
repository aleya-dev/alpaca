import sys


def show_progress_bar(current: int, total: int, bar_length: int = 40):
    """
    Displays a progress bar

    Args:
        current (int): The current progress
        total (int): The total progress
        bar_length (int, optional): The length of the progress bar. Defaults to 40.
    """
    percent = current / total * 100
    block = int(round(bar_length * current / total))
    progress = "#" * block + "-" * (bar_length - block)
    sys.stdout.write(f"\r[{progress}] {percent:.1f}% ({current}/{total} bytes)")
    sys.stdout.flush()

    if current == total:
        sys.stdout.write("\n")
        sys.stdout.flush()
