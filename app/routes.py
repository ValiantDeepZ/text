# -*- coding: utf-8 -*-
from flask import render_template, request, jsonify, redirect, url_for
from app import db
from app.models import Supplier, Client, Contract, Payment, Invoice, Cost
import os
from sqlalchemy.orm import joinedload


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
                'SignDate': contract.SignDate.isoformat() if contract.SignDate else None
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
                
                result.append({
                    'ContractID': contract.ContractID,
                    'ProjectName': contract.ProjectName,
                    'ContractNumber': contract.ContractNumber,
                    'TotalAmount': float(contract.TotalAmount),
                    'Supplier': ', '.join([s.SupplierName for s in contract.suppliers]) if contract.suppliers else '',
                    'Client': contract.client.ClientName if contract.client else '',
                    'ClientID': contract.ClientID,  # 添加客户ID
                    'SignDate': contract.SignDate.isoformat() if contract.SignDate else None,
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
                SignDate=data.get('SignDate')
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
    
    # 合同编辑
    @app.route('/api/contracts/<int:contract_id>', methods=['PUT'])
    def edit_contract(contract_id):
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
        
        # 更新基本信息
        contract.ProjectName = data.get('ProjectName', contract.ProjectName)
        contract.ContractNumber = data.get('ContractNumber', contract.ContractNumber)
        contract.TotalAmount = data.get('TotalAmount', contract.TotalAmount)
        contract.SignDate = data.get('SignDate', contract.SignDate)
        
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
    def edit_supplier(supplier_id):
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
    def edit_client(client_id):
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
            
            result.append({
                'ContractID': contract.ContractID,
                'ProjectName': contract.ProjectName,
                'ContractNumber': contract.ContractNumber,
                'TotalAmount': float(contract.TotalAmount),
                'TotalPayments': float(total_payments),
                'TotalInvoices': float(total_invoices),
                'RemainingPayment': float(contract.TotalAmount) - float(total_payments),
                'RemainingInvoice': float(contract.TotalAmount) - float(total_invoices),
                'SignDate': contract.SignDate.isoformat() if contract.SignDate else None
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
            
            result.append({
                'ContractID': contract.ContractID,
                'ProjectName': contract.ProjectName,
                'ContractNumber': contract.ContractNumber,
                'TotalAmount': float(contract.TotalAmount),
                'TotalPayments': float(total_payments),
                'TotalInvoices': float(total_invoices),
                'SignDate': contract.SignDate.isoformat() if contract.SignDate else None
            })
        
        return jsonify(result)
    
    # 测试路由
    @app.route('/test')
    def test():
        return "OJ8K!"