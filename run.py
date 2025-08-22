# -*- coding: utf-8 -*-
from app import create_app

app = create_app()

if __name__ == '__main__':
    # 打印所有已注册的路由（用于调试）
    with app.app_context():
        print("OK!:")
        for rule in app.url_map.iter_rules():
            print(f"{rule.endpoint}: {rule.rule}")
    
    app.run(debug=True)