import subprocess
import zipfile
from pathlib import Path

import pandas as pd

from rdagent.app.kaggle.conf import KAGGLE_IMPLEMENT_SETTING
from rdagent.core.experiment import FBWorkspace
from rdagent.log import rdagent_logger as logger
from rdagent.utils.env import KGDockerEnv

KG_FEATURE_PREPROCESS_SCRIPT = """import pickle

from fea_share_preprocess import preprocess_script

X_train, X_valid, y_train, y_valid, X_test, passenger_ids = preprocess_script()

pickle.dump(X_train, open("X_train.pkl", "wb"))
pickle.dump(X_valid, open("X_valid.pkl", "wb"))
pickle.dump(y_train, open("y_train.pkl", "wb"))
pickle.dump(y_valid, open("y_valid.pkl", "wb"))
pickle.dump(X_test, open("X_test.pkl", "wb"))
pickle.dump(passenger_ids, open("passenger_ids.pkl", "wb"))
"""


class KGFBWorkspace(FBWorkspace):
    def __init__(self, template_folder_path: Path, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.inject_code_from_folder(template_folder_path)
        self.data_description: list[str] = []
        self.model_description: dict[str, str] = {}

    def generate_preprocess_data(
        self,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.DataFrame, pd.Series]:
        kgde = KGDockerEnv(KAGGLE_IMPLEMENT_SETTING.competition)
        kgde.prepare()

        execute_log, results = kgde.dump_python_code_run_and_get_results(
            code=KG_FEATURE_PREPROCESS_SCRIPT,
            local_path=str(self.workspace_path),
            dump_file_names=[
                "X_train.pkl",
                "X_valid.pkl",
                "y_train.pkl",
                "y_valid.pkl",
                "X_test.pkl",
                "passenger_ids.pkl",
            ],
            running_extra_volume=(
                {KAGGLE_IMPLEMENT_SETTING.local_data_path + "/" + KAGGLE_IMPLEMENT_SETTING.competition: "/kaggle/input"}
                if KAGGLE_IMPLEMENT_SETTING.competition
                else None
            ),
        )
        if results is None:
            logger.error("Feature preprocess failed.")
            raise Exception("Feature preprocess failed.")
        else:
            X_train, X_valid, y_train, y_valid, X_test, passenger_ids = results
            return X_train, X_valid, y_train, y_valid, X_test, passenger_ids

    def execute(self, run_env: dict = {}, *args, **kwargs) -> str:
        logger.info(f"Running the experiment in {self.workspace_path}")

        # link the data to the workspace to speed up the preprocessing
        source_data_path = Path(KAGGLE_IMPLEMENT_SETTING.local_data_path) / KAGGLE_IMPLEMENT_SETTING.competition
        self.link_all_files_in_folder_to_workspace(source_data_path, self.workspace_path)

        kgde = KGDockerEnv(KAGGLE_IMPLEMENT_SETTING.competition)
        kgde.prepare()

        execute_log = kgde.run(
            local_path=str(self.workspace_path),
            entry=f"python train.py",
            env=run_env,
            running_extra_volume=(
                {KAGGLE_IMPLEMENT_SETTING.local_data_path + "/" + KAGGLE_IMPLEMENT_SETTING.competition: "/kaggle/input"}
                if KAGGLE_IMPLEMENT_SETTING.competition
                else None
            ),
        )

        csv_path = self.workspace_path / "submission_score.csv"

        if not csv_path.exists():
            logger.error(f"File {csv_path} does not exist.")
            return None
        return pd.read_csv(csv_path, index_col=0).iloc[:, 0]
