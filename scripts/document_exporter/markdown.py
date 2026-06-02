import re


def clean_markdown_content(content: str) -> str:
    content = re.sub(r'<!--\s*图表占位符[^\n]*-->\s*\n', '', content)
    content = re.sub(r'>\s*(?:\[统计\]\s*|📊\s*)?\*\*\[图表占位符\]\*\*[^\n]*\n(?:> [^\n]*\n)*', '', content)
    content = re.sub(r'> - \*\*图表编号\*\*[^\n]*\n', '', content)
    content = re.sub(r'> - \*\*图表名称\*\*[^\n]*\n', '', content)
    content = re.sub(r'> - \*\*图表类型\*\*[^\n]*\n', '', content)
    content = re.sub(r'\[(image_(?:\d+_)?\d+)\]', '', content)
    content = re.sub(r'\n-{3,}\n', '\n\n', content)
    content = re.sub(r'\n-{3,}\s*\n', '\n\n', content)
    content = re.sub(r'^-{3,}\s*\n', '', content)
    content = re.sub(r'\n\s*-{3,}$', '', content)
    content = re.sub(r'\n\*{3,}\n', '\n\n', content)
    content = re.sub(r'\n{4,}', '\n\n\n', content)
    content = re.sub(r'[ \t]+\n', '\n', content)
    return content


def strip_doi_links(content: str) -> str:
    content = re.sub(r'\s*\[DOI\]\(https?://doi\.org/[^\)]+\)', '', content)
    content = re.sub(r'\s*DOI:\s*10\.\S+', '', content)
    return content


def parse_markdown(content: str) -> list:
    lines = content.split('\n')
    elements = []

    in_code_block = False
    code_buffer = []
    code_lang = ''
    in_table = False
    table_rows = []

    for line in lines:
        if line.startswith('```'):
            if in_code_block:
                elements.append(('code', code_buffer, code_lang))
                code_buffer = []
                code_lang = ''
                in_code_block = False
            else:
                in_code_block = True
                code_lang = line[3:].strip()
            continue

        if in_code_block:
            code_buffer.append(line)
            continue

        if line.startswith('|'):
            if not in_table:
                in_table = True
                table_rows = []
            if not re.match(r'^\|[\s\-:]+\|', line):
                cells = [c.strip() for c in line.split('|')[1:-1]]
                if cells:
                    table_rows.append(cells)
            continue
        else:
            if in_table and table_rows:
                elements.append(('table', table_rows))
                table_rows = []
                in_table = False

        if line.strip() == '\\newpage' or line.strip() == '\\pagebreak' or line.strip() == '<!-- PAGE_BREAK -->':
            elements.append(('pagebreak',))
            continue

        block_img_match = re.match(r'^>\s*\*\*!\[([^\]]*)\]\(([^)]+)\)[：:]\s*(.+?)\*\*\s*$', line)
        if block_img_match:
            alt_text = block_img_match.group(1).strip() or block_img_match.group(3).strip()
            img_path = block_img_match.group(2).strip()
            elements.append(('image', img_path, alt_text))
            continue

        img_match = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)\s*$', line)
        if img_match:
            alt_text = img_match.group(1)
            img_path = img_match.group(2)
            elements.append(('image', img_path, alt_text))
            continue

        if line.startswith('#### '):
            elements.append(('h4', line[5:].strip()))
        elif line.startswith('### ') and not line.startswith('#### '):
            elements.append(('h3', line[4:].strip()))
        elif line.startswith('## ') and not line.startswith('### '):
            elements.append(('h2', line[3:].strip()))
        elif line.startswith('# ') and not line.startswith('## '):
            elements.append(('h1', line[2:].strip()))
        elif line.startswith('- ') or line.startswith('* '):
            elements.append(('list', line[2:].strip(), False))
        elif re.match(r'^\d+\.\s', line):
            text = re.sub(r'^\d+\.\s', '', line).strip()
            elements.append(('list', text, True))
        elif not line.strip():
            pass
        else:
            elements.append(('para', line))

    if in_table and table_rows:
        elements.append(('table', table_rows))

    return elements
