# 医案数据分析与机器学习项目

## 项目简介
本项目基于中医医案数据，构建从数据获取、清洗、分析到机器学习建模的完整流程，实现医案数据的结构化与初步建模分析。

## 项目结构
medical_case_mining100/
│
├── data/ # 数据目录
│ ├── raw/ # 原始数据
│ └── processed/ # 清洗后数据
│
├── src/
│ ├── crawler/ # 数据获取
│ ├── preprocess/ # 数据清洗
│ ├── analysis/ # 数据分析
│ ├── ml/ # 机器学习模型
│ └── main.py # 项目入口
│
├── requirements.txt
└── README.md

## 技术栈
- Python
- pandas
- matplotlib
- scikit-learn

## 功能模块

### 1. 数据获取
- 医案数据爬取

### 2. 数据清洗
- 空值处理
- 重复值去除
- 字段规范化

### 3. 数据分析
- 标签分布统计
- 特征分布分析
- 可视化展示

### 4. 机器学习
- 分类/回归模型训练
- 模型评估

## 使用方法

### 1. 创建虚拟环境
python -m venv venv
venv\Scripts\activate

### 2. 安装依赖
pip install -r requirements.txt

### 3. 运行项目
python src/main.py

## 项目意义
该项目展示了从原始医案数据到机器学习建模的完整流程，具备基础数据分析与建模能力。
