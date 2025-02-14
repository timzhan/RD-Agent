import json
import pickle
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from rdagent.components.benchmark.conf import BenchmarkSettings
from rdagent.components.benchmark.eval_method import FactorImplementEval


class BenchmarkAnalyzer:
    def __init__(self, settings):
        self.settings = settings
        self.index_map = self.load_index_map()

    def load_index_map(self):
        index_map = {}
        with open(self.settings.bench_data_path, "r") as file:
            factor_dict = json.load(file)
        for factor_name, data in factor_dict.items():
            index_map[factor_name] = (factor_name, data["Category"], data["Difficulty"])
        return index_map

    def load_data(self, file_path):
        file_path = Path(file_path)
        if not (file_path.is_file() and file_path.suffix == ".pkl"):
            raise ValueError("Invalid file path")

        with file_path.open("rb") as f:
            res = pickle.load(f)

        return res

    def process_results(self, results):
        final_res = {}
        for experiment, path in results.items():
            data = self.load_data(path)
            summarized_data = FactorImplementEval.summarize_res(data)
            processed_data = self.analyze_data(summarized_data)
            final_res[experiment] = processed_data.iloc[-1, :]
        return final_res

    def reformat_succ_rate(self, display_df):
        new_idx = []
        display_df = display_df[display_df.index.isin(self.index_map.keys())]
        for idx in display_df.index:
            new_idx.append(self.index_map[idx])

        display_df.index = pd.MultiIndex.from_tuples(
            new_idx,
            names=["Factor", "Category", "Difficulty"],
        )
        display_df = display_df.swaplevel(0, 2).swaplevel(0, 1).sort_index(axis=0)

        return display_df.sort_index(
            key=lambda x: [{"Easy": 0, "Medium": 1, "Hard": 2, "New Discovery": 3}.get(i, i) for i in x]
        )

    def result_all_key_order(self, x):
        order_v = []
        for i in x:
            order_v.append(
                {
                    "avg. Run successful rate": 0,
                    "avg. Format successful rate": 1,
                    "avg. Correlation (value only)": 2,
                    "max. Correlation": 3,
                    "max. accuracy": 4,
                    "avg. accuracy": 5,
                }.get(i, i),
            )
        return order_v

    def analyze_data(self, sum_df):
        index = [
            "FactorSingleColumnEvaluator",
            "FactorOutputFormatEvaluator",
            "FactorRowCountEvaluator",
            "FactorIndexEvaluator",
            "FactorMissingValuesEvaluator",
            "FactorEqualValueCountEvaluator",
            "FactorCorrelationEvaluator",
            "run factor error",
        ]
        sum_df = sum_df.reindex(index, axis=0)
        sum_df_clean = sum_df.T.groupby(level=0).apply(lambda x: x.reset_index(drop=True))

        run_error = sum_df_clean["run factor error"].unstack().T.fillna(False).astype(bool)
        succ_rate = ~run_error
        succ_rate = succ_rate.mean(axis=0).to_frame("success rate")

        succ_rate_f = self.reformat_succ_rate(succ_rate)
        succ_rate_f

        sum_df_clean["FactorRowCountEvaluator"]

        format_issue = sum_df_clean["FactorRowCountEvaluator"] & sum_df_clean["FactorIndexEvaluator"]
        eval_series = format_issue.unstack()
        succ_rate = eval_series.T.fillna(False).astype(bool)  # false indicate failure
        format_succ_rate = succ_rate.mean(axis=0).to_frame("success rate")
        format_succ_rate_f = self.reformat_succ_rate(format_succ_rate)

        corr = sum_df_clean["FactorCorrelationEvaluator"] * format_issue
        corr = corr.unstack().T.mean(axis=0).to_frame("corr(only success)")
        corr_res = self.reformat_succ_rate(corr)
        corr_max = sum_df_clean["FactorCorrelationEvaluator"] * format_issue

        corr_max = corr_max.unstack().T.max(axis=0).to_frame("corr(only success)")
        corr_max_res = self.reformat_succ_rate(corr_max)

        value_max = sum_df_clean["FactorMissingValuesEvaluator"] * format_issue
        value_max = value_max.unstack().T.max(axis=0).to_frame("max_value")
        value_max_res = self.reformat_succ_rate(value_max)

        value_avg = (
            (sum_df_clean["FactorMissingValuesEvaluator"] * format_issue).unstack().T.mean(axis=0).to_frame("avg_value")
        )
        value_avg_res = self.reformat_succ_rate(value_avg)

        result_all = pd.concat(
            {
                "avg. Correlation (value only)": corr_res.iloc[:, 0],
                "avg. Format successful rate": format_succ_rate_f.iloc[:, 0],
                "avg. Run successful rate": succ_rate_f.iloc[:, 0],
                "max. Correlation": corr_max_res.iloc[:, 0],
                "max. accuracy": value_max_res.iloc[:, 0],
                "avg. accuracy": value_avg_res.iloc[:, 0],
            },
            axis=1,
        )

        df = result_all.sort_index(axis=1, key=self.result_all_key_order)
        print(df)

        # Calculate the mean of each column
        mean_values = df.fillna(0.0).mean()
        mean_df = pd.DataFrame(mean_values).T

        # Assign the MultiIndex to the DataFrame
        mean_df.index = pd.MultiIndex.from_tuples([("-", "-", "Average")], names=["Factor", "Category", "Difficulty"])

        # Append the mean values to the end of the dataframe
        df_w_mean = pd.concat([df, mean_df]).astype("float")

        return df_w_mean


class Plotter:
    @staticmethod
    def change_fs(font_size):
        plt.rc("font", size=font_size)
        plt.rc("axes", titlesize=font_size)
        plt.rc("axes", labelsize=font_size)
        plt.rc("xtick", labelsize=font_size)
        plt.rc("ytick", labelsize=font_size)
        plt.rc("legend", fontsize=font_size)
        plt.rc("figure", titlesize=font_size)

    @staticmethod
    def plot_data(data, file_name):
        plt.figure(figsize=(10, 6))
        sns.barplot(x="index", y="b", hue="a", data=data)
        plt.xlabel("Method")
        plt.ylabel("Value")
        plt.title("Comparison of Different Methods")
        plt.savefig(file_name)


if __name__ == "__main__":
    settings = BenchmarkSettings()
    benchmark = BenchmarkAnalyzer(settings)
    results = {
        "1 round experiment": "git_ignore_folder/eval_results/res_promptV220240724-060037.pkl",
    }
    final_results = benchmark.process_results(results)
    final_results_df = pd.DataFrame(final_results)

    Plotter.change_fs(20)
    plot_data = final_results_df.drop(["max. accuracy", "avg. accuracy"], axis=0).T
    plot_data = plot_data.reset_index().melt("index", var_name="a", value_name="b")
    Plotter.plot_data(plot_data, "rdagent/app/quant_factor_benchmark/comparison_plot.png")
