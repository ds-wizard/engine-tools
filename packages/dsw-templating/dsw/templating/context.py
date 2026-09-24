"""Values the document worker adds to the document context before rendering."""
from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class ContextDefaults:
    """Service information and fallbacks of the instance branding (``ctx.config``).

    The defaults are those of the document worker's configuration.
    """
    service_name: str = 'Data Stewardship Wizard'
    service_name_short: str = 'DSW'
    service_url: str = 'https://ds-wizard.org'
    service_domain_name: str = 'ds-wizard.org'
    default_primary_color: str = '#0033aa'
    default_illustrations_color: str = '#0033aa'
    default_logo_url: str = '{{clientUrl}}/assets/logo.svg'
    default_app_title: str = 'DS Wizard'
    default_app_title_short: str = 'DS Wizard'


def enrich_context_config(context: dict, defaults: ContextDefaults):
    """Fill ``context['config']`` as the document worker does.

    The service fields are always set from `defaults`; the branding of the
    instance is kept when present and falls back to `defaults` otherwise.
    """
    old = context.get('config', {})

    client_url = old.get('clientUrl', '').rstrip('/')
    app_title = (old.get('appTitle', None) or
                 defaults.default_app_title)
    app_title_short = (old.get('appTitleShort', None) or
                       defaults.default_app_title_short)
    primary_color = (old.get('primaryColor', None) or
                     defaults.default_primary_color)
    illustrations_color = (old.get('illustrationsColor', None) or
                           defaults.default_illustrations_color)
    logo_url_template = (old.get('logoUrl', None) or
                         defaults.default_logo_url)
    logo_url = logo_url_template.replace('{{clientUrl}}', client_url)

    context['config'].update({
        'serviceName': defaults.service_name,
        'serviceNameShort': defaults.service_name_short,
        'serviceUrl': defaults.service_url,
        'serviceDomainName': defaults.service_domain_name,
        'appTitle': app_title,
        'appTitleShort': app_title_short,
        'primaryColor': primary_color,
        'illustrationsColor': illustrations_color,
        'logoUrl': logo_url,
    })
