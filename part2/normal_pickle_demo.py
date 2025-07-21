#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示正常的pickle序列化用法 - 用作模板系统的"高级配置"
"""

import pickle
import base64
import json
from datetime import datetime, date
from collections import namedtuple

# 1. 复杂数据结构示例
class EmployeeData:
    """员工数据类 - 这是一个"正常"的复杂对象"""
    def __init__(self, name, department, level, join_date):
        self.name = name
        self.department = department
        self.level = level
        self.join_date = join_date
        self.performance_history = []
    
    def add_performance(self, quarter, score):
        self.performance_history.append({
            'quarter': quarter,
            'score': score,
            'date': datetime.now()
        })
    
    def get_average_score(self):
        if not self.performance_history:
            return 0
        return sum(p['score'] for p in self.performance_history) / len(self.performance_history)
    
    def __str__(self):
        return f"{self.name} ({self.department}, Level {self.level})"

# 2. 配置对象示例
EvaluationConfig = namedtuple('EvaluationConfig', ['weights', 'criteria', 'scale'])

def create_normal_examples():
    """创建正常的pickle序列化示例"""
    
    print("=== 正常的Pickle序列化示例 ===\n")
    
    examples = []
    
    # 示例1：复杂员工数据
    employee = EmployeeData("张三", "工程部", "P6", date(2020, 3, 15))
    employee.add_performance("Q1-2024", 85)
    employee.add_performance("Q2-2024", 90)
    employee.add_performance("Q3-2024", 88)
    
    employee_data = {
        'employee_name': employee.name,
        'department': employee.department,
        'level': employee.level,
        'average_score': employee.get_average_score(),
        'join_date': employee.join_date.strftime('%Y-%m-%d'),
        'performance_count': len(employee.performance_history)
    }
    
    pickled_employee = pickle.dumps(employee_data)
    encoded_employee = base64.b64encode(pickled_employee).decode('utf-8')
    
    examples.append({
        'name': '员工绩效数据',
        'description': '包含员工的详细绩效信息',
        'template_content': '''员工绩效报告

姓名：{{employee_name}}
部门：{{department}}
级别：{{level}}
入职日期：{{join_date}}
平均分数：{{average_score}}
评估次数：{{performance_count}}

本季度表现良好，建议继续保持。''',
        'variables': f'pickle:{encoded_employee}',
        'expected_result': '正常的模板渲染，显示员工信息'
    })
    
    # 示例2：评估配置对象
    config = EvaluationConfig(
        weights={'technical': 0.4, 'teamwork': 0.3, 'innovation': 0.3},
        criteria=['代码质量', '项目交付', '团队协作', '创新思维'],
        scale={'excellent': 90, 'good': 80, 'average': 70, 'poor': 60}
    )
    
    config_data = {
        'tech_weight': config.weights['technical'],
        'team_weight': config.weights['teamwork'],
        'innovation_weight': config.weights['innovation'],
        'criteria_count': len(config.criteria),
        'max_score': config.scale['excellent']
    }
    
    pickled_config = pickle.dumps(config_data)
    encoded_config = base64.b64encode(pickled_config).decode('utf-8')
    
    examples.append({
        'name': '评估配置数据',
        'description': '评估系统的权重和标准配置',
        'template_content': '''评估标准配置

技术能力权重：{{tech_weight}}
团队协作权重：{{team_weight}}
创新能力权重：{{innovation_weight}}
评估维度数量：{{criteria_count}}
最高分数：{{max_score}}

请按照以上标准进行评估。''',
        'variables': f'pickle:{encoded_config}',
        'expected_result': '显示评估系统的配置信息'
    })
    
    # 示例3：简单的嵌套数据
    nested_data = {
        'company': '科技有限公司',
        'quarter': 'Q4-2024',
        'departments': ['工程部', '产品部', '市场部'],
        'metrics': {
            'total_employees': 150,
            'new_hires': 12,
            'promotions': 8
        },
        'summary': '本季度业绩良好'
    }
    
    pickled_nested = pickle.dumps(nested_data)
    encoded_nested = base64.b64encode(pickled_nested).decode('utf-8')
    
    examples.append({
        'name': '公司季度数据',
        'description': '包含嵌套结构的复杂数据',
        'template_content': '''{{company}} - {{quarter}}季度报告

部门数量：{{departments}}
总员工数：{{total_employees}}
新入职：{{new_hires}}人
晋升：{{promotions}}人

{{summary}}''',
        'variables': f'pickle:{encoded_nested}',
        'expected_result': '显示公司季度报告信息'
    })
    
    return examples

def show_comparison():
    """对比JSON和Pickle的区别"""
    print("=== JSON vs Pickle 对比 ===\n")
    
    # 相同的数据，用两种方式序列化
    data = {
        'name': '李四',
        'score': 85.5,
        'department': '产品部',
        'active': True
    }
    
    # JSON方式
    json_str = json.dumps(data, ensure_ascii=False)
    print("JSON格式：")
    print(json_str)
    print(f"长度：{len(json_str)}")
    
    # Pickle方式
    pickled = pickle.dumps(data)
    encoded = base64.b64encode(pickled).decode('utf-8')
    print(f"\nPickle格式（base64编码）：")
    print(f"pickle:{encoded}")
    print(f"长度：{len(encoded)}")
    
    print(f"\n两种方式在模板系统中的使用：")
    print(f"JSON: {json_str}")
    print(f"Pickle: pickle:{encoded}")

def main():
    """主函数"""
    examples = create_normal_examples()
    
    for i, example in enumerate(examples, 1):
        print(f"=== 示例 {i}：{example['name']} ===")
        print(f"说明：{example['description']}")
        print(f"\n模板内容：")
        print(example['template_content'])
        print(f"\n变量配置（Pickle格式）：")
        print(example['variables'])
        print(f"\n预期结果：{example['expected_result']}")
        print("\n" + "-"*80 + "\n")
    
    show_comparison()
    
    print("\n=== 使用说明 ===")
    print("1. 复制上述任一示例的'模板内容'到模板内容框")
    print("2. 复制对应的'变量配置'到变量配置框")
    print("3. 点击'预览效果'查看渲染结果")
    print("4. 这些都是正常的、安全的pickle序列化数据")

if __name__ == "__main__":
    main() 