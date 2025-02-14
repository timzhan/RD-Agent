import os

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder


def prepreprocess():
    """
    This method loads the data, drops the unnecessary columns, and splits it into train and validation sets.
    """
    # Load and preprocess the data
    data_df = pd.read_csv("/kaggle/input/train.csv")
    data_df = data_df.drop(["PassengerId"], axis=1)

    X = data_df.drop(["Transported"], axis=1)
    y = data_df[["Transported"]]

    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(y)  # Convert class labels to numeric

    # Split the data into training and validation sets
    X_train, X_valid, y_train, y_valid = train_test_split(X, y, test_size=0.10, random_state=42)

    return X_train, X_valid, y_train, y_valid


def preprocess_fit(X_train: pd.DataFrame):
    """
    Fits the preprocessor on the training data and returns the fitted preprocessor.
    """
    # Identify numerical and categorical features
    numerical_cols = [cname for cname in X_train.columns if X_train[cname].dtype in ["int64", "float64"]]
    categorical_cols = [cname for cname in X_train.columns if X_train[cname].dtype == "object"]

    # Define preprocessors for numerical and categorical features
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    numerical_transformer = Pipeline(steps=[("imputer", SimpleImputer(strategy="mean"))])

    # Combine preprocessing steps
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", categorical_transformer, categorical_cols),
            ("num", numerical_transformer, numerical_cols),
        ]
    )

    # Fit the preprocessor on the training data
    preprocessor.fit(X_train)

    return preprocessor


def preprocess_transform(X: pd.DataFrame, preprocessor):
    """
    Transforms the given DataFrame using the fitted preprocessor.
    Ensures the processed data has consistent features across train, validation, and test sets.
    """
    # Transform the data using the fitted preprocessor
    X_array = preprocessor.transform(X).toarray()

    # Get feature names for the columns in the transformed data
    categorical_cols = [cname for cname in X.columns if X[cname].dtype == "object"]
    feature_names = preprocessor.named_transformers_["cat"]["onehot"].get_feature_names_out(
        categorical_cols
    ).tolist() + [cname for cname in X.columns if X[cname].dtype in ["int64", "float64"]]

    # Convert arrays back to DataFrames
    X_transformed = pd.DataFrame(X_array, columns=feature_names, index=X.index)

    return X_transformed


def preprocess_script():
    """
    This method applies the preprocessing steps to the training, validation, and test datasets.
    """
    if os.path.exists("X_train.pkl"):
        X_train = pd.read_pickle("X_train.pkl")
        X_valid = pd.read_pickle("X_valid.pkl")
        y_train = pd.read_pickle("y_train.pkl")
        y_valid = pd.read_pickle("y_valid.pkl")
        X_test = pd.read_pickle("X_test.pkl")
        passenger_ids = pd.read_pickle("passenger_ids.pkl")

        return X_train, X_valid, y_train, y_valid, X_test, passenger_ids
    X_train, X_valid, y_train, y_valid = prepreprocess()

    # Fit the preprocessor on the training data
    preprocessor = preprocess_fit(X_train)

    # Preprocess the train, validation, and test data
    X_train = preprocess_transform(X_train, preprocessor)
    X_valid = preprocess_transform(X_valid, preprocessor)

    # Load and preprocess the test data
    submission_df = pd.read_csv("/kaggle/input/test.csv")
    passenger_ids = submission_df["PassengerId"]
    submission_df = submission_df.drop(["PassengerId"], axis=1)
    X_test = preprocess_transform(submission_df, preprocessor)

    return X_train, X_valid, y_train, y_valid, X_test, passenger_ids
