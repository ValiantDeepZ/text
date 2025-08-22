# -*- coding: utf-8 -*-
from flask import Flask, g
from flask_sqlalchemy import SQLAlchemy
from config import Config
import os
import sys
import codecs

# 强制使用 UTF-8 编码
if sys.stdout.encoding != 'UTF-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
if sys.stderr.encoding != 'UTF-8':
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

db = SQLAlchemy()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 强制模板使用 UTF-8 编码
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['JSON_AS_ASCII'] = False  # 确保 JSON 响应使用 UTF-8
    
    # 添加自定义过滤器
    @app.template_filter('number_format')
    def number_format_filter(value, decimals=2):
        try:
            value = float(value)
            return f"{value:,.{decimals}f}"
        except (ValueError, TypeError):
            return value
    
    # 替换 before_first_request 为 before_request 并添加条件判断
    @app.before_request
    def check_templates_encoding():
        """检查模板文件编码，只在第一个请求时执行"""
        if not hasattr(g, 'encoding_checked'):
            template_dir = os.path.join(os.path.dirname(__file__), 'templates')
            if os.path.exists(template_dir):
                print("检查模板文件编码...")
                for file_name in os.listdir(template_dir):
                    if file_name.endswith('.html'):
                        file_path = os.path.join(template_dir, file_name)
                        try:
                            # 尝试以UTF-8编码读取文件
                            with open(file_path, 'r', encoding='utf-8') as f:
                                f.read()
                            print(f"✓ {file_name}: UTF-8 编码正常")
                        except UnicodeDecodeError as e:
                            print(f"✗ {file_name}: 编码错误 - {e}")
                            print("请运行 fix_encoding.py 修复编码问题")
            g.encoding_checked = True  # 标记为已检查
    
    db.init_app(app)
    
    # 测试数据库连接
    with app.app_context():
        try:
            # 尝试执行一个简单的查询来测试连接
            from sqlalchemy import text
            result = db.session.execute(text('SELECT 1'))
            print("数据库连接测试成功")
        except Exception as e:
            print(f"数据库连接测试失败: {str(e)}")
    
    # 导入并注册路由
    from app.routes import init_routes
    init_routes(app)
    
    # 创建数据库表
    with app.app_context():
        db.create_all()
        print("数据库表已创建或确认存在")
    
    return app
    