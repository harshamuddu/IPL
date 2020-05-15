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




    def reset_scorecards(self):
        self.bat_scorecard = {}
        self.bowl_scorecard = {}


        for player in self.lineup:
            self.bat_scorecard[player] = {"Runs": 0,
                                          "Balls": 0,
                                          "Dismissal type": None}


        for bowler in self.bowler_list:
            self.bowl_scorecard[bowler] = {"Balls": 0,
                                           "Dots": 0,
                                           "Runs": 0,
                                           "Wickets": 0}


