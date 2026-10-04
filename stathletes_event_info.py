import numpy as np
import pandas as pd

file_path = "data/raw/stathletes/bdc_2026/2025-10-11.Team.A.@.Team.D.Events.csv"


def load_events(file_path):
    return pd.read_csv(file_path)


def filter_passes(events):
    return events[events["Event"].isin(["Play", "Incomplete Play"])].copy()


def normalize_player_id(value):
    if pd.isna(value):
        return pd.NA

    value = str(value)

    if value.endswith(".0"):
        value = value.removesuffix(".0")

    return value


def build_pass_table(events):
    passes = filter_passes(events)

    pass_table = passes[
        [
            "Date",
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
            "Home_Team_Skaters",
            "Away_Team_Skaters",
            "Home_Team_Goals",
            "Away_Team_Goals",
        ]
    ].copy()

    pass_table = pass_table.rename(
        columns={
            "Player_Id": "passer_id",
            "Player_Id_2": "receiver_id",
            "X_Coordinate": "start_x",
            "Y_Coordinate": "start_y",
            "X_Coordinate_2": "end_x",
            "Y_Coordinate_2": "end_y",
            "Detail_1": "pass_type",
        }
    )

    pass_table["passer_id"] = pass_table["passer_id"].map(normalize_player_id)
    pass_table["receiver_id"] = pass_table["receiver_id"].map(normalize_player_id)

    pass_table["completed"] = pass_table["Event"].eq("Play")

    pass_table["pass_distance"] = np.hypot(
        pass_table["end_x"] - pass_table["start_x"],
        pass_table["end_y"] - pass_table["start_y"],
    )

    pass_table["strength_state"] = (
        pass_table["Home_Team_Skaters"].astype(str)
        + "v"
        + pass_table["Away_Team_Skaters"].astype(str)
    )

    pass_table["event_sequence"] = np.arange(len(pass_table))

    return pass_table


def build_edge_list(pass_table):
    completed = pass_table[pass_table["completed"]].copy()

    edges = (
        completed.groupby(
            ["Team", "passer_id", "receiver_id"],
            as_index=False,
        )
        .agg(
            pass_count=("completed", "size"),
            avg_pass_distance=("pass_distance", "mean"),
        )
        .sort_values(
            ["Team", "pass_count"],
            ascending=[True, False],
        )
    )

    return edges


def main():
    events = load_events(file_path)

    print("Events shape:", events.shape)

    pass_table = build_pass_table(events)

    print("\nPass table shape:", pass_table.shape)
    print(pass_table.head(20).to_string(index=False))

    print("\nCompletion counts:")
    print(pass_table["completed"].value_counts())

    print("\nPass-type counts:")
    print(pass_table["pass_type"].value_counts())

    print(
        pass_table[
            [
                "event_sequence",
                "Period",
                "Clock",
                "Team",
                "passer_id",
                "receiver_id",
                "pass_distance",
                "strength_state",
                "completed",
                "pass_type",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )

    edge_list = build_edge_list(pass_table)

    print("\nEdge list:")
    print(edge_list.head(30).to_string(index=False))


if __name__ == "__main__":
    main()
