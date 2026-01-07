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

class IntelligentLearningCoach:
    def __init__(self):
        self.access_token = None
        self.token_expiry = None
        self.methods_cache = None
        self.targets_cache = None
        self.history_cache = None
        self.cache_time = None
        
    def get_feishu_token(self, force_refresh=False):
        """获取飞书访问令牌，带缓存机制"""
        if not force_refresh and self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token
            
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json"}
        data = {
            "app_id": FEISHU_APP_ID,
            "app_secret": FEISHU_APP_SECRET
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            self.access_token = result.get("tenant_access_token", "")
            self.token_expiry = datetime.now() + timedelta(minutes=110)
            return self.access_token
        except Exception as e:
            print(f"获取飞书token失败: {e}")
            return None
    
    def fetch_table_data(self, app_token, table_id, record_type=None, recent_days=7, max_records=100):
        """获取表格数据，支持筛选"""
        token = self.get_feishu_token()
        if not token:
            return []
        
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/search"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        data = {"page_size": min(max_records, 100)}
        
        if record_type:
            data["filter"] = {
                "conjunction": "and",
                "conditions": [
                    {
                        "field_name": "记录类型",
                        "operator": "is",
                        "value": [record_type]
                    }
                ]
            }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=15)
            response.raise_for_status()
            result = response.json()
            items = result.get("data", {}).get("items", [])
            
            if record_type == "学习记录":
                items.sort(key=lambda x: x.get("fields", {}).get("日期", ""), reverse=True)
                
                if recent_days > 0:
                    cutoff_date = datetime.now() - timedelta(days=recent_days)
                    filtered_items = []
                    for item in items:
                        date_str = item.get("fields", {}).get("日期", "")
                        if date_str:
                            try:
                                date_str = date_str[:19]
                                record_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                                if record_date >= cutoff_date:
                                    filtered_items.append(item)
                            except:
                                try:
                                    record_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
                                    if record_date >= cutoff_date.date():
                                        filtered_items.append(item)
                                except:
                                    continue
                    items = filtered_items[:max_records]
            
            return items
            
        except Exception as e:
            print(f"获取表格数据失败({record_type}): {e}")
            return []
    
    def get_targets(self, app_token, table_id):
        """获取活跃目标"""
        cache_key = f"targets_{app_token}_{table_id}"
        
        if self.targets_cache and self.cache_time and (datetime.now() - self.cache_time).seconds < 600:
            if cache_key in self.targets_cache:
                return self.targets_cache[cache_key]
        
        items = self.fetch_table_data(app_token, table_id, "目标看板", recent_days=0, max_records=20)
        
        targets = []
        for item in items:
            fields = item.get("fields", {})
            if fields.get("目标名称"):
                target = {
                    "record_id": item.get("record_id", ""),
                    "目标名称": fields.get("目标名称", ""),
                    "当前阶段": fields.get("当前阶段", ""),
                    "季度OKR": fields.get("季度OKR", ""),
                    "本周焦点": fields.get("本周焦点", ""),
                    "进度%": fields.get("进度%", ""),
                    "环境扫描": fields.get("环境扫描", ""),
                    "AI战略建议": fields.get("AI战略建议", ""),
                    "关联商机": fields.get("关联商机", ""),
                    "上次复盘日期": fields.get("上次复盘日期", ""),
                    "下次调整日期": fields.get("下次调整日期", "")
                }
                targets.append(target)
        
        if not self.targets_cache:
            self.targets_cache = {}
        self.targets_cache[cache_key] = targets
        self.cache_time = datetime.now()
        
        return targets
    
    def get_methods(self, app_token, table_id):
        """获取学习方法库"""
        cache_key = f"methods_{app_token}_{table_id}"
        
        if self.methods_cache and self.cache_time and (datetime.now() - self.cache_time).seconds < 600:
            if cache_key in self.methods_cache:
                return self.methods_cache[cache_key]
        
        items = self.fetch_table_data(app_token, table_id, "方法卡片", recent_days=0, max_records=50)
        
        methods = []
        for item in items:
            fields = item.get("fields", {})
            if fields.get("方法ID"):
                method = {
                    "方法ID": fields.get("方法ID", ""),
                    "方法名称": fields.get("方法名称", ""),
                    "适用问题": fields.get("适用问题", ""),
                    "适用模块": fields.get("适用模块", ""),
                    "最佳时机": fields.get("最佳时机", ""),
                    "预期耗时（分钟）": fields.get("预期耗时（分钟）", ""),
                    "具体步骤": fields.get("具体步骤", ""),
                    "成功指标": fields.get("成功指标", ""),
                    "战略连接": fields.get("战略连接", ""),
                    "难度等级": fields.get("难度等级", ""),
                    "关联商机": fields.get("关联商机", "")
                }
                methods.append(method)
        
        if not self.methods_cache:
            self.methods_cache = {}
        self.methods_cache[cache_key] = methods
        self.cache_time = datetime.now()
        
        return methods
    
    def get_recent_learning_records(self, app_token, table_id, days=7, limit=20):
        """获取最近的学习记录"""
        cache_key = f"history_{app_token}_{table_id}_{days}"
        
        if self.history_cache and self.cache_time and (datetime.now() - self.cache_time).seconds < 300:
            if cache_key in self.history_cache:
                return self.history_cache[cache_key]
        
        items = self.fetch_table_data(app_token, table_id, "学习记录", recent_days=days, max_records=limit)
        
        records = []
        for item in items:
            fields = item.get("fields", {})
            record = {
                "record_id": item.get("record_id", ""),
                "日期": fields.get("日期", ""),
                "学习模式": fields.get("学习模式", ""),
                "内容": fields.get("内容", ""),
                "困难/问题": fields.get("困难/问题", ""),
                "AI分析与方案": fields.get("AI分析与方案", ""),
                "关联方法": fields.get("关联方法", ""),
                "能量状态": fields.get("能量状态", ""),
                "专注评分": fields.get("专注评分", ""),
                "执行时长": fields.get("执行时长", ""),
                "诊断标签": fields.get("诊断标签", ""),
                "明日优化点": fields.get("明日优化点", "")
            }
            records.append(record)
        
        if not self.history_cache:
            self.history_cache = {}
        self.history_cache[cache_key] = records
        self.cache_time = datetime.now()
        
        return records
    
    def analyze_learning_session(self, current_record, targets, methods, recent_records):
        """分析单次学习记录"""
        headers = {
            'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        target_context = ""
        if targets:
            target_context = "\n【你的当前目标】\n"
            for i, target in enumerate(targets[:3], 1):
                target_context += f"{i}. {target['目标名称']}"
                if target.get("当前阶段"):
                    target_context += f"（{target['当前阶段']}）"
                if target.get("本周焦点"):
                    target_context += f"\n   本周焦点：{target['本周焦点']}"
                if target.get("进度%"):
                    target_context += f"\n   当前进度：{target['进度%']}%"
                target_context += "\n"
        
        method_context = ""
        if methods:
            method_context = "\n【你的学习方法库】\n"
            for i, method in enumerate(methods[:8], 1):
                method_context += f"{i}. {method['方法名称']} (ID:{method['方法ID']})\n"
                method_context += f"   适用：{method['适用问题']}\n"
                if method.get("预期耗时（分钟）"):
                    method_context += f"   耗时：{method['预期耗时（分钟）']}分钟"
                if method.get("难度等级"):
                    method_context += f"，难度：{method['难度等级']}"
                method_context += "\n"
        
        history_context = ""
        if recent_records:
            history_context = "\n【最近学习历史】\n"
            for i, record in enumerate(recent_records[:3], 1):
                history_context += f"{i}. {record['日期'][:10] if record['日期'] else '无日期'} - {record['学习模式']}\n"
                if record.get("困难/问题"):
                    problem = record['困难/问题']
                    history_context += f"   问题：{problem[:60]}{'...' if len(problem) > 60 else ''}\n"
                if record.get("诊断标签"):
                    history_context += f"   诊断：{record['诊断标签']}\n"
                if record.get("明日优化点"):
                    optimization = record['明日优化点']
                    history_context += f"   优化：{optimization[:60]}{'...' if len(optimization) > 60 else ''}\n"
                history_context += "\n"
        
        current_context = f"""
【今日学习记录】
学习模式：{current_record['学习模式']}
学习内容：{current_record['内容']}
遇到困难：{current_record['困难/问题']}
能量状态：{current_record['能量状态']}
专注评分：{current_record['专注评分']}/10
执行时长：{current_record['执行时长']}分钟
"""
        
        prompt = f"""你是一位专业的成长教练，请结合用户的完整学习生态，提供深度、个性化、可执行的建议。

{target_context}{method_context}{history_context}{current_context}

请基于以下维度进行深度思考：
1. 目标对齐：今日学习如何服务于用户的长期目标？
2. 方法匹配：从方法库中选择最匹配的1-3个方法（必须从提供的方法库中选择）
3. 问题诊断：识别根本问题并提供具体解决方案
4. 良性循环：如果现有方法有效，建议保持并微调；如果无效，推荐新方法

请以JSON格式返回分析结果，必须包含以下字段：
1. problem_diagnosis: "AI分析与方案"（400字内，包含具体行动步骤）
2. diagnostic_labels: "诊断标签"（数组，如["目标偏离", "方法不当", "能量管理不佳"]）
3. tomorrow_optimization: "明日优化点"（200字内，具体可执行，如果方法适用则建议"保持并优化[方法名称]"）
4. related_methods: "关联方法"（数组，方法ID，必须从方法库中选择）
5. confidence_adjustment: "专注评分调整建议"（基于当前状态给出1-10的合理评分）
6. energy_suggestion: "能量状态调整建议"（50字内具体建议）

请确保返回纯JSON格式，不要有其他文字。"""

        try:
            response = requests.post(
                'https://api.deepseek.com/v1/chat/completions',
                headers=headers,
                json={
                    'model': 'deepseek-chat',
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0.7,
                    'max_tokens': 2000
                },
                timeout=45
            )
            response.raise_for_status()
            
            content = response.json()['choices'][0]['message']['content']
            
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
            else:
                result = json.loads(content.strip())
            
            required_fields = ['problem_diagnosis', 'diagnostic_labels', 'tomorrow_optimization', 'related_methods']
            for field in required_fields:
                if field not in result:
                    result[field] = ""
                    if field == 'diagnostic_labels':
                        result[field] = []
                    elif field == 'related_methods':
                        result[field] = []
            
            return result
            
        except Exception as e:
            print(f"DeepSeek API调用失败: {e}")
            return {
                "problem_diagnosis": "AI分析系统暂时不可用。建议：1. 回顾类似问题的成功经验 2. 从方法库中选择一个相关方法尝试 3. 保持当前学习节奏",
                "diagnostic_labels": ["系统维护"],
                "tomorrow_optimization": "等待系统恢复，或手动选择方法库中的一个方法尝试。记录效果，便于后续分析。",
                "related_methods": [],
                "confidence_adjustment": current_record['专注评分'],
                "energy_suggestion": "保持当前能量管理方式，注意劳逸结合"
            }
    
    def update_feishu_record(self, app_token, table_id, record_id, analysis_data, update_fields=None):
        """更新飞书表格记录"""
        token = self.get_feishu_token()
        if not token:
            return {"error": "无法获取飞书token"}
        
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        if not update_fields:
            update_fields = {
                "AI分析与方案": analysis_data.get("problem_diagnosis", ""),
                "关联方法": ", ".join(analysis_data.get("related_methods", [])),
                "诊断标签": ", ".join(analysis_data.get("diagnostic_labels", [])),
                "明日优化点": analysis_data.get("tomorrow_optimization", ""),
                "分析时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        update_fields = {k: v for k, v in update_fields.items() if v}
        
        data = {
            "fields": update_fields
        }
        
        try:
            response = requests.patch(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"更新飞书表格失败: {e}")
            return {"error": str(e)}

coach = IntelligentLearningCoach()

@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "service": "深度成长智能教练系统",
        "version": "1.0",
        "author": "AI Learning Coach",
        "endpoints": {
            "健康检查": "/health",
            "分析学习记录": "POST /analyze",
            "测试端点": "GET /test"
        }
    })

@app.route('/health')
def health():
    token_status = "available" if coach.get_feishu_token() else "unavailable"
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "deepseek_api": "available" if DEEPSEEK_API_KEY else "unconfigured",
            "feishu_api": token_status
        }
    })

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        
        required_fields = ['app_token', 'table_id', 'record_id', '困难/问题']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                "success": False,
                "error": f"缺少必要字段: {', '.join(missing_fields)}",
                "required_fields": required_fields
            }), 400
        
        user_fields = {
            '学习模式': data.get('学习模式', ''),
            '内容': data.get('内容', ''),
            '困难/问题': data['困难/问题'],
            '能量状态': data.get('能量状态', '中'),
            '专注评分': int(data.get('专注评分', 5)) if str(data.get('专注评分', '5')).isdigit() else 5,
            '执行时长': int(data.get('执行时长', 0)) if str(data.get('执行时长', '0')).isdigit() else 0
        }
        
        app_token = data['app_token']
        table_id = data['table_id']
        
        targets = coach.get_targets(app_token, table_id)
        methods = coach.get_methods(app_token, table_id)
        recent_records = coach.get_recent_learning_records(app_token, table_id, days=3, limit=10)
        
        analysis_result = coach.analyze_learning_session(
            current_record=user_fields,
            targets=targets,
            methods=methods,
            recent_records=recent_records
        )
        
        update_result = coach.update_feishu_record(
            app_token,
            table_id,
            data['record_id'],
            analysis_result
        )
        
        response_data = {
            "success": True,
            "message": "学习记录分析完成",
            "timestamp": datetime.now().isoformat(),
            "analysis_summary": {
                "诊断标签": analysis_result.get("diagnostic_labels", []),
                "推荐方法数量": len(analysis_result.get("related_methods", [])),
                "专注评分建议": analysis_result.get("confidence_adjustment", user_fields['专注评分'])
            },
            "update_status": "表格已更新" if "error" not in update_result else "更新失败",
            "next_steps": [
                "查看表格中的'AI分析与方案'和'明日优化点'",
                "按照优化建议调整明天的学习计划",
                "如果方法有效，继续使用并记录效果"
            ]
        }
        
        if "error" in update_result:
            response_data["update_error"] = update_result["error"]
        
        return jsonify(response_data)
        
    except json.JSONDecodeError:
        return jsonify({
            "success": False,
            "error": "请求数据格式错误，必须是有效的JSON"
        }), 400
    except Exception as e:
        error_msg = f"处理请求失败: {str(e)}"
        print(error_msg)
        return jsonify({
            "success": False,
            "error": error_msg,
            "timestamp": datetime.now().isoformat(),
            "suggestion": "请检查网络连接和API密钥，或稍后重试"
        }), 500

@app.route('/test', methods=['GET'])
def test_endpoint():
    return jsonify({
        "status": "test_endpoint_ready",
        "method": "GET",
        "timestamp": datetime.now().isoformat(),
        "instructions": "发送POST请求到/analyze测试分析功能"
    })

if __name__ == '__main__':
    missing_envs = []
    if not DEEPSEEK_API_KEY:
        missing_envs.append("DEEPSEEK_API_KEY")
    if not FEISHU_APP_ID:
        missing_envs.append("FEISHU_APP_ID")
    if not FEISHU_APP_SECRET:
        missing_envs.append("FEISHU_APP_SECRET")
    
    if missing_envs:
        print(f"警告：缺少环境变量: {', '.join(missing_envs)}")
        print("请在Vercel环境变量中配置这些变量")
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
