__version__ = "0.1.6-dev"

import asyncio


def main():
    from .server import start_server

    asyncio.run(start_server())


if __name__ == "__main__":
    main()
