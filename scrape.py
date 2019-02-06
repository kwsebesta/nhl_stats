# ~/nhl-stats/nhl-venv/bin/ python
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
    game_url = "https://statsapi.web.nhl.com/api/v1/game/" + str(game_id) + "/boxscore"
    game_boxscore = requests.get(game_url).json()
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
    boxscore_stats["result"] = "win" if boxscore_stats["goals"] > goals_opp else "lose"
    return boxscore_stats


def get_team_stats(team_name):
    """Retrieve team stats for date range"""
    # Get teams
    teams = requests.get("https://statsapi.web.nhl.com/api/v1/teams").json()
    # Search for specific teams
    for team in teams["teams"]:
        if team["name"] == team_name:
            team_id = team["id"]
    # Load season games
    # Choose dates in yyyy-mm-dd
    start_date = "2016-09-01"
    end_date = "2017-05-31"
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
    team_name = "Chicago Blackhawks"
    season_stats = get_team_stats(team_name)

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

    # connect to database and create table
    conn = sqlcmds.create_connection("nhl-stats.sqlite3")
    if conn is not None:
        # Create team table
        sqlcmds.create_table(conn, sql_create_team_table)
    else:
        print("Error! Cannot create database connection")

    n = 0
    for game in season_stats:
        n += 1
        print(game)
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
    print(n)


if __name__ == "__main__":
    main()