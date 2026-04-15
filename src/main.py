from src.preprocess.clean import DataCleaner
from src.analysis.stats import DataAnalyzer
from src.ml.model import MLModel

def main():
    cleaner = DataCleaner(
        input_file="data/processed/cases_UNC.csv",
        output_file="data/processed/cases_ml_final.csv",
        stats_file="data/processed/cases_ml_stats.csv"
    )

    analyzer = DataAnalyzer(
        input_file="data/processed/cases_ml_final.csv"
    )

    model = MLModel(
        input_file="data/processed/cases_ml_final.csv"
    )

    print("开始数据清洗...")
    cleaner.run()

    print("开始数据分析...")
    analyzer.run()

    print("开始模型训练...")
    model.train()

if __name__ == "__main__":
    main()