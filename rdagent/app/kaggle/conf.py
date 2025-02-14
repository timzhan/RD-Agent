from pathlib import Path

from pydantic_settings import BaseSettings

from rdagent.components.workflow.conf import BasePropSetting


class KaggleBasePropSetting(BasePropSetting):
    class Config:
        env_prefix = "KG_"
        """Use `KG_` as prefix for environment variables"""
        protected_namespaces = ()
        """Do not allow overriding of these namespaces"""

    # 1) overriding the default
    scen: str = "rdagent.scenarios.kaggle.experiment.scenario.KGScenario"
    """Scenario class for data mining model"""

    hypothesis_gen: str = "rdagent.scenarios.kaggle.proposal.proposal.KGHypothesisGen"
    """Hypothesis generation class"""

    hypothesis2experiment: str = "rdagent.scenarios.kaggle.proposal.proposal.KGHypothesis2Experiment"
    """Hypothesis to experiment class"""

    feature_coder: str = "rdagent.scenarios.kaggle.developer.coder.KGFactorCoSTEER"
    """Feature Coder class"""

    model_coder: str = "rdagent.scenarios.kaggle.developer.coder.KGModelCoSTEER"
    """Model Coder class"""

    feature_runner: str = "rdagent.scenarios.kaggle.developer.runner.KGFactorRunner"
    """Feature Runner class"""

    model_runner: str = "rdagent.scenarios.kaggle.developer.runner.KGModelRunner"
    """Model Runner class"""

    summarizer: str = "rdagent.scenarios.kaggle.developer.feedback.KGHypothesisExperiment2Feedback"
    """Summarizer class"""

    evolving_n: int = 10
    """Number of evolutions"""

    competition: str = ""

    local_data_path: str = "/data/userdata/share/kaggle"

    rag_path: str = "git_ignore_folder/rag"


KAGGLE_IMPLEMENT_SETTING = KaggleBasePropSetting()
