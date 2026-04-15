import pandas as pd
import matplotlib.pyplot as plt


class DataAnalyzer:
    def __init__(self, input_file):
        self.input_file = input_file

    def run(self):
        df = pd.read_csv(self.input_file)

        print("===== 数据概览 =====")
        print("样本数：", len(df))
        print("\n字段信息：")
        print(df.info())

        print("\n===== 标签分布 =====")
        label_counts = df["label_coarse"].value_counts()
        print(label_counts)

        # 核心：画图（这才是重点）
        plt.figure(figsize=(6,4))
        label_counts.plot(kind='bar')
        plt.title("标签分布")
        plt.xlabel("类别")
        plt.ylabel("数量")
        plt.grid(True)
        plt.show()

        print("\n===== 文本长度分布 =====")
        df["text_len"] = df["input_text"].apply(len)
        print(df["text_len"].describe())
        plt.figure(figsize=(6,4))
        plt.hist(df["text_len"], bins=20)
        plt.title("文本长度分布")
        plt.xlabel("长度")
        plt.ylabel("频数")
        plt.grid(True)
        plt.show()

        print("\n===== 数据质量 =====")
        print("缺失值：")
        print(df.isna().sum())
        print("\n重复值：")
        print(df.duplicated().sum())