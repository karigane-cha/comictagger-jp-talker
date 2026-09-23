import pytest

from comictagger_jp_talker.isbn import isbn10, isbn13, isbn_from_gtin, normalize_isbn


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("978-4-10-101013-7", "9784101010137"),
        (" 978 4\t10 101013 7\n", "9784101010137"),
        ("4-88594-287-X", "488594287X"),
        ("4 88594 287 x", "488594287X"),
        ("0-306-40615-2", "0306406152"),
    ],
)
def test_normalize(raw, expected):
    assert normalize_isbn(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "123",
        "9784101010138",
        "4885942870",
        "X885942871",
        "978410101013X",
        "abcdefghij",
        "１２３４５６７８９０",
        "4006381333931",
    ],
)
def test_invalid(raw):
    assert normalize_isbn(raw) is None
    assert isbn13(raw) is None


def test_conversion():
    assert isbn13("0306406152") == "9780306406157"
    assert isbn10("9780306406157") == "0306406152"
    assert isbn13("488594287X") == "9784885942877"
    assert isbn10("9784885942877") == "488594287X"
    assert isbn10("9791090636071") is None
    assert isbn_from_gtin("09784101010137") == "9784101010137"


@pytest.mark.parametrize("isbn", ["0306406152", "488594287X", "9784101010137"])
def test_every_single_digit_corruption_rejected(isbn):
    for i in range(len(isbn)):
        for digit in "0123456789":
            if digit != isbn[i]:
                assert normalize_isbn(isbn[:i] + digit + isbn[i + 1 :]) is None
