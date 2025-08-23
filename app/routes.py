# -*- coding: utf-8 -*-
from flask import render_template, request, jsonify, redirect, url_for
from app import db
from app.models import Supplier, Client, Contract, Payment, Invoice, Cost, FixedCost  # 添加 FixedCost 导入
import os
from sqlalchemy.orm import joinedload
from datetime import datetime


def init_routes(app):
    # 主页面路由
    @app.route('/')
    def index():
        contracts = Contract.query.options(
            joinedload(Contract.suppliers),
            joinedload(Contract.client)
        ).all()

        contract_data = []
        
        for contract in contracts:
            total_payments = sum([p.Amount for p in contract.payments]) if contract.payments else 0
            total_invoices = sum([i.Amount for i in contract.invoices]) if contract.invoices else 0
            total_costs = sum([c.Amount for c in contract.costs]) if contract.costs else 0
            
            # 处理 CompletionRate 可能为 None 的情况
            completion_rate = float(contract.CompletionRate) if contract.CompletionRate is not None else 0.0
            
            contract_data.append({
                'ContractID': contract.ContractID,
                'ProjectName': contract.ProjectName,
                'ContractNumber': contract.ContractNumber,
                'TotalAmount': float(contract.TotalAmount),
                'Supplier': ', '.join([s.SupplierName for s in contract.suppliers]) if contract.suppliers else '',
                'Client': contract.client.ClientName if contract.client else '',
                'TotalPayments': float(total_payments),
                'TotalInvoices': float(total_invoices),
                'TotalCosts': float(total_costs),
                'IsOverBudget': total_costs > contract.TotalAmount,
                'SignDate': contract.SignDate.isoformat() if contract.SignDate else None,
                'CompletionRate': completion_rate  # 添加完工率
            })
        
        return render_template('index.html', contracts=contract_data)
    
    # 搜索供应商接口
    @app.route('/api/suppliers/search/<string:term>')
    @app.route('/api/suppliers/search/')
    def search_suppliers(term=''):
        if not term:
            suppliers = Supplier.query.all()
        else:
            suppliers = Supplier.query.filter(Supplier.SupplierName.ilike(f'%{term}%')).all()
        return jsonify([{'id': s.SupplierID, 'text': s.SupplierName} for s in suppliers])

    # 搜索客户接口
    @app.route('/api/clients/search/<string:term>')
    @app.route('/api/clients/search/')
    def search_clients(term=''):
        if not term:
            clients = Client.query.all()
        else:
            clients = Client.query.filter(Client.ClientName.ilike(f'%{term}%')).all()
        return jsonify([{'id': c.ClientID, 'text': c.ClientName} for c in clients])
    
    # 合同管理接口（查询/创建）
    @app.route('/api/contracts', methods=['GET', 'POST'])
    def contracts():
        if request.method == 'GET':
            contracts = Contract.query.all()
            result = []
            
            for contract in contracts:
                total_payments = sum([p.Amount for p in contract.payments]) if contract.payments else 0
                total_invoices = sum([i.Amount for i in contract.invoices]) if contract.invoices else 0
                total_costs = sum([c.Amount for c in contract.costs]) if contract.costs else 0
                
                # 处理 CompletionRate 可能为 None 的情况
                completion_rate = float(contract.CompletionRate) if contract.CompletionRate is not None else 0.0
                
                result.append({
                    'ContractID': contract.ContractID,
                    'ProjectName': contract.ProjectName,
                    'ContractNumber': contract.ContractNumber,
                    'TotalAmount': float(contract.TotalAmount),
                    'Supplier': ', '.join([s.SupplierName for s in contract.suppliers]) if contract.suppliers else '',
                    'Client': contract.client.ClientName if contract.client else '',
                    'ClientID': contract.ClientID,  # 添加客户ID
                    'SignDate': contract.SignDate.isoformat() if contract.SignDate else None,
                    'CompletionRate': completion_rate,  # 添加完工率
                    'TotalPayments': float(total_payments),
                    'TotalInvoices': float(total_invoices),
                    'TotalCosts': float(total_costs),
                    'RemainingAmount': float(contract.TotalAmount) - float(total_payments),
                    'IsOverBudget': total_costs > contract.TotalAmount
                })
            
            return jsonify(result)
        
        elif request.method == 'POST':
            data = request.json
            
            # 客户处理
            client = None
            if data.get('Client'):
                client = Client.query.filter_by(ClientName=data['Client']).first()
                if not client:
                    return jsonify({'error': f'客户"{data["Client"]}"不存在'}), 400
            
            # 创建新合同
            new_contract = Contract(
                ProjectName=data['ProjectName'],
                ContractNumber=data['ContractNumber'],
                TotalAmount=data['TotalAmount'],
                ClientID=client.ClientID if client else None,
                SignDate=data.get('SignDate'),
                CompletionRate=data.get('CompletionRate', 0)  # 新增完工率字段
            )
            
            # 供应商处理
            if data.get('Supplier'):
                supplier = Supplier.query.filter_by(SupplierName=data['Supplier']).first()
                if not supplier:
                    return jsonify({'error': f'供应商"{data["Supplier"]}"不存在'}), 400
                new_contract.suppliers.append(supplier)
            
            db.session.add(new_contract)
            db.session.commit()
            
            return jsonify({
                'message': '合同创建成功', 
                'id': new_contract.ContractID
            })
    
    # 合同编辑 - 重命名为 update_contract 以避免冲突
    @app.route('/api/contracts/<int:contract_id>', methods=['PUT'])
    def update_contract(contract_id):
        contract = Contract.query.get_or_404(contract_id)
        data = request.json
        
        # 客户处理
        if data.get('Client'):
            client = Client.query.filter_by(ClientName=data['Client']).first()
            if not client:
                return jsonify({'error': f'客户"{data["Client"]}"不存在'}), 400
            contract.ClientID = client.ClientID
        
        # 供应商处理
        if data.get('Supplier'):
            contract.suppliers = []  # 清空现有关联
            supplier = Supplier.query.filter_by(SupplierName=data['Supplier']).first()
            if not supplier:
                return jsonify({'error': f'供应商"{data["Supplier"]}"不存在'}), 400
            contract.suppliers.append(supplier)  # 仅在supplier存在时执行
        
        # 更新基本信息，包括完工率
        contract.ProjectName = data.get('ProjectName', contract.ProjectName)
        contract.ContractNumber = data.get('ContractNumber', contract.ContractNumber)
        contract.TotalAmount = data.get('TotalAmount', contract.TotalAmount)
        contract.SignDate = data.get('SignDate', contract.SignDate)
        contract.CompletionRate = data.get('CompletionRate', contract.CompletionRate or 0)  # 新增完工率字段
        
        db.session.commit()
        
        return jsonify({'message': '合同更新成功'})
    
    # 合同删除
    @app.route('/api/contracts/<int:contract_id>', methods=['DELETE'])
    def delete_contract(contract_id):
        contract = Contract.query.get_or_404(contract_id)
        
        # 删除相关记录
        Payment.query.filter_by(ContractID=contract_id).delete()
        Invoice.query.filter_by(ContractID=contract_id).delete()
        Cost.query.filter_by(ContractID=contract_id).delete()
        
        db.session.delete(contract)
        db.session.commit()
        
        return jsonify({'message': '合同删除成功'})
    
    # 供应商管理
    @app.route('/suppliers')
    def suppliers():
        suppliers = Supplier.query.all()
        return render_template('suppliers.html', suppliers=suppliers)
    
    @app.route('/api/suppliers', methods=['POST'])
    def add_supplier():
        data = request.json
        new_supplier = Supplier(
            SupplierName=data['SupplierName'],
            ContactInfo=data.get('ContactInfo', '')
        )
        db.session.add(new_supplier)
        db.session.commit()
        return jsonify({'message': '供应商添加成功', 'id': new_supplier.SupplierID})
    
    @app.route('/api/suppliers/<int:supplier_id>', methods=['DELETE'])
    def delete_supplier(supplier_id):
        supplier = Supplier.query.get_or_404(supplier_id)
        db.session.delete(supplier)
        db.session.commit()
        return jsonify({'message': '供应商删除成功'})
    
    @app.route('/api/suppliers/<int:supplier_id>', methods=['PUT'])
    def update_supplier(supplier_id):
        supplier = Supplier.query.get_or_404(supplier_id)
        data = request.json
        supplier.SupplierName = data.get('SupplierName', supplier.SupplierName)
        supplier.ContactInfo = data.get('ContactInfo', supplier.ContactInfo)
        db.session.commit()
        return jsonify({'message': '供应商更新成功'})
    
    # 客户管理
    @app.route('/clients')
    def clients():
        clients = Client.query.all()
        return render_template('clients.html', clients=clients)
    
    @app.route('/api/clients', methods=['POST'])
    def add_client():
        data = request.json
        new_client = Client(
            ClientName=data['ClientName'],
            ContactInfo=data.get('ContactInfo', '')
        )
        db.session.add(new_client)
        db.session.commit()
        return jsonify({'message': '客户添加成功', 'id': new_client.ClientID})
    
    @app.route('/api/clients/<int:client_id>', methods=['DELETE'])
    def delete_client(client_id):
        client = Client.query.get_or_404(client_id)
        db.session.delete(client)
        db.session.commit()
        return jsonify({'message': '客户删除成功'})
    
    @app.route('/api/clients/<int:client_id>', methods=['PUT'])
    def update_client(client_id):
        client = Client.query.get_or_404(client_id)
        data = request.json
        client.ClientName = data.get('ClientName', client.ClientName)
        client.ContactInfo = data.get('ContactInfo', client.ContactInfo)
        db.session.commit()
        return jsonify({'message': '客户更新成功'})
    
    # 成本管理页面
    @app.route('/costs')
    def costs():
        contracts = Contract.query.all()
        return render_template('costs.html', 
                         contracts=contracts, 
                         contract=None, 
                         total_costs=0, 
                         is_over_budget=False)
    
    # 固定成本页面
    @app.route('/fixed_costs')
    def fixed_costs():
        return render_template('fixed_costs.html')
    
    # 合同付款页面
    @app.route('/contract/<int:contract_id>/payments')
    def contract_payments(contract_id):
        contract = Contract.query.get_or_404(contract_id)
        payments = Payment.query.filter_by(ContractID=contract_id).all()
        return render_template('payments.html', contract=contract, payments=payments)
    
    # 合同发票页面
    @app.route('/contract/<int:contract_id>/invoices')
    def contract_invoices(contract_id):
        contract = Contract.query.get_or_404(contract_id)
        invoices = Invoice.query.filter_by(ContractID=contract_id).all()
        return render_template('invoices.html', contract=contract, invoices=invoices)
    
    # 合同成本页面
    @app.route('/contract/<int:contract_id>/costs')
    def contract_costs(contract_id):
        contract = Contract.query.get_or_404(contract_id)
        costs = Cost.query.filter_by(ContractID=contract_id).all()
        total_costs = sum([cost.Amount for cost in costs]) if costs else 0
        is_over_budget = total_costs > contract.TotalAmount
        return render_template('costs.html', 
                             contract=contract, 
                             costs=costs,
                             total_costs=total_costs,
                             is_over_budget=is_over_budget)
    
    # 付款记录接口
    @app.route('/api/payments', methods=['POST'])
    def add_payment():
        data = request.json
        new_payment = Payment(** data)
        db.session.add(new_payment)
        db.session.commit()
        return jsonify({'message': '付款记录添加成功', 'id': new_payment.PaymentID})
    
    # 发票记录接口
    @app.route('/api/invoices', methods=['POST'])
    def add_invoice():
        data = request.json
        new_invoice = Invoice(**data)
        db.session.add(new_invoice)
        db.session.commit()
        return jsonify({'message': '发票记录添加成功', 'id': new_invoice.InvoiceID})
    
    # 成本记录接口
    @app.route('/api/costs', methods=['POST'])
    def add_cost():
        data = request.json
        new_cost = Cost(** data)
        db.session.add(new_cost)
        db.session.commit()
        return jsonify({'message': '成本记录添加成功', 'id': new_cost.CostID})
    
    # 删除付款记录
    @app.route('/api/payments/<int:id>', methods=['DELETE'])
    def delete_payment(id):
        payment = Payment.query.get_or_404(id)
        db.session.delete(payment)
        db.session.commit()
        return jsonify({'message': '付款记录删除成功'})
    
    # 删除发票记录
    @app.route('/api/invoices/<int:id>', methods=['DELETE'])
    def delete_invoice(id):
        invoice = Invoice.query.get_or_404(id)
        db.session.delete(invoice)
        db.session.commit()
        return jsonify({'message': '发票记录删除成功'})
    
    # 删除成本记录
    @app.route('/api/costs/<int:id>', methods=['DELETE'])
    def delete_cost(id):
        cost = Cost.query.get_or_404(id)
        db.session.delete(cost)
        db.session.commit()
        return jsonify({'message': '成本记录删除成功'})
    
    # 客户合同查询接口
    @app.route('/api/clients/<int:client_id>/contracts')
    def client_contracts(client_id):
        contracts = Contract.query.filter_by(ClientID=client_id).all()
        result = []
        
        for contract in contracts:
            total_payments = sum([p.Amount for p in contract.payments]) if contract.payments else 0
            total_invoices = sum([i.Amount for i in contract.invoices]) if contract.invoices else 0
            
            # 处理 CompletionRate 可能为 None 的情况
            completion_rate = float(contract.CompletionRate) if contract.CompletionRate is not None else 0.0
            
            result.append({
                'ContractID': contract.ContractID,
                'ProjectName': contract.ProjectName,
                'ContractNumber': contract.ContractNumber,
                'TotalAmount': float(contract.TotalAmount),
                'TotalPayments': float(total_payments),
                'TotalInvoices': float(total_invoices),
                'RemainingPayment': float(contract.TotalAmount) - float(total_payments),
                'RemainingInvoice': float(contract.TotalAmount) - float(total_invoices),
                'SignDate': contract.SignDate.isoformat() if contract.SignDate else None,
                'CompletionRate': completion_rate  # 添加完工率
            })
        
        return jsonify(result)
    
    # 供应商合同查询接口
    @app.route('/api/suppliers/<int:supplier_id>/contracts')
    def supplier_contracts(supplier_id):
        supplier = Supplier.query.get_or_404(supplier_id)
        contracts = Contract.query.filter(Contract.suppliers.any(SupplierID=supplier_id)).all()
        
        result = []
        
        for contract in contracts:
            total_payments = sum([p.Amount for p in contract.payments]) if contract.payments else 0
            total_invoices = sum([i.Amount for i in contract.invoices]) if contract.invoices else 0
            
            # 处理 CompletionRate 可能为 None 的情况
            completion_rate = float(contract.CompletionRate) if contract.CompletionRate is not None else 0.0
            
            result.append({
                'ContractID': contract.ContractID,
                'ProjectName': contract.ProjectName,
                'ContractNumber': contract.ContractNumber,
                'TotalAmount': float(contract.TotalAmount),
                'TotalPayments': float(total_payments),
                'TotalInvoices': float(total_invoices),
                'SignDate': contract.SignDate.isoformat() if contract.SignDate else None,
                'CompletionRate': completion_rate  # 添加完工率
            })
        
        return jsonify(result)
    
    # 获取工资薪金记录API
    @app.route('/api/salary_costs', methods=['GET'])
    def get_salary_costs():
        salary_costs = FixedCost.query.filter_by(CostType="工资薪金").all()
        result = []
        
        for cost in salary_costs:
            result.append({
                'FixedCostID': cost.FixedCostID,
                'Month': cost.Month,
                'Amount': float(cost.Amount),
                'Description': cost.Description,
                'CostDate': cost.CostDate.isoformat() if cost.CostDate else None
            })
        
        return jsonify(result)
    
    # 添加工资薪金记录API
    @app.route('/api/salary_costs', methods=['POST'])
    def add_salary_cost():
        data = request.json
        new_salary_cost = FixedCost(
            CostType="工资薪金",
            Amount=data['Amount'],
            CostDate=data.get('CostDate', datetime.utcnow().date()),
            Description=data.get('Description', ''),
            Month=data['Month']  # 格式: YYYY-MM
        )
        db.session.add(new_salary_cost)
        db.session.commit()
        return jsonify({'message': '工资薪金记录添加成功', 'id': new_salary_cost.FixedCostID})
    
    # 删除工资薪金记录API
    @app.route('/api/salary_costs/<int:id>', methods=['DELETE'])
    def delete_salary_cost(id):
        salary_cost = FixedCost.query.get_or_404(id)
        db.session.delete(salary_cost)
        db.session.commit()
        return jsonify({'message': '工资薪金记录删除成功'})
    
    # 固定成本分摊计算API
    @app.route('/api/allocate_fixed_costs', methods=['POST'])
    def allocate_fixed_costs():
        data = request.json
        month = data['month']  # 格式: YYYY-MM
        fixed_cost_type = data.get('cost_type', '工资薪金')
        
        # 获取当月固定成本总额
        fixed_costs = FixedCost.query.filter(
            FixedCost.Month == month,
            FixedCost.CostType == fixed_cost_type
        ).all()
        
        total_fixed_cost = sum([fc.Amount for fc in fixed_costs]) if fixed_costs else 0
        
        if total_fixed_cost == 0:
            return jsonify({'error': f'当月没有{fixed_cost_type}记录'}), 400
        
        # 获取所有合同及其完工率
        contracts = Contract.query.filter(Contract.CompletionRate > 0).all()
        
        if not contracts:
            return jsonify({'error': '没有找到有完工率的合同'}), 400
        
        # 计算权重和总权重
        weights = []
        total_weight = 0
        
        for contract in contracts:
            # 处理 CompletionRate 可能为 None 的情况
            completion_rate = float(contract.CompletionRate) if contract.CompletionRate is not None else 0.0
            weight = float(contract.TotalAmount) * completion_rate / 100
            weights.append({
                'contract_id': contract.ContractID,
                'contract_name': contract.ProjectName,
                'amount': float(contract.TotalAmount),
                'completion_rate': completion_rate,
                'weight': weight
            })
            total_weight += weight
        
        if total_weight == 0:
            return jsonify({'error': '总权重为0，无法分摊成本'}), 400
        
        # 计算分配率
        allocation_rate = total_fixed_cost / total_weight
        
        # 分配成本并保存到数据库
        results = []
        for weight_info in weights:
            allocated_cost = allocation_rate * weight_info['weight']
            
            # 创建成本记录
            new_cost = Cost(
                ContractID=weight_info['contract_id'],
                CostType=f"固定成本分摊-{fixed_cost_type}",
                Amount=allocated_cost,
                CostDate=datetime.strptime(month + '-01', '%Y-%m-%d').date(),
                Description=f"{month}月份{fixed_cost_type}分摊"
            )
            db.session.add(new_cost)
            
            results.append({
                'contract_id': weight_info['contract_id'],
                'contract_name': weight_info['contract_name'],
                'amount': weight_info['amount'],
                'completion_rate': weight_info['completion_rate'],
                'weight': weight_info['weight'],
                'allocated_cost': allocated_cost
            })
        
        db.session.commit()
        
        return jsonify({
            'total_fixed_cost': total_fixed_cost,
            'total_weight': total_weight,
            'allocation_rate': allocation_rate,
            'results': results
        })
    
    # 测试路由
    @app.route('/test')
    def test():
        return "OJ8K!"