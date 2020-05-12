import numpy as np
import pandas as pd
import os
import random
import copy
from abc import ABC, abstractmethod

team_2 = ["CH Gayle", "MA Agarwal", "V Kohli", "AB de Villiers", "LA Pomersbach",
       "SS Tiwary", "DL Vettori", "S Aravind", "A Mithun", "Z Khan",
       "J Syed Mohammad"]
team_1 = ["MEK Hussey", "M Vijay", "SK Raina", "S Badrinath", "WP Saha",
       "MS Dhoni", "DJ Bravo", "JA Morkel", "R Ashwin", "SB Jakati",
       "DE Bollinger"]

class AbstractSimulator(ABC):

    @abstractmethod
    def toss(self):
        pass

    def fixed_order(team, batsmen_thus_far):
        return team[len(batsmen_thus_far)]

    def random_pick(team, prev_bowler):

        bowler_list = copy.deepcopy(team.bowler_list)

        if prev_bowler in bowler_list:
            bowler_list.remove(prev_bowler)

        for bowler, stats in team.bowl_scorecard:
            if stats["Balls"] >= 24 and bowler in team.bowl_scorecard:
                bowler_list.remove(bowler)

        return np.random.choice(bowler_list)[0]



class SimplisticSimulator(AbstractSimulator):

    def __init__(self, team_1, team_2):
        self.team_1 = team_1
        self.team_2 = team_2

        self.bowler_dismissals = ['bowled', 'caught', 'caught and bowled', 'lbw', 'stumped']
        self.valid_dismissals = self.bowler_dismissals + ["run out"]

        self.ball_choices = [0, 1, 2, 3, 4, 5, 6, "Out", "No Ball", "Wide"]


    def toss(self, outcome=random.random()):
        if outcome < 0.25:
            toss_statement = f"{self.team_1.name} has won the toss and chosen to bat first."
            self.bat_first = self.team_1
            self.bat_second = self.team_2

        elif outcome < 0.5:
            toss_statement = f"{self.team_1.name} has won the toss and chosen to bowl first."
            self.bat_first = self.team_2
            self.bat_second = self.team_1

        elif outcome < 0.75:
            toss_statement = f"{self.team_2.name} has won the toss and chosen to bat first."
            self.bat_first = self.team_2
            self.bat_second = self.team_1

        else:
            toss_statement = f"{self.team_2.name} has won the toss and chosen to bowl first."
            self.bat_first = self.team_1
            self.bat_second = self.team_2


        return toss_statement


    def print_lineups(self):

        self.file_lines.append(f"{self.bat_first.name} lineup:")
        self.file_lines.append("-------------------------")
        for player in self.bat_first.lineup:
            pstr = player
            if player == self.bat_first.captain:
                pstr += " (C)"
            if player == self.bat_first.wk:
                pstr += " (wk)"


        self.file_lines.append(f"{self.bat_second.name} lineup:")
        self.file_lines.append("-------------------------")
        for player in self.bat_second.lineup:
            pstr = player
            if player == self.bat_second.captain:
                pstr += " (C)"
            if player == self.bat_second.wk:
                pstr += " (wk)"

        self.file_lines.append("-------------------------")


    def play_match(self, to_file=False, out_folder=None):
        toss_statement = self.toss()

        self.assign_probabilities(self.team_1, self.team_2.bowler_list)
        self.assign_probabilities(self.team_2, self.team_1.bowler_list)

        self.play_first_innings()
        self.play_second_innings()

        if to_file:
            assert out_folder is not None
            self.file_lines = [f"Welcome to Match {self.deliveries[0]['match_id']}" +
                               f" between {self.team_1.name} and {self.team_2.name}."]
            self.file_lines.append(toss_statement)
            self.print_lineups()
            self.write_to_file(out_folder)









    def assign_probabilities(self, team_1, team_2_bowlers, eps = 1e-9):


        # Tables have (batsmen, bowler) pairs as keys and probabilities as values
        for batsman_name in team_1.lineup:
            for bowler_name in team_2_bowlers:
                bat_srs = team_1.players[batsman_name].batting_stats
                bowl_srs = team_2.players[bowler_name].bowling_stats

                mat = np.zeros((10,))

                # P(dot ball) = P(batsman play defensive) or P(bowler bowls difficult ball) - overlap

                for i in range(7):
                    # Run probability
                    bat_prob = bat_srs[i] / bat_srs["Balls Faced"]
                    bowl_prob = bowl_srs[i] / bowl_srs["Balls Bowled"]
                    mat[i] = bat_prob + bowl_prob - (bat_prob * bowl_prob)


                bat_prob = bat_srs["Dismissals"] / bat_srs["Balls Faced"]
                bowl_prob = bowl_srs["Wickets"] / bowl_srs["Balls Bowled"]

                # Dismissal probability
                mat[7] = bat_prob + bowl_prob - (bat_prob * bowl_prob)

                # No Ball probability
                mat[8] = bowl_srs["No Balls"].values[0] / bowl_srs["Balls Bowled"].values[0]

                # Wide probability
                mat[9] = bowl_srs["Wides"].values[0] / bowl_srs["Balls Bowled"].values[0]

                # Correction in case missing data
                mat += eps

                # Normalization
                mat /= np.sum(mat)

                self.tables[(batsman_name, bowler_name)] = mat

                dmat = np.zeros((len(self.valid_dismissals),))

                for i, d in enumerate(self.valid_dismissals):
                    if d == "run out":
                        # Double because it relies on nonstriker's risk
                        dmat[i] = (bat_srs["run out"].values[0] / bat_srs["Dismissals"].values[0]) * 2
                    else:
                        bat_prob = bat_srs[d].values[0] / bat_srs["Dismissals"].values[0]
                        bowl_prob = bowl_srs[d].values[0] / bowl_srs["Wickets"].values[0]
                        dmat[i] = bat_prob + bowl_prob - (bat_prob * bowl_prob)

                # Correction zeros
                dmat += eps

                # Normalization
                dmat /= np.sum(dmat)

                self.dismissal_tables[(batsman_name, bowler_name)] = dmat



    def play_first_innings(self, next_bat=super().fixed_order, next_bowl=super().random_pick, id=1):
        # First Innings

        # Openers
        batsmen_thus_far = []
        striker = next_bat(self.bat_first, batsmen_thus_far)
        batsmen_thus_far.append(striker)
        non_striker = next_bat(self.bat_first, batsmen_thus_far)
        batsmen_thus_far.append(non_striker)

        self.summary_1 = {"Runs":0,
                          "Wickets":0,
                          "Balls":0}

        prev_bowler = None
        curr_bowler = None

        template = {'match_id':id,
                    'inning':1,
                    'batting_team':self.bat_first.name,
                    'bowling_team':self.bat_second.name,
                    'over':0,
                    'ball':0,
                    'batsman': None,
                    'non_striker': None,
                    'bowler': None,
                    'is_super_over': False,
                    'wide_runs': 0,
                    'bye_runs': 0,
                    'legbye_runs': 0,
                    'noball_runs': 0,
                    'penalty_runs': 0,
                    'batsman_runs': 0,
                    'extra_runs': 0,
                    'total_runs': 0,
                    'player_dismissed': None,
                    'dismissal_kind': None,
                    'fielder': None}

        self.deliveries = []


        while self.summary_1["Balls"] < 120 and self.summary_1["Wickets"] < 10:
            # Pre Over processing
            curr_bowler = next_bowl(self.bat_second, prev_bowler)
            legal_balls = 0

            delivery = copy.deepcopy(template)

            while legal_balls < 6 and self.summary_1["Wickets"] < 10:
                delivery["over"] = self.summary_1["Balls"] // 6
                delivery["ball"] = legal_balls + 1
                delivery["batsman"] = striker
                delivery["non_striker"] = non_striker
                delivery["bowler"] = curr_bowler

                ball = random.choices(np.arange(len(self.bowl_choices)), weights=self.tables[(striker, curr_bowler)])[0]
                if ball <= 6:
                    # Runs
                    legal_balls += 1
                    self.summary_1["Runs"] += ball
                    delivery["batsman_runs"] += ball


                    self.bat_first.bat_scorecard[striker]["Runs"] += ball
                    self.bat_first.bat_scorecard[striker]["Balls"] += 1
                    self.bat_second.bowl_scorecard[curr_bowler]["Runs"] += ball
                    self.bat_second.bowl_scorecard[curr_bowler]["Balls"] += 1

                    if ball == 0:
                        self.bat_second.bowl_scorecard[curr_bowler]["Dots"] += 1

                    if ball % 2 == 1:
                        striker, non_striker = non_striker, striker


                elif self.bowl_choices[ball] == "Out":
                    # OUT
                    legal_balls += 1
                    dismissal_type = random.choices(self.valid_dismissals, weights=self.dismissal_tables[(striker, curr_bowler)])[0]
                    delivery["player_dismissed"] = striker
                    delivery["dismissal_kind"] = dismissal_type

                    self.bat_first.bat_scorecard[striker]["Balls"] += 1
                    self.bat_first.bat_scorecard[striker]["Dismissal type"] = dismissal_type

                    self.bat_second.bowl_scorecard[curr_bowler]["Balls"] += 1
                    self.bat_second.bowl_scorecard[curr_bowler]["Dots"] += 1
                    if dismissal_type != "run out":
                        self.bat_second.bowl_scorecard[curr_bowler]["Wickets"] += 1

                    self.summary_1["Wickets"] += 1
                    if self.summary_1["Wickets"] < 10:
                        striker = next_bat(self.bat_first, batsmen_thus_far)
                        batsmen_thus_far.append(striker)
                    else:
                        break


                elif self.bowl_choices[ball] == "No Ball":
                    # No Ball
                    self.summary_1["Runs"] += 1
                    self.bat_second.bowl_scorecard[curr_bowler]["Runs"] += 1
                    delivery["noball_runs"] = 1
                    delivery["extra_runs"] = 1

                elif self.bowl_choices[ball] == "Wide":
                    # Wide
                    self.summary_1["Runs"] += 1
                    self.bat_second.bowl_scorecard[curr_bowler]["Runs"] += 1
                    delivery["wide_runs"] = 1
                    delivery["extra_runs"] = 1

                self.deliveries.append(delivery)

            # Post over processing
            striker, non_striker = non_striker, striker
            prev_bowler = curr_bowler
            curr_bowler = None
            self.summary_1["Balls"] += legal_balls

    def play_second_innings(self, next_bat=super().fixed_order, next_bowl=super().random_pick, id=1):
        # Second Innings
        target = self.summary_1["Runs"] + 1

        # Openers
        batsmen_thus_far = []
        striker = next_bat(self.bat_second, batsmen_thus_far)
        batsmen_thus_far.append(striker)
        non_striker = next_bat(self.bat_second, batsmen_thus_far)
        batsmen_thus_far.append(non_striker)

        self.summary_2 = {"Runs": 0,
                          "Wickets": 0,
                          "Balls": 0}

        prev_bowler = None
        curr_bowler = None

        template = {'match_id': id,
                    'inning': 2,
                    'batting_team': self.bat_second.name,
                    'bowling_team': self.bat_first.name,
                    'over': 0,
                    'ball': 0,
                    'batsman': None,
                    'non_striker': None,
                    'bowler': None,
                    'is_super_over': False,
                    'wide_runs': 0,
                    'bye_runs': 0,
                    'legbye_runs': 0,
                    'noball_runs': 0,
                    'penalty_runs': 0,
                    'batsman_runs': 0,
                    'extra_runs': 0,
                    'total_runs': 0,
                    'player_dismissed': None,
                    'dismissal_kind': None,
                    'fielder': None}

        while self.summary_2["Balls"] < 120 and self.summary_2["Wickets"] < 10 and self.summary_2["Runs"] < target:
            # Pre Over processing
            curr_bowler = next_bowl(self.bat_first, prev_bowler)
            legal_balls = 0

            delivery = copy.deepcopy(template)

            while legal_balls < 6 and self.summary_2["Wickets"] < 10 and self.summary_2["Runs"] < target:
                delivery["over"] = self.summary_2["Balls"] // 6
                delivery["ball"] = legal_balls + 1
                delivery["batsman"] = striker
                delivery["non_striker"] = non_striker
                delivery["bowler"] = curr_bowler

                ball = random.choices(np.arange(len(self.bowl_choices)),
                                      weights=self.tables[(striker, curr_bowler)])[0]
                if ball <= 6:
                    # Runs
                    legal_balls += 1
                    self.summary_2["Runs"] += ball
                    delivery["batsman_runs"] += ball

                    self.bat_second.bat_scorecard[striker]["Runs"] += ball
                    self.bat_second.bat_scorecard[striker]["Balls"] += 1
                    self.bat_first.bowl_scorecard[curr_bowler]["Runs"] += ball
                    self.bat_first.bowl_scorecard[curr_bowler]["Balls"] += 1

                    if ball == 0:
                        self.bat_first.bowl_scorecard[curr_bowler]["Dots"] += 1

                    if ball % 2 == 1:
                        striker, non_striker = non_striker, striker


                elif self.bowl_choices[ball] == "Out":
                    # OUT
                    legal_balls += 1
                    dismissal_type = random.choices(self.valid_dismissals,
                                                    weights=self.dismissal_tables[
                                                        (striker, curr_bowler)])[0]
                    delivery["player_dismissed"] = striker
                    delivery["dismissal_kind"] = dismissal_type

                    self.bat_second.bat_scorecard[striker]["Balls"] += 1
                    self.bat_second.bat_scorecard[striker][
                        "Dismissal type"] = dismissal_type

                    self.bat_first.bowl_scorecard[curr_bowler]["Balls"] += 1
                    self.bat_first.bowl_scorecard[curr_bowler]["Dots"] += 1
                    if dismissal_type != "run out":
                        self.bat_first.bowl_scorecard[curr_bowler]["Wickets"] += 1

                    self.summary_2["Wickets"] += 1
                    if self.summary_2["Wickets"] < 10:
                        striker = next_bat(self.bat_second, batsmen_thus_far)
                        batsmen_thus_far.append(striker)
                    else:
                        break


                elif self.bowl_choices[ball] == "No Ball":
                    # No Ball
                    self.summary_2["Runs"] += 1
                    self.bat_first.bowl_scorecard[curr_bowler]["Runs"] += 1
                    delivery["noball_runs"] = 1
                    delivery["extra_runs"] = 1

                elif self.bowl_choices[ball] == "Wide":
                    # Wide
                    self.summary_2["Runs"] += 1
                    self.bat_first.bowl_scorecard[curr_bowler]["Runs"] += 1
                    delivery["wide_runs"] = 1
                    delivery["extra_runs"] = 1


                self.deliveries.append(delivery)

            # Post over processing
            striker, non_striker = non_striker, striker
            prev_bowler = curr_bowler
            curr_bowler = None
            self.summary_2["Balls"] += legal_balls


    def write_to_file(self, prefix):
        id  = self.deliveries[0]["match_id"]

        filename = f"Match_{id}_{team_1.name}_vs_{team_2.name}Match_{id}.txt"
        i = 0
        while filename in os.listdir(prefix):
            i += 1

        filename = prefix + f"Match_{id + i}_{team_1.name}_vs_{team_2.name}Match_{id}.txt"

        self.file_lines.append("First Innings:")
        separator = "--------------"
        self.file_lines.append(separator)
        delivery = self.deliveries[0]
        i = 0
        runs = 0
        wkts = 0

        while delivery["innings"] == 1:
            i += 1
            runs += delivery["batsman_runs"] + delivery["extra_runs"]

            template = f"{delivery['over']}.{delivery['ball']}: " + \
                       f"{delivery['bowler']} to {delivery['batsman']}: "

            if delivery["player_dismissed"] is not None:
                if delivery["noball_runs"] > 0:
                    template += "No Ball."
                elif delivery["wide_runs"] > 0:
                    template += "Wide."
                elif delivery["batsman_runs"] == 0:
                    template += "dot."
                elif delivery["batsman_runs"] == 1:
                    template += "1 run"
                else:
                    template += delivery["batsman_runs"] + " runs."
            else:
                template += delivery["dismissal_kind"].upper() + "."
                wkts += 1

            self.file_lines.append(template)

            delivery = self.deliveries[i]

            if i % 6 == 0:
                if self.bat_first.abbrev is not None:
                    name = self.bat_first.abbrev
                else:
                    name = self.bat_first.name

                self.file_lines.append(f"{name}: {runs}/{wkts} after {i // 6} ov")
                self.file_lines.append(separator)

        self.file_lines.append(separator)
        self.file_lines.append(f"At the end of the first innings, {self.bat_first.name} have made " +
                               f"{self.bat_first.bat_scorecard['Runs']} / " +
                               f"{self.bat_first.bat_scorecard['Wickets']} in " +
                               f"{self.bat_first.bat_scorecard['Balls'] // 6}." +
                               f"{self.bat_first.bat_scorecard['Balls'] % 6} overs.")

        self.file_lines.append(separator)
        self.file_lines.append(f"{self.bat_second.name} need to chase {runs + 1} in 20 overs to win this match.")

        self.file_lines.append(separator)
        self.file_lines.append(separator)

        i_2 = 0
        runs = 0
        wkts = 0
        while delivery["innings"] == 2:
            i += 1
            i_2 += 1
            runs += delivery["batsman_runs"] + delivery["extra_runs"]

            template = f"{delivery['over']}.{delivery['ball']}: " + \
                       f"{delivery['bowler']} to {delivery['batsman']}: "

            if delivery["player_dismissed"] is not None:
                if delivery["noball_runs"] > 0:
                    template += "No Ball."
                elif delivery["wide_runs"] > 0:
                    template += "Wide."
                elif delivery["batsman_runs"] == 0:
                    template += "dot."
                elif delivery["batsman_runs"] == 1:
                    template += "1 run"
                else:
                    template += delivery["batsman_runs"] + " runs."
            else:
                template += delivery["dismissal_kind"].upper() + "."
                wkts += 1

            self.file_lines.append(template)

            delivery = self.deliveries[i]

            if i % 6 == 0:
                if self.bat_first.abbrev is not None:
                    name = self.bat_first.abbrev
                else:
                    name = self.bat_first.name

                self.file_lines.append(f"{name}: {runs}/{wkts} after {i_2 // 6} ov")
                self.file_lines.append(f"{name} need {self.bat_first.bat_scorecard['Runs'] + 1 - runs}" +
                                       f" in {20 - (i_2//6)}.")
                self.file_lines.append(separator)

        self.file_lines.append(separator)
        self.file_lines.append(f"At the end of the second innings, {self.bat_first.name} have made " +
                               f"{self.bat_second.bat_scorecard['Runs']} / " +
                               f"{self.bat_second.bat_scorecard['Wickets']} in " +
                               f"{self.bat_second.bat_scorecard['Balls'] // 6}." +
                               f"{self.bat_second.bat_scorecard['Balls'] % 6} overs.")

        self.file_lines.append(separator)
        self.file_lines.append(separator)

        if self.summary_2["Runs"] > self.summary_1["Runs"]:
            self.file_lines.append(f"{self.bat_second} win by {10 - self.summary_2['Wickets']} wickets.")
        elif self.summary_2["Runs"] == self.summary_1["Runs"]:
            self.file_lines.append("Match tied.")
        else:
            self.file_lines.append(f"{self.bat_first} win by " +
                                   f"{self.summary_1['Runs'] - self.summary_2['Runs']} runs.")

        self.file_lines.append(separator)
        self.file_lines.append(separator)

        self.file_lines.append("SCORECARD")
        self.file_lines.append(separator)
        self.print_bat_scorecard(self.bat_first)
        self.print_bowl_scorecard(self.bat_second)
        self.print_bat_scorecard(self.bat_second)
        self.print_bowl_scorecard(self.bat_first)

        with open(filename, 'w') as f:
            for line in self.file_lines:
                f.write(line)
                f.write("\n")

    def print_bat_scorecard(self, team):
        separator = "----------"
        self.file_lines.append(separator)
        self.file_lines.append(f"{self.bat_first.name} Batting")
        self.file_lines.append(separator)


        for player in self.bat_first.lineup:

            template = "{:<15}".format(player.name) + "|"

            dismissal = team.bat_scorecard[player]["Dismissal type"]


            if dismissal is None:

                template += (20 * " ") + "| " + str(team.bat_scorecard[player]["Runs"])

                if team.bat_scorecard[player]["Balls"] > 0:
                    template += "*"

            else:
                template += "{:<20}".format(dismissal) + "| " + \
                             str(team.bat_scorecard[player]["Runs"])

            template += "(" + str(team.bat_scorecard[player]["Balls"]) + ")"
            self.file_lines.append(template)

        self.file_lines.append(separator)
        self.file_lines.append(f"|{self.bat_first.name}" +
                               f"{self.bat_second.bat_scorecard['Runs']} / " +
                               f"{self.bat_second.bat_scorecard['Wickets']} | (" +
                               f"{self.bat_second.bat_scorecard['Balls'] // 6}." +
                               f"{self.bat_second.bat_scorecard['Balls'] % 6})")

        self.file_lines.append(separator)


    def print_bowl_scorecard(self, team):
        separator = "--------"

        self.file_lines.append(f"{team.name} Bowling")
        self.file_lines.append(separator)

        for bowler in team.bowl_scorecard.keys():
            self.file_lines.append("{:<15}".format(bowler.name) + "|" +
                              "{:<5}".format(team.bowl_scorecard[bowler]["Balls"]) +
                              f"{team.bowl_scorecard[bowler]['Balls'] // 6}." +
                              f"{team.bowl_scorecard[bowler]['Balls'] % 6}  |" +
                              "{:<5}".format(team.bowl_scorecard[bowler]["Dots"]) + "|" +
                              "{:<5}".format(team.bowl_scorecard[bowler]["Runs"]) + "|" +
                              "{:<5}".format(team.bowl_scorecard[bowler]["Wickets"]))

        self.file_lines.append(separator)
        self.file_lines.append(separator)














