import pandas as pd

file_path = "data/raw/stathletes/bdc_2026/2025-10-11.Team.A.@.Team.D.Events.csv"


def load_events(file_path):
    return pd.read_csv(file_path)


def filter_passes(events):
    return events[events["Event"].isin(["Play", "Incomplete Play"])].copy()


def main():
    events = load_events(file_path)
    print(events.shape)
    print(events.columns.tolist())
    print(events["Event"].value_counts(dropna=False))
    print(events.head())
    passes = filter_passes(events)
    print(passes.shape)
    print(
        passes[
            [
                "Period",
                "Clock",
                "Team",
                "Player_Id",
                "Player_Id_2",
                "X_Coordinate",
                "Y_Coordinate",
                "X_Coordinate_2",
                "Y_Coordinate_2",
                "Event",
                "Detail_1",
            ]
        ].head(20)
    )


if __name__ == "__main__":
    main()
