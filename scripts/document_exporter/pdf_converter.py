from pathlib import Path
import sys

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

import subprocess
import sys
from pathlib import Path
from typing import Tuple

from core.terminal_encoding import subprocess_text_kwargs


def convert_docx_to_pdf(docx_path: str, pdf_path: str) -> Tuple[bool, str]:
    """
    将 Word 文档转换为 PDF

    支持多种转换方式：
    1. Microsoft Word COM（仅 Windows，需要安装 Word）
    2. LibreOffice（跨平台）
    3. docx2pdf（Python 库）
    """
    # 方法 1: 使用 docx2pdf 库（推荐）
    try:
        from docx2pdf import convert
        convert(docx_path, pdf_path)
        print(f"[成功] PDF 文档已保存: {pdf_path}")
        return True, f"PDF 文档已保存到 {pdf_path}"
    except ImportError:
        pass
    except Exception as e:
        print(f"[警告] docx2pdf 转换失败: {e}")

    # 方法 2: 使用 LibreOffice
    try:
        result = subprocess.run(
            ['soffice', '--headless', '--convert-to', 'pdf', '--outdir',
             str(Path(pdf_path).parent), docx_path],
            capture_output=True,
            timeout=60,
            **subprocess_text_kwargs()
        )
        if result.returncode == 0:
            print(f"[成功] PDF 文档已保存: {pdf_path}")
            return True, f"PDF 文档已保存到 {pdf_path}"
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[警告] LibreOffice 转换失败: {e}")

    # 方法 3: 使用 Microsoft Word COM（仅 Windows）
    if sys.platform == 'win32':
        try:
            import win32com.client
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            doc = word.Documents.Open(str(Path(docx_path).absolute()))
            doc.SaveAs(str(Path(pdf_path).absolute()), FileFormat=17)  # 17 = PDF
            doc.Close()
            word.Quit()
            print(f"[成功] PDF 文档已保存: {pdf_path}")
            return True, f"PDF 文档已保存到 {pdf_path}"
        except ImportError:
            pass
        except Exception as e:
            print(f"[警告] Word COM 转换失败: {e}")

    return False, "PDF 转换需要安装以下工具之一：\n  - docx2pdf: pip install docx2pdf\n  - LibreOffice\n  - Microsoft Word（仅 Windows）"
