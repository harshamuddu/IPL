from itertools import count
import os

class Player:

    def __init__(self, name, batsmen_df, bowlers_df):
        self.name = name

        bat_srs = batsmen_df[batsmen_df["Name"] == name]
        bowl_srs = bowlers_df[bowlers_df["Name"] == name]

        self.batting_stats = bat_srs.to_dict()
        self.bowling_stats = bowl_srs.to_dict()

        for k, v in self.batting_stats.items():
            if v == {}:
                self.batting_stats[k] = 0
            else:
                self.batting_stats[k] = list(v.values())[0]

        for k, v in self.bowling_stats.items():
            if v == {}:
                self.bowling_stats[k] = 0
            else:
                self.bowling_stats[k] = list(v.values())[0]

class Team:

    def __init__(self, name, lineup, abbrev=None, captain=None, wk=None):
        self.name = name
        self.lineup = lineup
        self.abbrev = abbrev
        self.captain = captain
        self.wk = wk
        self.players = {}

        assert len(lineup) == 11

        if captain is not None:
            assert captain in lineup

        if wk is not None:
            assert wk in lineup


    def set_bowlers(self, cutoff=60):
        self.bowler_list = []
        for player in self.lineup:
            if self.players[player].bowling_stats["Balls Bowled"] >= cutoff:
                self.bowler_list.append(player)


    def generate_team(self, batsmen_df, bowlers_df):
        for player in self.lineup:
            self.players[player] = Player(player, batsmen_df, bowlers_df)

        self.set_bowlers()



class Match:

    _ids = count(1)

    template = {'match_id': 0,
                'inning': 0,
                'batting_team': None,
                'bowling_team': None,
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

    bowler_dismissals = ['bowled', 'caught', 'caught and bowled', 'lbw',
                         'stumped']
    valid_dismissals = bowler_dismissals + ["run out"]

    ball_choices = [0, 1, 2, 3, 4, 5, 6, "Out", "No Ball", "Wide", "Bye",
                    "Leg Bye"]

    separator = "-------------------------"

    def __init__(self, team_1, team_2):
        self.team_1 = team_1
        self.team_2 = team_2

        self.match_id = next(Match._ids)

        self.summary = {}
        self.summary[self.team_1] = {"Runs": 0,
                                     "Wickets": 0,
                                     "Balls": 0}
        self.summary[self.team_2] = {"Runs": 0,
                                     "Wickets": 0,
                                     "Balls": 0}

        self.scorecards = {}
        self.scorecards[self.team_1] = {"Bat":{}, "Bowl":{}}
        self.scorecards[self.team_2] = {"Bat":{}, "Bowl":{}}

        for i in range(11):
            self.scorecards[self.team_1]["Bat"][self.team_1.lineup[i]] = \
                {"Runs": 0, "Balls": 0, "Dismissal type": None}
            self.scorecards[self.team_2]["Bat"][self.team_2.lineup[i]] = \
                {"Runs": 0, "Balls": 0, "Dismissal type": None}

        for i in self.team_1.bowler_list:
            self.scorecards[self.team_1]["Bowl"][i] = \
                {"Balls": 0, "Dots": 0, "Runs": 0, "Wickets": 0}

        for i in self.team_2.bowler_list:
            self.scorecards[self.team_2]["Bowl"][i] = \
                {"Balls": 0, "Dots": 0, "Runs": 0, "Wickets": 0}


    def set_toss_result(self, bat_first, bat_second, statement):
        """

        :param bat_first: First batting team
        :param bat_second: Second batting team
        :param statement: declaration of who won the toss and what they chose to do
        """
        self.bat_first = bat_first
        self.bat_second = bat_second
        self.toss_statement = statement


    def print_lineups(team_1, team_2):
        """
        :param team_1: First batting team
        :param team_2: Second batting team
        :return: file_lines: list of sentences displaying lineup
        """

        file_lines = []
        file_lines.append(Match.separator)
        file_lines.append(f"{team_1.name} lineup:")
        file_lines.append(Match.separator)
        for player in team_1.lineup:
            pstr = player
            if player == team_1.captain:
                pstr += " (C)"
            if player == team_1.wk:
                pstr += " (wk)"
            file_lines.append(pstr)

        file_lines.append(Match.separator)
        file_lines.append(Match.separator)
        file_lines.append(f"{team_2.name} lineup:")
        file_lines.append(Match.separator)

        for player in team_2.lineup:
            pstr = player
            if player == team_2.captain:
                pstr += " (C)"
            if player == team_2.wk:
                pstr += " (wk)"

            file_lines.append(pstr)

        file_lines.append(Match.separator)

        return file_lines

    @staticmethod
    def write_deliveries(deliveries, bat_team, bowl_team, innings, target=None):
        assert innings == 1 or innings == 2
        if innings == 2:
            assert target is not None

        #print(list(filter(lambda x: x["inning"] == 2, deliveries))[0])
        second_innings_start = deliveries.index(list(filter(lambda x: x["inning"] == 2, deliveries))[0])

        if innings == 1:
            start = 0
            end = second_innings_start
        elif innings == 2:
            start = second_innings_start
            end = len(deliveries)

        file_lines = []
        bowl_order = []
        prev_ball_over = 1
        runs = 0
        wkts = 0

        if bat_team.abbrev is not None:
            name = bat_team.abbrev
        else:
            name = bat_team.name

        for i in range(start, end):
            delivery = deliveries[i]
            curr_over = delivery["over"]

            if curr_over != prev_ball_over:
                file_lines.append(f"{name}: {runs}/{wkts} after {prev_ball_over} ov")
                file_lines.append(Match.separator)
                if innings == 2:
                    file_lines.append(f"{name} need " +
                                      f"{target - runs} runs" +
                                      f" in {120 - (6 * prev_ball_over)} balls to win.")

            bowler = delivery["bowler"]
            if bowler not in bowl_order:
                bowl_order.append(bowler)

            runs += delivery["batsman_runs"] + delivery["extra_runs"]

            template = f"{delivery['over'] - 1}.{delivery['ball']}: " + \
                       f"{delivery['bowler']} to {delivery['batsman']}: "

            if delivery["player_dismissed"] is None:
                if delivery["noball_runs"] > 0:
                    template += "No Ball."
                elif delivery["wide_runs"] > 0:
                    template += "Wide."
                elif delivery["batsman_runs"] == 0:
                    template += "dot."
                elif delivery["batsman_runs"] == 1:
                    template += "1 run"
                else:
                    template += str(delivery["batsman_runs"]) + " runs."
            else:
                template += delivery["dismissal_kind"].upper() + "."
                wkts += 1

            file_lines.append(template)
            prev_ball_over = curr_over

        return file_lines, bowl_order


    def declare_result(self):

        file_lines = []

        if self.summary[self.bat_second]["Runs"] > self.summary[self.bat_first]["Runs"]:
            file_lines.append(f"{self.bat_second.name} win by " +
                                   f"{10 - self.summary[self.bat_second]['Wickets']} wickets.")
        elif self.summary[self.bat_second]["Runs"] == self.summary[self.bat_first]["Runs"]:
            file_lines.append("Match tied.")
        else:
            file_lines.append(f"{self.bat_first.name} win by " +
                f"{self.summary[self.bat_first]['Runs'] - self.summary[self.bat_second]['Runs']} runs.")

        return file_lines




    def print_bat_scorecard(self, team):
        file_lines = []
        file_lines.append(f"{team.name} Batting")
        file_lines.append(Match.separator)

        for player in team.lineup:

            scorecard = self.scorecards[team]["Bat"]

            template = "{:<25}".format(player) + "|"

            dismissal = scorecard[player]["Dismissal type"]

            if dismissal is None:

                template += (20 * " ") + "| " + str(scorecard[player]["Runs"])

                if scorecard[player]["Balls"] > 0:
                    template += "*"

            else:
                template += "{:<20}".format(dismissal) + "| " + str(scorecard[player]["Runs"])

            template += "(" + str(scorecard[player]["Balls"]) + ")"
            file_lines.append(template)

        file_lines.append(Match.separator)
        file_lines.append(Match.separator)
        file_lines.append(f"|{team.name}: " +
                               f"{self.summary[team]['Runs']} / " +
                               f"{self.summary[team]['Wickets']} | (" +
                               f"{self.summary[team]['Balls'] // 6}." +
                               f"{self.summary[team]['Balls'] % 6})")

        return file_lines


    def print_bowl_scorecard(self,team, bowl_order):

        file_lines = []

        file_lines.append(f"{team.name} Bowling")
        file_lines.append(Match.separator)

        for bowler in bowl_order:
            scorecard = self.scorecards[team]['Bowl'][bowler]
            file_lines.append("{:<25}".format(bowler) + "|" +
                                   f"{scorecard['Balls'] // 6}." +
                                   f"{scorecard['Balls'] % 6}  |" +
                                   "{:<5}".format(scorecard["Dots"]) + "|" +
                                   "{:<5}".format(scorecard["Runs"]) + "|" +
                                   "{:<5}".format(scorecard["Wickets"]))

        return file_lines


    def write_to_file(self, prefix, deliveries):

        filename = f"Match_{self.match_id}_{self.team_1.name}_vs_{self.team_2.name}.txt"
        i = 0
        while filename in os.listdir(prefix):
            i += 1
            filename = f"Match_{self.match_id + i}_{self.team_1.name}_vs_{self.team_2.name}.txt"

        filename = prefix + filename

        file_lines = [f"Welcome to Match {self.match_id}" +
                      f" between {self.team_1.name} and {self.team_2.name}."]

        file_lines.append(Match.separator)
        file_lines.append("First Innings:")
        file_lines.append(Match.separator)
        lines, bowl_1_order = Match.write_deliveries(deliveries, self.bat_first, self.bat_second, innings=1)
        file_lines.extend(lines)
        file_lines.append(Match.separator)
        file_lines.append(Match.separator)
        file_lines.append(f"At the end of the first innings, {self.bat_first.name} have made " +
                          f"{self.summary[self.bat_first]['Runs']} / " +
                          f"{self.summary[self.bat_first]['Wickets']} in " +
                          f"{self.summary[self.bat_first]['Balls'] // 6}." +
                          f"{self.summary[self.bat_first]['Balls'] % 6} overs.")

        file_lines.append(Match.separator)
        target = self.summary[self.bat_first]['Runs'] + 1
        file_lines.append(
            f"{self.bat_second.name} need to chase " +
            f"{target} in 20 overs to win this match.")

        file_lines.append("Second Innings:")
        file_lines.append(Match.separator)
        lines, bowl_2_order = Match.write_deliveries(deliveries, self.bat_second,
                                                     self.bat_first, innings=2, target=target)
        file_lines.extend(lines)
        file_lines.append(Match.separator)
        file_lines.append(Match.separator)
        file_lines.append(
            f"At the end of the second innings, {self.bat_second.name} have made " +
            f"{self.summary[self.bat_second]['Runs']} / " +
            f"{self.summary[self.bat_second]['Wickets']} in " +
            f"{self.summary[self.bat_second]['Balls'] // 6}." +
            f"{self.summary[self.bat_second]['Balls'] % 6} overs.")
        file_lines.append(Match.separator)
        file_lines.append(Match.separator)
        file_lines.extend(self.declare_result())
        file_lines.append(Match.separator)
        file_lines.append(Match.separator)

        file_lines.append("SCORECARD")
        file_lines.append(Match.separator)
        file_lines.append(Match.separator)
        file_lines.extend(self.print_bat_scorecard(self.bat_first))
        file_lines.append(Match.separator)
        file_lines.append(Match.separator)
        file_lines.extend(self.print_bowl_scorecard(self.bat_second, bowl_1_order))
        file_lines.append(Match.separator)
        file_lines.append(Match.separator)
        file_lines.extend(self.print_bat_scorecard(self.bat_second))
        file_lines.append(Match.separator)
        file_lines.append(Match.separator)
        file_lines.extend(self.print_bowl_scorecard(self.bat_first, bowl_2_order))
        file_lines.append(Match.separator)
        file_lines.append(Match.separator)

        with open(filename, 'w') as f:
            for line in file_lines:
                f.write(line)
                f.write("\n")

















