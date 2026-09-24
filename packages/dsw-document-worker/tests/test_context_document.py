from dsw.models.document_context.graph import Document


BASE_DATA = {
    'uuid': '55555555-5555-5555-5555-555555555555',
    'name': 'My Document',
    'documentTemplateUuid': '33333333-3333-3333-3333-333333333333',
    'formatUuid': '66666666-6666-6666-6666-666666666666',
    'createdBy': None,
    'createdAt': '2026-01-01T00:00:00Z',
}


def test_load_without_language_and_locale():
    doc = Document.load(dict(BASE_DATA))
    assert doc.language is None
    assert doc.locale is None


def test_load_with_null_locale():
    doc = Document.load({**BASE_DATA, 'language': 'cs', 'locale': None})
    assert doc.language == 'cs'
    assert doc.locale is None


def test_load_with_locale():
    doc = Document.load({
        **BASE_DATA,
        'language': 'cs',
        'locale': {
            'uuid': '44444444-4444-4444-4444-444444444444',
            'name': 'Czech',
            'code': 'cs',
            'createdAt': '2026-01-01T00:00:00Z',
            'updatedAt': '2026-02-02T00:00:00Z',
        },
    })
    assert doc.language == 'cs'
    assert doc.locale is not None
    assert doc.locale.uuid == '44444444-4444-4444-4444-444444444444'
    assert doc.locale.name == 'Czech'
    assert doc.locale.code == 'cs'
    assert doc.locale.created_at.year == 2026
    assert doc.locale.updated_at.month == 2
