import numpy as np
import random
import copy
from abc import ABC, abstractmethod
from game_tools import Match


class AbstractSimulator(ABC):

	@staticmethod
	def fixed_order(team, batsmen_thus_far):
		return team.lineup[len(batsmen_thus_far)]

	@staticmethod
	def random_weighted_pick(match, team, prev_bowler, weight_col="Wickets"):

		bowler_list = copy.deepcopy(team.bowler_list)

		if prev_bowler in bowler_list:
			bowler_list.remove(prev_bowler)

		for bowler, stats in match.scorecards[team]["Bowl"].items():
			if stats["Balls"] >= 24 and bowler in bowler_list:
				bowler_list.remove(bowler)

		weighter = []
		for b in bowler_list:
			weighter.append(team.players[b].bowling_stats[weight_col] /
							team.players[b].bowling_stats["Matches"])

		if weight_col is not None:
			return random.choices(bowler_list, weights=weighter)[0]
		else:
			return random.choices(bowler_list)[0]



class SimplisticSimulator(AbstractSimulator):

	def __init__(self, team_1, team_2):
		self.team_1 = team_1
		self.team_2 = team_2

		self.deliveries = []




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





	def play_match(self, to_file=False, out_folder=None):
		self.match = Match(self.team_1, self.team_2)
		toss_statement = self.toss()

		self.table = {}
		self.dismissal_table = {}


		self.assign_probabilities(self.team_1, self.team_2)
		self.assign_probabilities(self.team_2, self.team_1)

		deliveries = self.play_innings(self.bat_first, self.bat_second)

		if to_file:
			assert out_folder is not None
			self.match.set_toss_result(self.bat_first, self.bat_second, toss_statement)
			self.match.write_to_file(out_folder, deliveries)






	def play_matches(self, n, to_file=False, out_folder=None):

		for i in range(n):
			self.play_match(to_file, out_folder)


	def assign_probabilities(self, team_1, team_2, eps = 1e-9):


		# Tables have (batsmen, bowler) pairs as keys and probabilities as values
		for batsman_name in team_1.lineup:
			for bowler_name in team_2.bowler_list:
				bat_srs = team_1.players[batsman_name].batting_stats
				bowl_srs = team_2.players[bowler_name].bowling_stats

				mat = np.zeros((len(Match.ball_choices),))

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
				mat[8] = bowl_srs["No Balls"] / bowl_srs["Balls Bowled"]

				# Wide probability
				mat[9] = bowl_srs["Wides"] / bowl_srs["Balls Bowled"]

				# Correction in case missing data
				mat += eps

				# Normalization
				mat /= np.sum(mat)

				self.table[(batsman_name, bowler_name)] = mat

				dmat = np.zeros((len(Match.valid_dismissals),))

				for i, d in enumerate(Match.valid_dismissals):
					if d == "run out":
						# Double because it relies on nonstriker's risk
						dmat[i] = (bat_srs["run out"] / bat_srs["Dismissals"]) * 2
					else:
						bat_prob = bat_srs[d] / bat_srs["Dismissals"]
						bowl_prob = bowl_srs[d] / bowl_srs["Wickets"]
						dmat[i] = bat_prob + bowl_prob - (bat_prob * bowl_prob)

				# Correction zeros
				dmat += eps

				# Normalization
				dmat /= np.sum(dmat)

				self.dismissal_table[(batsman_name, bowler_name)] = dmat


	def play_innings(self, bat_team, bowl_team, innings=1,
					 next_bat=AbstractSimulator.fixed_order,
					 next_bowl=AbstractSimulator.random_weighted_pick):

		if innings == 2:
			# Second Innings
			target = self.match.summary[bowl_team]["Runs"] + 1

		# Openers
		batsmen_thus_far = []
		striker = next_bat(bat_team, batsmen_thus_far)
		batsmen_thus_far.append(striker)
		non_striker = next_bat(bat_team, batsmen_thus_far)
		batsmen_thus_far.append(non_striker)

		prev_bowler = None
		curr_bowler = None

		deliveries = []

		while self.match.summary[bat_team]["Balls"] < 120 and self.match.summary[bat_team]["Wickets"] < 10:


			if innings == 2 and self.match.summary[bat_team]["Runs"] >= target:
				# Target chased
				break

			# Pre Over processing
			curr_bowler = next_bowl(self.match, bowl_team, prev_bowler)
			legal_balls = 0

			while legal_balls < 6 and self.match.summary[bat_team]["Wickets"] < 10:

				if innings == 2 and self.match.summary[bat_team]["Runs"] >= target:
					# Target chased
					break

				# Delivery detail setting
				delivery = copy.deepcopy(Match.template)
				delivery["over"] = (self.match.summary[bat_team]["Balls"] // 6) + 1
				delivery["ball"] = legal_balls + 1
				delivery["batsman"] = striker
				delivery["non_striker"] = non_striker
				delivery["bowler"] = curr_bowler
				delivery["batting_team"] = bat_team
				delivery["bowling_team"] = bowl_team
				delivery["match_id"] = self.match.match_id
				delivery["inning"] = innings

				ball = random.choices(np.arange(len(Match.ball_choices)),
									  weights=self.table[(striker, curr_bowler)])[0]
				if ball <= 6:
					# Runs
					legal_balls += 1
					self.match.summary[bat_team]["Runs"] += ball
					delivery["batsman_runs"] += ball

					self.match.scorecards[bat_team]["Bat"][striker]["Runs"] += ball
					self.match.scorecards[bat_team]["Bat"][striker]["Balls"] += 1
					self.match.scorecards[bowl_team]["Bowl"][curr_bowler]["Runs"] += ball
					self.match.scorecards[bowl_team]["Bowl"][curr_bowler]["Balls"] += 1

					if ball == 0:
						self.match.scorecards[bowl_team]["Bowl"][curr_bowler]["Dots"] += 1

					if ball % 2 == 1:
						striker, non_striker = non_striker, striker


				elif Match.ball_choices[ball] == "Out":
					# OUT
					legal_balls += 1
					dismissal_type = random.choices(Match.valid_dismissals,
													weights=self.dismissal_table[(striker, curr_bowler)])[0]
					delivery["player_dismissed"] = striker
					delivery["dismissal_kind"] = dismissal_type

					self.match.scorecards[bat_team]["Bat"][striker]["Balls"] += 1
					self.match.scorecards[bat_team]["Bat"][striker]["Dismissal type"] = dismissal_type

					self.match.scorecards[bowl_team]["Bowl"][curr_bowler]["Balls"] += 1
					self.match.scorecards[bowl_team]["Bowl"][curr_bowler]["Dots"] += 1
					if dismissal_type != "run out":
						self.match.scorecards[bowl_team]["Bowl"][curr_bowler]["Wickets"] += 1

					self.match.summary[bat_team]["Wickets"] += 1
					if self.match.summary[bat_team]["Wickets"] < 10:
						striker = next_bat(bat_team, batsmen_thus_far)
						batsmen_thus_far.append(striker)
					else:
						break


				elif Match.ball_choices[ball] == "No Ball":
					# No Ball
					self.match.summary[bat_team]["Runs"] += 1
					self.match.scorecards[bowl_team]["Bowl"][curr_bowler]["Runs"] += 1
					delivery["noball_runs"] = 1
					delivery["extra_runs"] = 1

				elif Match.ball_choices[ball] == "Wide":
					# Wide
					self.match.summary[bat_team]["Runs"] += 1
					self.match.scorecards[bowl_team]["Bowl"][curr_bowler]["Runs"] += 1
					delivery["wide_runs"] = 1
					delivery["extra_runs"] = 1


				deliveries.append(delivery)

			# Post over processing
			striker, non_striker = non_striker, striker
			prev_bowler = curr_bowler
			curr_bowler = None
			self.match.summary[bat_team]["Balls"] += legal_balls


		if innings == 1:
			# The deliveries from the second innings are getting appended to first innings deliveries
			deliveries.extend(self.play_innings(bowl_team, bat_team, innings=2))
			self.deliveries.extend(deliveries)

		return deliveries



	def get_deliveries(self):
		return self.deliveries




