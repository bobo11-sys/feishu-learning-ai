from flask import Flask, request, jsonify
import requests
import json
import os
from datetime import datetime, timedelta
import re
from typing import Dict, List, Optional

app = Flask(__name__)

# 从环境变量获取配置
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET")

@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "service": "深度成长智能教练系统",
        "version": "1.0"
    })

if __name__ == '__main__':
    app.run(debug=True)
