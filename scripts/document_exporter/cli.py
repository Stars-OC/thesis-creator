import argparse

from .exporter import export_document


def print_export_report(results: dict):
    """打印导出报告"""
    print("\n" + "=" * 50)
    print("[文档导出报告]")
    print("=" * 50)
    print(f"输入文件: {results['input']}")
    print(f"输出目录: {results['output_dir']}")
    print(f"导出时间: {results['timestamp']}")
    print("-" * 50)

    for fmt, info in results['formats'].items():
        status = "[成功]" if info['success'] else "[失败]"
        print(f"{fmt.upper()}: {status}")
        print(f"  路径: {info['path']}")
        if not info['success']:
            print(f"  原因: {info['message']}")
        print()

    print("=" * 50)


def main(argv=None):
    parser = argparse.ArgumentParser(description='论文文档导出工具')
    parser.add_argument('--input', '-i', required=True, help='输入 Markdown 文件路径')
    parser.add_argument('--output', '-o', default='workspace/final/', help='输出目录')
    parser.add_argument('--format', '-f', choices=['docx', 'pdf', 'both'], default='both', help='输出格式')

    args = parser.parse_args(argv)

    results = export_document(args.input, args.output, args.format)
    print_export_report(results)
    return results
