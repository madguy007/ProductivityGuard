import logging
import os
import socket
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "productivityguard.log"


def is_server_running(host="127.0.0.1", port=5000):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex((host, port)) == 0


def configure_logging():
    LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def main():
    os.chdir(BASE_DIR)
    configure_logging()

    if is_server_running():
        logging.info("ProductivityGuard is already running on http://127.0.0.1:5000")
        return

    logging.info("Starting ProductivityGuard")
    from main import main as run_app

    run_app()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        configure_logging()
        logging.exception("ProductivityGuard failed to start")
        raise
