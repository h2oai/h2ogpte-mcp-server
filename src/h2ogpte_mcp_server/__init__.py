__version__ = "0.1.2-dev"

import asyncio
from .server import start_server


def main():
    asyncio.run(start_server())


if __name__ == "__main__":
    main()
