import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import random
import time
from game_tools import Team, Player
from simulators import SimplisticSimulator


deliveries_path_colab = "/content/drive/My Drive/deliveries.csv"
matches_path_colab = "/content/drive/My Drive/matches.csv"

deliveries_path_local = "data/deliveries.csv"
matches_path_local = "data/matches.csv"

prefix_colab = "/content/drive/My Drive/IPL Simulations/Simplistic Simulations/"
prefix_local = "output/"

colab = False

if colab:
    deliveries_path = deliveries_path_colab
    matches_path = matches_path_colab

    from google.colab import drive

    drive.mount('/content/drive')

    prefix = prefix_colab

else:
    deliveries_path = deliveries_path_local
    matches_path = matches_path_local
    prefix = prefix_local

# deliveries_df = pd.read_csv(deliveries_path)
# matches_df = pd.read_csv(matches_path)
#
#
# deliveries_df = deliveries_df.astype({"batsman_runs":"int32",
#                       "over":"int32",
#                       "ball":"int32",
#                       "bye_runs":"int32",
#                       "noball_runs":"int32",
#                       "wide_runs":"int32",
#                       "penalty_runs":"int32",
#                       "legbye_runs":"int32",
#                       "extra_runs":"int32",
#                       "total_runs":"int32"})
#
# batsmen_names = set(deliveries_df["batsman"]) # list of all batsmen
# batsmen_stats_dict = {}
#
# for batter in batsmen_names:
#     batter_data = deliveries_df[deliveries_df["batsman"] == batter]
#     innings = len(set(batter_data["match_id"]))
#
#     # Balls Faced = Total balls on strike - no balls - wide balls
#     balls_faced = len(batter_data) - len(batter_data[batter_data["noball_runs"] > 0]) - len(batter_data[batter_data["wide_runs"] > 0])
#     runs_scored = sum(batter_data["batsman_runs"])
#     dismissals = len(deliveries_df[deliveries_df["player_dismissed"] == batter])
#
#     run_distribution = batter_data["batsman_runs"].value_counts().to_dict()
#     dismissal_distribution = batter_data[batter_data["dismissal_kind"].notna()]["dismissal_kind"].value_counts().to_dict()
#
#     batsmen_stats_dict[batter] = {"Innings":innings,
#                                   "Runs": runs_scored,
#                                   "Balls Faced": balls_faced,
#                                   "Dismissals": dismissals,
#                                   "Run Distribution":run_distribution,
#                                   "Dismissal Distribution": dismissal_distribution}
#
#
# # In[7]:
#
#
# batsmen_df = pd.DataFrame(batsmen_stats_dict).T
# batsmen_df = pd.concat([batsmen_df.drop(["Run Distribution"], axis=1), batsmen_df["Run Distribution"].apply(pd.Series)], axis=1)
# batsmen_df = pd.concat([batsmen_df.drop(["Dismissal Distribution"], axis=1), batsmen_df["Dismissal Distribution"].apply(pd.Series)], axis=1)
# batsmen_df.fillna(0, inplace=True)
# batsmen_df = batsmen_df.astype(int)
#
# #Renaming
# batsmen_df.reset_index(inplace=True)
# colnames = batsmen_df.columns.values
# colnames[0] = "Name"
# batsmen_df.columns = colnames
# batsmen_df.reset_index(drop=True, inplace=True)
#
#
# # Additional Columns
# batsmen_df["Average"] = batsmen_df["Runs"] / batsmen_df["Dismissals"]
# batsmen_df["Strike Rate"] = 100 * batsmen_df["Runs"] / batsmen_df["Balls Faced"]
#
# dismissal_kinds = set(deliveries_df['dismissal_kind'])
# bowler_dismissals = ['bowled', 'caught', 'caught and bowled', 'lbw', 'stumped']
#
# # In[15]:
#
#
# bowler_names = list(set(deliveries_df['bowler']))
# bowler_stats_dict = {}
#
# for bowler in bowler_names:
#     bowler_data = deliveries_df[deliveries_df['bowler'] == bowler]
#
#     batter_data = deliveries_df[deliveries_df["batsman"] == bowler]
#     innings = set(batter_data["match_id"])
#     matches = set(bowler_data["match_id"])
#     matches = matches.union(innings)
#     matches = len(matches)
#
#     noballs = len(bowler_data[bowler_data["noball_runs"] > 0])
#     wides = len(bowler_data[bowler_data["wide_runs"] > 0])
#
#     # Total runs conceded = runs off bat + noballs + wides
#     runs_conceded = np.sum(bowler_data['batsman_runs']) + np.sum(
#         bowler_data['noball_runs']) + np.sum(bowler_data['wide_runs'])
#     # Num balls = balls bowled - no balls - wides
#     legal_balls_bowled = len(bowler_data) - noballs - wides
#
#     dismissal_distribution = bowler_data[bowler_data["dismissal_kind"].notna()][
#         "dismissal_kind"].value_counts().to_dict()
#     wickets_taken = 0
#     for bd in bowler_dismissals:
#         if bd in dismissal_distribution.keys():
#             wickets_taken += dismissal_distribution[bd]
#
#     run_distribution = bowler_data["batsman_runs"].value_counts().to_dict()
#
#     bowler_stats_dict[bowler] = {"Matches": matches,
#                                  "Wickets": wickets_taken,
#                                  "Balls Bowled": legal_balls_bowled,
#                                  "Runs Conceded": runs_conceded,
#                                  "Dismissal Distribution": dismissal_distribution,
#                                  "Run Distribution": run_distribution,
#                                  "No Balls": noballs,
#                                  "Wides": wides}
#
# # In[16]:
#
#
# bowlers_df = pd.DataFrame(bowler_stats_dict).T
# bowlers_df = pd.concat([bowlers_df.drop(["Dismissal Distribution"], axis=1),
#                         bowlers_df["Dismissal Distribution"].apply(pd.Series)],
#                        axis=1)
# bowlers_df = pd.concat([bowlers_df.drop(["Run Distribution"], axis=1),
#                         bowlers_df["Run Distribution"].apply(pd.Series)],
#                        axis=1)
# bowlers_df.fillna(0, inplace=True)
# bowlers_df = bowlers_df.astype(int)
#
# # Renaming
# bowlers_df.reset_index(inplace=True)
# colnames = bowlers_df.columns.values
# colnames[0] = "Name"
# bowlers_df.columns = colnames
# bowlers_df.reset_index(drop=True, inplace=True)
#
# # Additional Columns
# bowlers_df["Average"] = bowlers_df["Runs Conceded"] / bowlers_df["Wickets"]
# bowlers_df["Strike Rate"] = bowlers_df["Balls Bowled"] / bowlers_df["Wickets"]
# bowlers_df["Economy"] = 6 * bowlers_df["Runs Conceded"] / bowlers_df[
#     "Balls Bowled"]
#
# # Display settings
# # decimal display format
# pd.options.display.float_format = '{:.2f}'.format
# # Note the below four columns are being dropped
# bowlers_df = bowlers_df.drop(
#     ["retired hurt", "hit wicket", "obstructing the field", "run out"], axis=1)
#
# batsmen_df.to_pickle("batsmendf.pickle")
# bowlers_df.to_pickle("bowlersdf.pickle")

batsmen_df = pd.read_pickle("batsmendf.pickle")
bowlers_df = pd.read_pickle("bowlersdf.pickle")



rcb_lineup = ["CH Gayle", "MA Agarwal", "V Kohli", "AB de Villiers", "LA Pomersbach",
       "SS Tiwary", "DL Vettori", "S Aravind", "A Mithun", "Z Khan",
       "J Syed Mohammad"]
csk_lineup = ["MEK Hussey", "M Vijay", "SK Raina", "S Badrinath", "WP Saha",
       "MS Dhoni", "DJ Bravo", "JA Morkel", "R Ashwin", "SB Jakati",
       "DE Bollinger"]


rcb = Team("Royal Challengers Bangalore", rcb_lineup, abbrev="RCB", captain="DL Vettori", wk="AB de Villiers")
csk = Team("Chennai Super Kings", csk_lineup, abbrev="CSK", captain="MS Dhoni", wk="MS Dhoni")

rcb.generate_team(batsmen_df, bowlers_df)
csk.generate_team(batsmen_df, bowlers_df)

mi_lineup = ["SR Tendulkar",
             "AC Blizzard",
             "AT Rayudu",
             "RG Sharma",
             "JEC Franklin",
             "KA Pollard",
             "TL Suman",
             "DS Kulkarni",
             "Harbhajan Singh",
             "SL Malinga",
             "MM Patel"]

kkr_lineup = ["JH Kallis",
              "SP Goswami",
              "G Gambhir",
              "MK Tiwary",
              "YK Pathan",
              "RN ten Doeschate",
              "Shakib Al Hasan",
              "R Bhatia",
              "B Lee",
              "L Balaji",
              "Iqbal Abdulla"]


mi = Team("Mumbai Indians", mi_lineup, abbrev="MI", captain="SR Tendulkar", wk = "AT Rayudu")
kkr = Team("Kolkata Knight Riders", kkr_lineup, abbrev="KKR", captain="G Gambhir", wk="SP Goswami")
mi.generate_team(batsmen_df, bowlers_df)
kkr.generate_team(batsmen_df, bowlers_df)

ss1 = SimplisticSimulator(mi, kkr)
#ss1.play_match(to_file=True, out_folder=prefix)
ss1.play_matches(10, to_file=True, out_folder=prefix)

ss2 = SimplisticSimulator(mi, rcb)
ss2.play_matches(10, to_file=True, out_folder=prefix)

ss3 = SimplisticSimulator(mi, csk)
ss3.play_matches(10, to_file=True, out_folder=prefix)

ss4 = SimplisticSimulator(rcb, kkr)
ss4.play_matches(10, to_file=True, out_folder=prefix)

ss5 = SimplisticSimulator(csk, kkr)
ss5.play_matches(10, to_file=True, out_folder=prefix)

ss6 = SimplisticSimulator(rcb, csk)
ss6.play_matches(10, to_file=True, out_folder=prefix)