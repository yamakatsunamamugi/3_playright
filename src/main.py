import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.gui.main_window import MainWindow
from src.utils.logger import setup_logger
from config.settings import settings


def main():
    setup_logger(settings.LOG_LEVEL, settings.LOG_FILE)
    
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()