import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    # 数据库配置 - 使用 Windows 身份验证
    SQL_SERVER = 'localhost\\SQLEXPRESS'  # 注意是双反斜杠
    SQL_DATABASE = 'ContractManagement'
    SQL_DRIVER = 'ODBC Driver 17 for SQL Server'
    
    # 使用 Windows 身份验证的连接字符串
    SQLALCHEMY_DATABASE_URI = f'mssql+pyodbc://@{SQL_SERVER}/{SQL_DATABASE}?driver={SQL_DRIVER}&trusted_connection=yes'
    SQLALCHEMY_TRACK_MODIFICATIONS = False