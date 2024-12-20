# AUTOGENERATED! DO NOT EDIT! File to edit: ../../notebooks/coding_projects/P2_SVM/03svm_kernel_hpo.ipynb.

# %% auto 0
__all__ = ['fixed_meta_params', 'frozen_rvs', 'study_path', 'sqlite_url', 'study', 'SupportVectorClassifierConfig',
           'evaluate_svm', 'objective_svm', 'dict_to_dataclass', 'draw_probs']

# %% ../../notebooks/coding_projects/P2_SVM/03svm_kernel_hpo.ipynb 6
from scholarly_infrastructure.logging.nucleus import logger, print
from sklearn.datasets import load_digits, fetch_openml
from thu_big_data_ml.svm.infra import process_sklearn_dataset_dict, compute_classification_metrics
import plotly.io as pio
pio.renderers.default = "notebook"

# %% ../../notebooks/coding_projects/P2_SVM/03svm_kernel_hpo.ipynb 12
from scholarly_infrastructure.rv_args.nucleus import RandomVariable, experiment_setting
from optuna.distributions import IntDistribution, FloatDistribution, CategoricalDistribution
from typing import Optional, Union

# %% ../../notebooks/coding_projects/P2_SVM/03svm_kernel_hpo.ipynb 13
@experiment_setting
class SupportVectorClassifierConfig:
    # 惩罚系数 C
    C: float = ~RandomVariable(
        default=1.0,
        description="Regularization parameter. The strength of the regularization is inversely proportional to C.",
        distribution=FloatDistribution(1e-5, 1e2, log=True)
    )
    
    # 核函数类型
    kernel: str = ~RandomVariable(
        default="rbf",
        description="Kernel type to be used in the algorithm.",
        distribution=CategoricalDistribution(choices=["linear", "poly", "rbf", "sigmoid",
                                                      "precomputed"
                                                      ])
    )
    
    # 多项式核函数的度数
    degree: int = ~RandomVariable(
        default=3,
        description="Degree of the polynomial kernel function ('poly').",
        distribution=IntDistribution(1, 10, log=False)
    )
    
    # 核函数系数 gamma
    gamma: Union[str, float] = ~RandomVariable(
        default="scale",
        description="Kernel coefficient for 'rbf', 'poly' and 'sigmoid'.",
        distribution=CategoricalDistribution(choices=["scale", "auto"])  # 可以添加浮点数分布视需求
    )
    
    # 核函数独立项 coef0
    coef0: float = ~RandomVariable(
        default=0.0,
        description="Independent term in kernel function. It is significant in 'poly' and 'sigmoid'.",
        distribution=FloatDistribution(0, 1)
    )
    
    # 收缩启发式算法
    shrinking: bool = ~RandomVariable(
        default=True,
        description="Whether to use the shrinking heuristic.",
        distribution=CategoricalDistribution(choices=[True, False])
    )
    
    # 是否启用概率估计
    probability: bool = ~RandomVariable(
        default=False,
        description="Whether to enable probability estimates. Slows down fit when enabled.",
        distribution=CategoricalDistribution(choices=[True, False])
    )
    
    # 停止准则的容差 tol
    tol: float = ~RandomVariable(
        default=1e-3,
        description="Tolerance for stopping criterion.",
        distribution=FloatDistribution(1e-6, 1e-1, log=True)
    )
    
    # 内核缓存的大小（MB）
    cache_size: float = ~RandomVariable(
        default=200,
        description="Specify the size of the kernel cache (in MB).",
        distribution=FloatDistribution(50, 500, log=False)
    )
    
    # 类别权重 class_weight
    class_weight: Optional[Union[dict, str]] = ~RandomVariable(
        default=None,
        description="Set C of class i to class_weight[i]*C or use 'balanced' to adjust weights inversely to class frequencies.",
        distribution=CategoricalDistribution(choices=[None, "balanced"])
    )
    
    # 是否启用详细输出
    verbose: bool = ~RandomVariable(
        default=False,
        description="Enable verbose output (may not work properly in a multithreaded context).",
        distribution=CategoricalDistribution(choices=[True, False])
    )
    
    # 最大迭代次数
    max_iter: int = ~RandomVariable(
        default=-1,
        description="Hard limit on iterations within solver, or -1 for no limit.",
        distribution=IntDistribution(-1, 1000, log=False)
    )
    
    # 决策函数形状
    decision_function_shape: str = ~RandomVariable(
        default="ovr",
        description="Whether to return a one-vs-rest ('ovr') decision function or original one-vs-one ('ovo').",
        distribution=CategoricalDistribution(choices=["ovo", "ovr"])
    )
    
    # 是否打破决策函数平局
    break_ties: bool = ~RandomVariable(
        default=False,
        description="If True, break ties according to the confidence values of decision_function when decision_function_shape='ovr'.",
        distribution=CategoricalDistribution(choices=[True, False])
    )
    
    # 随机种子 random_state
    random_state: Optional[int] = ~RandomVariable(
        default=None,
        description="Controls random number generation for probability estimates. Ignored when probability=False.",
        distribution=IntDistribution(0, 100)  # 根据需求设置范围
    )

# %% ../../notebooks/coding_projects/P2_SVM/03svm_kernel_hpo.ipynb 15
from dataclasses import asdict

# %% ../../notebooks/coding_projects/P2_SVM/03svm_kernel_hpo.ipynb 17
import optuna
from sklearn.svm import SVC
from sklearn.model_selection import KFold

# %% ../../notebooks/coding_projects/P2_SVM/03svm_kernel_hpo.ipynb 18
def evaluate_svm(config:SupportVectorClassifierConfig, X_train, y_train,
                 trial:optuna.Trial = None, 
                 critical_metric="acc1_pred", num_of_repeated=5):
    # 使用k fold交叉验证，相当于做了5次独立实验。
    kf = KFold(n_splits=num_of_repeated, shuffle=True, random_state=config.random_state)
    
    
    result_dict = dict()

    metric_names = set()
    
    # 进行5折交叉验证
    for experiment_index, (train_index, test_index) in enumerate(kf.split(X_train)):
        # 分割训练集和测试集
        X_train_fold, X_test_fold = X_train[train_index], X_train[test_index]
        y_train_fold, y_test_fold = y_train[train_index], y_train[test_index]
        
        # 创建分类器实例
        model = SVC(**asdict(config))
        
        # 训练模型
        model.fit(X_train_fold, y_train_fold)
        
        # 预测测试集
        y_pred = model.predict(X_test_fold)
        
        # 计算准确率
        single_run_result = compute_classification_metrics(y_test_fold, y_pred=y_pred, labels=list(range(10)), y_pred_metrics_only=True)
        
        metric_names.update(single_run_result.keys())
        single_run_result = {f"{k}-run{experiment_index}":v for k, v in single_run_result.items()}
        result_dict|=single_run_result
        
        if trial is not None:
            for k, v in single_run_result.items():
                trial.set_user_attr(k, v)
            trial.report(single_run_result[f"{critical_metric}-run{experiment_index}"], experiment_index)
    for metric_name in metric_names:
        all_runs_results = [result_dict[f"{metric_name}-run{i}"] for i in range(num_of_repeated)]
        result_dict[f"{metric_name}-mean"] = sum(all_runs_results) / len(all_runs_results)
        if trial is not None:
            trial.set_user_attr(f"{metric_name}-mean", result_dict[f"{metric_name}-mean"])
    if trial is not None:
        trial.set_user_attr(f"num_of_repeated", num_of_repeated)
    return result_dict

# %% ../../notebooks/coding_projects/P2_SVM/03svm_kernel_hpo.ipynb 23
fixed_meta_params = SupportVectorClassifierConfig(
    probability = False, # 暂时不研究，只关注 acc1_pred
    # 与性能无关
    cache_size  = 200, 
    verbose = False,
    random_state = 42, # 今天我们根据 K Fold 来做重复实验，不根据随机种子来做重复实验
)
frozen_rvs = {"probability", "cache_size", "verbose", "random_state"}

# %% ../../notebooks/coding_projects/P2_SVM/03svm_kernel_hpo.ipynb 24
def objective_svm(trial:optuna.Trial, X_train_val, y_train_val, num_of_repeated=5, critical_metric="acc1_pred", critical_reduction="mean"):
    config:SupportVectorClassifierConfig = SupportVectorClassifierConfig.optuna_suggest(
        trial, fixed_meta_params, frozen_rvs=frozen_rvs)
    try:
        cross_val_results = evaluate_svm(config, X_train_val, y_train_val, 
                                        trial=trial,
                                        critical_metric=critical_metric, num_of_repeated=num_of_repeated)
        critical_metric_name = f"{critical_metric}-{critical_reduction}"
        critical_result = cross_val_results[critical_metric_name]
    except ValueError as e:
        # logger.exception(e)
        logger.warning(f"Trial {trial.number} failed with error: {e}, we consider this as a pruned trial since we believe such failure is due to the implicit constraints of the problem. ")
        raise optuna.exceptions.TrialPruned()
    return critical_result

# %% ../../notebooks/coding_projects/P2_SVM/03svm_kernel_hpo.ipynb 26
from ..help import runs_path

# %% ../../notebooks/coding_projects/P2_SVM/03svm_kernel_hpo.ipynb 27
study_path = runs_path / "optuna_studies.db"
sqlite_url = f"sqlite:///{study_path}"

# %% ../../notebooks/coding_projects/P2_SVM/03svm_kernel_hpo.ipynb 28
from optuna.samplers import *
from optuna.pruners import *
import json

# %% ../../notebooks/coding_projects/P2_SVM/03svm_kernel_hpo.ipynb 29
study = optuna.create_study(
    study_name="svm kernel hpo 11.17 3.0", 
    storage=sqlite_url, 
    load_if_exists=True, 
    sampler=QMCSampler(seed=42), # 谷歌建议
    pruner=WilcoxonPruner(), # 对重复实验进行假设检验剪枝
    direction="maximize")
study.set_user_attr("contributors", ["Ye Canming"])
study.set_user_attr("fixed_meta_parameters", json.dumps(asdict(fixed_meta_params)))

# %% ../../notebooks/coding_projects/P2_SVM/03svm_kernel_hpo.ipynb 78
import scikit_posthocs as sp
from scikit_posthocs import posthoc_dunn

# %% ../../notebooks/coding_projects/P2_SVM/03svm_kernel_hpo.ipynb 113
def dict_to_dataclass(dataclass_type, data_dict):
    converted_dict = {}
    for field in fields(dataclass_type):
        field_name = field.name
        field_type = field.type
        if field_name in data_dict:
            value = data_dict[field_name]
            # 处理 Union 类型
            if getattr(field_type, '__origin__', None) is Union:
                # 获取 Union 中的所有类型
                types = get_args(field_type)
                # 选择第一个非 NoneType 的类型
                non_none_types = [t for t in types if t is not type(None)]
                target_type = non_none_types[0] if non_none_types else None
                # print(target_type)
                if target_type not in [dict, list, tuple]: # TODO 递归处理
                    converted_dict[field_name] = target_type(value)
                else:
                    converted_dict[field_name] = value
            else:
                converted_dict[field_name] = field_type(value)
    return dataclass_type(**converted_dict)

# %% ../../notebooks/coding_projects/P2_SVM/03svm_kernel_hpo.ipynb 127
import seaborn as sns

# %% ../../notebooks/coding_projects/P2_SVM/03svm_kernel_hpo.ipynb 128
def draw_probs(y_pred_prob, y_test, interested_class:int):
    sns.scatterplot(y_pred_prob[y_test!=interested_class][:, interested_class], label=f"is not {interested_class}")
    sns.scatterplot(y_pred_prob[y_test==interested_class][:, interested_class], label=f"is {interested_class}", color="red")
