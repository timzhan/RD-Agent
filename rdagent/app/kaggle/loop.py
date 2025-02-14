from collections import defaultdict
from typing import Any

import fire

from rdagent.app.kaggle.conf import KAGGLE_IMPLEMENT_SETTING
from rdagent.components.workflow.conf import BasePropSetting
from rdagent.components.workflow.rd_loop import RDLoop
from rdagent.core.developer import Developer
from rdagent.core.exception import FactorEmptyError, ModelEmptyError
from rdagent.core.proposal import (
    Hypothesis2Experiment,
    HypothesisExperiment2Feedback,
    HypothesisGen,
    Trace,
)
from rdagent.core.scenario import Scenario
from rdagent.core.utils import import_class
from rdagent.log import rdagent_logger as logger
from rdagent.log.time import measure_time
from rdagent.scenarios.kaggle.kaggle_crawler import download_data
from rdagent.scenarios.kaggle.proposal.proposal import (
    KG_ACTION_FEATURE_ENGINEERING,
    KG_ACTION_FEATURE_PROCESSING,
)


class KaggleRDLoop(RDLoop):
    @measure_time
    def __init__(self, PROP_SETTING: BasePropSetting):
        with logger.tag("init"):
            scen: Scenario = import_class(PROP_SETTING.scen)(PROP_SETTING.competition)
            logger.log_object(scen, tag="scenario")

            self.hypothesis_gen: HypothesisGen = import_class(PROP_SETTING.hypothesis_gen)(scen)
            logger.log_object(self.hypothesis_gen, tag="hypothesis generator")

            self.hypothesis2experiment: Hypothesis2Experiment = import_class(PROP_SETTING.hypothesis2experiment)()
            logger.log_object(self.hypothesis2experiment, tag="hypothesis2experiment")

            self.feature_coder: Developer = import_class(PROP_SETTING.feature_coder)(scen)
            logger.log_object(self.feature_coder, tag="feature coder")
            self.model_coder: Developer = import_class(PROP_SETTING.model_coder)(scen)
            logger.log_object(self.model_coder, tag="model coder")

            self.feature_runner: Developer = import_class(PROP_SETTING.feature_runner)(scen)
            logger.log_object(self.feature_runner, tag="feature runner")
            self.model_runner: Developer = import_class(PROP_SETTING.model_runner)(scen)
            logger.log_object(self.model_runner, tag="model runner")

            self.summarizer: HypothesisExperiment2Feedback = import_class(PROP_SETTING.summarizer)(scen)
            logger.log_object(self.summarizer, tag="summarizer")
            self.trace = Trace(scen=scen)
            super(RDLoop, self).__init__()

    @measure_time
    def coding(self, prev_out: dict[str, Any]):
        with logger.tag("d"):  # develop
            if prev_out["propose"].action in [KG_ACTION_FEATURE_ENGINEERING, KG_ACTION_FEATURE_PROCESSING]:
                exp = self.feature_coder.develop(prev_out["exp_gen"])
            else:
                exp = self.model_coder.develop(prev_out["exp_gen"])
            logger.log_object(exp.sub_workspace_list, tag="coder result")
        return exp

    @measure_time
    def running(self, prev_out: dict[str, Any]):
        with logger.tag("ef"):  # evaluate and feedback
            if prev_out["propose"].action in [KG_ACTION_FEATURE_ENGINEERING, KG_ACTION_FEATURE_PROCESSING]:
                exp = self.feature_runner.develop(prev_out["coding"])
            else:
                exp = self.model_runner.develop(prev_out["coding"])
            logger.log_object(exp, tag="runner result")
        return exp

    skip_loop_error = (ModelEmptyError, FactorEmptyError)


def main(path=None, step_n=None, competition=None):
    """
    Auto R&D Evolving loop for models in a kaggle{} scenario.

    You can continue running session by

    .. code-block:: bash

        dotenv run -- python rdagent/app/kaggle/loop.py [--competition titanic] $LOG_PATH/__session__/1/0_propose  --step_n 1   # `step_n` is a optional parameter
        rdagent kaggle --competition playground-series-s4e8  # You are encouraged to use this one.

    """
    if competition:
        KAGGLE_IMPLEMENT_SETTING.competition = competition
        download_data(competition=competition, local_path=KAGGLE_IMPLEMENT_SETTING.local_data_path)
    else:
        logger.error("Please specify competition name.")

    if path is None:
        kaggle_loop = KaggleRDLoop(KAGGLE_IMPLEMENT_SETTING)
    else:
        kaggle_loop = KaggleRDLoop.load(path)
    kaggle_loop.run(step_n=step_n)


if __name__ == "__main__":
    fire.Fire(main)
