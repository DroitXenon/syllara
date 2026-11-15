from syllara.browser import looks_like_login

BASE = "https://scientia.school.edu"


def test_same_host_portal_is_not_login():
    assert not looks_like_login("https://scientia.school.edu/courses/123", BASE)


def test_idp_redirect_is_login():
    assert looks_like_login("https://login.microsoftonline.com/abc/saml2", BASE)


def test_same_host_login_path_is_login():
    assert looks_like_login("https://scientia.school.edu/login?next=/", BASE)
    assert looks_like_login("https://scientia.school.edu/sso/start", BASE)


def test_login_word_in_filename_is_not_login():
    assert not looks_like_login("https://scientia.school.edu/files/login-notes.pdf", BASE)
