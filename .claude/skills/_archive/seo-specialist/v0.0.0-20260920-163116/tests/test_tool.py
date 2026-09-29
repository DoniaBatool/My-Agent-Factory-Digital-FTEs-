import json
import subprocess
import sys
import urllib.error
from pathlib import Path

import pytest

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("seo_specialist_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)  # unique module name avoids cross-skill "tool" collisions in combined pytest runs


class _Args:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# ---------------------------------------------------------------------------
# print_* helpers
# ---------------------------------------------------------------------------

def test_print_header_exact_format(capsys):
    tool.print_header("Hello")
    out = capsys.readouterr().out
    assert out == f"\n{tool.Colors.BLUE}==>{tool.Colors.RESET} Hello\n"


def test_print_success_exact_format(capsys):
    tool.print_success("ok")
    out = capsys.readouterr().out
    assert out == f"{tool.Colors.GREEN}✓{tool.Colors.RESET} ok\n"


def test_print_warning_exact_format(capsys):
    tool.print_warning("careful")
    out = capsys.readouterr().out
    assert out == f"{tool.Colors.YELLOW}⚠{tool.Colors.RESET} careful\n"


def test_print_error_exact_format(capsys):
    tool.print_error("bad")
    out = capsys.readouterr().out
    assert out == f"{tool.Colors.RED}✗{tool.Colors.RESET} bad\n"


def test_print_info_exact_format(capsys):
    tool.print_info("fyi")
    out = capsys.readouterr().out
    assert out == f"{tool.Colors.BOLD}→{tool.Colors.RESET} fyi\n"


def test_print_score_green_at_90(capsys):
    tool.print_score(90, "label")
    out = capsys.readouterr().out
    assert out == f"{tool.Colors.GREEN}90/100{tool.Colors.RESET} label\n"


def test_print_score_yellow_just_below_90(capsys):
    tool.print_score(89, "label")
    out = capsys.readouterr().out
    assert out == f"{tool.Colors.YELLOW}89/100{tool.Colors.RESET} label\n"


def test_print_score_yellow_at_70(capsys):
    tool.print_score(70, "label")
    out = capsys.readouterr().out
    assert out == f"{tool.Colors.YELLOW}70/100{tool.Colors.RESET} label\n"


def test_print_score_red_just_below_70(capsys):
    tool.print_score(69, "label")
    out = capsys.readouterr().out
    assert out == f"{tool.Colors.RED}69/100{tool.Colors.RESET} label\n"


def test_print_score_red_at_zero(capsys):
    tool.print_score(0, "label")
    out = capsys.readouterr().out
    assert out == f"{tool.Colors.RED}0/100{tool.Colors.RESET} label\n"


# ---------------------------------------------------------------------------
# fetch_url
# ---------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, body: bytes, code: int, headers: dict):
        self._body = body
        self._code = code
        self._headers = headers

    def read(self):
        return self._body

    def getcode(self):
        return self._code

    @property
    def headers(self):
        return self._headers

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_fetch_url_success_returns_content_status_headers(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured['req'] = req
        captured['timeout'] = timeout
        return _FakeResponse(b"<html>hi</html>", 200, {"Content-Type": "text/html"})

    monkeypatch.setattr(tool.urllib.request, "urlopen", fake_urlopen)

    content, status, headers = tool.fetch_url("https://example.com", timeout=5)

    assert content == "<html>hi</html>"
    assert status == 200
    assert headers == {"Content-Type": "text/html"}
    assert captured['timeout'] == 5
    assert captured['req'].get_header('User-agent') == 'SEO-Specialist-Tool/1.0'
    assert captured['req'].full_url == "https://example.com"


def test_fetch_url_decodes_invalid_utf8_without_raising(monkeypatch):
    def fake_urlopen(req, timeout=None):
        return _FakeResponse(b"\xff\xfebroken", 200, {})

    monkeypatch.setattr(tool.urllib.request, "urlopen", fake_urlopen)

    content, status, _ = tool.fetch_url("https://example.com")
    assert status == 200
    assert isinstance(content, str)


def test_fetch_url_http_error_returns_code_and_empty_content(monkeypatch):
    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError("https://example.com", 404, "Not Found", {}, None)

    monkeypatch.setattr(tool.urllib.request, "urlopen", fake_urlopen)

    content, status, headers = tool.fetch_url("https://example.com")
    assert content == ""
    assert status == 404
    assert headers == {}


def test_fetch_url_generic_exception_returns_zero_status(monkeypatch, capsys):
    def fake_urlopen(req, timeout=None):
        raise ValueError("boom")

    monkeypatch.setattr(tool.urllib.request, "urlopen", fake_urlopen)

    content, status, headers = tool.fetch_url("https://example.com")
    assert content == ""
    assert status == 0
    assert headers == {}
    out = capsys.readouterr().out
    assert "Failed to fetch https://example.com" in out
    assert "boom" in out


def test_fetch_url_default_timeout_is_ten(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured['timeout'] = timeout
        return _FakeResponse(b"x", 200, {})

    monkeypatch.setattr(tool.urllib.request, "urlopen", fake_urlopen)
    tool.fetch_url("https://example.com")
    assert captured['timeout'] == 10


# ---------------------------------------------------------------------------
# extract_meta_tags
#
# NOTE: several of the capture regexes in tool.py use a broken character
# class "[ ^"\']+" (a literal space/caret/quote class) instead of the
# intended negated class "[^"\']+". As written, this means description,
# keywords, Open Graph, Twitter Card and canonical values are captured
# ONLY when their content consists entirely of spaces/'^'/'"'/"'" characters
# -- i.e. never for realistic text. The tests below assert the tool's
# actual behavior (including this bug) rather than the "intended" behavior.
# ---------------------------------------------------------------------------

def test_extract_meta_tags_title_is_captured_correctly():
    html = "<html><head><title>My Great Page</title></head></html>"
    tags = tool.extract_meta_tags(html)
    assert tags['title'] == "My Great Page"


def test_extract_meta_tags_title_is_case_insensitive_and_stripped():
    html = "<TITLE>  Spaced Title  </TITLE>"
    tags = tool.extract_meta_tags(html)
    assert tags['title'] == "Spaced Title"


def test_extract_meta_tags_missing_title_has_no_key():
    html = "<html><head></head></html>"
    tags = tool.extract_meta_tags(html)
    assert 'title' not in tags


def test_extract_meta_tags_description_with_real_text_is_not_captured():
    html = '<meta name="description" content="A real description of the page">'
    tags = tool.extract_meta_tags(html)
    assert 'description' not in tags


def test_extract_meta_tags_description_with_only_allowed_chars_is_captured_empty_after_strip():
    html = '<meta name="description" content="   ">'
    tags = tool.extract_meta_tags(html)
    assert tags['description'] == ""


def test_extract_meta_tags_keywords_with_real_text_is_not_captured():
    html = '<meta name="keywords" content="seo, marketing, tools">'
    tags = tool.extract_meta_tags(html)
    assert 'keywords' not in tags


def test_extract_meta_tags_keywords_with_allowed_chars_is_captured():
    html = '<meta name="keywords" content=" ^ ">'
    tags = tool.extract_meta_tags(html)
    assert tags['keywords'] == "^"


def test_extract_meta_tags_og_tags_with_real_text_not_captured():
    html = '<meta property="og:title" content="My Great Page">'
    tags = tool.extract_meta_tags(html)
    assert not any(k.startswith('og:') for k in tags)


def test_extract_meta_tags_og_tags_with_allowed_chars_captured():
    html = '<meta property="og:title" content="   ">'
    tags = tool.extract_meta_tags(html)
    assert tags['og:title'] == ""


def test_extract_meta_tags_twitter_tags_with_real_text_not_captured():
    html = '<meta name="twitter:card" content="summary_large_image">'
    tags = tool.extract_meta_tags(html)
    assert not any(k.startswith('twitter:') for k in tags)


def test_extract_meta_tags_twitter_tags_with_allowed_chars_captured():
    html = '<meta name="twitter:card" content="  ">'
    tags = tool.extract_meta_tags(html)
    assert tags['twitter:card'] == ""


def test_extract_meta_tags_canonical_with_real_url_not_captured():
    html = '<link rel="canonical" href="https://example.com/page">'
    tags = tool.extract_meta_tags(html)
    assert 'canonical' not in tags


def test_extract_meta_tags_canonical_with_allowed_chars_captured():
    html = '<link rel="canonical" href="   ">'
    tags = tool.extract_meta_tags(html)
    assert tags['canonical'] == ""


def test_extract_meta_tags_returns_empty_dict_for_empty_html():
    assert tool.extract_meta_tags("") == {}


# ---------------------------------------------------------------------------
# extract_headings
# ---------------------------------------------------------------------------

def test_extract_headings_extracts_each_level():
    html = "<h1>Title</h1><h2>Sub</h2><h3>Sub sub</h3>"
    headings = tool.extract_headings(html)
    assert headings['h1'] == ['Title']
    assert headings['h2'] == ['Sub']
    assert headings['h3'] == ['Sub sub']
    assert headings['h4'] == []
    assert headings['h5'] == []
    assert headings['h6'] == []


def test_extract_headings_multiple_of_same_level_and_strip_whitespace():
    html = "<h2> First </h2><h2>Second</h2>"
    headings = tool.extract_headings(html)
    assert headings['h2'] == ['First', 'Second']


def test_extract_headings_case_insensitive():
    html = "<H1>Shouty</H1>"
    headings = tool.extract_headings(html)
    assert headings['h1'] == ['Shouty']


def test_extract_headings_empty_html_all_empty_lists():
    headings = tool.extract_headings("")
    assert all(v == [] for v in headings.values())
    assert set(headings.keys()) == {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}


# ---------------------------------------------------------------------------
# extract_links
#
# The href-capture regex has the same broken character class bug, so real
# href values (containing letters, '/', ':') are never matched. Only
# href values made up solely of spaces/'^'/quote characters are captured,
# and via urljoin() those always resolve back to the same page as the
# base_url, so they are classified as "internal". The 'broken' key is
# never populated anywhere in the function (a documented dead field).
# ---------------------------------------------------------------------------

def test_extract_links_real_hrefs_are_not_captured_at_all():
    html = '<a href="https://example.com/other">x</a><a href="/relative/path">y</a>'
    links = tool.extract_links(html, "https://example.com/page")
    assert links['internal'] == []
    assert links['external'] == []


def test_extract_links_whitespace_only_href_classified_internal():
    html = '<a href="   ">link</a>'
    links = tool.extract_links(html, "https://example.com/page")
    assert links['internal'] == ["https://example.com/page"]
    assert links['external'] == []


def test_extract_links_broken_key_always_empty():
    html = '<a href="   ">link</a>'
    links = tool.extract_links(html, "https://example.com/page")
    assert links['broken'] == []


def test_extract_links_no_anchors_returns_empty_lists():
    links = tool.extract_links("<p>no links here</p>", "https://example.com")
    assert links == {'internal': [], 'external': [], 'broken': []}


def test_extract_links_dedupe_is_not_performed_by_the_function_itself():
    # extract_links appends every match; de-duplication happens later
    # (via set()) in the callers, not inside this function.
    html = '<a href="   ">a</a><a href="   ">b</a>'
    links = tool.extract_links(html, "https://example.com/page")
    assert links['internal'] == [
        "https://example.com/page",
        "https://example.com/page",
    ]


# ---------------------------------------------------------------------------
# extract_images
#
# Same broken character class bug applies to src/alt capture. A real src
# URL never matches, so the 'src' key is typically absent. The alt
# capture uses '*' (zero-or-more) so it "matches" but only ever succeeds
# when the alt text itself is made of allowed chars; for real alt text it
# fails to match and the function falls back to alt=''.
# ---------------------------------------------------------------------------

def test_extract_images_real_src_and_alt_text_yields_no_src_and_empty_alt():
    html = '<img src="https://example.com/cat.png" alt="A fluffy cat">'
    images = tool.extract_images(html)
    assert len(images) == 1
    assert 'src' not in images[0]
    assert images[0]['alt'] == ''


def test_extract_images_alt_with_only_allowed_chars_is_captured():
    html = '<img src="https://example.com/cat.png" alt="^^">'
    images = tool.extract_images(html)
    assert images[0]['alt'] == '^^'


def test_extract_images_explicit_empty_alt_is_empty_string():
    html = '<img src="https://example.com/cat.png" alt="">'
    images = tool.extract_images(html)
    assert images[0]['alt'] == ''


def test_extract_images_src_with_only_allowed_chars_is_captured_unstripped():
    html = '<img src="   " alt="^">'
    images = tool.extract_images(html)
    assert images[0]['src'] == '   '


def test_extract_images_multiple_images_and_no_images():
    html = '<img src="a.png" alt="one"><img src="b.png" alt="two">'
    images = tool.extract_images(html)
    assert len(images) == 2

    assert tool.extract_images("<p>no images</p>") == []


# ---------------------------------------------------------------------------
# calculate_content_score
# ---------------------------------------------------------------------------

def _html_with_word_count(n, extra=""):
    words = " ".join(f"word{i}" for i in range(n))
    return f"<html><body>{extra}{words}</body></html>"


def test_content_score_title_optimal_band():
    html = "<title>" + ("x" * 40) + "</title>" + _html_with_word_count(300) + "<meta name=viewport content=x>"
    meta_tags = tool.extract_meta_tags(html)
    score, issues = tool.calculate_content_score(html, meta_tags)
    assert not any("Title length" in i for i in issues)


def test_content_score_title_mid_band_adds_issue():
    title = "x" * 25  # 20-29 range -> +15 with issue
    html = f"<title>{title}</title>"
    meta_tags = tool.extract_meta_tags(html)
    score, issues = tool.calculate_content_score(html, meta_tags)
    assert f"Title length {len(title)} (optimal: 30-60)" in issues


def test_content_score_title_bad_band_adds_issue_low_score():
    title = "x" * 5  # <20 -> +5 with issue
    html = f"<title>{title}</title>"
    meta_tags = tool.extract_meta_tags(html)
    score, issues = tool.calculate_content_score(html, meta_tags)
    assert f"Title length {len(title)} (optimal: 30-60)" in issues


def test_content_score_missing_title_issue():
    html = "<p>no title here</p>"
    meta_tags = tool.extract_meta_tags(html)
    score, issues = tool.calculate_content_score(html, meta_tags)
    assert "Missing title tag" in issues


def test_content_score_description_missing_issue():
    html = "<title>abc</title>"
    meta_tags = tool.extract_meta_tags(html)
    score, issues = tool.calculate_content_score(html, meta_tags)
    assert "Missing meta description" in issues


def test_content_score_description_present_but_short_gives_low_band():
    # Because of the extraction bug only whitespace-only content can ever
    # be captured as a 'description' -- so desc_len is effectively always
    # very small (e.g. 0), landing in the "else" (+5) branch.
    meta_tags = {'description': ''}
    score, issues = tool.calculate_content_score("<p>x</p>", meta_tags)
    assert "Description length 0 (optimal: 120-160)" in issues


def test_content_score_description_optimal_band_via_direct_meta_tags():
    meta_tags = {'description': 'x' * 140}
    score, issues = tool.calculate_content_score("<p>x</p>", meta_tags)
    assert not any("Description length" in i for i in issues)


def test_content_score_description_mid_band_via_direct_meta_tags():
    meta_tags = {'description': 'x' * 110}
    score, issues = tool.calculate_content_score("<p>x</p>", meta_tags)
    assert "Description length 110 (optimal: 120-160)" in issues


def test_content_score_h1_exactly_one_no_issue():
    html = "<h1>Only heading</h1>"
    score, issues = tool.calculate_content_score(html, {})
    assert not any("H1" in i for i in issues)


def test_content_score_h1_zero_issue():
    html = "<p>no h1</p>"
    score, issues = tool.calculate_content_score(html, {})
    assert "Missing H1 tag" in issues


def test_content_score_h1_multiple_issue():
    html = "<h1>One</h1><h1>Two</h1>"
    score, issues = tool.calculate_content_score(html, {})
    assert "Multiple H1 tags (2)" in issues


def test_content_score_images_high_alt_ratio_no_issue():
    # 9/10 images with a truthy (bug-compatible) alt value -> ratio 0.9 -> +15, no issue
    imgs = '<img src="a" alt="^">' * 9 + '<img src="a" alt="realtext">'
    score, issues = tool.calculate_content_score(imgs, {})
    assert not any("alt tags" in i for i in issues)


def test_content_score_images_mid_alt_ratio_issue():
    # 7/10 with alt="^" (truthy) -> ratio 0.7 -> +10 with issue
    imgs = '<img src="a" alt="^">' * 7 + '<img src="a" alt="realtext">' * 3
    score, issues = tool.calculate_content_score(imgs, {})
    assert "Only 7/10 images have alt tags" in issues


def test_content_score_images_low_alt_ratio_issue():
    imgs = '<img src="a" alt="realtext">' * 4
    score, issues = tool.calculate_content_score(imgs, {})
    assert "Only 0/4 images have alt tags" in issues


def test_content_score_no_images_no_alt_issue_and_no_points():
    html_no_images = "<p>text</p>"
    html_with_bad_images = '<img src="a" alt="realtext">' * 4
    score_no_images, issues_no_images = tool.calculate_content_score(html_no_images, {})
    score_with_images, issues_with_images = tool.calculate_content_score(html_with_bad_images, {})
    assert not any("alt" in i for i in issues_no_images)
    # both contribute 0 points from the image bucket, but the "no images"
    # case never appends an issue while the "bad alt" case does.
    assert any("alt" in i for i in issues_with_images)


def test_content_score_word_count_high_band_no_issue():
    html = _html_with_word_count(300)
    score, issues = tool.calculate_content_score(html, {})
    assert not any("words" in i for i in issues)


def test_content_score_word_count_mid_band_issue():
    html = _html_with_word_count(150)
    score, issues = tool.calculate_content_score(html, {})
    assert "Content only 150 words (recommended: 300+)" in issues


def test_content_score_word_count_low_band_issue():
    html = _html_with_word_count(10)
    score, issues = tool.calculate_content_score(html, {})
    assert "Content only 10 words (recommended: 300+)" in issues


def test_content_score_viewport_present_no_issue():
    html = "<meta name=viewport content=x>"
    score, issues = tool.calculate_content_score(html, {})
    assert not any("viewport" in i for i in issues)


def test_content_score_viewport_missing_issue():
    score, issues = tool.calculate_content_score("<p>x</p>", {})
    assert "Missing viewport meta tag for mobile" in issues


def _score_for_title_len(title_len):
    meta_tags = {'title': 'x' * title_len}
    score, issues = tool.calculate_content_score("<p>x</p>", meta_tags)
    return score


# baseline html/meta_tags contribute exactly 0 from every other bucket, so the
# total score isolates the title bucket precisely -- this is what's needed to
# distinguish the primary/mid/low bands, since the mid and low bands emit the
# SAME issue text and only differ in points. (Not using pytest.mark.parametrize:
# the skill_gate.py promotion baseline tracks tests by bare function name and
# does not recognize parametrized instance ids, so every case is its own
# named test function instead.)
def test_content_score_title_len_19_is_low_band_score_5():
    assert _score_for_title_len(19) == 5


def test_content_score_title_len_20_is_mid_band_score_15():
    assert _score_for_title_len(20) == 15


def test_content_score_title_len_29_is_mid_band_score_15():
    assert _score_for_title_len(29) == 15


def test_content_score_title_len_30_is_primary_band_score_25():
    assert _score_for_title_len(30) == 25


def test_content_score_title_len_60_is_primary_band_score_25():
    assert _score_for_title_len(60) == 25


def test_content_score_title_len_61_is_mid_band_score_15():
    assert _score_for_title_len(61) == 15


def test_content_score_title_len_70_is_mid_band_score_15():
    assert _score_for_title_len(70) == 15


def test_content_score_title_len_71_is_low_band_score_5():
    assert _score_for_title_len(71) == 5


def _score_for_desc_len(desc_len):
    meta_tags = {'description': 'x' * desc_len}
    score, issues = tool.calculate_content_score("<p>x</p>", meta_tags)
    return score


def test_content_score_desc_len_99_is_low_band_score_5():
    assert _score_for_desc_len(99) == 5


def test_content_score_desc_len_100_is_mid_band_score_15():
    assert _score_for_desc_len(100) == 15


def test_content_score_desc_len_119_is_mid_band_score_15():
    assert _score_for_desc_len(119) == 15


def test_content_score_desc_len_120_is_primary_band_score_25():
    assert _score_for_desc_len(120) == 25


def test_content_score_desc_len_160_is_primary_band_score_25():
    assert _score_for_desc_len(160) == 25


def test_content_score_desc_len_161_is_mid_band_score_15():
    assert _score_for_desc_len(161) == 15


def test_content_score_desc_len_180_is_mid_band_score_15():
    assert _score_for_desc_len(180) == 15


def test_content_score_desc_len_181_is_low_band_score_5():
    assert _score_for_desc_len(181) == 5


def _score_for_alt_ratio(truthy_count, total):
    falsy_count = total - truthy_count
    imgs = '<img src="a" alt="^">' * truthy_count + '<img src="a" alt="realtext">' * falsy_count
    score, issues = tool.calculate_content_score(imgs, {})
    return score


def test_content_score_alt_ratio_69_pct_is_low_band_score_5():
    assert _score_for_alt_ratio(69, 100) == 5


def test_content_score_alt_ratio_70_pct_is_mid_band_score_10():
    assert _score_for_alt_ratio(70, 100) == 10


def test_content_score_alt_ratio_89_pct_is_mid_band_score_10():
    assert _score_for_alt_ratio(89, 100) == 10


def test_content_score_alt_ratio_90_pct_is_high_band_score_15():
    assert _score_for_alt_ratio(90, 100) == 15


def test_content_score_word_count_149_is_zero_band_score_0():
    score, issues = tool.calculate_content_score(_html_with_word_count(149), {})
    assert score == 0


def test_content_score_word_count_150_is_mid_band_score_5():
    score, issues = tool.calculate_content_score(_html_with_word_count(150), {})
    assert score == 5


def test_content_score_word_count_299_is_mid_band_score_5():
    score, issues = tool.calculate_content_score(_html_with_word_count(299), {})
    assert score == 5


def test_content_score_word_count_300_is_high_band_score_10():
    score, issues = tool.calculate_content_score(_html_with_word_count(300), {})
    assert score == 10


def test_content_score_full_breakdown_sums_correctly():
    # title optimal (25) + h1 optimal (15) + word count high (10) + viewport (10)
    # description missing (0) + no images (0) = 60
    html = (
        "<title>" + ("x" * 40) + "</title>"
        + "<h1>Heading</h1>"
        + "<meta name=viewport content=x>"
        + _html_with_word_count(300)
    )
    meta_tags = tool.extract_meta_tags(html)
    score, issues = tool.calculate_content_score(html, meta_tags)
    assert score == 60


# ---------------------------------------------------------------------------
# save_audit_report
# ---------------------------------------------------------------------------

def test_save_audit_report_writes_expected_structure(tmp_path):
    out_file = tmp_path / "report.json"
    tool.save_audit_report(
        url="https://example.com",
        score=77,
        meta_tags={'title': 'T'},
        headings={'h1': ['A'], 'h2': [], 'h3': [], 'h4': [], 'h5': [], 'h6': []},
        links={'internal': ['a', 'a', 'b'], 'external': ['c']},
        images=[{'alt': 'x'}, {'alt': ''}],
        issues=['issue one'],
        recommendations=['rec one'],
        output_file=str(out_file),
    )

    data = json.loads(out_file.read_text())
    assert data['url'] == "https://example.com"
    assert data['score'] == 77
    assert data['meta_tags'] == {'title': 'T'}
    assert data['links'] == {'internal_count': 2, 'external_count': 1}
    assert data['images'] == {'total': 2, 'with_alt': 1, 'without_alt': 1}
    assert data['issues'] == ['issue one']
    assert data['recommendations'] == ['rec one']
    assert 'timestamp' in data


# ---------------------------------------------------------------------------
# audit_site
# ---------------------------------------------------------------------------

def test_audit_site_fetch_failure_exits_1(monkeypatch):
    monkeypatch.setattr(tool, "fetch_url", lambda url: ("", 0, {}))
    args = _Args(url="https://example.com", output=None)
    with pytest.raises(SystemExit) as exc:
        tool.audit_site(args)
    assert exc.value.code == 1


def test_audit_site_success_returns_zero_and_prints_status(monkeypatch, capsys):
    html = "<title>" + ("x" * 40) + "</title><h1>Head</h1>" + "<meta name=viewport content=x>" + " ".join(["w"] * 300)
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", output=None)
    result = tool.audit_site(args)
    out = capsys.readouterr().out
    assert result == 0
    assert "Status: 200" in out


def test_audit_site_reports_https_and_viewport_and_canonical_missing(monkeypatch, capsys):
    html = "<title>" + ("x" * 40) + "</title><h1>Head</h1>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="http://example.com", output=None)
    tool.audit_site(args)
    out = capsys.readouterr().out
    assert "Not using HTTPS" in out
    assert "Missing canonical URL" in out
    assert "Missing viewport meta tag" in out
    assert "Missing Open Graph tags" in out


def test_audit_site_writes_report_when_output_given(monkeypatch, tmp_path):
    html = "<title>" + ("x" * 40) + "</title><h1>Head</h1>" + "<meta name=viewport content=x>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    out_file = tmp_path / "report.json"
    args = _Args(url="https://example.com", output=str(out_file))
    tool.audit_site(args)
    assert out_file.exists()
    data = json.loads(out_file.read_text())
    assert data['url'] == "https://example.com"


def test_audit_site_recommendations_for_missing_fields(monkeypatch, capsys):
    html = "<p>short</p>"  # missing title, description, h1, og, viewport
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", output=None)
    tool.audit_site(args)
    out = capsys.readouterr().out
    assert "Add a title tag (30-60 characters)" in out
    assert "Add meta description (120-160 characters)" in out
    assert "Use exactly one H1 tag per page" in out
    assert "Add Open Graph tags for social sharing" in out
    assert "Add viewport meta tag for mobile optimization" in out


def test_audit_site_title_length_recommendation_when_out_of_band(monkeypatch, capsys):
    html = "<title>short</title><h1>H</h1><meta name=viewport content=x>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", output=None)
    tool.audit_site(args)
    out = capsys.readouterr().out
    assert "Optimize title length (currently 5 chars)" in out


def test_audit_site_missing_alt_recommendation(monkeypatch, capsys):
    html = (
        "<title>" + ("x" * 40) + "</title><h1>H</h1><meta name=viewport content=x>"
        + '<img src="a" alt="realtext">' * 4
    )
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", output=None)
    tool.audit_site(args)
    out = capsys.readouterr().out
    assert "Add alt tags to 4 images" in out


def test_audit_site_high_score_prints_no_critical_issues(monkeypatch, capsys):
    # calculate_content_score is monkeypatched directly to exercise the
    # >=90 branch, since the real extraction bug caps achievable scores
    # well below 90 for any realistic HTML (see extract_meta_tags notes).
    html = "<title>" + ("x" * 40) + "</title><h1>H</h1><meta name=viewport content=x>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    monkeypatch.setattr(tool, "calculate_content_score", lambda html, meta: (95, []))
    args = _Args(url="https://example.com", output=None)
    tool.audit_site(args)
    out = capsys.readouterr().out
    assert "No critical issues found!" in out
    assert "1." not in out.split("Recommendations")[-1].split("No critical")[0]


def test_audit_site_h1_present_prints_optimal_and_multiple_h1_warns(monkeypatch, capsys):
    html = "<title>" + ("x" * 40) + "</title><h1>Only</h1><meta name=viewport content=x>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", output=None)
    tool.audit_site(args)
    out = capsys.readouterr().out
    assert "H1: 1 (optimal)" in out

    html2 = "<title>" + ("x" * 40) + "</title><h1>One</h1><h1>Two</h1><meta name=viewport content=x>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html2, 200, {}))
    tool.audit_site(args)
    out2 = capsys.readouterr().out
    assert "H1: 2 (should be 1)" in out2


def test_audit_site_description_canonical_og_present_via_bug_workaround(monkeypatch, capsys):
    # These meta values can only ever be non-missing when their content is
    # made purely of the regex's allowed chars (see extract_meta_tags notes).
    html = (
        "<title>" + ("x" * 40) + "</title><h1>H</h1><h2>sub</h2>"
        + '<meta name="viewport" content="w">'
        + '<meta name="description" content="^">'
        + '<link rel="canonical" href="   ">'
        + '<meta property="og:image" content="   ">'
    )
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", output=None)
    tool.audit_site(args)
    out = capsys.readouterr().out
    assert "Description (1 chars):" in out
    assert "Canonical: " in out
    assert "Open Graph: 1 tags found" in out
    assert "H2: 1" in out
    assert "Optimize description length (currently 1 chars)" in out


def test_audit_site_h2_h3_present_vs_absent_uses_distinct_print_functions(monkeypatch, capsys):
    # print_success and print_info render the SAME trailing text ("H2: 1")
    # but with different colored prefixes -- assert the exact prefix so a
    # mutation of `count > 0` can't hide behind a loose substring match.
    html = "<title>" + ("x" * 40) + "</title><h1>H</h1><h2>sub</h2><meta name=viewport content=x>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", output=None)
    tool.audit_site(args)
    out = capsys.readouterr().out
    assert f"{tool.Colors.GREEN}✓{tool.Colors.RESET} H2: 1" in out
    assert f"{tool.Colors.BOLD}→{tool.Colors.RESET} H3: 0" in out


def test_audit_site_title_over_60_chars_recommendation(monkeypatch, capsys):
    html = "<title>" + ("x" * 65) + "</title><h1>H</h1><meta name=viewport content=x>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", output=None)
    tool.audit_site(args)
    out = capsys.readouterr().out
    assert "Optimize title length (currently 65 chars)" in out


def test_audit_site_description_over_160_chars_recommendation(monkeypatch, capsys):
    # only reachable via the extraction bug's allowed-char workaround
    html = (
        "<title>" + ("x" * 40) + "</title><h1>H</h1><meta name=viewport content=x>"
        + '<meta name="description" content="' + ("^" * 165) + '">'
    )
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", output=None)
    tool.audit_site(args)
    out = capsys.readouterr().out
    assert "Optimize description length (currently 165 chars)" in out


def test_audit_site_all_images_have_alt_no_missing_alt_recommendation(monkeypatch, capsys):
    html = (
        "<title>" + ("x" * 40) + "</title><h1>H</h1><meta name=viewport content=x>"
        + '<img src="a" alt="^">' * 4
    )
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", output=None)
    tool.audit_site(args)
    out = capsys.readouterr().out
    assert "Add alt tags to" not in out


def test_audit_site_images_without_alt_warns(monkeypatch, capsys):
    html = (
        "<title>" + ("x" * 40) + "</title><h1>H</h1><meta name=viewport content=x>"
        + '<img src="a" alt="realtext">'
    )
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", output=None)
    tool.audit_site(args)
    out = capsys.readouterr().out
    assert "Total images: 1" in out
    assert "Without alt tags: 1" in out


# ---------------------------------------------------------------------------
# analyze_keywords
# ---------------------------------------------------------------------------

def test_analyze_keywords_fetch_failure_exits_1(monkeypatch):
    monkeypatch.setattr(tool, "fetch_url", lambda url: ("", 0, {}))
    args = _Args(url="https://example.com", keyword=None, top=20, output=None)
    with pytest.raises(SystemExit) as exc:
        tool.analyze_keywords(args)
    assert exc.value.code == 1


def test_analyze_keywords_ranks_by_frequency_and_excludes_stopwords(monkeypatch, capsys):
    html = "<p>alpha alpha alpha beta beta the the the and and</p>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", keyword=None, top=5, output=None)
    tool.analyze_keywords(args)
    out = capsys.readouterr().out
    assert "alpha" in out
    assert "beta" in out
    # stop words must never appear as ranked keywords
    lines = [l for l in out.splitlines() if "times)" in l]
    assert not any(l.strip().split('.')[1].strip().startswith("the ") for l in lines if '.' in l)


def test_analyze_keywords_top_n_limits_results(monkeypatch, capsys):
    words = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india", "juliet"]
    html = "<p>" + " ".join(" ".join([w] * (10 - i)) for i, w in enumerate(words)) + "</p>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", keyword=None, top=3, output=None)
    tool.analyze_keywords(args)
    out = capsys.readouterr().out
    kw_lines = [l for l in out.splitlines() if l.strip().startswith(tuple("123456789")) and "times)" in l]
    assert len(kw_lines) == 3
    assert "alpha" in kw_lines[0]
    assert "bravo" in kw_lines[1]
    assert "charlie" in kw_lines[2]


def test_analyze_keywords_keyword_found_in_title_and_h1(monkeypatch, capsys):
    html = "<title>great widgets</title><h1>Buy widgets now</h1><p>widgets are great widgets</p>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", keyword="widgets", top=5, output=None)
    tool.analyze_keywords(args)
    out = capsys.readouterr().out
    assert "Keyword 'widgets' found in title" in out
    assert "Keyword 'widgets' found in H1" in out
    # description extraction is broken for real text -> always "NOT in description"
    assert "Keyword 'widgets' NOT in description" in out


def test_analyze_keywords_keyword_not_found_anywhere(monkeypatch, capsys):
    html = "<title>nothing relevant</title><h1>irrelevant</h1><p>filler filler filler</p>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", keyword="widgets", top=5, output=None)
    tool.analyze_keywords(args)
    out = capsys.readouterr().out
    assert "Keyword 'widgets' NOT in title" in out
    assert "Keyword 'widgets' NOT in H1" in out


def test_analyze_keywords_keyword_found_in_description_via_bug_workaround(monkeypatch, capsys):
    # 'description' can only ever be captured as a run of allowed chars
    # (space/^/quotes); using a keyword drawn from that same alphabet is the
    # only way to exercise the "found in description" success branch.
    html = '<meta name="description" content="^^^"><title>x</title><h1>y</h1>'
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", keyword="^", top=5, output=None)
    tool.analyze_keywords(args)
    out = capsys.readouterr().out
    assert "Keyword '^' found in description" in out


def test_analyze_keywords_writes_output_report(monkeypatch, tmp_path):
    html = "<p>alpha alpha beta</p>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    out_file = tmp_path / "kw.json"
    args = _Args(url="https://example.com", keyword=None, top=5, output=str(out_file))
    tool.analyze_keywords(args)
    data = json.loads(out_file.read_text())
    assert data['url'] == "https://example.com"
    assert data['total_words'] == 3
    words = {kw['word']: kw for kw in data['top_keywords']}
    assert words['alpha']['count'] == 2
    assert words['beta']['count'] == 1
    assert abs(words['alpha']['density'] - (2 / 3 * 100)) < 1e-9


# ---------------------------------------------------------------------------
# generate_sitemap
# ---------------------------------------------------------------------------

def test_generate_sitemap_single_page_real_links_not_followed(monkeypatch, tmp_path):
    # A page with real <a href> links won't have those links captured by
    # extract_links (see the docs above), so the crawl only ever visits
    # the starting URL.
    html = '<a href="https://example.com/other">x</a>'
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    out_file = tmp_path / "sitemap.xml"
    args = _Args(url="https://example.com", max_urls=100, output=str(out_file))
    tool.generate_sitemap(args)

    import xml.etree.ElementTree as ET
    tree = ET.parse(out_file)
    urls = tree.getroot().findall('{http://www.sitemaps.org/schemas/sitemap/0.9}url')
    assert len(urls) == 1
    loc = urls[0].find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
    assert loc.text == "https://example.com"


def test_generate_sitemap_max_urls_zero_produces_empty_sitemap(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(tool, "fetch_url", lambda url: (calls.append(url), "", 200, {})[1:])
    out_file = tmp_path / "sitemap.xml"
    args = _Args(url="https://example.com", max_urls=0, output=str(out_file))
    tool.generate_sitemap(args)
    assert calls == []  # loop body never executes

    import xml.etree.ElementTree as ET
    tree = ET.parse(out_file)
    urls = tree.getroot().findall('{http://www.sitemaps.org/schemas/sitemap/0.9}url')
    assert len(urls) == 0


def test_generate_sitemap_non_200_status_excluded(monkeypatch, tmp_path):
    monkeypatch.setattr(tool, "fetch_url", lambda url: ("", 404, {}))
    out_file = tmp_path / "sitemap.xml"
    args = _Args(url="https://example.com", max_urls=100, output=str(out_file))
    tool.generate_sitemap(args)

    import xml.etree.ElementTree as ET
    tree = ET.parse(out_file)
    urls = tree.getroot().findall('{http://www.sitemaps.org/schemas/sitemap/0.9}url')
    assert len(urls) == 0


def test_generate_sitemap_multi_page_crawl_via_mocked_extract_links(monkeypatch, tmp_path):
    # Bypass the extraction bug entirely to exercise generate_sitemap's own
    # crawl/queue/dedup/priority orchestration logic in isolation.
    pages = {
        "https://example.com": ["https://example.com/a", "https://example.com/b"],
        "https://example.com/a": ["https://example.com/b", "https://example.com"],
        "https://example.com/b": [],
    }

    def fake_fetch(url):
        if url in pages:
            return ("<html></html>", 200, {})
        return ("", 404, {})

    def fake_extract_links(html, base_url):
        return {'internal': pages.get(base_url, []), 'external': []}

    monkeypatch.setattr(tool, "fetch_url", fake_fetch)
    monkeypatch.setattr(tool, "extract_links", fake_extract_links)

    out_file = tmp_path / "sitemap.xml"
    args = _Args(url="https://example.com", max_urls=100, output=str(out_file))
    tool.generate_sitemap(args)

    import xml.etree.ElementTree as ET
    tree = ET.parse(out_file)
    ns = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
    urls = tree.getroot().findall(f'{ns}url')
    locs = [u.find(f'{ns}loc').text for u in urls]
    priorities = {u.find(f'{ns}loc').text: u.find(f'{ns}priority').text for u in urls}

    assert set(locs) == {"https://example.com", "https://example.com/a", "https://example.com/b"}
    assert priorities["https://example.com"] == "0.8"
    assert priorities["https://example.com/a"] == "0.5"
    assert priorities["https://example.com/b"] == "0.5"


def test_generate_sitemap_writes_real_xml_declaration(monkeypatch, tmp_path):
    monkeypatch.setattr(tool, "fetch_url", lambda url: ("<html></html>", 200, {}))
    out_file = tmp_path / "sitemap.xml"
    args = _Args(url="https://example.com", max_urls=1, output=str(out_file))
    tool.generate_sitemap(args)
    raw = out_file.read_bytes()
    assert raw.startswith(b"<?xml version=")


def test_generate_sitemap_max_urls_limits_crawl(monkeypatch, tmp_path):
    pages = {
        "https://example.com": ["https://example.com/a", "https://example.com/b"],
        "https://example.com/a": [],
        "https://example.com/b": [],
    }

    def fake_fetch(url):
        return ("<html></html>", 200, {}) if url in pages else ("", 404, {})

    def fake_extract_links(html, base_url):
        return {'internal': pages.get(base_url, []), 'external': []}

    monkeypatch.setattr(tool, "fetch_url", fake_fetch)
    monkeypatch.setattr(tool, "extract_links", fake_extract_links)

    out_file = tmp_path / "sitemap.xml"
    args = _Args(url="https://example.com", max_urls=1, output=str(out_file))
    tool.generate_sitemap(args)

    import xml.etree.ElementTree as ET
    tree = ET.parse(out_file)
    ns = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
    urls = tree.getroot().findall(f'{ns}url')
    assert len(urls) == 1


def test_generate_sitemap_default_output_filename(monkeypatch, tmp_path, monkeypatch_cwd=None):
    monkeypatch.setattr(tool, "fetch_url", lambda url: ("<html></html>", 200, {}))
    args = _Args(url="https://example.com", max_urls=1, output=None)
    import os
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        tool.generate_sitemap(args)
        assert (tmp_path / "sitemap.xml").exists()
    finally:
        os.chdir(old_cwd)


# ---------------------------------------------------------------------------
# generate_robots_txt
# ---------------------------------------------------------------------------

def test_generate_robots_txt_writes_file_with_sitemap_line(tmp_path, capsys):
    out_file = tmp_path / "robots.txt"
    args = _Args(url="https://example.com/", output=str(out_file))
    tool.generate_robots_txt(args)
    content = out_file.read_text()
    assert "Sitemap: https://example.com/sitemap.xml" in content
    assert "User-agent: *" in content
    out = capsys.readouterr().out
    assert "robots.txt saved to" in out


def test_generate_robots_txt_strips_trailing_slash_from_url(tmp_path):
    out_file = tmp_path / "robots.txt"
    args = _Args(url="https://example.com///", output=str(out_file))
    tool.generate_robots_txt(args)
    content = out_file.read_text()
    # rstrip('/') removes ALL trailing slash characters, not just one
    assert "Sitemap: https://example.com/sitemap.xml" in content


def test_generate_robots_txt_default_output_filename(tmp_path):
    args = _Args(url="https://example.com", output=None)
    import os
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        tool.generate_robots_txt(args)
        assert (tmp_path / "robots.txt").exists()
    finally:
        os.chdir(old_cwd)


# ---------------------------------------------------------------------------
# generate_schema
# ---------------------------------------------------------------------------

def test_generate_schema_website_default_type(capsys):
    args = _Args(url="https://example.com", type=None, name=None, description=None, output=None)
    tool.generate_schema(args)
    out = capsys.readouterr().out
    assert '"@type": "WebSite"' in out
    assert '"name": "Your Website Name"' in out


def test_generate_schema_organization_with_custom_name_and_description(capsys):
    args = _Args(url="https://example.com", type="organization", name="Acme", description="We make things", output=None)
    tool.generate_schema(args)
    out = capsys.readouterr().out
    assert '"@type": "Organization"' in out
    assert '"name": "Acme"' in out
    assert '"description": "We make things"' in out
    assert '"logo": "https://example.com/logo.png"' in out


def test_generate_schema_article_type_uses_name_as_headline(capsys):
    args = _Args(url="https://example.com", type="article", name="Big News", description=None, output=None)
    tool.generate_schema(args)
    out = capsys.readouterr().out
    assert '"@type": "Article"' in out
    assert '"headline": "Big News"' in out


def test_generate_schema_breadcrumb_type_has_three_items(capsys):
    args = _Args(url="https://example.com", type="breadcrumb", name=None, description=None, output=None)
    tool.generate_schema(args)
    out = capsys.readouterr().out
    assert '"@type": "BreadcrumbList"' in out
    # the schema JSON is printed twice (once as raw JSON-LD, once again
    # embedded inside the <script> HTML block), so each ListItem shows up twice
    assert out.count('"@type": "ListItem"') == 6


def test_generate_schema_invalid_type_exits_1(capsys):
    args = _Args(url="https://example.com", type="bogus", name=None, description=None, output=None)
    with pytest.raises(SystemExit) as exc:
        tool.generate_schema(args)
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "Unknown schema type: bogus" in out


def test_generate_schema_writes_output_file(tmp_path):
    out_file = tmp_path / "schema.html"
    args = _Args(url="https://example.com", type="website", name=None, description=None, output=str(out_file))
    tool.generate_schema(args)
    content = out_file.read_text()
    assert content.startswith('<script type="application/ld+json">')
    assert '"@type": "WebSite"' in content


# ---------------------------------------------------------------------------
# content_optimizer
# ---------------------------------------------------------------------------

def test_content_optimizer_fetch_failure_exits_1(monkeypatch):
    monkeypatch.setattr(tool, "fetch_url", lambda url: ("", 0, {}))
    args = _Args(url="https://example.com", keyword=None)
    with pytest.raises(SystemExit) as exc:
        tool.content_optimizer(args)
    assert exc.value.code == 1


def test_content_optimizer_short_content_warns(monkeypatch, capsys):
    html = "<p>too short</p>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", keyword=None)
    tool.content_optimizer(args)
    out = capsys.readouterr().out
    assert "Content is too short" in out
    assert "Add more content" in out


def test_content_optimizer_keyword_density_optimal(monkeypatch, capsys):
    # 300 words, keyword appears 3 times -> density = 1.0% (optimal 0.5-2.5)
    words = ["seo"] * 3 + ["filler"] * 297
    html = "<p>" + " ".join(words) + "</p>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", keyword="seo")
    tool.content_optimizer(args)
    out = capsys.readouterr().out
    assert "Keyword density is optimal" in out


def test_content_optimizer_keyword_density_too_low(monkeypatch, capsys):
    words = ["seo"] + ["filler"] * 999
    html = "<p>" + " ".join(words) + "</p>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", keyword="seo")
    tool.content_optimizer(args)
    out = capsys.readouterr().out
    assert "Keyword density too low" in out


def test_content_optimizer_keyword_density_too_high(monkeypatch, capsys):
    words = ["seo"] * 10 + ["filler"] * 90
    html = "<p>" + " ".join(words) + "</p>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", keyword="seo")
    tool.content_optimizer(args)
    out = capsys.readouterr().out
    assert "Keyword density too high" in out


def test_content_optimizer_zero_word_count_density_guard(monkeypatch, capsys):
    # word_count == 0 must not raise ZeroDivisionError; density falls back to 0
    monkeypatch.setattr(tool, "fetch_url", lambda url: ("", 200, {}))
    args = _Args(url="https://example.com", keyword="seo")
    tool.content_optimizer(args)
    out = capsys.readouterr().out
    assert "Keyword density: 0.00%" in out
    assert "Keyword density too low" in out


def test_content_optimizer_suggestion_increase_usage_for_low_density(monkeypatch, capsys):
    words = ["seo"] + ["filler"] * 999
    html = "<p>" + " ".join(words) + "</p>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", keyword="seo")
    tool.content_optimizer(args)
    out = capsys.readouterr().out
    assert "Increase 'seo' usage (current density: 0.10%)" in out


def test_content_optimizer_suggestion_reduce_usage_for_high_density(monkeypatch, capsys):
    words = ["seo"] * 10 + ["filler"] * 90
    html = "<p>" + " ".join(words) + "</p>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", keyword="seo")
    tool.content_optimizer(args)
    out = capsys.readouterr().out
    assert "Reduce 'seo' usage to avoid keyword stuffing" in out


def test_content_optimizer_word_count_mid_band_prints_okay(monkeypatch, capsys):
    html = "<p>" + " ".join(["word"] * 400) + "</p>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", keyword=None)
    tool.content_optimizer(args)
    out = capsys.readouterr().out
    assert "Content length is okay (600+ words recommended)" in out


def test_content_optimizer_keyword_placement_all_found(monkeypatch, capsys):
    html = "<title>seo tips</title><h1>seo guide</h1><p>" + " ".join(["seo"] + ["w"] * 5) + "</p>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", keyword="seo")
    tool.content_optimizer(args)
    out = capsys.readouterr().out
    assert "✓ Keyword in title" in out
    assert "✓ Keyword in H1" in out
    assert "✓ Keyword in first 100 words" in out
    # description extraction is broken for real text -> always NOT found
    assert "✗ Keyword NOT in meta description" in out


def test_content_optimizer_keyword_placement_none_found(monkeypatch, capsys):
    html = "<title>widgets</title><h1>widgets</h1><p>" + " ".join(["filler"] * 200) + "</p>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", keyword="seo")
    tool.content_optimizer(args)
    out = capsys.readouterr().out
    assert "✗ Keyword NOT in title (important!)" in out
    assert "✗ Keyword NOT in H1" in out
    assert "✗ Keyword NOT in first 100 words" in out


def test_content_optimizer_keyword_found_in_description_via_bug_workaround(monkeypatch, capsys):
    html = (
        '<meta name="description" content="^^^"><title>x</title><h1>y</h1>'
        + " ".join(["filler"] * 300)
    )
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", keyword="^")
    tool.content_optimizer(args)
    out = capsys.readouterr().out
    assert "✓ Keyword in meta description" in out


def test_content_optimizer_no_keyword_skips_keyword_sections(monkeypatch, capsys):
    html = "<p>" + " ".join(["filler"] * 300) + "</p>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", keyword=None)
    tool.content_optimizer(args)
    out = capsys.readouterr().out
    assert "Keyword Analysis" not in out
    assert "Keyword Placement" not in out


def test_content_optimizer_long_sentences_warns(monkeypatch, capsys):
    # one giant "sentence" (no punctuation) of 25 words
    html = "<p>" + " ".join(["word"] * 25) + "</p>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", keyword=None)
    tool.content_optimizer(args)
    out = capsys.readouterr().out
    assert "Sentences are too long" in out


def test_content_optimizer_short_sentences_good(monkeypatch, capsys):
    html = "<p>" + ("Short sentence here. " * 30) + "</p>"
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", keyword=None)
    tool.content_optimizer(args)
    out = capsys.readouterr().out
    assert "Sentence length is good" in out


def test_content_optimizer_suggestions_h2_and_description(monkeypatch, capsys):
    html = "<title>" + ("x" * 40) + "</title><h1>H</h1>" + " ".join(["word"] * 400)
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    args = _Args(url="https://example.com", keyword=None)
    tool.content_optimizer(args)
    out = capsys.readouterr().out
    assert "Add more H2 subheadings for better structure" in out
    assert "Add meta description (120-160 characters)" in out


def test_content_optimizer_well_optimized_prints_success(monkeypatch, capsys):
    # Because of the description-extraction bug, a real 'description' value
    # is always either absent or degenerates to '' (falsy), so the
    # `if not meta_tags.get('description')` suggestion would otherwise always
    # fire. To exercise the "fully optimized" branch of content_optimizer's
    # own suggestion logic, force a non-empty description directly.
    html = (
        "<title>" + ("x" * 40) + "</title>"
        + "<h1>H</h1><h2>a</h2><h2>b</h2><h2>c</h2>"
        + " ".join(["word"] * 400)
    )
    monkeypatch.setattr(tool, "fetch_url", lambda url: (html, 200, {}))
    monkeypatch.setattr(
        tool, "extract_meta_tags",
        lambda h: {'title': 'x' * 40, 'description': 'a real non-empty description'},
    )
    args = _Args(url="https://example.com", keyword=None)
    tool.content_optimizer(args)
    out = capsys.readouterr().out
    assert "Content is well optimized!" in out


# ---------------------------------------------------------------------------
# main() CLI dispatch
# ---------------------------------------------------------------------------

def test_main_no_command_prints_help_and_exits_1(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "usage" in out.lower()


def test_main_audit_dispatch_exits_with_audit_site_return_value(monkeypatch):
    captured = {}

    def fake_audit_site(args):
        captured['url'] = args.url
        return 0

    monkeypatch.setattr(tool, "audit_site", fake_audit_site)
    monkeypatch.setattr(sys, "argv", ["tool.py", "audit", "--url", "https://example.com"])
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code == 0
    assert captured['url'] == "https://example.com"


def test_main_audit_dispatch_nonzero_exit(monkeypatch):
    monkeypatch.setattr(tool, "audit_site", lambda args: 1)
    monkeypatch.setattr(sys, "argv", ["tool.py", "audit", "--url", "https://example.com"])
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code == 1


def test_main_keywords_dispatch(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "analyze_keywords", lambda args: captured.setdefault('called', args))
    monkeypatch.setattr(sys, "argv", ["tool.py", "keywords", "--url", "https://example.com", "--keyword", "seo", "--top", "5"])
    result = tool.main()
    assert result is None
    assert captured['called'].url == "https://example.com"
    assert captured['called'].keyword == "seo"
    assert captured['called'].top == 5


def test_main_sitemap_dispatch(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "generate_sitemap", lambda args: captured.setdefault('called', args))
    monkeypatch.setattr(sys, "argv", ["tool.py", "sitemap", "--url", "https://example.com", "--max-urls", "3"])
    tool.main()
    assert captured['called'].max_urls == 3


def test_main_robots_dispatch(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "generate_robots_txt", lambda args: captured.setdefault('called', args))
    monkeypatch.setattr(sys, "argv", ["tool.py", "robots", "--url", "https://example.com"])
    tool.main()
    assert captured['called'].url == "https://example.com"


def test_main_schema_dispatch(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "generate_schema", lambda args: captured.setdefault('called', args))
    monkeypatch.setattr(sys, "argv", ["tool.py", "schema", "--url", "https://example.com", "--type", "article"])
    tool.main()
    assert captured['called'].type == "article"


def test_main_optimize_dispatch(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "content_optimizer", lambda args: captured.setdefault('called', args))
    monkeypatch.setattr(sys, "argv", ["tool.py", "optimize", "--url", "https://example.com", "--keyword", "seo"])
    tool.main()
    assert captured['called'].keyword == "seo"


def _assert_missing_url_exits_2(monkeypatch, subcommand):
    monkeypatch.setattr(sys, "argv", ["tool.py", subcommand])
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code == 2


def test_main_audit_missing_required_url_raises_systemexit_2(monkeypatch):
    _assert_missing_url_exits_2(monkeypatch, "audit")


def test_main_keywords_missing_required_url_raises_systemexit_2(monkeypatch):
    _assert_missing_url_exits_2(monkeypatch, "keywords")


def test_main_sitemap_missing_required_url_raises_systemexit_2(monkeypatch):
    _assert_missing_url_exits_2(monkeypatch, "sitemap")


def test_main_robots_missing_required_url_raises_systemexit_2(monkeypatch):
    _assert_missing_url_exits_2(monkeypatch, "robots")


def test_main_schema_missing_required_url_raises_systemexit_2(monkeypatch):
    _assert_missing_url_exits_2(monkeypatch, "schema")


def test_main_optimize_missing_required_url_raises_systemexit_2(monkeypatch):
    _assert_missing_url_exits_2(monkeypatch, "optimize")


def test_main_keyboard_interrupt_exits_130(monkeypatch, capsys):
    def raise_ki(args):
        raise KeyboardInterrupt()

    monkeypatch.setattr(tool, "audit_site", raise_ki)
    monkeypatch.setattr(sys, "argv", ["tool.py", "audit", "--url", "https://example.com"])
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code == 130
    out = capsys.readouterr().out
    assert "Interrupted by user" in out


def test_main_unrecognized_command_falls_through_to_help_and_exit_1(monkeypatch, capsys):
    # argparse's own subparser validation can never actually produce an
    # unrecognized args.command (it would raise SystemExit(2) itself first),
    # so the final `else: parser.print_help(); sys.exit(1)` inside main()'s
    # dispatch is unreachable through the real CLI. We exercise it directly
    # by making parse_args() return a Namespace argparse itself could never
    # produce, to verify main()'s own fallback behavior in isolation.
    import argparse as _argparse
    monkeypatch.setattr(
        _argparse.ArgumentParser, "parse_args",
        lambda self, *a, **k: _argparse.Namespace(command="bogus-command"),
    )
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "usage" in out.lower()


def test_main_unexpected_exception_exits_1_and_prints_traceback(monkeypatch, capsys):
    def raise_err(args):
        raise ValueError("kaboom")

    monkeypatch.setattr(tool, "generate_robots_txt", raise_err)
    monkeypatch.setattr(sys, "argv", ["tool.py", "robots", "--url", "https://example.com"])
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "Unexpected error: kaboom" in captured.out
    assert "Traceback" in captured.err


# ---------------------------------------------------------------------------
# Real subprocess smoke test (no network call involved: 'robots' command)
# ---------------------------------------------------------------------------

def test_subprocess_runs_as_script_and_exercises_main_guard(tmp_path):
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    out_file = tmp_path / "robots.txt"
    result = subprocess.run(
        [sys.executable, str(script), "robots", "--url", "https://example.com", "--output", str(out_file)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert out_file.exists()
    assert "Sitemap: https://example.com/sitemap.xml" in out_file.read_text()
