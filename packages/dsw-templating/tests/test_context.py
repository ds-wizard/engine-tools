import pytest

from dsw.templating import ContextDefaults, enrich_context_config


def test_defaults_fill_missing_branding():
    context = {'config': {'clientUrl': 'https://fw.example.org/', 'appTitle': None}}
    enrich_context_config(context, ContextDefaults())
    assert context['config'] == {
        'clientUrl': 'https://fw.example.org/',
        'serviceName': 'Data Stewardship Wizard',
        'serviceNameShort': 'DSW',
        'serviceUrl': 'https://ds-wizard.org',
        'serviceDomainName': 'ds-wizard.org',
        'appTitle': 'DS Wizard',
        'primaryColor': '#0033aa',
        'logoUrl': 'https://fw.example.org/assets/logo.svg',
    }


def test_branding_is_kept_and_service_is_set():
    context = {'config': {
        'clientUrl': '', 'appTitle': 'My Wizard',
        'primaryColor': '#ff0000',
        'logoUrl': 'https://cdn.example.org/logo.png', 'serviceName': 'Stale',
    }}
    enrich_context_config(context, ContextDefaults(service_name='FAIR Wizard'))
    config = context['config']
    assert config['appTitle'] == 'My Wizard'
    assert config['primaryColor'] == '#ff0000'
    assert config['logoUrl'] == 'https://cdn.example.org/logo.png'
    assert config['serviceName'] == 'FAIR Wizard'


def test_keys_removed_in_5_0_are_not_added():
    # appTitleShort and illustrationsColor are gone from document context 19.0 (WEP 29)
    context = {'config': {'clientUrl': '', 'appTitle': None}}
    enrich_context_config(context, ContextDefaults())
    assert not {'appTitleShort', 'illustrationsColor'} & context['config'].keys()


def test_context_without_config_is_rejected():
    # as in the document worker: the server always sends it
    with pytest.raises(KeyError):
        enrich_context_config({}, ContextDefaults())
