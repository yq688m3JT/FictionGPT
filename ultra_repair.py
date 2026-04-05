import sqlite3
import os
from pathlib import Path

def ultra_repair():
    data_dir = Path("data")
    for db_path in data_dir.glob("**/story.db"):
        print(f"终极抢救中: {db_path}")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 1. 彻底删除所有非中文记录，不留活口
            cursor.execute("DELETE FROM chapters WHERE lang != 'zh'")
            cursor.execute("DELETE FROM characters WHERE lang != 'zh'")
            
            # 2. 扫描中文记录，如果标题是空的或者叫'en'，立刻修复
            cursor.execute("SELECT chapter_number, title FROM chapters WHERE lang = 'zh'")
            rows = cursor.fetchall()
            for num, title in rows:
                # 只要标题不对劲，就重置为 "第 X 章"
                if not title or title.strip().lower() in ['en', 'en-us', 'translation pending...', 'pending']:
                    new_title = f"第 {num} 章"
                    cursor.execute("UPDATE chapters SET title = ? WHERE chapter_number = ? AND lang = 'zh'", (new_title, num))
            
            conn.commit()
            conn.close()
            print("抢救完成。")
        except Exception as e:
            print(f"报错了: {e}")

if __name__ == "__main__":
    ultra_repair()
