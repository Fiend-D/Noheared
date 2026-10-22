#!/bin/bash
# 将case6的MP3音频文件转换为WAV格式

AUDIO_DIR="/home/zhaohaipeng/WorkSpacee/qt/unheared/unheared/audio/case6"

for file in "$AUDIO_DIR"/*.wav; do
    if [ -f "$file" ]; then
        # 检查文件是否是MP3格式
        if file "$file" | grep -q "MPEG"; then
            echo "转换: $file"
            # 创建临时文件
            temp_file="${file%.wav}.mp3"
            # 重命名为.mp3
            mv "$file" "$temp_file"
            # 转换为WAV
            ffmpeg -i "$temp_file" -acodec pcm_s16le -ar 44100 -ac 2 "${file}" -y > /dev/null 2>&1
            # 删除临时MP3文件
            rm "$temp_file"
            echo "完成: $file"
        fi
    fi
done

echo "所有文件转换完成！"