from fastapi import APIRouter
import importlib
import logging
import pkgutil
import pathlib
from typing import List

logger = logging.getLogger(__name__)

api_router = APIRouter(prefix="/api/v1")
BASE_PACKAGE = "app.api"
BASE_PATH = pathlib.Path(__file__).parent


def include_routers_from_package(package: str, path: pathlib.Path) -> List[str]:
    """
    Dynamically discover and include all routers from the API package.
    """
    loaded_routers = []

    logger.info("🔨 Smithy API - Loading routers...")
    logger.info(f"📦 Scanning package: {package}")
    logger.info(f"📁 Base path: {path}")

    for module_info in pkgutil.walk_packages([str(path)], prefix=f"{package}."):
        module_name = module_info.name.split(".")[-1]

        # Skip internal modules and __init__.py
        if module_name.startswith("_") or module_name in ["main", "test", "tests"]:
            logger.debug(f"⏭️  Skipping module: {module_name}")
            continue

        try:
            logger.debug(f"🔍 Examining module: {module_info.name}")
            module = importlib.import_module(module_info.name)
            router = getattr(module, "router", None)

            if router:
                # Get router info for logging
                prefix = getattr(router, "prefix", "")
                tags = getattr(router, "tags", [])
                routes_count = len(router.routes) if hasattr(router, "routes") else 0

                api_router.include_router(router)
                loaded_routers.append(module_name)

                logger.info(
                    f"✅ Loaded router: {module_name} "
                    f"(prefix: {prefix or 'none'}, "
                    f"tags: {tags or 'none'}, "
                    f"routes: {routes_count})"
                )
            else:
                logger.debug(f"⚠️  No router found in module: {module_name}")

        except Exception as e:
            logger.error(f"❌ Failed to load router from {module_info.name}: {e}")
            continue

    # Summary
    logger.info("🎯 Router loading complete!")
    logger.info(
        f"📊 Successfully loaded {len(loaded_routers)} routers: {', '.join(loaded_routers)}"
    )

    return loaded_routers


# Load all routers
loaded_modules = include_routers_from_package(BASE_PACKAGE, BASE_PATH)

__all__ = ["api_router", "loaded_modules"]
