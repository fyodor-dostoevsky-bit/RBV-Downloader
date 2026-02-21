import sys
import time

class ProgressBar:
    def __init__(self, total, prefix="", length=30):
        self.total = total
        self.prefix = prefix
        self.length = length
        self.current = 0
        self.start_time = time.time()

    def update(self, step=1):
        self.current += step
        self.draw()

    def draw(self):
        percent = self.current / self.total if self.total else 0
        filled = int(self.length * percent)
        bar = "█" * filled + "░" * (self.length - filled)

        elapsed = time.time() - self.start_time
        speed = self.current / elapsed if elapsed > 0 else 0

        sys.stdout.write(
            f"\r{self.prefix} [{bar}] {self.current}/{self.total} "
            f"{percent*100:5.1f}%  {speed:4.1f} p/s"
        )
        sys.stdout.flush()

    def finish(self):
        self.current = self.total
        self.draw()
        print()
