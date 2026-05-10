from datetime import datetime
from pathlib import Path

from .docx_writer import convert_md_to_docx
from .pdf_converter import convert_docx_to_pdf
from .preflight import preflight_validate_images


def export_document(input_path: str, output_dir: str, format_type: str = 'both') -> dict:
    """
    导出文档

    Args:
        input_path: 输入的 Markdown 文件路径
        output_dir: 输出目录
        format_type: 'docx', 'pdf', 或 'both'

    Returns:
        结果字典
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 生成文件名
    base_name = input_path.stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    preflight_ok, preflight_message = preflight_validate_images(input_path)

    results = {
        'input': str(input_path),
        'output_dir': str(output_dir),
        'timestamp': timestamp,
        'formats': {}
    }

    if not preflight_ok:
        results['formats']['preflight'] = {
            'path': str(input_path),
            'success': False,
            'message': preflight_message
        }
        return results

    # 转换为 Word
    if format_type in ['docx', 'both']:
        docx_path = output_dir / f"{base_name}.docx"
        success, message = convert_md_to_docx(str(input_path), str(docx_path))
        results['formats']['docx'] = {
            'path': str(docx_path),
            'success': success,
            'message': message
        }

    # 转换为 PDF
    if format_type in ['pdf', 'both']:
        # 先确保有 Word 文件
        docx_path = output_dir / f"{base_name}.docx"
        if not docx_path.exists():
            convert_md_to_docx(str(input_path), str(docx_path))

        pdf_path = output_dir / f"{base_name}.pdf"
        success, message = convert_docx_to_pdf(str(docx_path), str(pdf_path))
        results['formats']['pdf'] = {
            'path': str(pdf_path),
            'success': success,
            'message': message
        }

    return results
