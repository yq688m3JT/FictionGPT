import sqlite3
from pathlib import Path

def cleanup():
    data_dir = Path("data")
    for db_path in data_dir.glob("**/story.db"):
        print(f"清理数据库: {db_path}")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            # 删除所有非中文的章节和角色记录
            cursor.execute("DELETE FROM chapters WHERE lang != 'zh'")
            cursor.execute("DELETE FROM characters WHERE lang != 'zh'")
            # 同时清空那些被错误同步的正文为空的中文记录（如果有的话）
            cursor.execute("UPDATE chapters SET full_text='' WHERE lang != 'zh'")
            conn.commit()
            conn.close()
            print("清理成功")
        except Exception as e:
            print(f"清理失败: {e}")

if __name__ == "__main__":
    cleanup()
