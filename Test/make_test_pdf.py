# -*- coding: utf-8 -*-
"""生成用于知识库上传测试的最小合法 PDF（含独特英文关键词，便于检索验证）。

用法: .venv\\Scripts\\python.exe Test\\make_test_pdf.py [输出路径]
默认输出 Test\\zenith_test_manual.pdf
内容特征: Project Zenith 逃生舱位置 + 访问码 7391 + 版本号，上传后应在智能问答中可检索。
"""

import sys
from pathlib import Path


def build_pdf(lines: list[str]) -> bytes:
    """手工构建单页 PDF（Helvetica，仅 ASCII 文本），动态计算 xref 偏移。"""
    # 内容流：每行文字向下移动 18pt
    ops = ["BT", "/F1 12 Tf", "72 720 Td", "18 TL"]
    for line in lines:
        escaped = line.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        ops.append(f"({escaped}) Tj T*")
    ops.append("ET")
    content = ("\n".join(ops)).encode("ascii")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_pos = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n"
    ).encode()
    return bytes(out)


def main() -> None:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "Test/zenith_test_manual.pdf")
    lines = [
        "Project Zenith Operations Manual (Test Document)",
        "Emergency Escape Pod Location: Deck B, Level 3, Section 7.",
        "The escape pod access code is 7391.",
        "Zenith reactor coolant must be replaced every 90 days.",
        "This document is only used for knowledge base upload testing.",
        "Unique marker: ZENITH-2026-KBTEST.",
    ]
    pdf = build_pdf(lines)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(pdf)
    print(f"written: {target} ({len(pdf)} bytes)")


if __name__ == "__main__":
    main()
