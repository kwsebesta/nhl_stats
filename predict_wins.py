# ~/nhl-stats/nhl-venv/bin/ python
"""predict_wins.py predict wins of an NHL team"""
import pandas as pd
import sqlalchemy
import sklearn
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn import model_selection


def main():
    """Main Function"""
    # Create sqlalchemy connection for pandas read_sql functions
    engine = sqlalchemy.create_engine("sqlite:///nhl-stats.sqlite3")
    conn = engine.connect()

    # Store table from database as pd.df
    bhawks_stats = pd.read_sql_table("Chicago Blackhawks", conn)

    feature_cols = [
        "venue",
        "goals",
        "powerPlayPercentage",
        "powerPlayGoals",
        "powerPlayOpportunities",
        "faceOffWinPercentage",
        "shots",
        "blocked",
        "takeaways",
        "giveaways",
        "hits",
    ]

    X = bhawks_stats[feature_cols]
    X["venue"] = X["venue"].map({"home": 1, "away": 0})  # integer encode venue

    y = bhawks_stats.result
    y = y.map({"win": 1, "loss": 0})  # map to binary for logistic regression

    kfold = model_selection.KFold(n_splits=10, random_state=0)
    model = LogisticRegression()
    results = model_selection.cross_val_score(model, X, y, cv=kfold)
    print("Accuracy: %.3f%% (%.3f%%)" % (results.mean() * 100.0, results.std() * 100.0))


if __name__ == "__main__":
    main()
