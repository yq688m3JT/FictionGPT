import sqlite3
from pathlib import Path

def repair():
    data_dir = Path("data")
    for db_path in data_dir.glob("**/story.db"):
        print(f"正在抢救数据库: {db_path}")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 1. 删除所有坏掉的英文记录
            cursor.execute("DELETE FROM chapters WHERE lang = 'en'")
            cursor.execute("DELETE FROM characters WHERE lang = 'en'")
            
            # 2. 修复被误改的中文标题
            # 由于我们不知道原标题是什么，但我们可以根据 chapter_number 
            # 暂时给它一个占位符，或者如果 full_text 还在，我们可以保留它。
            # 这里最关键的是把标题从 "en" 改回 "第X章" 这种形式，
            # 这样用户至少能看到章节号，真正的标题可以通过重新生成摘要来恢复。
            cursor.execute("SELECT chapter_number, title FROM chapters WHERE lang = 'zh'")
            rows = cursor.fetchall()
            for num, title in rows:
                if title == 'en' or title == 'en-US' or not title:
                    new_title = f"第 {num} 章"
                    cursor.execute("UPDATE chapters SET title = ? WHERE chapter_number = ? AND lang = 'zh'", (new_title, num))
            
            conn.commit()
            conn.close()
            print("抢救成功")
        except Exception as e:
            print(f"抢救失败: {e}")

if __name__ == "__main__":
    repair()
