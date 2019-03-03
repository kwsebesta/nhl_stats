# ~/projects/nhl-stats/nhl-venv/bin/ python
"""scrape.py scrapes the nhl website to download stats"""
import time
import requests
import sqlcmds


def get_game_boxscore(team_id, game_id):
    """
    Retrive boxscore stats for a team and game id
    :param boxscore_stats: dictionary with boxscore stats
    :param goals_opp: opponent goals to calculate win
    """
    boxscore_url = (
        "https://statsapi.web.nhl.com/api/v1/game/" + str(game_id) + "/boxscore"
    )
    game_boxscore = requests.get(boxscore_url).json()
    # Check if team is in game
    if game_boxscore["teams"]["home"]["team"]["id"] == team_id:
        boxscore_stats = game_boxscore["teams"]["home"]["teamStats"]["teamSkaterStats"]
        boxscore_stats["venue"] = "home"
        goals_opp = game_boxscore["teams"]["away"]["teamStats"]["teamSkaterStats"][
            "goals"
        ]
    elif game_boxscore["teams"]["away"]["team"]["id"] == team_id:
        boxscore_stats = game_boxscore["teams"]["away"]["teamStats"]["teamSkaterStats"]
        boxscore_stats["venue"] = "away"
        goals_opp = game_boxscore["teams"]["home"]["teamStats"]["teamSkaterStats"][
            "goals"
        ]
    else:
        print("Error: Team not found in game")
    # Assign result
    if boxscore_stats["goals"] > goals_opp:
        boxscore_stats["result"] = "win"
    elif boxscore_stats["goals"] < goals_opp:
        boxscore_stats["result"] = "loss"
    else:  # a tie after overtime, goes to shootout
        # Check linescore for shootout information
        linescore_url = (
            "https://statsapi.web.nhl.com/api/v1/game/" + str(game_id) + "/linescore"
        )
        game_linescore = requests.get(linescore_url).json()
        if boxscore_stats["venue"] == "home":
            boxscore_stats["result"] = (
                "win"
                if game_linescore["shootoutInfo"]["home"]["scores"]
                > game_linescore["shootoutInfo"]["away"]["scores"]
                else "loss"
            )
        else:
            boxscore_stats["result"] = (
                "win"
                if game_linescore["shootoutInfo"]["away"]["scores"]
                > game_linescore["shootoutInfo"]["home"]["scores"]
                else "loss"
            )
    return boxscore_stats


def get_team_stats(team_name, team_id, season):
    """Retrieve team stats for date range"""

    # Load season games
    # Choose dates in yyyy-mm-dd
    start_date = str(season) + "-09-01"
    end_date = str(season + 1) + "-05-31"

    url = (
        "https://statsapi.web.nhl.com/api/v1/schedule?teamId="
        + str(team_id)
        + "&startDate="
        + start_date
        + "&endDate="
        + end_date
    )
    games = requests.get(url).json()
    # Get regular season games
    game_ids = [
        i["games"][0]["gamePk"]
        for i in games["dates"]
        if i["games"][0]["gamePk"] // 10 ** 4 % 10 == 2
    ]

    boxscore_stats = {}
    for game_id in game_ids:
        time.sleep(1)  # delay for 1 request/sec
        boxscore_stats[game_id] = get_game_boxscore(team_id=team_id, game_id=game_id)

    return boxscore_stats


def get_teams():
    """
    Retrieve NHL team names
    :param team_names: list of team names
    :param team_ids: list of team ids
    :return: team_names, team_ids
    """
    teams = requests.get("https://statsapi.web.nhl.com/api/v1/teams").json()
    team_names, team_ids = [], []
    # Search for specific teams
    for team in teams["teams"]:
        team_names.append(team["name"])
        team_ids.append(team["id"])
    return team_names, team_ids


def create_game(conn, game, team):
    """
    Create a new game into a teams record table if it doesn't exist
    :param conn: Connection object
    :param game: tuple of boxscore stats
    :param team: team name of interest
    :return: None  
    """
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM {0} WHERE id = (?)".format("[" + team + "]"), [game[1]])
    if cur.fetchone() is None:
        sql = """INSERT INTO {0}(season, id, venue, result, goals, pim, shots, powerPlayPercentage, 
                                powerPlayGoals, powerPlayOpportunities, 
                                faceOffWinPercentage, blocked, takeaways, 
                                giveaways, hits) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""".format(
            "[" + team + "]"
        )
        cur.execute(sql, game)
        conn.commit()
    else:
        print("Game ID ", game[1], "in database")
        return


def main():
    """Main function"""
    team_names, team_ids = get_teams()

    # Pick season, choose beginning year of season
    season = 2018

    conn = sqlcmds.create_connection("nhl-stats.sqlite3")

    # Insert team's season data into SQLite database
    for i, team_name in enumerate(team_names):
        season_stats = get_team_stats(team_name, team_ids[i], season)

        sql_create_team_table = """CREATE TABLE IF NOT EXISTS {0} (
                                        season int(4),
                                        id int(10), 
                                        venue char(4),
                                        result char, 
                                        goals int(2), 
                                        pim int(3), 
                                        shots int(3), 
                                        powerPlayPercentage float(3,1), 
                                        powerPlayGoals int(2), 
                                        powerPlayOpportunities int(2), 
                                        faceOffWinPercentage float(3,1), 
                                        blocked int(3), 
                                        takeaways int(3), 
                                        giveaways int(3), 
                                        hits int(3)
                                    );""".format(
            "[" + team_name + "]"
        )

        if conn is not None:
            # Create team table
            sqlcmds.create_table(conn, sql_create_team_table)
        else:
            print("Error! Cannot create database connection")

        # Insert season games into SQLite database
        n = 0
        for game in season_stats:
            n += 1
            create_game(
                conn,
                (
                    game // 10 ** 6,
                    game,
                    season_stats[game]["venue"],
                    season_stats[game]["result"],
                    season_stats[game]["goals"],
                    season_stats[game]["pim"],
                    season_stats[game]["shots"],
                    season_stats[game]["powerPlayPercentage"],
                    season_stats[game]["powerPlayGoals"],
                    season_stats[game]["powerPlayOpportunities"],
                    season_stats[game]["faceOffWinPercentage"],
                    season_stats[game]["blocked"],
                    season_stats[game]["takeaways"],
                    season_stats[game]["giveaways"],
                    season_stats[game]["hits"],
                ),
                team_name,
            )
            print(team_name, n)


if __name__ == "__main__":
    main()
