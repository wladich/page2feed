# coding: utf-8
import cssselect
import difflib
import html2text
import requests
import requests.exceptions
from copy import deepcopy
from lxml import html, etree
from lxml.html.clean import Cleaner
import web
from bs4 import UnicodeDammit


class HtmlException(Exception):
    pass


def retrieve_url(url):
    try:
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.108 Safari/537.36'})
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}
    encoding = response.encoding
    if encoding == 'ISO-8859-1':
        encoding = None
    return {'url': response.url, 'content': response.content, 'encoding': encoding}


def extract_by_selectors(doc, selectors):
    selected_nodes = []
    for selector in selectors:
        try:
            elements = doc.cssselect(selector)
        except cssselect.parser.SelectorSyntaxError:
            raise HtmlException('Invalid selector "%s"' % selector)
        if not elements:
            raise HtmlException('Selector "%s" not matched' % selector)
        selected_nodes.extend(elements)
    seen_nodes = {}
    for element in selected_nodes:
        if element in seen_nodes:
            continue
        new_element = deepcopy(element)
        seen_nodes[element] = new_element
        while True:
            parent = element.getparent()
            if parent is None:
                break
            if parent in seen_nodes:
                seen_nodes[parent].append(new_element)
                break
            else:
                attrs = dict((k, v) for k, v in parent.items() if k.isalpha())
                new_parent = html.Element(parent.tag, **attrs)
                new_parent.append(new_element)
                seen_nodes[parent] = new_parent
            element = parent
            new_element = new_parent
    return seen_nodes.values()[0].getroottree().getroot()


def filter_doc(doc):
    cleaner = Cleaner(scripts=True, javascript=True, comments=True, style=True, links=True,
                      meta=True, page_structure=False, processing_instructions=True, embedded=True, frames=True,
                      forms=False, annoying_tags=False, remove_tags=None, kill_tags=None, remove_unknown_tags=False,
                      safe_attrs_only=True)
    return cleaner.clean_html(doc)


def simplify_html(s, url):
    txt = html2text.html2text(s, url, 1e100)
    return txt


def prepare_html(s, url, selectors, encoding):
    doc = None
    if encoding:
        decoded = s.decode(encoding, errors='relace')
    else:
        decoded = UnicodeDammit(s).unicode_markup
    try:
        doc = html.fromstring(decoded)
    except (etree.ParserError, ValueError):
        pass
    if doc and doc.tag == 'html':
        title = doc.find('.//title')
        if title is not None:
            title = title.text.strip()
        doc = filter_doc(doc)
        if selectors:
            try:
                doc = extract_by_selectors(doc, selectors)
            except HtmlException as e:
                return {'error': str(e)}
        doc.make_links_absolute(url)
        txt = simplify_html(serialize_doc(doc), url)
    else:
        txt = decoded
        title = None
        if selectors:
            return {'error': 'Can not apply selectors to non-html document'}
    return {'txt': txt, 'title': title}


def get_prepared_html(url, selectors):
    res1 = retrieve_url(url)
    if 'error' in res1:
        return res1
    res2 = prepare_html(res1['content'], url, selectors, res1['encoding'])
    if 'error' in res2:
        return res2
    res2['url'] = res1['url']
    return res2


def serialize_doc(doc):
    return html.tostring(doc)


class InsensitiveSequenceMatcher(difflib.SequenceMatcher):
    """
    Acts like SequenceMatcher, but tries not to find very small equal
    blocks amidst large spans of changes
    """

    threshold = 2

    def get_matching_blocks(self):
        size = min(len(self.b), len(self.b))
        threshold = min(self.threshold, size / 4)
        actual = difflib.SequenceMatcher.get_matching_blocks(self)
        return [item for item in actual
                if item[2] > threshold
                or not item[2]]


def tokenize_line(s):
    delimiters = ' ', '<', '>', '\n'
    tokens = []
    last_pos = 0
    for i, c in enumerate(s[1:], 1):
        if c in delimiters:
            tokens.append(s[last_pos:i])
            last_pos = i
    tokens.append(s[last_pos:])
    return tokens


def diff_inline(text1, text2):
    words1 = tokenize_line(text1)
    words2 = tokenize_line(text2)
    diff = []
    s = InsensitiveSequenceMatcher(a=words1, b=words2)
    commands = s.get_opcodes()
    for command, i1, i2, j1, j2 in commands:
        if command == 'equal':
            diff.extend(words1[i1:i2])
        elif command == 'insert':
            diff.append(DiffTag('<ins>'))
            diff.extend(words2[j1:j2])
            diff.append(DiffTag('</ins>'))
        elif command == 'delete':
            diff.append(DiffTag('<del>'))
            diff.extend(words1[i1:i2])
            diff.append(DiffTag('</del>'))
        elif command == 'replace':
            diff.append(DiffTag('<del>'))
            diff.extend(words1[i1:i2])
            diff.append(DiffTag('</del>'))
            diff.append(DiffTag('<ins>'))
            diff.extend(words2[j1:j2])
            diff.append(DiffTag('</ins>'))
    return diff


class DiffTag(str):
    pass


def get_web_safe_diff(text1, text2):
    lines1 = text1.splitlines(True)
    lines2 = text2.splitlines(True)
    diff = []
    s = InsensitiveSequenceMatcher(a=lines1, b=lines2)
    commands = s.get_opcodes()
    for command, i1, i2, j1, j2 in commands:
        if command == 'replace':
            inline_diff = diff_inline(''.join(lines1[i1:i2]), ''.join(lines2[j1:j2]))
            diff.extend(inline_diff)
        elif command == 'insert':
            diff.append(DiffTag('<ins>'))
            diff.extend(lines2[j1:j2])
            diff.append(DiffTag('</ins>'))
        elif command == 'delete':
            diff.append(DiffTag('<del>'))
            diff.extend(lines1[i1:i2])
            diff.append(DiffTag('</del>'))
    escaped_diff = []
    for s in diff:
        if isinstance(s, DiffTag):
            pass
        else:
            s = web.htmlquote(s)
        escaped_diff.append(s)
    return ''.join(escaped_diff).replace('\n', '<br>\n')


def style_diff(s):
    return '''
    <html>
        <head>
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
            <style>
                ins {background-color: #dfd}
                del {background-color: #fdd}
            </style>
        </head>
        <body>%s</body>
    </html>''' % s


if __name__ == '__main__':
    pass