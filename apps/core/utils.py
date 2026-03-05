# core/utils.py

def get_themed_template(site_settings, page_type, fallback):
    """Resolve the themed template path for a given page type."""
    template_fk = getattr(site_settings, f'{page_type}_template', None)
    if template_fk and template_fk.template_file:
        theme = site_settings.active_theme
        if theme and theme.theme_directory:
            return f"{theme.theme_directory}/{template_fk.template_file}"
        return template_fk.template_file
    return fallback