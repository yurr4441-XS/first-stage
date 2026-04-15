import os
import re
import pandas as pd


class DataCleaner:
    def __init__(self, input_file, output_file, stats_file):
        self.input_file = input_file
        self.output_file = output_file
        self.stats_file = stats_file
    # 标签归并函数
    def coarse_label(self,diag: str) -> str | None:
        """将原始中医诊断归并为粗粒度标签。"""
        if pd.isna(diag):
            return None
        text = str(diag).strip()
        # 去掉前导符号
        text = re.sub(r"^[：:；;，,。\.\s]+", "", text)
        # 去掉编号
        text = re.sub(r"^[①②③④⑤⑥⑦⑧⑨⑩0-9、.．]+", "", text)
        # 去括号内容
        text = re.sub(r"（.*?）|\(.*?\)", "", text)
        # 去多余空白
        text = re.sub(r"\s+", "", text)
        # 统一连接符
        text = text.replace("——", "--").replace("—", "-").replace("－", "-")
        # 明显无效短语
        bad_phrases = {
            "与辨病相结合",
            "之一",
            "分型的方法治疗偏头痛",
            "",
        }
        if text in bad_phrases:
            return None
        # 脑系病
        if any(k in text for k in ["中风", "眩晕", "头痛", "痫", "风痫"]):
            return "脑系病"
        # 痹证类
        if any(k in text for k in ["痹", "腰腿痛", "项痹", "胸痹"]):
            return "痹证类"
        # 外表类 / 杂病类
        if any(k in text for k in ["感冒", "耳聋", "失音", "鼻渊", "尿浊", "淋证", "疝证", "心悸", "桃疮", "石淋"]):
            return "外表类"
        return None
    # 输入文本构造
    def build_input_text(row: pd.Series) -> str:
        """拼接主诉 + 现病史作为模型输入文本。"""
        chief = "" if pd.isna(row.get("chief_complaint")) else str(row.get("chief_complaint")).strip()
        history = "" if pd.isna(row.get("history")) else str(row.get("history")).strip()
        return f"{chief} {history}".strip()
    def run(self):
        df = pd.read_csv(self.input_file)

        stats = {
            "raw_total": len(df)
        }

        print(f"读取文件：{self.input_file}")
        print(f"原始总数：{stats['raw_total']}")

        # 1. 保留有处方
        df_prescription = df.dropna(subset=["prescription"]).copy()
        stats["after_prescription"] = len(df_prescription)
        print(f"有处方后：{stats['after_prescription']}")

        # 2. 保留主诉和现病史都存在
        df_core = df_prescription[
            df_prescription["chief_complaint"].notna() &
            df_prescription["history"].notna()
            ].copy()
        stats["after_chief_history"] = len(df_core)
        print(f"有主诉且有现病史后：{stats['after_chief_history']}")

        # 3. 粗标签
        df_core["label_coarse"] = df_core["tcm_diag"].apply(self.coarse_label)
        stats["label_coarse_notna"] = df_core["label_coarse"].notna().sum()
        print(f"label_coarse 非空：{stats['label_coarse_notna']}")

        # 4. 输入文本
        df_core["input_text"] = df_core.apply(self.build_input_text, axis=1)

        # 5. 输入长度过滤
        df_model = df_core[df_core["input_text"].str.len() >= 8].copy()
        stats["after_input_len"] = len(df_model)
        print(f"输入长度>=8 后：{stats['after_input_len']}")

        # 6. 只保留标签非空
        df_model = df_model[df_model["label_coarse"].notna()].copy()
        stats["final_total"] = len(df_model)
        print(f"最终可建模样本数：{stats['final_total']}")

        # 7. 标签分布
        label_counts = df_model["label_coarse"].value_counts()
        print("\n标签分布：")
        print(label_counts)

        # 8. 输出列
        output_columns = [
            "source_url",
            "case_no",
            "page_title",
            "catalog_title",
            "chief_complaint",
            "history",
            "tcm_diag",
            "prescription",
            "input_text",
            "label_coarse",
            "raw_text",
        ]

        existing_columns = [col for col in output_columns if col in df_model.columns]
        df_output = df_model[existing_columns].reset_index(drop=True)

        # 9. 保存最终数据
        df_output.to_csv(self.output_file, index=False, encoding="utf-8-sig")
        # 10. 保存统计文件
        stats_rows = [{"metric": k, "value": v} for k, v in stats.items()]
        stats_rows.extend(
            [{"metric": f"label_{label}", "value": int(count)} for label, count in label_counts.items()] )
        pd.DataFrame(stats_rows).to_csv(self.stats_file, index=False, encoding="utf-8-sig")
        print("\n===== 保存完成 =====")
        print(f"最终数据文件：{self.output_file}")
        print(f"统计文件：{self.stats_file}")
        print(f"最终样本数：{len(df_output)}")

if __name__ == "__main__":
    cleaner = DataCleaner(
        input_file="data/processed/cases_UNC.csv",
        output_file="data/processed/cases_ml_final.csv",
        stats_file="data/processed/cases_ml_stats.csv"
    )
    cleaner.run()