{% raw %}"""Application assembly and lifecycle for {{cookiecutter.package_name}}."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from {{cookiecutter.package_name}}.routers.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Initialize required resources before marking this instance ready.
    app.state.ready = True
    try:
        yield
    finally:
        app.state.ready = False
        # Close application resources here.


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.state.ready = False
    app.include_router(health_router)
    return app


app = create_app()
{% endraw -%}
