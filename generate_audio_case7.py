#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
永夜酒店谋杀案 - 语音生成脚本
"""

import os
import tempfile
import shutil
from generate_audio import process_case


def main():
    output_dir = 'unheared'
    os.makedirs(output_dir, exist_ok=True)

    temp_dir = tempfile.mkdtemp(prefix='audio_gen_')
    print(f"临时目录: {temp_dir}")

    try:
        case_path = 'unheared/cases/case7.json'
        if not os.path.exists(case_path):
            print(f"错误: {case_path} 不存在")
            return

        files = process_case(case_path, output_dir, temp_dir)

        print(f"\n=== 完成！共生成 {len(files)} 个音频文件 ===")
        for f in files:
            size_mb = os.path.getsize(f) / (1024 * 1024)
            print(f"  - {f} ({size_mb:.1f}MB)")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"已清理临时目录")


if __name__ == '__main__':
    main()
