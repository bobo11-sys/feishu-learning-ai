import sys
import os

print("=== api/index.py 被加载 ===", file=sys.stderr)
print(f"当前目录: {os.getcwd()}", file=sys.stderr)
print(f"Python路径: {sys.path}", file=sys.stderr)

try:
    from app import app
    print("=== Flask应用导入成功 ===", file=sys.stderr)
    print(f"App对象类型: {type(app)}", file=sys.stderr)
except Exception as e:
    print(f"=== 导入app失败: {e} ===", file=sys.stderr)
    raise

# Vercel需要这个application变量
application = app
print("=== application变量已设置 ===", file=sys.stderr)
