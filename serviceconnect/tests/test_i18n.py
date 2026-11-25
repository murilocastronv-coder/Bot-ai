from i18n import LANGS, MENU_KEYS, MENU_LOOKUP, missing_translations, t


def test_all_strings_translated_in_4_languages():
    assert LANGS == ("pt", "en", "fr", "es")
    assert missing_translations() == []


def test_menu_has_12_buttons_unique_per_language():
    assert len(MENU_KEYS) == 12
    for lang in LANGS:
        labels = [t(k, lang) for k in MENU_KEYS]
        assert len(set(labels)) == 12
        for label in labels:
            assert label in MENU_LOOKUP


def test_format_placeholders_work():
    for lang in LANGS:
        assert "#7" in t("req.published", lang, id=7, n=3)
        assert "3" in t("req.published", lang, id=7, n=3)
