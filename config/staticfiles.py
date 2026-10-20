"""
Static files setup.

Tailwind is built only on dev machines (npm run build → static/dist/output.css,
committed to git). Production never runs Tailwind: collectstatic copies the
committed files into staticfiles/ and nginx serves them from there.
"""
import logging

from django.contrib.staticfiles.apps import StaticFilesConfig as BaseStaticFilesConfig
from django.contrib.staticfiles.storage import ManifestStaticFilesStorage

logger = logging.getLogger(__name__)


class StaticFilesConfig(BaseStaticFilesConfig):
    """Keeps the Tailwind source (static/src/) out of collectstatic."""

    ignore_patterns = BaseStaticFilesConfig.ignore_patterns + ['src/*']


class HashedStaticFilesStorage(ManifestStaticFilesStorage):
    """
    Production storage: collectstatic writes content-hashed copies
    (output.3f9a1c.css) and {% static %} links to them, so browsers fetch
    new CSS/JS after every deploy without manual cache-busting.

    A reference to a file that isn't in the manifest falls back to its plain
    name (logged) rather than raising a 500 for the whole page.
    """

    manifest_strict = False

    def stored_name(self, name):
        try:
            return super().stored_name(name)
        except ValueError:
            logger.warning('Static file %r not in manifest; serving unhashed name', name)
            return name
