import asyncio

from mdm_agent.config import AgentConfig
from mdm_agent.service import AgentService


def main():
    config = AgentConfig()
    service = AgentService(config)
    asyncio.run(service.run())


if __name__ == "__main__":
    main()
