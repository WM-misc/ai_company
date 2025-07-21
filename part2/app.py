#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
员工绩效管理系统 v2.1.3
内部使用 - 机密
"""

import os
import json
import sqlite3
import hashlib
import pickle
import base64
import tempfile
from datetime import datetime, timedelta
from flask import Flask, request, render_template, redirect, url_for, session, jsonify, flash
from functools import wraps
import uuid

app = Flask(__name__)
app.secret_key = os.urandom(32)

# 添加自定义过滤器
@app.template_filter('from_json')
def from_json_filter(s):
    try:
        return json.loads(s) if s else {}
    except:
        return {}

@app.template_filter('nl2br')
def nl2br_filter(s):
    return s.replace('\n', '<br>') if s else ''

# 数据库初始化
def init_db():
    conn = sqlite3.connect('performance.db')
    cursor = conn.cursor()
    
    # 用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT,
            department TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 绩效评估表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY,
            employee_id INTEGER,
            evaluator_id INTEGER,
            quarter TEXT,
            scores TEXT,
            comments TEXT,
            status TEXT DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES users (id),
            FOREIGN KEY (evaluator_id) REFERENCES users (id)
        )
    ''')
    
    # 模板配置表 - 这里是漏洞的关键
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY,
            name TEXT,
            content TEXT,
            variables TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')
    
    # 插入默认用户
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, password, role, department) VALUES
        ('admin', ?, 'admin', 'HR'),
        ('manager1', ?, 'manager', 'Engineering'),
        ('employee1', ?, 'employee', 'Engineering'),
        ('hr_lead', ?, 'hr', 'HR')
    ''', (
        hashlib.sha256('admin@2024'.encode()).hexdigest(),
        hashlib.sha256('manager123'.encode()).hexdigest(),
        hashlib.sha256('emp2024'.encode()).hexdigest(),
        hashlib.sha256('hr_secure'.encode()).hexdigest()
    ))
    
    # 插入默认模板
    default_template = {
        'quarterly_review': {
            'title': '季度绩效评估',
            'fields': ['工作质量', '团队协作', '创新能力', '目标达成'],
            'weights': [0.3, 0.2, 0.2, 0.3]
        }
    }
    
    cursor.execute('''
        INSERT OR IGNORE INTO templates (name, content, variables, created_by) VALUES
        ('default_quarterly', ?, ?, 1)
    ''', (json.dumps(default_template), '{}'))
    
    conn.commit()
    conn.close()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('需要管理员权限')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('performance.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, role, department FROM users WHERE username = ? AND password = ?',
                      (username, hashlib.sha256(password.encode()).hexdigest()))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[2]
            session['department'] = user[3]
            return redirect(url_for('dashboard'))
        else:
            flash('用户名或密码错误')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = sqlite3.connect('performance.db')
    cursor = conn.cursor()
    
    # 获取用户的评估数据
    if session['role'] == 'admin':
        cursor.execute('SELECT COUNT(*) FROM evaluations')
        total_evaluations = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM users WHERE role = "employee"')
        total_employees = cursor.fetchone()[0]
    else:
        cursor.execute('SELECT COUNT(*) FROM evaluations WHERE employee_id = ?', (session['user_id'],))
        total_evaluations = cursor.fetchone()[0]
        total_employees = 1
    
    conn.close()
    
    return render_template('dashboard.html', 
                          total_evaluations=total_evaluations,
                          total_employees=total_employees)

@app.route('/evaluations')
@login_required
def evaluations():
    conn = sqlite3.connect('performance.db')
    cursor = conn.cursor()
    
    if session['role'] in ['admin', 'manager']:
        cursor.execute('''
            SELECT e.id, u.username, e.quarter, e.status, e.created_at
            FROM evaluations e
            JOIN users u ON e.employee_id = u.id
            ORDER BY e.created_at DESC
        ''')
    else:
        cursor.execute('''
            SELECT e.id, u.username, e.quarter, e.status, e.created_at
            FROM evaluations e
            JOIN users u ON e.employee_id = u.id
            WHERE e.employee_id = ?
            ORDER BY e.created_at DESC
        ''', (session['user_id'],))
    
    evaluations = cursor.fetchall()
    conn.close()
    
    return render_template('evaluations.html', evaluations=evaluations)

# 新建评估
@app.route('/evaluations/create', methods=['GET', 'POST'])
@login_required
def create_evaluation():
    if session['role'] not in ['admin', 'manager']:
        flash('只有管理员和经理可以创建评估')
        return redirect(url_for('evaluations'))
    
    if request.method == 'POST':
        employee_id = request.form['employee_id']
        quarter = request.form['quarter']
        scores = request.form.get('scores', '{}')
        comments = request.form.get('comments', '')
        status = request.form.get('status', 'draft')  # 获取状态参数
        
        conn = sqlite3.connect('performance.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO evaluations (employee_id, evaluator_id, quarter, scores, comments, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (employee_id, session['user_id'], quarter, scores, comments, status))
        conn.commit()
        conn.close()
        
        if status == 'completed':
            flash('评估已完成并提交')
        else:
            flash('评估已保存为草稿')
        return redirect(url_for('evaluations'))
    
    # GET请求，显示创建表单
    conn = sqlite3.connect('performance.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, department FROM users WHERE role = "employee"')
    employees = cursor.fetchall()
    conn.close()
    
    return render_template('create_evaluation.html', employees=employees)

# 查看评估详情
@app.route('/evaluations/<int:evaluation_id>')
@login_required
def view_evaluation(evaluation_id):
    conn = sqlite3.connect('performance.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT e.id, e.quarter, e.scores, e.comments, e.status, e.created_at,
               emp.username as employee_name, emp.department,
               eva.username as evaluator_name
        FROM evaluations e
        JOIN users emp ON e.employee_id = emp.id
        JOIN users eva ON e.evaluator_id = eva.id
        WHERE e.id = ?
    ''', (evaluation_id,))
    evaluation = cursor.fetchone()
    conn.close()
    
    if not evaluation:
        flash('评估不存在')
        return redirect(url_for('evaluations'))
    
    # 检查权限
    if session['role'] not in ['admin', 'manager'] and evaluation[6] != session['username']:
        flash('无权查看此评估')
        return redirect(url_for('evaluations'))
    
    evaluation_data = {
        'id': evaluation[0],
        'quarter': evaluation[1],
        'scores': evaluation[2],
        'comments': evaluation[3],
        'status': evaluation[4],
        'created_at': evaluation[5],
        'employee_name': evaluation[6],
        'department': evaluation[7],
        'evaluator_name': evaluation[8]
    }
    
    return render_template('view_evaluation.html', evaluation=evaluation_data)

# 关键漏洞点：模板系统
@app.route('/admin/templates')
@admin_required
def admin_templates():
    conn = sqlite3.connect('performance.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, created_at FROM templates ORDER BY created_at DESC')
    templates = cursor.fetchall()
    conn.close()
    
    return render_template('admin_templates.html', templates=templates)

@app.route('/admin/templates/create', methods=['GET', 'POST'])
@admin_required
def create_template():
    if request.method == 'POST':
        name = request.form['name']
        content = request.form['content']
        variables = request.form.get('variables', '{}')
        
        # 这里是漏洞的核心 - 序列化用户输入
        try:
            # 验证variables是否为有效的JSON
            json.loads(variables)
            
            conn = sqlite3.connect('performance.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO templates (name, content, variables, created_by)
                VALUES (?, ?, ?, ?)
            ''', (name, content, variables, session['user_id']))
            conn.commit()
            conn.close()
            
            flash('模板创建成功')
            return redirect(url_for('admin_templates'))
        except json.JSONDecodeError:
            flash('变量配置格式错误，请使用有效的JSON格式')
    
    return render_template('create_template.html')

# 获取单个模板数据
@app.route('/admin/templates/<int:template_id>')
@admin_required
def get_template(template_id):
    conn = sqlite3.connect('performance.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, content, variables FROM templates WHERE id = ?', (template_id,))
    template = cursor.fetchone()
    conn.close()
    
    if template:
        return jsonify({
            'id': template[0],
            'name': template[1],
            'content': template[2],
            'variables': template[3]
        })
    else:
        return jsonify({'error': '模板不存在'}), 404

# 编辑模板
@app.route('/admin/templates/<int:template_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_template(template_id):
    conn = sqlite3.connect('performance.db')
    cursor = conn.cursor()
    
    if request.method == 'GET':
        cursor.execute('SELECT id, name, content, variables FROM templates WHERE id = ?', (template_id,))
        template = cursor.fetchone()
        conn.close()
        
        if template:
            template_data = {
                'id': template[0],
                'name': template[1],
                'content': template[2],
                'variables': template[3]
            }
            return render_template('edit_template.html', template=template_data)
        else:
            flash('模板不存在')
            return redirect(url_for('admin_templates'))
    
    elif request.method == 'POST':
        name = request.form['name']
        content = request.form['content']
        variables = request.form.get('variables', '{}')
        
        try:
            # 验证variables格式
            if not variables.startswith('pickle:'):
                json.loads(variables)
            
            cursor.execute('''
                UPDATE templates SET name = ?, content = ?, variables = ?
                WHERE id = ?
            ''', (name, content, variables, template_id))
            conn.commit()
            conn.close()
            
            flash('模板更新成功')
            return redirect(url_for('admin_templates'))
        except json.JSONDecodeError:
            flash('变量配置格式错误，请使用有效的JSON格式')
            conn.close()
            return redirect(url_for('edit_template', template_id=template_id))

# 删除模板
@app.route('/admin/templates/<int:template_id>/delete', methods=['POST'])
@admin_required
def delete_template(template_id):
    conn = sqlite3.connect('performance.db')
    cursor = conn.cursor()
    
    # 检查模板是否存在
    cursor.execute('SELECT id FROM templates WHERE id = ?', (template_id,))
    if not cursor.fetchone():
        return jsonify({'error': '模板不存在'}), 404
    
    # 删除模板
    cursor.execute('DELETE FROM templates WHERE id = ?', (template_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': '模板删除成功'})

# 漏洞触发点：模板预览功能
@app.route('/admin/templates/preview', methods=['POST'])
@admin_required
def preview_template():
    try:
        template_data = request.json
        
        # 获取模板内容和变量
        content = template_data.get('content', '')
        variables_str = template_data.get('variables', '{}')
        
        # 这里是关键的漏洞点：
        # 为了支持"复杂的模板变量配置"，系统支持序列化的Python对象
        # 但是没有正确验证输入，导致pickle反序列化漏洞
        
        if variables_str.startswith('pickle:'):
            # 移除前缀并解码
            encoded_data = variables_str[7:]
            try:
                # 危险的pickle反序列化 - 这是RCE的入口点
                variables = pickle.loads(base64.b64decode(encoded_data))
            except Exception as e:
                return jsonify({'error': f'变量反序列化失败: {str(e)}'}), 400
        else:
            # 正常的JSON解析
            variables = json.loads(variables_str)
        
        # 模拟模板渲染
        rendered_content = content
        if isinstance(variables, dict):
            for key, value in variables.items():
                placeholder = f'{{{{{key}}}}}'
                rendered_content = rendered_content.replace(placeholder, str(value))
        else:
            # 如果variables不是字典（比如pickle反序列化的结果），创建一个默认的渲染
            rendered_content = content.replace('{{test_var}}', '命令已执行')
        
        return jsonify({
            'success': True,
            'original': content,
            'rendered_content': rendered_content
        })
        
    except json.JSONDecodeError:
        return jsonify({'error': '变量配置格式错误'}), 400
    except Exception as e:
        return jsonify({'error': f'预览生成失败: {str(e)}'}), 500

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/help')
@login_required
def help_page():
    return render_template('help.html')

if __name__ == '__main__':
    init_db()
    # 创建flag文件
    if not os.path.exists('/flag'):
        with open('/flag', 'w') as f:
            f.write('wmctf{P1ckl3_D3s3r14l1z4t10n_1s_D4ng3r0us_4nd_RCE}')
    
    app.run(host='0.0.0.0', port=5000, debug=False) 