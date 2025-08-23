from app import db
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# 合同-供应商关联表（多对多）：修复外键引用的表名
contract_supplier = db.Table('contract_supplier',
    db.Column('contract_id', db.Integer, db.ForeignKey('Contracts.ContractID'), primary_key=True),  # 对应Contract表的实际表名Contracts
    db.Column('supplier_id', db.Integer, db.ForeignKey('Suppliers.SupplierID'), primary_key=True)  # 对应Supplier表的实际表名Suppliers
)

class Supplier(db.Model):
    __tablename__ = 'Suppliers'  # 表名是Suppliers（复数）
    SupplierID = db.Column(db.Integer, primary_key=True)
    SupplierName = db.Column(db.String(255), nullable=False)
    ContactInfo = db.Column(db.String(500))
    CreatedDate = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Supplier {self.SupplierName}>'

class Client(db.Model):
    __tablename__ = 'Clients'  # 表名是Clients（复数）
    ClientID = db.Column(db.Integer, primary_key=True)
    ClientName = db.Column(db.String(255), nullable=False)
    ContactInfo = db.Column(db.String(500))
    CreatedDate = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Client {self.ClientName}>'

class Contract(db.Model):
    __tablename__ = 'Contracts'  # 表名是Contracts（复数），只保留一个Contract模型
    ContractID = db.Column(db.Integer, primary_key=True)
    ProjectName = db.Column(db.String(255), nullable=False)
    ContractNumber = db.Column(db.String(100), unique=True, nullable=False)
    TotalAmount = db.Column(db.Numeric(18,2), nullable=False)
    ClientID = db.Column(db.Integer, db.ForeignKey('Clients.ClientID'))  # 关联Clients表
    SignDate = db.Column(db.Date)
    CompletionRate = db.Column(db.Numeric(5,2), default=0.00)  # 新增完工率字段，百分比格式
    CreatedDate = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 多对多关系：一个合同对应多个供应商
    suppliers = db.relationship('Supplier', secondary=contract_supplier, lazy='subquery',
        backref=db.backref('contracts', lazy=True))
    # 与客户的一对多关系
    client = db.relationship('Client', backref='contracts')
    # 与其他表的关系
    payments = db.relationship('Payment', backref='contract', lazy=True, cascade="all, delete-orphan")
    invoices = db.relationship('Invoice', backref='contract', lazy=True, cascade="all, delete-orphan")
    costs = db.relationship('Cost', backref='contract', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Contract {self.ContractNumber}>'
    
    def get_total_payments(self):
        return sum([payment.Amount for payment in self.payments]) or 0
    
    def get_total_costs(self):
        return sum([cost.Amount for cost in self.costs]) or 0
    
    def is_over_budget(self):
        return self.get_total_costs() > self.TotalAmount

class Payment(db.Model):
    __tablename__ = 'Payments'
    PaymentID = db.Column(db.Integer, primary_key=True)
    ContractID = db.Column(db.Integer, db.ForeignKey('Contracts.ContractID'))  # 关联Contracts表
    PaymentDate = db.Column(db.Date, nullable=False)
    Amount = db.Column(db.Numeric(18,2), nullable=False)
    PaymentType = db.Column(db.String(50))
    CreatedDate = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Payment {self.PaymentID} for Contract {self.ContractID}>'

class Invoice(db.Model):
    __tablename__ = 'Invoices'
    InvoiceID = db.Column(db.Integer, primary_key=True)
    ContractID = db.Column(db.Integer, db.ForeignKey('Contracts.ContractID'))  # 关联Contracts表
    InvoiceDate = db.Column(db.Date, nullable=False)
    Amount = db.Column(db.Numeric(18,2), nullable=False)
    InvoiceType = db.Column(db.String(50))
    CreatedDate = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Invoice {self.InvoiceID} for Contract {self.ContractID}>'

class Cost(db.Model):
    __tablename__ = 'Costs'
    CostID = db.Column(db.Integer, primary_key=True)
    ContractID = db.Column(db.Integer, db.ForeignKey('Contracts.ContractID'))  # 关联Contracts表
    CostType = db.Column(db.String(100), nullable=False)
    Amount = db.Column(db.Numeric(18,2), nullable=False)
    CostDate = db.Column(db.Date)
    Description = db.Column(db.String(500))
    CreatedDate = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Cost {self.CostID} for Contract {self.ContractID}>'
    
# 添加FixedCost模型
class FixedCost(db.Model):
    __tablename__ = 'FixedCosts'
    FixedCostID = db.Column(db.Integer, primary_key=True)
    CostType = db.Column(db.String(100), nullable=False)  # 成本类型，如"工资薪金"
    Amount = db.Column(db.Numeric(18,2), nullable=False)
    CostDate = db.Column(db.Date)
    Description = db.Column(db.String(500))
    Month = db.Column(db.String(7), nullable=False)  # 月份，格式: YYYY-MM
    CreatedDate = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<FixedCost {self.CostType} {self.Month}>'