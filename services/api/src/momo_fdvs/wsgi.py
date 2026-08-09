"""Production WSGI entry point."""

from momo_fdvs import create_app

app = create_app()
